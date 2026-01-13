"""
Datenmodelle für die PPTX-Analyse.
"""

from dataclasses import dataclass, field


@dataclass
class SlideImage:
    """Repräsentiert ein Bild in einer Folie."""

    slide_index: int
    shape_index: int
    image_bytes: bytes
    current_alt_text: str = ""
    generated_alt_text: str | None = None
    content_type: str = "image/png"

    @property
    def has_alt_text(self) -> bool:
        """Prüft ob ein Alt-Text vorhanden ist."""
        return bool(self.current_alt_text or self.generated_alt_text)

    @property
    def effective_alt_text(self) -> str:
        """Gibt den zu verwendenden Alt-Text zurück."""
        return self.generated_alt_text or self.current_alt_text or ""


@dataclass
class SlideContent:
    """Repräsentiert den Inhalt einer Folie."""

    index: int
    title: str = ""
    text_content: list[str] = field(default_factory=list)
    images: list[SlideImage] = field(default_factory=list)
    has_table: bool = False
    has_chart: bool = False
    speaker_notes: str = ""

    @property
    def image_count(self) -> int:
        return len(self.images)

    @property
    def images_without_alt(self) -> list[SlideImage]:
        return [img for img in self.images if not img.has_alt_text]


@dataclass
class AnalysisResult:
    """Ergebnis der PPTX-Analyse."""

    slides: list[SlideContent]
    presentation_title: str = ""
    total_slides: int = 0
    images_total: int = 0
    images_without_alt: int = 0
    images_alt_generated: int = 0
    tables: int = 0
    charts: int = 0

    def summary(self) -> str:
        """Gibt eine Zusammenfassung als String zurück."""
        return (
            f"Folien: {self.total_slides}, "
            f"Bilder: {self.images_total} ({self.images_without_alt} ohne Alt-Text), "
            f"Tabellen: {self.tables}, Charts: {self.charts}"
        )


@dataclass
class ValidationResult:
    """Ergebnis der Barrierefreiheits-Validierung."""

    has_tags: bool = False
    has_language: bool = False
    has_title: bool = False
    display_doc_title: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Grundlegende Validierung bestanden?"""
        return self.has_tags and self.has_language and not self.errors

    @property
    def score(self) -> int:
        """Einfacher Score von 0-4."""
        return sum([
            self.has_tags,
            self.has_language,
            self.has_title,
            self.display_doc_title,
        ])


@dataclass
class ConversionResult:
    """Ergebnis der gesamten Konvertierung."""

    success: bool
    input_path: str
    output_path: str | None = None
    analysis: AnalysisResult | None = None
    validation: ValidationResult | None = None
    steps: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None
