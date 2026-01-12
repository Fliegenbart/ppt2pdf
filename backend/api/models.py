"""
Pydantic models for API requests and responses.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Types of elements that can appear on a slide."""
    TEXT = "text"
    IMAGE = "image"
    SHAPE = "shape"
    TABLE = "table"
    CHART = "chart"
    GROUP = "group"
    PLACEHOLDER = "placeholder"


class ContentType(str, Enum):
    """Classification of image/visual content for alt-text generation."""
    PHOTO = "photo"
    CHART = "chart"
    DIAGRAM = "diagram"
    ICON = "icon"
    DECORATIVE = "decorative"
    LOGO = "logo"
    SCREENSHOT = "screenshot"
    UNKNOWN = "unknown"


class AccessibilityIssueType(str, Enum):
    """Types of accessibility issues."""
    MISSING_ALT_TEXT = "missing_alt_text"
    LOW_CONTRAST = "low_contrast"
    SMALL_TEXT = "small_text"
    MISSING_TITLE = "missing_title"
    READING_ORDER = "reading_order"
    MISSING_LANGUAGE = "missing_language"


class AccessibilitySeverity(str, Enum):
    """Severity levels for accessibility issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BoundingBox(BaseModel):
    """Bounding box for element positioning."""
    x: float = Field(..., description="X coordinate (EMUs or pixels)")
    y: float = Field(..., description="Y coordinate (EMUs or pixels)")
    width: float = Field(..., description="Width (EMUs or pixels)")
    height: float = Field(..., description="Height (EMUs or pixels)")


class TextStyle(BaseModel):
    """Text styling information."""
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Optional[str] = None
    background_color: Optional[str] = None


class TextRun(BaseModel):
    """A run of text with consistent formatting."""
    text: str
    style: TextStyle = Field(default_factory=TextStyle)
    language: Optional[str] = None


class TextParagraph(BaseModel):
    """A paragraph containing text runs."""
    runs: list[TextRun] = Field(default_factory=list)
    level: int = Field(default=0, description="Indentation level (0-8)")
    is_bullet: bool = False
    bullet_char: Optional[str] = None


class TableCell(BaseModel):
    """A table cell."""
    text: str = ""
    row_span: int = 1
    col_span: int = 1
    is_header: bool = False
    style: TextStyle = Field(default_factory=TextStyle)


class TableData(BaseModel):
    """Table structure data."""
    rows: list[list[TableCell]] = Field(default_factory=list)
    has_header_row: bool = False
    has_header_column: bool = False


class ChartData(BaseModel):
    """Extracted chart data."""
    chart_type: str = "unknown"
    title: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    series: list[dict] = Field(default_factory=list)
    summary: Optional[str] = None


class SlideElement(BaseModel):
    """A single element on a slide."""
    id: str
    element_type: ElementType
    bounds: BoundingBox
    reading_order: int = Field(default=0, description="Order in which element should be read")

    # Text content
    paragraphs: list[TextParagraph] = Field(default_factory=list)

    # Image content
    image_data: Optional[bytes] = Field(default=None, exclude=True)
    image_base64: Optional[str] = None
    content_type: ContentType = ContentType.UNKNOWN
    alt_text: Optional[str] = None
    alt_text_generated: bool = False

    # Table content
    table_data: Optional[TableData] = None

    # Chart content
    chart_data: Optional[ChartData] = None

    # Accessibility
    is_decorative: bool = False
    language: Optional[str] = None

    # Hierarchy
    heading_level: Optional[int] = Field(default=None, ge=1, le=6)

    class Config:
        arbitrary_types_allowed = True


class AccessibilityIssue(BaseModel):
    """An accessibility issue found in the presentation."""
    issue_type: AccessibilityIssueType
    severity: AccessibilitySeverity
    slide_number: int
    element_id: Optional[str] = None
    message: str
    suggestion: Optional[str] = None
    details: Optional[dict] = None


class Slide(BaseModel):
    """A single slide with all its elements."""
    slide_number: int
    title: Optional[str] = None
    elements: list[SlideElement] = Field(default_factory=list)
    speaker_notes: Optional[str] = None
    background_color: Optional[str] = None
    layout_name: Optional[str] = None

    # AI-analyzed reading order
    reading_order_analyzed: bool = False
    reading_order_confidence: float = 0.0


class Presentation(BaseModel):
    """Complete presentation data."""
    filename: str
    title: Optional[str] = None
    author: Optional[str] = None
    slides: list[Slide] = Field(default_factory=list)
    default_language: Optional[str] = None

    # Analysis status
    analyzed: bool = False
    accessibility_issues: list[AccessibilityIssue] = Field(default_factory=list)


class ConversionJob(BaseModel):
    """Status of a conversion job."""
    job_id: str
    status: str = "pending"  # pending, parsing, analyzing, generating, complete, error
    progress: float = 0.0
    current_step: Optional[str] = None
    error_message: Optional[str] = None

    # Results
    presentation: Optional[Presentation] = None
    output_path: Optional[str] = None


class UploadResponse(BaseModel):
    """Response from file upload."""
    job_id: str
    filename: str
    message: str


class AnalysisRequest(BaseModel):
    """Request to analyze a presentation."""
    job_id: str
    generate_alt_text: bool = True
    analyze_reading_order: bool = True
    check_contrast: bool = True
    detect_languages: bool = True


class ConversionRequest(BaseModel):
    """Request to convert to PDF."""
    job_id: str
    include_speaker_notes: bool = False
    pdf_ua_compliant: bool = True


class ElementUpdate(BaseModel):
    """Update to a single element."""
    element_id: str
    slide_number: int
    alt_text: Optional[str] = None
    reading_order: Optional[int] = None
    is_decorative: Optional[bool] = None
    heading_level: Optional[int] = None


class UpdateRequest(BaseModel):
    """Request to update presentation elements."""
    job_id: str
    updates: list[ElementUpdate]


class AccessibilityReport(BaseModel):
    """Complete accessibility analysis report."""
    job_id: str
    total_slides: int
    total_elements: int
    total_images: int
    images_with_alt_text: int
    issues: list[AccessibilityIssue]
    score: float = Field(..., ge=0, le=100, description="Accessibility score 0-100")
    pdf_ua_ready: bool = False
