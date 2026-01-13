"""Tests für PPTX-Modifier."""

import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import Config
from src.models import AnalysisResult, SlideContent, SlideImage
from src.modifier import PPTXAccessibilityEnhancer, PPTXModifier


class TestPPTXModifier:
    """Tests für PPTXModifier-Klasse."""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def modifier(self, config):
        return PPTXModifier(config)

    def test_init_registers_namespaces(self, modifier):
        """Modifier sollte XML-Namespaces registrieren."""
        # Die Namespaces sollten in ET registriert sein
        assert "a" in modifier.NAMESPACES
        assert "p" in modifier.NAMESPACES
        assert "r" in modifier.NAMESPACES

    @pytest.fixture
    def sample_analysis(self):
        """Beispiel-AnalysisResult mit generiertem Alt-Text."""
        image = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
            generated_alt_text="Beschreibung eines Bildes",
        )
        slide = SlideContent(index=0)
        slide.images = [image]
        return AnalysisResult(slides=[slide], total_slides=1)

    @pytest.fixture
    def sample_analysis_no_alt(self):
        """AnalysisResult ohne generierte Alt-Texte."""
        image = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
        )
        slide = SlideContent(index=0)
        slide.images = [image]
        return AnalysisResult(slides=[slide], total_slides=1)

    def test_inject_no_alt_texts(self, modifier, sample_analysis_no_alt):
        """Ohne Alt-Texte sollte nur kopiert werden."""
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as src:
            src.write(b"dummy content")
            src_path = Path(src.name)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as dst:
            dst_path = Path(dst.name)

        try:
            result = modifier.inject_alt_texts(
                src_path, sample_analysis_no_alt, dst_path
            )

            assert result is True
            assert dst_path.exists()
        finally:
            src_path.unlink(missing_ok=True)
            dst_path.unlink(missing_ok=True)

    def test_inject_with_valid_pptx(self, modifier, sample_analysis):
        """inject_alt_texts sollte Alt-Texte in gültiges PPTX injizieren."""
        # Erstelle minimales PPTX (ZIP mit XML)
        with tempfile.TemporaryDirectory() as tmpdir:
            pptx_path = Path(tmpdir) / "test.pptx"
            output_path = Path(tmpdir) / "output.pptx"

            # Minimale PPTX-Struktur erstellen
            slide_xml = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:pic>
                <p:nvPicPr>
                    <p:cNvPr id="1" name="Bild 1"/>
                </p:nvPicPr>
            </p:pic>
        </p:spTree>
    </p:cSld>
</p:sld>"""

            with zipfile.ZipFile(pptx_path, "w") as zf:
                zf.writestr("ppt/slides/slide1.xml", slide_xml)
                zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')

            result = modifier.inject_alt_texts(pptx_path, sample_analysis, output_path)

            assert result is True
            assert output_path.exists()

            # Prüfe ob Alt-Text injiziert wurde
            with zipfile.ZipFile(output_path, "r") as zf:
                content = zf.read("ppt/slides/slide1.xml").decode()
                assert 'descr="Beschreibung eines Bildes"' in content


class TestSetAltTextOnPic:
    """Tests für _set_alt_text_on_pic Methode."""

    @pytest.fixture
    def modifier(self):
        return PPTXModifier(Config())

    def test_sets_descr_attribute(self, modifier):
        """Sollte descr-Attribut auf cNvPr setzen."""
        # Erstelle pic-Element mit korrekter Struktur
        pic_xml = """
        <p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
            <p:nvPicPr>
                <p:cNvPr id="1" name="Bild"/>
            </p:nvPicPr>
        </p:pic>
        """
        pic = ET.fromstring(pic_xml)

        modifier._set_alt_text_on_pic(pic, "Neuer Alt-Text")

        # Prüfe ob descr gesetzt wurde
        cnvpr = pic.find(".//p:cNvPr", modifier.NAMESPACES)
        assert cnvpr is not None
        assert cnvpr.get("descr") == "Neuer Alt-Text"

    def test_handles_missing_nv_pic_pr(self, modifier):
        """Sollte bei fehlendem nvPicPr nicht crashen."""
        pic_xml = """
        <p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
        </p:pic>
        """
        pic = ET.fromstring(pic_xml)

        # Sollte nicht crashen
        modifier._set_alt_text_on_pic(pic, "Alt-Text")


class TestPPTXAccessibilityEnhancer:
    """Tests für PPTXAccessibilityEnhancer-Klasse."""

    @pytest.fixture
    def enhancer(self):
        return PPTXAccessibilityEnhancer(Config())

    def test_enhance_delegates_to_modifier(self, enhancer):
        """enhance sollte an PPTXModifier delegieren."""
        with patch.object(enhancer.modifier, "inject_alt_texts", return_value=True) as mock:
            analysis = AnalysisResult(slides=[], total_slides=0)

            result = enhancer.enhance("input.pptx", analysis, "output.pptx")

            assert result is True
            mock.assert_called_once_with("input.pptx", analysis, "output.pptx")
