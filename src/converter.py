"""
PDF-Konvertierung mit LibreOffice und Metadaten-Enhancement.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from .config import Config
from .models import AnalysisResult

logger = logging.getLogger(__name__)


class PDFConverter:
    """Konvertiert PPTX zu PDF mit LibreOffice."""

    def __init__(self, config: Config):
        self.config = config
        self._libreoffice_path: str | None = None

    def _find_libreoffice(self) -> str | None:
        """Findet den LibreOffice-Pfad."""
        if self._libreoffice_path:
            return self._libreoffice_path

        # Mögliche Pfade
        candidates = [
            "soffice",  # Standard Linux/PATH
            "/usr/bin/soffice",
            "/usr/bin/libreoffice",
            "/usr/local/bin/soffice",
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            # Windows
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]

        for path in candidates:
            if shutil.which(path):
                self._libreoffice_path = path
                return path

        return None

    def is_available(self) -> bool:
        """Prüft ob LibreOffice verfügbar ist."""
        return self._find_libreoffice() is not None

    def convert(
        self,
        pptx_path: str | Path,
        output_dir: str | Path,
        tagged: bool = True,
    ) -> Path | None:
        """
        Konvertiert PPTX zu PDF via LibreOffice.

        Args:
            pptx_path: Eingabe-PPTX
            output_dir: Ausgabe-Verzeichnis
            tagged: PDF mit Tags erstellen (für Screenreader)

        Returns:
            Pfad zur erstellten PDF oder None bei Fehler
        """
        soffice = self._find_libreoffice()
        if not soffice:
            logger.error("LibreOffice nicht gefunden")
            return None

        pptx_path = Path(pptx_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # PDF Export Filter mit Tags
        if tagged:
            # Export mit Tagged PDF Option
            export_filter = 'pdf:impress_pdf_Export:{"UseTaggedPDF":{"type":"boolean","value":"true"}}'
        else:
            export_filter = "pdf:impress_pdf_Export"

        cmd = [
            soffice,
            "--headless",
            "--convert-to", export_filter,
            "--outdir", str(output_dir),
            str(pptx_path),
        ]

        logger.debug(f"LibreOffice Befehl: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.error(f"LibreOffice Fehler: {result.stderr}")
                return None

            # PDF-Dateiname ermitteln
            pdf_name = pptx_path.stem + ".pdf"
            pdf_path = output_dir / pdf_name

            if pdf_path.exists():
                logger.info(f"✓ PDF erstellt: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF wurde nicht erstellt: {pdf_path}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("LibreOffice Timeout (120s)")
        except FileNotFoundError:
            logger.error(f"LibreOffice nicht ausführbar: {soffice}")
        except Exception as e:
            logger.error(f"Konvertierungsfehler: {e}")

        return None


class PDFMetadataEnhancer:
    """Verbessert PDF-Metadaten für Barrierefreiheit."""

    def __init__(self, config: Config):
        self.config = config

    def enhance(
        self,
        pdf_path: str | Path,
        analysis: AnalysisResult | None = None,
    ) -> bool:
        """
        Verbessert PDF-Metadaten für Barrierefreiheit.

        Args:
            pdf_path: Pfad zur PDF
            analysis: Optional - Analyse-Ergebnis für Titel

        Returns:
            True bei Erfolg
        """
        try:
            import pikepdf
        except ImportError:
            logger.warning("pikepdf nicht installiert - Metadaten-Enhancement übersprungen")
            return False

        pdf_path = Path(pdf_path)

        try:
            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                # Titel bestimmen
                title = self.config.pdf_title
                if not title and analysis:
                    title = analysis.presentation_title
                if not title:
                    title = pdf_path.stem

                # XMP Metadaten setzen
                with pdf.open_metadata() as meta:
                    meta["dc:title"] = title
                    meta["dc:language"] = self.config.pdf_language
                    meta["pdf:Producer"] = self.config.pdf_creator
                    meta["xmp:CreatorTool"] = "Accessible PPTX Converter"

                # ViewerPreferences für bessere Zugänglichkeit
                if "/ViewerPreferences" not in pdf.Root:
                    pdf.Root.ViewerPreferences = pikepdf.Dictionary()

                # Titel in Titelleiste anzeigen statt Dateiname
                pdf.Root.ViewerPreferences.DisplayDocTitle = True

                # Dokumentsprache setzen (wichtig für Screenreader)
                pdf.Root.Lang = self.config.pdf_language

                pdf.save()

            logger.info("✓ PDF-Metadaten optimiert")
            return True

        except Exception as e:
            logger.error(f"Metadaten-Enhancement fehlgeschlagen: {e}")
            return False


class PDFAccessibilityFixer:
    """
    Kombinierter PDF-Konverter und Enhancer.

    Zukünftig: Weitere Fixes wie:
    - Lesereihenfolge korrigieren
    - Tabellen-Tags hinzufügen
    - Link-Texte verbessern
    """

    def __init__(self, config: Config):
        self.config = config
        self.converter = PDFConverter(config)
        self.enhancer = PDFMetadataEnhancer(config)

    def convert_and_enhance(
        self,
        pptx_path: str | Path,
        output_pdf: str | Path,
        analysis: AnalysisResult | None = None,
    ) -> Path | None:
        """
        Konvertiert PPTX zu PDF und verbessert Metadaten.

        Args:
            pptx_path: Eingabe-PPTX
            output_pdf: Gewünschter Ausgabe-Pfad
            analysis: Optional - Analyse-Ergebnis

        Returns:
            Pfad zur PDF oder None bei Fehler
        """
        output_pdf = Path(output_pdf)
        output_dir = output_pdf.parent

        # Konvertieren
        pdf_path = self.converter.convert(pptx_path, output_dir)

        if not pdf_path:
            return None

        # Umbenennen falls nötig
        if pdf_path != output_pdf:
            shutil.move(pdf_path, output_pdf)
            pdf_path = output_pdf

        # Metadaten verbessern
        self.enhancer.enhance(pdf_path, analysis)

        return pdf_path
