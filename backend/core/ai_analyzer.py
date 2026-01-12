"""
AI Analyzer - Uses Claude for intelligent accessibility analysis.
"""
import os
import json
import asyncio
from typing import Optional
import anthropic
from langdetect import detect, LangDetectException

from api.models import (
    Presentation, Slide, SlideElement, ElementType, ContentType,
    AccessibilityIssue, AccessibilityIssueType, AccessibilitySeverity,
)


class AIAnalyzer:
    """Uses Claude AI for accessibility analysis and content generation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    async def analyze_presentation(
        self,
        presentation: Presentation,
        generate_alt_text: bool = True,
        analyze_reading_order: bool = True,
        detect_languages: bool = True,
    ) -> Presentation:
        """Analyze entire presentation with AI assistance."""

        for slide in presentation.slides:
            # Analyze reading order for the slide
            if analyze_reading_order:
                await self._analyze_reading_order(slide)

            # Generate alt-text for images
            if generate_alt_text:
                await self._generate_alt_texts(slide)

            # Detect languages
            if detect_languages:
                self._detect_languages(slide)

            # Analyze charts
            await self._analyze_charts(slide)

        # Detect default language
        if detect_languages:
            presentation.default_language = self._detect_presentation_language(presentation)

        presentation.analyzed = True
        return presentation

    async def _analyze_reading_order(self, slide: Slide):
        """Use AI to determine optimal reading order for slide elements."""
        if not slide.elements:
            return

        # Build context about element positions
        element_info = []
        for elem in slide.elements:
            info = {
                "id": elem.id,
                "type": elem.element_type.value,
                "position": {
                    "x": elem.bounds.x,
                    "y": elem.bounds.y,
                    "width": elem.bounds.width,
                    "height": elem.bounds.height,
                },
            }
            # Add text preview for context
            if elem.paragraphs:
                text_preview = " ".join(
                    run.text for para in elem.paragraphs[:2] for run in para.runs[:3]
                )[:100]
                info["text_preview"] = text_preview
            if elem.element_type == ElementType.IMAGE:
                info["content_type"] = elem.content_type.value
            element_info.append(info)

        prompt = f"""Analyze the following slide elements and determine the optimal reading order for accessibility.
Consider:
1. Logical flow of content (title first, then main content)
2. Visual layout (columns should read left-to-right within each row)
3. Relationships between elements (captions near images, labels near data)
4. Standard reading patterns (F-pattern, Z-pattern)

Slide title: {slide.title or 'Untitled'}
Layout: {slide.layout_name or 'Unknown'}

Elements:
{json.dumps(element_info, indent=2)}

Return a JSON object with:
- "reading_order": array of element IDs in optimal reading order
- "confidence": float 0-1 indicating confidence in the ordering
- "reasoning": brief explanation of the ordering logic

