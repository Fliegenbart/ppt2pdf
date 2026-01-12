"""
Structure Builder - Creates accessible document structure from parsed presentation.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from api.models import (
    Presentation, Slide, SlideElement, ElementType,
    TextParagraph, TableData,
)


class StructureRole(str, Enum):
    """PDF structure roles for accessibility."""
    DOCUMENT = "Document"
    PART = "Part"
    SECT = "Sect"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H5 = "H5"
    H6 = "H6"
    P = "P"
    L = "L"  # List
    LI = "LI"  # List item
    LBL = "Lbl"  # Label (bullet)
    LBODY = "LBody"  # List body
    TABLE = "Table"
    TR = "TR"
    TH = "TH"
    TD = "TD"
    FIGURE = "Figure"
    CAPTION = "Caption"
    SPAN = "Span"
    LINK = "Link"
    NOTE = "Note"


@dataclass
class StructureNode:
    """A node in the document structure tree."""
    role: StructureRole
    content: Optional[str] = None
    alt_text: Optional[str] = None
    language: Optional[str] = None
    children: list["StructureNode"] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)

    # For images
    image_data: Optional[bytes] = None
    image_base64: Optional[str] = None

    # Layout info for PDF positioning
    bounds: Optional[dict] = None

    def add_child(self, node: "StructureNode") -> "StructureNode":
        """Add a child node and return it."""
        self.children.append(node)
        return node


class StructureBuilder:
    """Builds accessible document structure from presentation data."""

    def __init__(self):
        self.heading_levels = {1: StructureRole.H1, 2: StructureRole.H2, 3: StructureRole.H3,
                              4: StructureRole.H4, 5: StructureRole.H5, 6: StructureRole.H6}

    def build(self, presentation: Presentation) -> StructureNode:
        """Build the complete document structure tree."""
        # Create root document node
        root = StructureNode(
            role=StructureRole.DOCUMENT,
            language=presentation.default_language or "en",
            attributes={
                "title": presentation.title or presentation.filename,
                "author": presentation.author,
            }
        )

        # Build structure for each slide
        for slide in presentation.slides:
            slide_node = self._build_slide_structure(slide)
            root.add_child(slide_node)

        return root

    def _build_slide_structure(self, slide: Slide) -> StructureNode:
        """Build structure for a single slide."""
        # Each slide is a section
        section = StructureNode(
            role=StructureRole.SECT,
            attributes={"slide_number": slide.slide_number}
        )

        # Sort elements by reading order
        sorted_elements = sorted(slide.elements, key=lambda e: e.reading_order)

        # Process elements
        for element in sorted_elements:
            element_nodes = self._build_element_structure(element, slide)
            for node in element_nodes:
                section.add_child(node)

        # Add speaker notes if present
        if slide.speaker_notes:
            note_node = StructureNode(
                role=StructureRole.NOTE,
                content=slide.speaker_notes,
                language=slide.elements[0].language if slide.elements else None,
            )
            section.add_child(note_node)

        return section

    def _build_element_structure(self, element: SlideElement, slide: Slide) -> list[StructureNode]:
        """Build structure nodes for an element."""
        nodes = []

        if element.element_type == ElementType.TEXT:
            nodes.extend(self._build_text_structure(element))
        elif element.element_type == ElementType.IMAGE:
            node = self._build_image_structure(element)
            if node:
                nodes.append(node)
        elif element.element_type == ElementType.TABLE:
            node = self._build_table_structure(element)
            if node:
                nodes.append(node)
        elif element.element_type == ElementType.CHART:
            nodes.extend(self._build_chart_structure(element))

        return nodes

    def _build_text_structure(self, element: SlideElement) -> list[StructureNode]:
        """Build structure for text content."""
        nodes = []

        if not element.paragraphs:
            return nodes

        # Check if this is a heading
        if element.heading_level and element.heading_level in self.heading_levels:
            role = self.heading_levels[element.heading_level]
            content = self._extract_text(element.paragraphs)
            nodes.append(StructureNode(
                role=role,
                content=content,
                language=element.language,
                bounds=self._bounds_to_dict(element.bounds),
            ))
            return nodes

        # Check if this is a list
        if self._is_list(element.paragraphs):
            list_node = self._build_list_structure(element.paragraphs, element.language)
            list_node.bounds = self._bounds_to_dict(element.bounds)
            nodes.append(list_node)
            return nodes

        # Regular paragraphs
        for para in element.paragraphs:
            content = " ".join(run.text for run in para.runs)
            if content.strip():
                nodes.append(StructureNode(
                    role=StructureRole.P,
                    content=content,
                    language=element.language,
                    bounds=self._bounds_to_dict(element.bounds),
                ))

        return nodes

    def _build_list_structure(self, paragraphs: list[TextParagraph], language: Optional[str]) -> StructureNode:
        """Build structure for a list."""
        list_node = StructureNode(role=StructureRole.L, language=language)

        for para in paragraphs:
            content = " ".join(run.text for run in para.runs)
            if not content.strip():
                continue

            # List item
            li_node = StructureNode(role=StructureRole.LI)

            # Bullet label
            if para.bullet_char:
                li_node.add_child(StructureNode(
                    role=StructureRole.LBL,
                    content=para.bullet_char,
                ))

            # List body
            li_node.add_child(StructureNode(
                role=StructureRole.LBODY,
                content=content,
                language=language,
            ))

            list_node.add_child(li_node)

        return list_node

    def _build_image_structure(self, element: SlideElement) -> Optional[StructureNode]:
        """Build structure for an image."""
        # Skip decorative images in structure (they'll be marked as artifacts)
        if element.is_decorative:
            return None

        return StructureNode(
            role=StructureRole.FIGURE,
            alt_text=element.alt_text or "Image",
            image_base64=element.image_base64,
            bounds=self._bounds_to_dict(element.bounds),
            attributes={
                "content_type": element.content_type.value,
            }
        )

    def _build_table_structure(self, element: SlideElement) -> Optional[StructureNode]:
        """Build structure for a table."""
        if not element.table_data:
            return None

        table_node = StructureNode(
            role=StructureRole.TABLE,
            bounds=self._bounds_to_dict(element.bounds),
        )

        for row_idx, row in enumerate(element.table_data.rows):
            tr_node = StructureNode(role=StructureRole.TR)

            for col_idx, cell in enumerate(row):
                # Determine if this is a header cell
                is_header = (
                    (row_idx == 0 and element.table_data.has_header_row) or
                    (col_idx == 0 and element.table_data.has_header_column) or
                    cell.is_header
                )

                cell_role = StructureRole.TH if is_header else StructureRole.TD
                cell_node = StructureNode(
                    role=cell_role,
                    content=cell.text,
                    attributes={
                        "row_span": cell.row_span,
                        "col_span": cell.col_span,
                    }
                )
                tr_node.add_child(cell_node)

            table_node.add_child(tr_node)

        return table_node

    def _build_chart_structure(self, element: SlideElement) -> list[StructureNode]:
        """Build structure for a chart."""
        nodes = []

        # Chart as figure
        figure_node = StructureNode(
            role=StructureRole.FIGURE,
            alt_text=element.chart_data.summary if element.chart_data else "Chart",
            bounds=self._bounds_to_dict(element.bounds),
        )
        nodes.append(figure_node)

        # Add data table as accessible alternative
        if element.chart_data and element.chart_data.series:
            table_node = self._build_chart_data_table(element)
            if table_node:
                nodes.append(table_node)

        return nodes

    def _build_chart_data_table(self, element: SlideElement) -> Optional[StructureNode]:
        """Build an accessible data table from chart data."""
        chart_data = element.chart_data
        if not chart_data or not chart_data.series:
            return None

        table_node = StructureNode(role=StructureRole.TABLE)

        # Header row with categories
        header_row = StructureNode(role=StructureRole.TR)
        header_row.add_child(StructureNode(role=StructureRole.TH, content=""))
        for cat in chart_data.categories:
            header_row.add_child(StructureNode(role=StructureRole.TH, content=str(cat)))
        table_node.add_child(header_row)

        # Data rows
        for series in chart_data.series:
            data_row = StructureNode(role=StructureRole.TR)
            data_row.add_child(StructureNode(
                role=StructureRole.TH,
                content=series.get("name", ""),
            ))
            for value in series.get("values", []):
                data_row.add_child(StructureNode(
                    role=StructureRole.TD,
                    content=str(value) if value is not None else "",
                ))
            table_node.add_child(data_row)

        return table_node

    def _is_list(self, paragraphs: list[TextParagraph]) -> bool:
        """Check if paragraphs form a list."""
        if not paragraphs:
            return False
        return any(para.is_bullet or para.level > 0 for para in paragraphs)

    def _extract_text(self, paragraphs: list[TextParagraph]) -> str:
        """Extract plain text from paragraphs."""
        texts = []
        for para in paragraphs:
            para_text = " ".join(run.text for run in para.runs)
            if para_text.strip():
                texts.append(para_text)
        return " ".join(texts)

    def _bounds_to_dict(self, bounds) -> Optional[dict]:
        """Convert bounds to dictionary."""
        if bounds:
            return {
                "x": bounds.x,
                "y": bounds.y,
                "width": bounds.width,
                "height": bounds.height,
            }
        return None
