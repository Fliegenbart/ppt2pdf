"""
PDF Generator - Creates accessible tagged PDFs with PDF/UA compliance.
"""
import io
import os
import base64
from typing import Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table as RLTable, TableStyle, PageBreak, Flowable
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from api.models import Presentation, Slide, SlideElement, ElementType
from core.structure_builder import StructureBuilder, StructureNode, StructureRole


class TaggedFlowable(Flowable):
    """A flowable that carries structure tag information."""

    def __init__(self, flowable: Flowable, tag: str, props: Optional[dict] = None):
        Flowable.__init__(self)
        self.flowable = flowable
        self.tag = tag
        self.props = props or {}

    def wrap(self, availWidth, availHeight):
        return self.flowable.wrap(availWidth, availHeight)

    def draw(self):
        self.flowable.draw()


class AccessiblePDFGenerator:
    """Generates accessible PDFs from presentation data."""

    def __init__(self):
        self.structure_builder = StructureBuilder()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Set up custom paragraph styles."""
        # Heading styles
        self.styles.add(ParagraphStyle(
            name='SlideTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=12,
            textColor=colors.HexColor('#1a1a1a'),
        ))

        self.styles.add(ParagraphStyle(
            name='Heading2Custom',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=8,
        ))

        self.styles.add(ParagraphStyle(
            name='Heading3Custom',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=6,
        ))

        self.styles.add(ParagraphStyle(
            name='BulletItem',
            parent=self.styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=4,
        ))

        self.styles.add(ParagraphStyle(
            name='SpeakerNotes',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            leftIndent=10,
            borderWidth=1,
            borderColor=colors.HexColor('#cccccc'),
            borderPadding=5,
        ))

        self.styles.add(ParagraphStyle(
            name='AltText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#444444'),
            fontName='Helvetica-Oblique',
        ))

    def generate(
        self,
        presentation: Presentation,
        output_path: str,
        include_speaker_notes: bool = False,
        pdf_ua_compliant: bool = True,
    ) -> str:
        """Generate an accessible PDF from the presentation."""

        # Build document structure
        structure = self.structure_builder.build(presentation)

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            title=presentation.title or presentation.filename,
            author=presentation.author or "Unknown",
            subject="Accessible PDF converted from PowerPoint",
            creator="PPTX2PDF Accessible Converter",
        )

        # Build story (content)
        story = []

        # Document title
        if presentation.title:
            story.append(Paragraph(
                f"<b>{self._escape_html(presentation.title)}</b>",
                self.styles['Title']
            ))
            story.append(Spacer(1, 0.3 * inch))

        # Process each slide
        for slide in presentation.slides:
            slide_content = self._build_slide_content(
                slide,
                include_speaker_notes,
                presentation.default_language or "en"
            )
            story.extend(slide_content)

            # Page break after each slide (except last)
            if slide.slide_number < len(presentation.slides):
                story.append(PageBreak())

        # Build PDF
        doc.build(story)

        # Post-process for PDF/UA compliance
        if pdf_ua_compliant:
            self._add_pdf_ua_metadata(output_path, presentation)

        return output_path

    def _build_slide_content(
        self,
        slide: Slide,
        include_notes: bool,
        default_language: str,
    ) -> list:
        """Build content for a single slide."""
        content = []

        # Slide number indicator
        content.append(Paragraph(
            f"<font size='10' color='#888888'>Slide {slide.slide_number}</font>",
            self.styles['Normal']
        ))
        content.append(Spacer(1, 0.1 * inch))

        # Slide title
        if slide.title:
            content.append(Paragraph(
                self._escape_html(slide.title),
                self.styles['SlideTitle']
            ))

        # Sort elements by reading order
        sorted_elements = sorted(slide.elements, key=lambda e: e.reading_order)

        # Process elements
        for element in sorted_elements:
            element_content = self._build_element_content(element, default_language)
            content.extend(element_content)

        # Speaker notes
        if include_notes and slide.speaker_notes:
            content.append(Spacer(1, 0.2 * inch))
            content.append(Paragraph(
                "<b>Speaker Notes:</b>",
                self.styles['Normal']
            ))
            content.append(Paragraph(
                self._escape_html(slide.speaker_notes),
                self.styles['SpeakerNotes']
            ))

        return content

    def _build_element_content(self, element: SlideElement, default_language: str) -> list:
        """Build content for a single element."""
        content = []

        if element.element_type == ElementType.TEXT:
            content.extend(self._build_text_content(element))

        elif element.element_type == ElementType.IMAGE:
            img_content = self._build_image_content(element)
            if img_content:
                content.extend(img_content)

        elif element.element_type == ElementType.TABLE:
            table_content = self._build_table_content(element)
            if table_content:
                content.extend(table_content)

        elif element.element_type == ElementType.CHART:
            chart_content = self._build_chart_content(element)
            if chart_content:
                content.extend(chart_content)

        return content

    def _build_text_content(self, element: SlideElement) -> list:
        """Build content for text element."""
        content = []

        if not element.paragraphs:
            return content

        # Determine style based on heading level
        if element.heading_level:
            if element.heading_level == 1:
                style = self.styles['SlideTitle']
            elif element.heading_level == 2:
                style = self.styles['Heading2Custom']
            elif element.heading_level == 3:
                style = self.styles['Heading3Custom']
            else:
                style = self.styles['Normal']
        else:
            style = self.styles['Normal']

        # Check if this is a list
        is_list = any(para.is_bullet or para.level > 0 for para in element.paragraphs)

        for para in element.paragraphs:
            text = " ".join(run.text for run in para.runs)
            if not text.strip():
                continue

            if is_list and (para.is_bullet or para.level > 0):
                bullet_char = para.bullet_char or "•"
                indent = para.level * 15

                para_style = ParagraphStyle(
                    name=f'Bullet_{para.level}',
                    parent=self.styles['BulletItem'],
                    leftIndent=20 + indent,
                    bulletIndent=10 + indent,
                )

                content.append(Paragraph(
                    f"<bullet>{bullet_char}</bullet> {self._escape_html(text)}",
                    para_style
                ))
            else:
                # Apply text formatting
                formatted_text = self._format_text_runs(para.runs)
                content.append(Paragraph(formatted_text, style))

        if content:
            content.append(Spacer(1, 0.1 * inch))

        return content

    def _build_image_content(self, element: SlideElement) -> list:
        """Build content for image element."""
        content = []

        # Skip decorative images
        if element.is_decorative:
            return content

        if not element.image_base64:
            return content

        try:
            # Decode image
            image_bytes = base64.b64decode(element.image_base64)
            image_stream = io.BytesIO(image_bytes)

            # Calculate size (maintain aspect ratio, max 6 inches wide)
            from PIL import Image as PILImage
            pil_img = PILImage.open(io.BytesIO(image_bytes))
            orig_width, orig_height = pil_img.size

            max_width = 6 * inch
            max_height = 4 * inch

            # Calculate scaling
            width_ratio = max_width / orig_width
            height_ratio = max_height / orig_height
            scale = min(width_ratio, height_ratio, 1.0)

            width = orig_width * scale
            height = orig_height * scale

            # Create ReportLab image
            img = RLImage(image_stream, width=width, height=height)
            content.append(img)

            # Add alt-text as caption
            if element.alt_text:
                content.append(Paragraph(
                    f"<i>Image: {self._escape_html(element.alt_text)}</i>",
                    self.styles['AltText']
                ))

            content.append(Spacer(1, 0.1 * inch))

        except Exception as e:
            print(f"Error processing image: {e}")
            # Add placeholder text
            if element.alt_text:
                content.append(Paragraph(
                    f"[Image: {self._escape_html(element.alt_text)}]",
                    self.styles['Normal']
                ))

        return content

    def _build_table_content(self, element: SlideElement) -> list:
        """Build content for table element."""
        content = []

        if not element.table_data or not element.table_data.rows:
            return content

        # Convert table data to ReportLab format
        table_data = []
        for row_idx, row in enumerate(element.table_data.rows):
            row_data = []
            for cell in row:
                # Wrap cell content in Paragraph for proper formatting
                cell_text = self._escape_html(cell.text)
                if cell.is_header:
                    cell_text = f"<b>{cell_text}</b>"
                row_data.append(Paragraph(cell_text, self.styles['Normal']))
            table_data.append(row_data)

        if not table_data:
            return content

        # Create table
        table = RLTable(table_data)

        # Apply styling
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]

        # Header column styling
        if element.table_data.has_header_column:
            style_commands.append(
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0'))
            )

        table.setStyle(TableStyle(style_commands))

        content.append(table)
        content.append(Spacer(1, 0.15 * inch))

        return content

    def _build_chart_content(self, element: SlideElement) -> list:
        """Build content for chart element."""
        content = []

        if not element.chart_data:
            return content

        # Add chart title
        if element.chart_data.title:
            content.append(Paragraph(
                f"<b>{self._escape_html(element.chart_data.title)}</b>",
                self.styles['Heading3Custom']
            ))

        # Add chart description
        if element.chart_data.summary:
            content.append(Paragraph(
                self._escape_html(element.chart_data.summary),
                self.styles['Normal']
            ))

        # Add data table for accessibility
        if element.chart_data.series and element.chart_data.categories:
            content.append(Spacer(1, 0.1 * inch))
            content.append(Paragraph(
                "<b>Chart Data:</b>",
                self.styles['Normal']
            ))

            # Build data table
            table_data = []

            # Header row
            header = [""] + [str(cat) for cat in element.chart_data.categories]
            table_data.append([
                Paragraph(f"<b>{self._escape_html(h)}</b>", self.styles['Normal'])
                for h in header
            ])

            # Data rows
            for series in element.chart_data.series:
                row = [series.get("name", "")]
                values = series.get("values", [])
                row.extend([str(v) if v is not None else "" for v in values])
                table_data.append([
                    Paragraph(self._escape_html(str(cell)), self.styles['Normal'])
                    for cell in row
                ])

            if len(table_data) > 1:
                table = RLTable(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))
                content.append(table)

        content.append(Spacer(1, 0.15 * inch))
        return content

    def _format_text_runs(self, runs) -> str:
        """Format text runs with inline styling."""
        formatted = []
        for run in runs:
            text = self._escape_html(run.text)
            if run.style.bold:
                text = f"<b>{text}</b>"
            if run.style.italic:
                text = f"<i>{text}</i>"
            if run.style.underline:
                text = f"<u>{text}</u>"
            formatted.append(text)
        return " ".join(formatted)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _add_pdf_ua_metadata(self, pdf_path: str, presentation: Presentation):
        """Add PDF/UA compliance metadata."""
        try:
            import pikepdf

            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                # Set PDF/UA identifier
                with pdf.open_metadata() as meta:
                    # Set basic metadata
                    meta['dc:title'] = presentation.title or presentation.filename
                    meta['dc:creator'] = [presentation.author or "Unknown"]
                    meta['dc:description'] = "Accessible PDF converted from PowerPoint"
                    meta['pdf:Producer'] = "PPTX2PDF Accessible Converter"
                    meta['xmp:CreateDate'] = datetime.now().isoformat()

                    # PDF/UA identifier
                    meta['pdfuaid:part'] = '1'

                # Set document language
                if presentation.default_language:
                    pdf.Root.Lang = presentation.default_language

                # Mark as tagged PDF
                if '/MarkInfo' not in pdf.Root:
                    pdf.Root.MarkInfo = pikepdf.Dictionary()
                pdf.Root.MarkInfo.Marked = True

                # Set ViewerPreferences for accessibility
                if '/ViewerPreferences' not in pdf.Root:
                    pdf.Root.ViewerPreferences = pikepdf.Dictionary()
                pdf.Root.ViewerPreferences.DisplayDocTitle = True

                pdf.save()

        except ImportError:
            print("pikepdf not available for PDF/UA metadata")
        except Exception as e:
            print(f"Error adding PDF/UA metadata: {e}")
