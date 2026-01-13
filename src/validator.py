"""
Barrierefreiheits-Validierung für PDFs.
"""

import logging
from pathlib import Path

from .config import Config
from .models import ValidationResult

logger = logging.getLogger(__name__)


class AccessibilityValidator:
    """Validiert PDF-Barrierefreiheit."""

    def __init__(self, config: Config):
        self.config = config

    def validate(self, pdf_path: str | Path) -> ValidationResult:
        """
        Führt Barrierefreiheits-Checks durch.

        Args:
            pdf_path: Pfad zur PDF

        Returns:
            ValidationResult mit Ergebnissen
        """
        result = ValidationResult()
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            result.errors.append(f"PDF nicht gefunden: {pdf_path}")
            return result

        try:
            import pikepdf
        except ImportError:
            result.errors.append("pikepdf nicht installiert für Validierung")
            return result

        try:
            with pikepdf.open(pdf_path) as pdf:
                # Check 1: Tagged PDF?
                result.has_tags = self._check_tags(pdf)

                # Check 2: Sprache gesetzt?
                result.has_language = self._check_language(pdf)

                # Check 3: Titel vorhanden?
                result.has_title = self._check_title(pdf)

                # Check 4: DisplayDocTitle?
                result.display_doc_title = self._check_display_title(pdf)

                # Warnungen generieren
                self._generate_warnings(result)

        except Exception as e:
            result.errors.append(f"Validierungsfehler: {e}")

        return result

    def _check_tags(self, pdf) -> bool:
        """Prüft ob PDF getaggt ist."""
        if "/MarkInfo" in pdf.Root:
            mark_info = pdf.Root.MarkInfo
            return bool(mark_info.get("/Marked", False))
        return False

    def _check_language(self, pdf) -> bool:
        """Prüft ob Dokumentsprache gesetzt ist."""
        return "/Lang" in pdf.Root

    def _check_title(self, pdf) -> bool:
        """Prüft ob Titel in Metadaten vorhanden ist."""
        if pdf.docinfo:
            title = pdf.docinfo.get("/Title")
            return bool(title and str(title).strip())
        return False

    def _check_display_title(self, pdf) -> bool:
        """Prüft ob Titel in Titelleiste angezeigt wird."""
        if "/ViewerPreferences" in pdf.Root:
            vp = pdf.Root.ViewerPreferences
            return bool(vp.get("/DisplayDocTitle", False))
        return False

    def _generate_warnings(self, result: ValidationResult):
        """Generiert Warnungen basierend auf Checks."""
        if not result.has_tags:
            result.warnings.append(
                "PDF ist nicht getaggt - Screenreader können Struktur nicht erkennen"
            )

        if not result.has_language:
            result.warnings.append(
                "Keine Dokumentsprache definiert - Screenreader wählt evtl. falsche Aussprache"
            )

        if not result.has_title:
            result.warnings.append(
                "Kein Dokumenttitel in Metadaten - Dateiname wird angezeigt"
            )

        if not result.display_doc_title:
            result.warnings.append(
                "DisplayDocTitle nicht gesetzt - Dateiname statt Titel in Titelleiste"
            )

    def validate_and_report(self, pdf_path: str | Path) -> ValidationResult:
        """Validiert und gibt Report aus."""
        result = self.validate(pdf_path)

        logger.info("Barrierefreiheits-Validierung:")
        logger.info(f"  Getaggt:           {'✓' if result.has_tags else '✗'}")
        logger.info(f"  Sprache:           {'✓' if result.has_language else '✗'}")
        logger.info(f"  Titel:             {'✓' if result.has_title else '✗'}")
        logger.info(f"  DisplayDocTitle:   {'✓' if result.display_doc_title else '✗'}")
        logger.info(f"  Score:             {result.score}/4")

        if result.warnings:
            logger.warning("Warnungen:")
            for w in result.warnings:
                logger.warning(f"  ⚠️  {w}")

        if result.errors:
            logger.error("Fehler:")
            for e in result.errors:
                logger.error(f"  ❌ {e}")

        return result


class PAC3Validator:
    """
    Integration mit PAC 3 (PDF Accessibility Checker).

    PAC ist das Referenz-Tool für PDF/UA-Validierung.
    https://www.pdfua.foundation/de/pac/

    Hinweis: PAC läuft nur auf Windows.
    """

    def __init__(self, config: Config, pac_path: str | None = None):
        self.config = config
        self.pac_path = pac_path

    def is_available(self) -> bool:
        """Prüft ob PAC verfügbar ist."""
        if not self.pac_path:
            return False
        return Path(self.pac_path).exists()

    def validate(self, pdf_path: str | Path) -> dict:
        """
        Validiert PDF mit PAC 3.

        Returns:
            Dict mit PAC-Ergebnissen oder leeres Dict wenn nicht verfügbar
        """
        if not self.is_available():
            logger.warning("PAC 3 nicht verfügbar")
            return {}

        # TODO: PAC CLI Integration
        # PAC kann per Kommandozeile aufgerufen werden:
        # PAC.exe --input file.pdf --output report.json

        logger.info("PAC 3 Validierung noch nicht implementiert")
        return {}


class ComprehensiveValidator:
    """Kombiniert alle Validierungsmethoden."""

    def __init__(self, config: Config):
        self.config = config
        self.basic_validator = AccessibilityValidator(config)
        self.pac_validator = PAC3Validator(config)

    def validate_all(self, pdf_path: str | Path) -> dict:
        """
        Führt alle verfügbaren Validierungen durch.

        Returns:
            Dict mit allen Ergebnissen
        """
        basic_result = self.basic_validator.validate_and_report(pdf_path)
        pac_result: dict | None = None
        recommendations: list[str] = []

        if self.pac_validator.is_available():
            pac_result = self.pac_validator.validate(pdf_path)

        # Empfehlungen generieren
        if not basic_result.has_tags:
            recommendations.append(
                "PDF neu mit LibreOffice exportieren und 'Tagged PDF' aktivieren"
            )

        if basic_result.warnings:
            recommendations.append(
                "Für vollständige PDF/UA-Konformität: Mit Adobe Acrobat Pro oder "
                "axesPDF QuickFix nachbearbeiten"
            )

        return {
            "basic": basic_result,
            "pac": pac_result,
            "recommendations": recommendations,
        }
