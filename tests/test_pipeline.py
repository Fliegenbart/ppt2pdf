"""Tests für die Haupt-Pipeline."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config
from src.models import AnalysisResult, ConversionResult, ValidationResult
from src.pipeline import AccessiblePDFPipeline, convert_pptx_to_accessible_pdf


class TestAccessiblePDFPipeline:
    """Tests für AccessiblePDFPipeline-Klasse."""

    @pytest.fixture
    def config(self):
        return Config(verbose=False)

    @pytest.fixture
    def pipeline(self, config):
        return AccessiblePDFPipeline(config)

    def test_init_creates_components(self, pipeline):
        """Pipeline sollte alle Komponenten erstellen."""
        assert pipeline.analyzer is not None
        assert pipeline.enhancer is not None
        assert pipeline.converter is not None
        assert pipeline.validator is not None

    def test_init_with_default_config(self):
        """Pipeline sollte mit Default-Config funktionieren."""
        pipeline = AccessiblePDFPipeline()
        assert pipeline.config is not None

    def test_convert_file_not_found(self, pipeline):
        """convert sollte Fehler bei nicht existierender Datei zurückgeben."""
        result = pipeline.convert("/nonexistent/file.pptx", "output.pdf")

        assert result.success is False
        assert result.error is not None

    @patch("src.pipeline.PPTXAnalyzer")
    def test_convert_analysis_error(self, mock_analyzer_class, config):
        """convert sollte Fehler bei Analyse-Fehler zurückgeben."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.side_effect = Exception("Parse error")
        mock_analyzer_class.return_value = mock_analyzer

        pipeline = AccessiblePDFPipeline(config)
        pipeline.analyzer = mock_analyzer

        with tempfile.NamedTemporaryFile(suffix=".pptx") as f:
            result = pipeline.convert(f.name, "output.pdf")

        assert result.success is False
        assert "Analyse" in str(result.steps)

    @patch.object(AccessiblePDFPipeline, "_print_header")
    @patch.object(AccessiblePDFPipeline, "_print_summary")
    def test_convert_full_success(self, mock_summary, mock_header, config):
        """convert sollte bei vollständigem Erfolg alle Schritte durchlaufen."""
        pipeline = AccessiblePDFPipeline(config)

        # Mock alle Komponenten
        analysis = AnalysisResult(slides=[], total_slides=1, images_alt_generated=0)
        pipeline.analyzer.analyze = MagicMock(return_value=analysis)

        pipeline.enhancer.enhance = MagicMock(return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_text("dummy")
            output_path = Path(tmpdir) / "output.pdf"

            # Mock converter
            pipeline.converter.convert_and_enhance = MagicMock(return_value=output_path)

            # Erstelle Output-Datei
            output_path.write_text("dummy pdf")

            # Mock validator
            validation = ValidationResult(has_tags=True, has_language=True)
            pipeline.validator.validate = MagicMock(return_value=validation)

            result = pipeline.convert(input_path, output_path)

        assert result.success is True
        assert result.analysis is not None
        assert result.validation is not None

    @patch.object(AccessiblePDFPipeline, "_print_header")
    @patch.object(AccessiblePDFPipeline, "_print_summary")
    def test_convert_pdf_conversion_failure(self, mock_summary, mock_header, config):
        """convert sollte Fehler bei PDF-Konvertierungsfehler zurückgeben."""
        pipeline = AccessiblePDFPipeline(config)

        analysis = AnalysisResult(slides=[], total_slides=1, images_alt_generated=0)
        pipeline.analyzer.analyze = MagicMock(return_value=analysis)
        pipeline.converter.convert_and_enhance = MagicMock(return_value=None)

        with tempfile.NamedTemporaryFile(suffix=".pptx") as f:
            result = pipeline.convert(f.name, "output.pdf")

        assert result.success is False
        assert "PDF" in result.error or "fehlgeschlagen" in result.error

    @patch.object(AccessiblePDFPipeline, "_print_header")
    @patch.object(AccessiblePDFPipeline, "_print_summary")
    def test_convert_tracks_steps(self, mock_summary, mock_header, config):
        """convert sollte alle Schritte tracken."""
        pipeline = AccessiblePDFPipeline(config)

        analysis = AnalysisResult(slides=[], total_slides=1, images_alt_generated=0)
        pipeline.analyzer.analyze = MagicMock(return_value=analysis)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_text("dummy")
            output_path = Path(tmpdir) / "output.pdf"

            pipeline.converter.convert_and_enhance = MagicMock(return_value=output_path)
            output_path.write_text("dummy pdf")

            validation = ValidationResult(has_tags=True, has_language=True)
            pipeline.validator.validate = MagicMock(return_value=validation)

            result = pipeline.convert(input_path, output_path)

        # Sollte mehrere Schritte haben
        assert len(result.steps) >= 2
        step_names = [s[0] for s in result.steps]
        assert "Analyse" in step_names


class TestConvertWithAltTextInjection:
    """Tests für Alt-Text Injection in Pipeline."""

    @pytest.fixture
    def config(self):
        return Config(verbose=False)

    @patch.object(AccessiblePDFPipeline, "_print_header")
    @patch.object(AccessiblePDFPipeline, "_print_summary")
    def test_skips_injection_without_generated_alt(
        self, mock_summary, mock_header, config
    ):
        """Pipeline sollte Injection überspringen ohne generierte Alt-Texte."""
        pipeline = AccessiblePDFPipeline(config)

        # Analyse ohne generierte Alt-Texte
        analysis = AnalysisResult(slides=[], total_slides=1, images_alt_generated=0)
        pipeline.analyzer.analyze = MagicMock(return_value=analysis)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_text("dummy")
            output_path = Path(tmpdir) / "output.pdf"

            pipeline.converter.convert_and_enhance = MagicMock(return_value=output_path)
            output_path.write_text("dummy")

            validation = ValidationResult(has_tags=True, has_language=True)
            pipeline.validator.validate = MagicMock(return_value=validation)

            result = pipeline.convert(input_path, output_path)

        # Injection sollte übersprungen werden
        step_dict = {s[0]: s[1] for s in result.steps}
        assert "übersprungen" in step_dict.get("Alt-Text Injection", "")


class TestConvenienceFunction:
    """Tests für convert_pptx_to_accessible_pdf Funktion."""

    @patch.object(AccessiblePDFPipeline, "convert")
    def test_creates_pipeline_and_converts(self, mock_convert):
        """Funktion sollte Pipeline erstellen und convert aufrufen."""
        mock_convert.return_value = ConversionResult(success=True)

        result = convert_pptx_to_accessible_pdf("input.pptx", "output.pdf")

        mock_convert.assert_called_once()
        assert result.success is True

    @patch.object(AccessiblePDFPipeline, "convert")
    def test_uses_provided_config(self, mock_convert):
        """Funktion sollte bereitgestellte Config verwenden."""
        mock_convert.return_value = ConversionResult(success=True)
        custom_config = Config(vision_model="qwen2-vl")

        convert_pptx_to_accessible_pdf("input.pptx", "output.pdf", config=custom_config)

        mock_convert.assert_called_once()


class TestPrintMethods:
    """Tests für _print_header und _print_summary."""

    @pytest.fixture
    def pipeline(self):
        return AccessiblePDFPipeline(Config(verbose=False))

    def test_print_header_logs_info(self, pipeline, caplog):
        """_print_header sollte Header-Informationen loggen."""
        import logging

        with caplog.at_level(logging.INFO):
            pipeline._print_header(Path("input.pptx"), Path("output.pdf"))

        assert "input.pptx" in caplog.text or len(caplog.records) > 0

    def test_print_summary_success(self, pipeline, caplog):
        """_print_summary sollte Erfolg anzeigen."""
        import logging

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).write_bytes(b"content")

            result = ConversionResult(
                success=True,
                output_path=f.name,
                validation=ValidationResult(has_tags=True, has_language=True),
            )

            with caplog.at_level(logging.INFO):
                pipeline._print_summary(result)

    def test_print_summary_failure(self, pipeline, caplog):
        """_print_summary sollte Fehler anzeigen."""
        import logging

        result = ConversionResult(
            success=False,
            error="Test error",
        )

        with caplog.at_level(logging.ERROR):
            pipeline._print_summary(result)
