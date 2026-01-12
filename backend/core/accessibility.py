"""
Accessibility - PDF/UA compliance and accessibility checking.
"""
from typing import Optional
from api.models import (
    Presentation, AccessibilityIssue, AccessibilityIssueType,
    AccessibilitySeverity, AccessibilityReport, ElementType
)
from utils.contrast_checker import ContrastChecker, analyze_presentation_contrast


class AccessibilityChecker:
    """Comprehensive accessibility checker for presentations."""

    def __init__(self):
        self.contrast_checker = ContrastChecker()

    def check_presentation(self, presentation: Presentation) -> list[AccessibilityIssue]:
        """Run all accessibility checks on a presentation."""
        issues = []

        # Document-level checks
        issues.extend(self._check_document_level(presentation))

        # Slide-level checks
        for slide in presentation.slides:
            issues.extend(self._check_slide(slide, presentation))

        # Contrast checks
        contrast_issues = analyze_presentation_contrast(presentation, self.contrast_checker)
        issues.extend(contrast_issues)

        return issues

    def _check_document_level(self, presentation: Presentation) -> list[AccessibilityIssue]:
        """Check document-level accessibility requirements."""
        issues = []

        # Missing title
        if not presentation.title:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_TITLE,
                severity=AccessibilitySeverity.ERROR,
                slide_number=0,
                message="Document is missing a title",
                suggestion="Add a title in the presentation properties for screen reader navigation",
            ))

        # Missing language
        if not presentation.default_language:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_LANGUAGE,
                severity=AccessibilitySeverity.ERROR,
                slide_number=0,
                message="Document language is not specified",
                suggestion="Ensure text content is present for automatic language detection",
            ))

        return issues

    def _check_slide(self, slide, presentation: Presentation) -> list[AccessibilityIssue]:
        """Check slide-level accessibility requirements."""
        issues = []

        # Missing slide title
        if not slide.title:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.MISSING_TITLE,
                severity=AccessibilitySeverity.WARNING,
                slide_number=slide.slide_number,
                message=f"Slide {slide.slide_number} is missing a title",
                suggestion="Add a descriptive title to help screen reader users navigate",
            ))

        # Check each element
        for element in slide.elements:
            issues.extend(self._check_element(element, slide.slide_number))

        # Reading order check
        if not slide.reading_order_analyzed or slide.reading_order_confidence < 0.5:
            issues.append(AccessibilityIssue(
                issue_type=AccessibilityIssueType.READING_ORDER,
                severity=AccessibilitySeverity.WARNING,
                slide_number=slide.slide_number,
                message=f"Reading order for slide {slide.slide_number} may need review",
                suggestion="Verify the reading order matches logical content flow",
            ))

        return issues

    def _check_element(self, element, slide_number: int) -> list[AccessibilityIssue]:
        """Check element-level accessibility requirements."""
        issues = []

        # Image alt-text
        if element.element_type == ElementType.IMAGE:
            if not element.is_decorative and not element.alt_text:
                issues.append(AccessibilityIssue(
                    issue_type=AccessibilityIssueType.MISSING_ALT_TEXT,
                    severity=AccessibilitySeverity.ERROR,
                    slide_number=slide_number,
                    element_id=element.id,
                    message=f"Image is missing alternative text",
                    suggestion="Add descriptive alt-text or mark as decorative if purely visual",
                ))

        # Chart/graph accessibility
        if element.element_type == ElementType.CHART:
            if not element.chart_data or not element.chart_data.summary:
                issues.append(AccessibilityIssue(
                    issue_type=AccessibilityIssueType.MISSING_ALT_TEXT,
                    severity=AccessibilitySeverity.WARNING,
                    slide_number=slide_number,
                    element_id=element.id,
                    message="Chart is missing a text description",
                    suggestion="Add a summary describing the chart's key insights",
                ))

        # Small text check
        if element.paragraphs:
            for para in element.paragraphs:
                for run in para.runs:
                    if run.style.font_size and run.style.font_size < 12:
                        issues.append(AccessibilityIssue(
                            issue_type=AccessibilityIssueType.SMALL_TEXT,
                            severity=AccessibilitySeverity.INFO,
                            slide_number=slide_number,
                            element_id=element.id,
                            message=f"Text size ({run.style.font_size}pt) may be difficult to read",
                            suggestion="Consider using at least 12pt font for body text",
                            details={"font_size": run.style.font_size},
                        ))
                        break  # Only report once per element

        return issues

    def generate_report(
        self,
        presentation: Presentation,
        job_id: str,
    ) -> AccessibilityReport:
        """Generate a comprehensive accessibility report."""
        issues = self.check_presentation(presentation)

        # Count statistics
        total_images = 0
        images_with_alt = 0

        for slide in presentation.slides:
            for element in slide.elements:
                if element.element_type == ElementType.IMAGE:
                    total_images += 1
                    if element.alt_text or element.is_decorative:
                        images_with_alt += 1

        total_elements = sum(len(slide.elements) for slide in presentation.slides)

        # Calculate score
        score = self._calculate_score(presentation, issues)

        # Determine PDF/UA readiness
        error_count = sum(1 for i in issues if i.severity == AccessibilitySeverity.ERROR)
        pdf_ua_ready = error_count == 0

        return AccessibilityReport(
            job_id=job_id,
            total_slides=len(presentation.slides),
            total_elements=total_elements,
            total_images=total_images,
            images_with_alt_text=images_with_alt,
            issues=issues,
            score=score,
            pdf_ua_ready=pdf_ua_ready,
        )

    def _calculate_score(
        self,
        presentation: Presentation,
        issues: list[AccessibilityIssue],
    ) -> float:
        """Calculate accessibility score (0-100)."""
        # Weight different issue types
        error_weight = 10
        warning_weight = 3
        info_weight = 1

        # Start with perfect score
        score = 100.0

        for issue in issues:
            if issue.severity == AccessibilitySeverity.ERROR:
                score -= error_weight
            elif issue.severity == AccessibilitySeverity.WARNING:
                score -= warning_weight
            elif issue.severity == AccessibilitySeverity.INFO:
                score -= info_weight

        # Bonus for good practices
        if presentation.title:
            score += 2
        if presentation.default_language:
            score += 2

        # Check for all images having alt-text
        all_images_have_alt = True
        for slide in presentation.slides:
            for element in slide.elements:
                if element.element_type == ElementType.IMAGE:
                    if not element.alt_text and not element.is_decorative:
                        all_images_have_alt = False
                        break

        if all_images_have_alt:
            score += 5

        return max(0.0, min(100.0, round(score, 1)))


