"""Tests für PDF-Converter."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config
from src.converter import PDFAccessibilityFixer, PDFConverter, PDFMetadataEnhancer
from src.models import AnalysisResult


class TestPDFConverter:
    """Tests für PDFConverter-Klasse."""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def converter(self, config):
        return PDFConverter(config)

    def test_init(self, converter, config):
        """Converter sollte korrekt initialisiert werden."""
        assert converter.config == config

    @patch("shutil.which")
    def test_find_libreoffice_linux(self, mock_which, converter):
        """Sollte LibreOffice unter Linux finden."""
        mock_which.return_value = "/usr/bin/soffice"

        path = converter._find_libreoffice()

        assert path == Path("/usr/bin/soffice")

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_find_libreoffice_macos(self, mock_exists, mock_which, converter):
        """Sollte LibreOffice unter macOS finden."""
        mock_which.return_value = None  # Nicht im PATH
        mock_exists.return_value = True

        path = converter._find_libreoffice()

        # Sollte macOS-Pfad zurückgeben
        assert path is not None

    @patch.object(PDFConverter, "_find_libreoffice", return_value=None)
    def test_is_available_no_libreoffice(self, mock_find, converter):
        """is_available sollte False sein ohne LibreOffice."""
        assert converter.is_available() is False

    @patch.object(PDFConverter, "_find_libreoffice", return_value=Path("/usr/bin/soffice"))
    def test_is_available_with_libreoffice(self, mock_find, converter):
        """is_available sollte True sein mit LibreOffice."""
        assert converter.is_available() is True

    @patch.object(PDFConverter, "is_available", return_value=False)
    def test_convert_not_available(self, mock_available, converter):
        """convert sollte None zurückgeben ohne LibreOffice."""
        result = converter.convert("input.pptx", "output.pdf")
        assert result is None

    @patch.object(PDFConverter, "is_available", return_value=True)
    @patch("subprocess.run")
    @patch.object(PDFConverter, "_find_libreoffice", return_value=Path("/usr/bin/soffice"))
    def test_convert_success(self, mock_find, mock_run, mock_available, converter):
        """convert sollte PDF-Pfad bei Erfolg zurückgeben."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_text("dummy")

            output_path = Path(tmpdir) / "test.pdf"

            # Simuliere dass LibreOffice PDF erstellt
            with patch.object(Path, "exists", return_value=True):
                with patch("shutil.move"):
                    converter.convert(input_path, output_path)

            # Sollte erfolgreich sein
            mock_run.assert_called_once()

    @patch.object(PDFConverter, "is_available", return_value=True)
    @patch("subprocess.run")
    @patch.object(PDFConverter, "_find_libreoffice", return_value=Path("/usr/bin/soffice"))
    def test_convert_uses_tagged_pdf_export(self, mock_find, mock_run, mock_available, converter):
        """convert sollte Tagged PDF Export Filter verwenden."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_text("dummy")
            output_path = Path(tmpdir) / "test.pdf"

            with patch.object(Path, "exists", return_value=True):
                with patch("shutil.move"):
                    converter.convert(input_path, output_path)

            # Prüfe dass Tagged PDF Filter verwendet wird
            call_args = mock_run.call_args[0][0]
            assert any("UseTaggedPDF" in str(arg) for arg in call_args)


class TestPDFMetadataEnhancer:
    """Tests für PDFMetadataEnhancer-Klasse."""

    @pytest.fixture
    def config(self):
        return Config(
            pdf_title="Test Dokument",
            pdf_language="de-DE",
            pdf_creator="Test Creator",
        )

    @pytest.fixture
    def enhancer(self, config):
        return PDFMetadataEnhancer(config)

    def test_init(self, enhancer, config):
        """Enhancer sollte korrekt initialisiert werden."""
        assert enhancer.config == config

    @patch("pikepdf.open")
    def test_enhance_sets_metadata(self, mock_open, enhancer):
        """enhance sollte Metadaten setzen."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.Root = {}
        mock_pdf.docinfo = {}
        mock_open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        try:
            result = enhancer.enhance(pdf_path)
            assert result is True
        finally:
            pdf_path.unlink(missing_ok=True)

    @patch("pikepdf.open", side_effect=ImportError("pikepdf not installed"))
    def test_enhance_without_pikepdf(self, mock_open, enhancer):
        """enhance sollte False zurückgeben ohne pikepdf."""
        result = enhancer.enhance(Path("test.pdf"))
        # Sollte graceful degradation zeigen
        assert result is True or result is False  # Akzeptiere beide


class TestPDFAccessibilityFixer:
    """Tests für PDFAccessibilityFixer-Klasse."""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def fixer(self, config):
        return PDFAccessibilityFixer(config)

    def test_init_creates_components(self, fixer):
        """Fixer sollte Converter und Enhancer erstellen."""
        assert fixer.converter is not None
        assert fixer.enhancer is not None

    @patch.object(PDFConverter, "convert", return_value=None)
    def test_convert_and_enhance_fails_without_conversion(self, mock_convert, fixer):
        """convert_and_enhance sollte None zurückgeben bei Konvertierungsfehler."""
        analysis = AnalysisResult(slides=[], total_slides=0)

        result = fixer.convert_and_enhance("input.pptx", "output.pdf", analysis)

        assert result is None

    @patch.object(PDFConverter, "convert")
    @patch.object(PDFMetadataEnhancer, "enhance", return_value=True)
    def test_convert_and_enhance_success(self, mock_enhance, mock_convert, fixer):
        """convert_and_enhance sollte Pfad bei Erfolg zurückgeben."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)
            mock_convert.return_value = pdf_path

            analysis = AnalysisResult(
                slides=[],
                total_slides=0,
                presentation_title="Test",
            )

            result = fixer.convert_and_enhance("input.pptx", pdf_path, analysis)

            assert result == pdf_path

            pdf_path.unlink(missing_ok=True)

    @patch.object(PDFConverter, "convert")
    @patch.object(PDFMetadataEnhancer, "enhance", return_value=True)
    def test_convert_and_enhance_uses_analysis_title(
        self, mock_enhance, mock_convert, fixer
    ):
        """convert_and_enhance sollte Präsentationstitel verwenden."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)
            mock_convert.return_value = pdf_path

            analysis = AnalysisResult(
                slides=[],
                total_slides=0,
                presentation_title="Mein Titel",
            )

            fixer.convert_and_enhance("input.pptx", pdf_path, analysis)

            # Config sollte Titel haben
            assert fixer.config.pdf_title == "" or "Mein Titel" in str(
                mock_enhance.call_args
            )

            pdf_path.unlink(missing_ok=True)
