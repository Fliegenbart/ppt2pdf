"""Tests für das CLI."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli import (
    _batch_parallel,
    _batch_sequential,
    _convert_single_file,
    cli,
)
from src.config import Config
from src.models import ConversionResult


class TestCLI:
    """Tests für CLI-Grundfunktionen."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cli_help(self, runner):
        """CLI sollte Hilfe anzeigen."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Accessible PPTX to PDF Converter" in result.output

    def test_cli_version(self, runner):
        """CLI sollte Version anzeigen."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestConvertCommand:
    """Tests für den convert-Befehl."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("src.cli.AccessiblePDFPipeline")
    def test_convert_success(self, mock_pipeline_class, runner):
        """convert sollte bei Erfolg Exit-Code 0 zurückgeben."""
        mock_pipeline = MagicMock()
        mock_pipeline.convert.return_value = ConversionResult(success=True)
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"dummy")
            input_path = f.name

        try:
            result = runner.invoke(cli, ["convert", input_path])
            # Exit 0 für Erfolg
            assert result.exit_code == 0
        finally:
            Path(input_path).unlink(missing_ok=True)

    @patch("src.cli.AccessiblePDFPipeline")
    def test_convert_failure(self, mock_pipeline_class, runner):
        """convert sollte bei Fehler Exit-Code 1 zurückgeben."""
        mock_pipeline = MagicMock()
        mock_pipeline.convert.return_value = ConversionResult(success=False)
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"dummy")
            input_path = f.name

        try:
            result = runner.invoke(cli, ["convert", input_path])
            assert result.exit_code == 1
        finally:
            Path(input_path).unlink(missing_ok=True)


class TestInitConfigCommand:
    """Tests für den init-config-Befehl."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_init_config_default(self, runner):
        """init-config sollte Default-Config erstellen."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init-config"])

            assert result.exit_code == 0
            assert Path("a11y-pdf.toml").exists()

    def test_init_config_custom_path(self, runner):
        """init-config sollte an benutzerdefinierten Pfad speichern."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init-config", "-o", "custom.toml"])

            assert result.exit_code == 0
            assert Path("custom.toml").exists()

    def test_init_config_drv_preset(self, runner):
        """init-config sollte DRV-Preset unterstützen."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init-config", "--preset", "drv"])

            assert result.exit_code == 0
            content = Path("a11y-pdf.toml").read_text()
            assert "Deutsche Rentenversicherung" in content


class TestBatchCommand:
    """Tests für den batch-Befehl."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_batch_no_files(self, runner):
        """batch sollte Warnung bei leerem Verzeichnis ausgeben."""
        with runner.isolated_filesystem():
            Path("empty_dir").mkdir()
            result = runner.invoke(cli, ["batch", "empty_dir"])

            assert "Keine PPTX-Dateien" in result.output

    @patch("src.cli._batch_sequential")
    def test_batch_sequential_mode(self, mock_sequential, runner):
        """batch sollte sequentiellen Modus verwenden ohne --parallel."""
        mock_sequential.return_value = 1

        with runner.isolated_filesystem():
            Path("test.pptx").write_bytes(b"dummy")
            runner.invoke(cli, ["batch", "."])

            mock_sequential.assert_called_once()

    @patch("src.cli._batch_parallel")
    def test_batch_parallel_mode(self, mock_parallel, runner):
        """batch sollte parallelen Modus verwenden mit --parallel > 1."""
        mock_parallel.return_value = 1

        with runner.isolated_filesystem():
            Path("test.pptx").write_bytes(b"dummy")
            runner.invoke(cli, ["batch", ".", "--parallel", "4"])

            mock_parallel.assert_called_once()


class TestBatchFunctions:
    """Tests für interne Batch-Funktionen."""

    @pytest.fixture
    def config(self):
        return Config(verbose=False)

    @patch("src.cli.AccessiblePDFPipeline")
    def test_convert_single_file_success(self, mock_pipeline_class, config):
        """_convert_single_file sollte (path, True) bei Erfolg zurückgeben."""
        mock_pipeline = MagicMock()
        mock_pipeline.convert.return_value = ConversionResult(success=True)
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_bytes(b"dummy")
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            result_path, success = _convert_single_file(input_path, output_dir, config)

            assert result_path == input_path
            assert success is True

    @patch("src.cli.AccessiblePDFPipeline")
    def test_convert_single_file_failure(self, mock_pipeline_class, config):
        """_convert_single_file sollte (path, False) bei Fehler zurückgeben."""
        mock_pipeline = MagicMock()
        mock_pipeline.convert.return_value = ConversionResult(success=False)
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "test.pptx"
            input_path.write_bytes(b"dummy")
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            result_path, success = _convert_single_file(input_path, output_dir, config)

            assert result_path == input_path
            assert success is False

    @patch("src.cli.AccessiblePDFPipeline")
    def test_batch_sequential_counts_success(self, mock_pipeline_class, config):
        """_batch_sequential sollte erfolgreiche Konvertierungen zählen."""
        mock_pipeline = MagicMock()
        mock_pipeline.convert.side_effect = [
            ConversionResult(success=True),
            ConversionResult(success=False),
            ConversionResult(success=True),
        ]
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            pptx_files = [
                Path(tmpdir) / "test1.pptx",
                Path(tmpdir) / "test2.pptx",
                Path(tmpdir) / "test3.pptx",
            ]
            for f in pptx_files:
                f.write_bytes(b"dummy")

            success_count = _batch_sequential(pptx_files, output_dir, config)

            assert success_count == 2

    @patch("src.cli._convert_single_file")
    def test_batch_parallel_uses_workers(self, mock_convert, config):
        """_batch_parallel sollte alle Dateien verarbeiten."""
        mock_convert.return_value = (Path("test.pptx"), True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            pptx_files = [Path(tmpdir) / f"test{i}.pptx" for i in range(4)]
            for f in pptx_files:
                f.write_bytes(b"dummy")

            success_count = _batch_parallel(pptx_files, output_dir, config, max_workers=2)

            # Alle Dateien sollten verarbeitet worden sein
            assert mock_convert.call_count == 4
            assert success_count == 4


class TestValidateCommand:
    """Tests für den validate-Befehl."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("src.cli.AccessibilityValidator")
    def test_validate_valid_pdf(self, mock_validator_class, runner):
        """validate sollte valide PDFs als solche anzeigen."""
        from src.models import ValidationResult

        mock_validator = MagicMock()
        mock_validator.validate_and_report.return_value = ValidationResult(
            has_tags=True,
            has_language=True,
        )
        mock_validator_class.return_value = mock_validator

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"dummy")
            pdf_path = f.name

        try:
            result = runner.invoke(cli, ["validate", pdf_path])
            assert "Grundlegende Barrierefreiheit gegeben" in result.output
        finally:
            Path(pdf_path).unlink(missing_ok=True)


class TestCheckCommand:
    """Tests für den check-Befehl."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_check_shows_packages(self, runner):
        """check sollte installierte Packages anzeigen."""
        result = runner.invoke(cli, ["check"])

        # Sollte mindestens einige installierte Packages zeigen
        assert "python-pptx" in result.output or "click" in result.output