def get_pdf_ua_requirements() -> list[dict]:
    """Return PDF/UA-1 requirements checklist."""
    return [
        {
            "id": "7.1",
            "requirement": "Document title",
            "description": "The document must have a title in metadata",
            "critical": True,
        },
        {
            "id": "7.2",
            "requirement": "Document language",
            "description": "The document must specify its primary language",
            "critical": True,
        },
        {
            "id": "7.3",
            "requirement": "Tagged PDF",
            "description": "All content must be tagged with appropriate structure tags",
            "critical": True,
        },
        {
            "id": "7.4",
            "requirement": "Reading order",
            "description": "Content must have a logical reading order",
            "critical": True,
        },
        {
            "id": "7.5",
            "requirement": "Alternative text",
            "description": "All non-text content must have alternative text or be marked as decorative",
            "critical": True,
        },
        {
            "id": "7.6",
            "requirement": "Table structure",
            "description": "Tables must have proper header associations",
            "critical": True,
        },
        {
            "id": "7.7",
            "requirement": "Color contrast",
            "description": "Text must have sufficient contrast with background",
            "critical": False,
        },
        {
            "id": "7.8",
            "requirement": "Heading hierarchy",
            "description": "Headings must follow a logical hierarchy",
            "critical": False,
        },
    ]