Return ONLY the JSON object, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)

            # Apply the reading order
            order_map = {elem_id: idx for idx, elem_id in enumerate(result.get("reading_order", []))}
            for elem in slide.elements:
                if elem.id in order_map:
                    elem.reading_order = order_map[elem.id]

            slide.reading_order_analyzed = True
            slide.reading_order_confidence = result.get("confidence", 0.5)

        except Exception as e:
            print(f"Error analyzing reading order: {e}")
            # Fall back to position-based order
            slide.reading_order_confidence = 0.3

    async def _generate_alt_texts(self, slide: Slide):
        """Generate alt-text for all images on the slide."""
        # Collect all text on the slide for context
        slide_context = self._extract_slide_context(slide)

        for elem in slide.elements:
            if elem.element_type == ElementType.IMAGE and elem.image_base64:
                # Skip if already has alt-text
                if elem.alt_text and not elem.alt_text_generated:
                    continue

                alt_text = await self._generate_single_alt_text(
                    elem, slide_context, slide.title
                )
                if alt_text:
                    elem.alt_text = alt_text
                    elem.alt_text_generated = True

    async def _generate_single_alt_text(
        self,
        element: SlideElement,
        slide_context: str,
        slide_title: Optional[str],
    ) -> Optional[str]:
        """Generate alt-text for a single image using Claude Vision."""

        prompt = f"""Analyze this image and generate appropriate alt-text for accessibility.

Context:
- Slide title: {slide_title or 'Unknown'}
- Surrounding text: {slide_context[:500] if slide_context else 'None'}

Guidelines:
1. Be concise but descriptive (typically 1-2 sentences)
2. Describe what's important in the context of the presentation
3. For charts/graphs: describe the data trend and key insights
4. For diagrams: describe the process or relationship shown
5. For photos: describe the subject and relevant details
6. For icons: describe the function/meaning, not appearance
7. For decorative images: respond with "DECORATIVE"

Respond with ONLY the alt-text, nothing else."""

        try:
            # Determine image media type
            media_type = "image/png"  # Default
            if element.image_base64:
                # Try to detect from magic bytes
                import base64
                img_bytes = base64.b64decode(element.image_base64[:100])
                if img_bytes.startswith(b'\xff\xd8'):
                    media_type = "image/jpeg"
                elif img_bytes.startswith(b'\x89PNG'):
                    media_type = "image/png"
                elif img_bytes.startswith(b'GIF'):
                    media_type = "image/gif"

            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": element.image_base64,
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            alt_text = response.content[0].text.strip()

            # Check if decorative
            if alt_text.upper() == "DECORATIVE":
                element.is_decorative = True
                element.content_type = ContentType.DECORATIVE
                return None

            # Classify content type based on alt-text
            element.content_type = self._classify_from_alt_text(alt_text)

            return alt_text

        except Exception as e:
            print(f"Error generating alt-text: {e}")
            return None

    async def _analyze_charts(self, slide: Slide):
        """Analyze charts and generate accessible descriptions."""
        for elem in slide.elements:
            if elem.element_type == ElementType.CHART and elem.chart_data:
                description = await self._generate_chart_description(elem)
                if description:
                    elem.chart_data.summary = description

    async def _generate_chart_description(self, element: SlideElement) -> Optional[str]:
        """Generate an accessible description for a chart."""
        chart_data = element.chart_data
        if not chart_data:
            return None

        prompt = f"""Generate an accessible text description for this chart.

Chart type: {chart_data.chart_type}
Title: {chart_data.title or 'Untitled'}
Categories: {chart_data.categories}
Data series: {json.dumps(chart_data.series)}

Provide a clear, concise description that:
1. States the chart type and what it shows
2. Highlights key trends or comparisons
3. Mentions notable data points (highest, lowest, outliers)
4. Is understandable without seeing the visual

Keep it to 2-4 sentences. Respond with ONLY the description."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Error generating chart description: {e}")
            return None

    def _detect_languages(self, slide: Slide):
        """Detect language for text elements."""
        for elem in slide.elements:
            if elem.paragraphs:
                text = " ".join(
                    run.text for para in elem.paragraphs for run in para.runs
                )
                if text.strip():
                    try:
                        elem.language = detect(text)
                    except LangDetectException:
                        elem.language = "en"  # Default to English

    def _detect_presentation_language(self, presentation: Presentation) -> str:
        """Detect the dominant language in the presentation."""
        language_counts = {}
        for slide in presentation.slides:
            for elem in slide.elements:
                if elem.language:
                    language_counts[elem.language] = language_counts.get(elem.language, 0) + 1

        if language_counts:
            return max(language_counts, key=language_counts.get)
        return "en"

    def _extract_slide_context(self, slide: Slide) -> str:
        """Extract all text from a slide for context."""
        texts = []
        if slide.title:
            texts.append(slide.title)
        for elem in slide.elements:
            if elem.paragraphs:
                for para in elem.paragraphs:
                    for run in para.runs:
                        texts.append(run.text)
        return " ".join(texts)

    def _classify_from_alt_text(self, alt_text: str) -> ContentType:
        """Classify content type based on generated alt-text."""
        lower = alt_text.lower()
        if any(word in lower for word in ['chart', 'graph', 'data', 'bar', 'pie', 'line']):
            return ContentType.CHART
        elif any(word in lower for word in ['diagram', 'flowchart', 'process', 'workflow']):
            return ContentType.DIAGRAM
        elif any(word in lower for word in ['icon', 'symbol', 'button']):
            return ContentType.ICON
        elif any(word in lower for word in ['logo', 'brand']):
            return ContentType.LOGO
        elif any(word in lower for word in ['screenshot', 'screen capture', 'interface']):
            return ContentType.SCREENSHOT
        elif any(word in lower for word in ['photo', 'photograph', 'picture', 'person', 'people']):
            return ContentType.PHOTO
        return ContentType.UNKNOWN

    def check_accessibility(self, presentation: Presentation) -> list[AccessibilityIssue]:
        """Check for accessibility issues in the presentation."""
        issues = []

        # Check presentation-level issues
        if not presentation.title:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_TITLE,
                severity=AccessibilitySeverity.ERROR,
                slide_number=0,
                message="Presentation is missing a title",
                suggestion="Add a title to the presentation properties",
            ))

        if not presentation.default_language:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_LANGUAGE,
                severity=AccessibilitySeverity.ERROR,
                slide_number=0,
                message="No language detected for presentation",
                suggestion="Ensure text content is present for language detection",
            ))

        # Check each slide
        for slide in presentation.slides:
            slide_issues = self._check_slide_accessibility(slide)
            issues.extend(slide_issues)

        presentation.accessibility_issues = issues
        return issues

    def _check_slide_accessibility(self, slide: Slide) -> list[AccessibilityIssue]:
        """Check accessibility issues on a single slide."""
        issues = []

        # Check for missing slide title
        if not slide.title:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_TITLE,
                severity=AccessibilitySeverity.WARNING,
                slide_number=slide.slide_number,
                message=f"Slide {slide.slide_number} is missing a title",
                suggestion="Add a descriptive title to help navigation",
            ))

        # Check elements
        for elem in slide.elements:
            # Check for missing alt-text on images
            if elem.element_type == ElementType.IMAGE:
                if not elem.is_decorative and not elem.alt_text:
                    issues.append(AccessibilityIssue(
                        issue_type=AccessibilityIssueType.MISSING_ALT_TEXT,
                        severity=AccessibilitySeverity.ERROR,
                        slide_number=slide.slide_number,
                        element_id=elem.id,
                        message=f"Image '{elem.id}' is missing alt-text",
                        suggestion="Add a descriptive alt-text or mark as decorative",
                    ))

            # Check for missing language tags
            if elem.paragraphs and not elem.language:
                issues.append(AccessibilityIssue(
                    issue_type=AccessibilityIssueType.MISSING_LANGUAGE,
                    severity=AccessibilitySeverity.INFO,
                    slide_number=slide.slide_number,
                    element_id=elem.id,
                    message=f"Element '{elem.id}' has no language tag",
                    suggestion="Language will be inferred from presentation default",
                ))

        return issues

    def calculate_accessibility_score(self, presentation: Presentation) -> float:
        """Calculate an accessibility score from 0-100."""
        if not presentation.slides:
            return 0.0

        total_checks = 0
        passed_checks = 0

        # Presentation-level checks
        total_checks += 2
        if presentation.title:
            passed_checks += 1
        if presentation.default_language:
            passed_checks += 1

        for slide in presentation.slides:
            # Slide title
            total_checks += 1
            if slide.title:
                passed_checks += 1

            for elem in slide.elements:
                # Image alt-text
                if elem.element_type == ElementType.IMAGE:
                    total_checks += 1
                    if elem.is_decorative or elem.alt_text:
                        passed_checks += 1

                # Language tags
                if elem.paragraphs:
                    total_checks += 1
                    if elem.language:
                        passed_checks += 1

        if total_checks == 0:
            return 100.0

        return round((passed_checks / total_checks) * 100, 1)
