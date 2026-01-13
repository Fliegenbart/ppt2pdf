"""
Haupt-Pipeline für die Konvertierung.
"""

import logging
import tempfile
from pathlib import Path

from .analyzer import PPTXAnalyzer
from .config import Config
from .converter import PDFAccessibilityFixer
from .models import ConversionResult
from .modifier import PPTXAccessibilityEnhancer
from .validator import AccessibilityValidator

logger = logging.getLogger(__name__)


class AccessiblePDFPipeline:
    """
    Haupt-Pipeline für PPTX → Barrierefreies PDF.

    Schritte:
    1. PPTX analysieren (Bilder, Text, Struktur)
    2. Alt-Texte via Ollama generieren
    3. Alt-Texte in PPTX injizieren
    4. PDF via LibreOffice erstellen
    5. PDF-Metadaten optimieren
    6. Barrierefreiheit validieren
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

        # Komponenten
        self.analyzer = PPTXAnalyzer(self.config)
        self.enhancer = PPTXAccessibilityEnhancer(self.config)
        self.converter = PDFAccessibilityFixer(self.config)
        self.validator = AccessibilityValidator(self.config)

    def convert(
        self,
        input_pptx: str | Path,
        output_pdf: str | Path,
    ) -> ConversionResult:
        """
        Konvertiert PPTX zu barrierefreiem PDF.

        Args:
            input_pptx: Pfad zur PowerPoint-Datei
            output_pdf: Pfad für die PDF-Ausgabe

        Returns:
            ConversionResult mit Statistiken und Validierungsergebnissen
        """
        input_pptx = Path(input_pptx)
        output_pdf = Path(output_pdf)

        result = ConversionResult(
            success=False,
            input_path=str(input_pptx),
        )

        self._print_header(input_pptx, output_pdf)

        # Schritt 1: Analyse
        logger.info("📊 Schritt 1: PPTX analysieren...")
        try:
            analysis = self.analyzer.analyze(input_pptx)
            result.analysis = analysis
            result.steps.append(("Analyse", "✓"))

            logger.info(f"   {analysis.summary()}")

        except Exception as e:
            result.steps.append(("Analyse", f"✗ {e}"))
            result.error = str(e)
            logger.error(f"   ❌ Fehler: {e}")
            return result

        # Schritt 2: Alt-Texte injizieren
        logger.info("\n🖼️  Schritt 2: Alt-Texte in PPTX einfügen...")

        modified_pptx = input_pptx

        if analysis.images_alt_generated > 0:
            try:
                # Temporäre Datei für modifizierte PPTX
                with tempfile.NamedTemporaryFile(
                    suffix=".pptx", delete=False
                ) as tmp:
                    modified_pptx = Path(tmp.name)

                self.enhancer.enhance(input_pptx, analysis, modified_pptx)
                result.steps.append(("Alt-Text Injection", "✓"))
                logger.info(f"   ✓ {analysis.images_alt_generated} Alt-Texte eingefügt")

            except Exception as e:
                result.steps.append(("Alt-Text Injection", f"⚠️ {e}"))
                logger.warning(f"   ⚠️  Warnung: {e}")
                modified_pptx = input_pptx
        else:
            result.steps.append(("Alt-Text Injection", "übersprungen"))
            logger.info("   ⏭️  Übersprungen (keine neuen Alt-Texte)")

        # Schritt 3: PDF-Konvertierung
        logger.info("\n📑 Schritt 3: PDF erstellen via LibreOffice...")

        try:
            pdf_path = self.converter.convert_and_enhance(
                modified_pptx,
                output_pdf,
                analysis,
            )

            if pdf_path:
                result.output_path = str(pdf_path)
                result.steps.append(("PDF Konvertierung", "✓"))
                logger.info("   ✓ PDF erstellt")
            else:
                result.steps.append(("PDF Konvertierung", "✗"))
                result.error = "PDF-Konvertierung fehlgeschlagen"
                logger.error("   ❌ Konvertierung fehlgeschlagen")
                return result

        except Exception as e:
            result.steps.append(("PDF Konvertierung", f"✗ {e}"))
            result.error = str(e)
            logger.error(f"   ❌ Fehler: {e}")
            return result

        # Schritt 4: Validierung
        logger.info("\n✅ Schritt 4: Barrierefreiheit validieren...")

        try:
            validation = self.validator.validate(output_pdf)
            result.validation = validation
            result.steps.append(("Validierung", "✓"))

            logger.info(f"   Getaggt: {'✓' if validation.has_tags else '✗'}")
            logger.info(f"   Sprache: {'✓' if validation.has_language else '✗'}")
            logger.info(f"   Titel:   {'✓' if validation.has_title else '✗'}")

            if validation.warnings:
                logger.warning("\n   ⚠️  Warnungen:")
                for w in validation.warnings:
                    logger.warning(f"      - {w}")

        except Exception as e:
            result.steps.append(("Validierung", f"⚠️ {e}"))
            logger.warning(f"   ⚠️  Validierung fehlgeschlagen: {e}")

        # Aufräumen
        if modified_pptx != input_pptx and modified_pptx.exists():
            modified_pptx.unlink()

        # Ergebnis
        result.success = output_pdf.exists()
        self._print_summary(result)

        return result

    def _print_header(self, input_pptx: Path, output_pdf: Path):
        """Gibt Header aus."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📄 Accessible PPTX to PDF Converter")
        logger.info("=" * 60)
        logger.info(f"Input:  {input_pptx}")
        logger.info(f"Output: {output_pdf}")
        logger.info("=" * 60)
        logger.info("")

    def _print_summary(self, result: ConversionResult):
        """Gibt Zusammenfassung aus."""
        logger.info("")
        logger.info("=" * 60)

        if result.success and result.output_path:
            output_path = Path(result.output_path)
            size_kb = output_path.stat().st_size / 1024
            logger.info(f"✅ Erfolgreich: {result.output_path}")
            logger.info(f"   Dateigröße: {size_kb:.1f} KB")

            if result.validation:
                logger.info(f"   A11y Score: {result.validation.score}/4")
        else:
            logger.error("❌ Konvertierung fehlgeschlagen")
            if result.error:
                logger.error(f"   Fehler: {result.error}")

        logger.info("=" * 60)
        logger.info("")


def convert_pptx_to_accessible_pdf(
    input_pptx: str | Path,
    output_pdf: str | Path,
    config: Config | None = None,
) -> ConversionResult:
    """
    Convenience-Funktion für schnelle Konvertierung.

    Args:
        input_pptx: Pfad zur PowerPoint-Datei
        output_pdf: Pfad für die PDF-Ausgabe
        config: Optional - Konfiguration

    Returns:
        ConversionResult
    """
    pipeline = AccessiblePDFPipeline(config)
    return pipeline.convert(input_pptx, output_pdf)
