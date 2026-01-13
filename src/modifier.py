"""
PPTX-Modifikation für Barrierefreiheit (Alt-Text Injection).
"""

import logging
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .config import Config
from .models import AnalysisResult, SlideContent

logger = logging.getLogger(__name__)


class PPTXModifier:
    """Modifiziert PPTX-Dateien für bessere Barrierefreiheit."""

    # XML Namespaces für PowerPoint
    NAMESPACES = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    }

    def __init__(self, config: Config):
        self.config = config

        # Registriere Namespaces für ET
        for prefix, uri in self.NAMESPACES.items():
            ET.register_namespace(prefix, uri)

    def inject_alt_texts(
        self,
        pptx_path: str | Path,
        analysis: AnalysisResult,
        output_path: str | Path,
    ) -> bool:
        """
        Fügt generierte Alt-Texte in die PPTX ein.

        Args:
            pptx_path: Original PPTX
            analysis: Analyse-Ergebnis mit generierten Alt-Texten
            output_path: Ausgabe-PPTX

        Returns:
            True bei Erfolg
        """
        pptx_path = Path(pptx_path)
        output_path = Path(output_path)

        # Zähle wie viele Alt-Texte wir haben
        alt_texts_to_inject = sum(
            1 for slide in analysis.slides
            for img in slide.images
            if img.generated_alt_text
        )

        if alt_texts_to_inject == 0:
            logger.info("Keine Alt-Texte zum Injizieren")
            # Einfach kopieren
            if pptx_path != output_path:
                import shutil
                shutil.copy2(pptx_path, output_path)
            return True

        logger.info(f"Injiziere {alt_texts_to_inject} Alt-Texte...")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # PPTX entpacken
                with zipfile.ZipFile(pptx_path, "r") as zip_ref:
                    zip_ref.extractall(temp_path)

                # Alt-Texte in XML-Dateien injizieren
                for slide in analysis.slides:
                    self._inject_slide_alt_texts(temp_path, slide)

                # Neu verpacken
                self._repack_pptx(temp_path, output_path)

            logger.info(f"✓ Alt-Texte injiziert: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Alt-Text Injection fehlgeschlagen: {e}")
            return False

    def _inject_slide_alt_texts(self, temp_path: Path, slide: SlideContent):
        """Injiziert Alt-Texte in eine Folie."""

        slide_xml_path = temp_path / "ppt" / "slides" / f"slide{slide.index + 1}.xml"

        if not slide_xml_path.exists():
            logger.warning(f"Slide XML nicht gefunden: {slide_xml_path}")
            return

        # Sammle Images mit neuen Alt-Texten
        images_with_alt = [img for img in slide.images if img.generated_alt_text]

        if not images_with_alt:
            return

        try:
            tree = ET.parse(slide_xml_path)
            root = tree.getroot()

            # Finde alle pic-Elemente
            pics = root.findall(".//p:pic", self.NAMESPACES)

            for img in images_with_alt:
                if img.shape_index < len(pics) and img.generated_alt_text:
                    self._set_alt_text_on_pic(
                        pics[img.shape_index],
                        img.generated_alt_text
                    )
                    logger.debug(
                        f"Alt-Text gesetzt für Folie {slide.index + 1}, "
                        f"Bild {img.shape_index}"
                    )

            # Speichern
            tree.write(
                slide_xml_path,
                xml_declaration=True,
                encoding="UTF-8",
            )

        except ET.ParseError as e:
            logger.error(f"XML Parse Fehler in {slide_xml_path}: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Modifizieren von {slide_xml_path}: {e}")

    def _set_alt_text_on_pic(self, pic_element, alt_text: str):
        """Setzt das descr-Attribut auf einem pic-Element."""

        # Suche nvPicPr/cNvPr Element
        # Namespace-aware XPath
        nvPicPr = pic_element.find("p:nvPicPr", self.NAMESPACES)

        if nvPicPr is None:
            # Versuche ohne Namespace (manchmal so in XML)
            nvPicPr = pic_element.find("nvPicPr")

        if nvPicPr is None:
            logger.warning("nvPicPr nicht gefunden in pic-Element")
            return

        # cNvPr finden oder erstellen
        cNvPr = nvPicPr.find("p:cNvPr", self.NAMESPACES)
        if cNvPr is None:
            cNvPr = nvPicPr.find("cNvPr")

        if cNvPr is not None:
            # descr-Attribut setzen
            cNvPr.set("descr", alt_text)
        else:
            logger.warning("cNvPr nicht gefunden in nvPicPr")

    def _repack_pptx(self, source_dir: Path, output_path: Path):
        """Verpackt entpackte PPTX-Dateien wieder als ZIP."""

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)


class PPTXAccessibilityEnhancer:
    """Erweiterte Barrierefreiheits-Verbesserungen für PPTX."""

    def __init__(self, config: Config):
        self.config = config
        self.modifier = PPTXModifier(config)

    def enhance(
        self,
        pptx_path: str | Path,
        analysis: AnalysisResult,
        output_path: str | Path,
    ) -> bool:
        """
        Führt alle Barrierefreiheits-Verbesserungen durch.

        Aktuell: Nur Alt-Text Injection.
        Zukünftig: Lesereihenfolge, Tabellen-Header, etc.
        """
        return self.modifier.inject_alt_texts(pptx_path, analysis, output_path)
