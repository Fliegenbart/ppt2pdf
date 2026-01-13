"""Tests für Accessibility-Validator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config
from src.models import ValidationResult
from src.validator import (
    AccessibilityValidator,
    ComprehensiveValidator,
    PAC3Validator,
)


class TestAccessibilityValidator:
    """Tests für AccessibilityValidator-Klasse."""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def validator(self, config):
        return AccessibilityValidator(config)

    def test_validate_file_not_found(self, validator):
        """validate sollte Fehler bei nicht existierender Datei zurückgeben."""
        result = validator.validate("/nonexistent/file.pdf")

        assert len(result.errors) > 0
        assert "nicht gefunden" in result.errors[0]

    @patch("pikepdf.open")
    def test_validate_tagged_pdf(self, mock_open, validator):
        """validate sollte getaggte PDF erkennen."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.Root = {
            "/MarkInfo": MagicMock(get=lambda k, d: True if k == "/Marked" else d),
            "/Lang": "de-DE",
        }
        mock_pdf.Root.__contains__ = lambda self, key: key in ["/MarkInfo", "/Lang"]
        mock_open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).touch()
            result = validator.validate(f.name)

        assert result.has_tags is True

    @patch("pikepdf.open")
    def test_validate_language(self, mock_open, validator):
        """validate sollte Dokumentsprache erkennen."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.Root = {}
        mock_pdf.Root.__contains__ = lambda self, key: key == "/Lang"
        mock_open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).touch()
            result = validator.validate(f.name)

        assert result.has_language is True

    @patch("pikepdf.open")
    def test_validate_title(self, mock_open, validator):
        """validate sollte Dokumenttitel erkennen."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.Root = {}
        mock_pdf.Root.__contains__ = lambda self, key: False
        mock_pdf.docinfo = {"/Title": "Test Titel"}
        mock_pdf.docinfo.get = lambda k, d=None: "Test Titel" if k == "/Title" else d
        mock_open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).touch()
            result = validator.validate(f.name)

        assert result.has_title is True

    @patch("pikepdf.open")
    def test_validate_generates_warnings(self, mock_open, validator):
        """validate sollte Warnungen für fehlende Features generieren."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.Root = {}
        mock_pdf.Root.__contains__ = lambda self, key: False
        mock_pdf.docinfo = None
        mock_open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).touch()
            result = validator.validate(f.name)

        # Sollte Warnungen für fehlende Tags, Sprache, Titel haben
        assert len(result.warnings) >= 1

    @patch("pikepdf.open", side_effect=Exception("Parse error"))
    def test_validate_handles_parse_error(self, mock_open, validator):
        """validate sollte Parse-Fehler graceful behandeln."""
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            Path(f.name).touch()
            result = validator.validate(f.name)

        assert len(result.errors) > 0


class TestCheckMethods:
    """Tests für die einzelnen Check-Methoden."""

    @pytest.fixture
    def validator(self):
        return AccessibilityValidator(Config())

    def test_check_tags_with_mark_info(self, validator):
        """_check_tags sollte True zurückgeben mit MarkInfo."""
        mock_pdf = MagicMock()
        mock_pdf.Root = MagicMock()
        mock_pdf.Root.__contains__ = lambda self, key: key == "/MarkInfo"
        mock_pdf.Root.MarkInfo = MagicMock()
        mock_pdf.Root.MarkInfo.get = lambda k, d: True if k == "/Marked" else d

        result = validator._check_tags(mock_pdf)
        assert result is True

    def test_check_tags_without_mark_info(self, validator):
        """_check_tags sollte False zurückgeben ohne MarkInfo."""
        mock_pdf = MagicMock()
        mock_pdf.Root = {}
        mock_pdf.Root.__contains__ = lambda self, key: False

        result = validator._check_tags(mock_pdf)
        assert result is False

    def test_check_language_present(self, validator):
        """_check_language sollte True zurückgeben mit Lang."""
        mock_pdf = MagicMock()
        mock_pdf.Root = {"/Lang": "de-DE"}
        mock_pdf.Root.__contains__ = lambda self, key: key == "/Lang"

        result = validator._check_language(mock_pdf)
        assert result is True

    def test_check_language_missing(self, validator):
        """_check_language sollte False zurückgeben ohne Lang."""
        mock_pdf = MagicMock()
        mock_pdf.Root = {}
        mock_pdf.Root.__contains__ = lambda self, key: False

        result = validator._check_language(mock_pdf)
        assert result is False


class TestPAC3Validator:
    """Tests für PAC3Validator-Klasse."""

    @pytest.fixture
    def validator(self):
        return PAC3Validator(Config())

    def test_is_available_no_path(self, validator):
        """is_available sollte False sein ohne PAC-Pfad."""
        assert validator.is_available() is False

    def test_is_available_invalid_path(self):
        """is_available sollte False sein mit ungültigem Pfad."""
        validator = PAC3Validator(Config(), pac_path="/nonexistent/PAC.exe")
        assert validator.is_available() is False

    def test_validate_not_available(self, validator):
        """validate sollte leeres Dict zurückgeben wenn nicht verfügbar."""
        result = validator.validate("test.pdf")
        assert result == {}


class TestComprehensiveValidator:
    """Tests für ComprehensiveValidator-Klasse."""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def validator(self, config):
        return ComprehensiveValidator(config)

    def test_init_creates_validators(self, validator):
        """Sollte Basic- und PAC-Validator erstellen."""
        assert validator.basic_validator is not None
        assert validator.pac_validator is not None

    @patch.object(AccessibilityValidator, "validate_and_report")
    @patch.object(PAC3Validator, "is_available", return_value=False)
    def test_validate_all_basic_only(self, mock_pac, mock_basic, validator):
        """validate_all sollte nur Basic-Validierung durchführen ohne PAC."""
        mock_basic.return_value = ValidationResult(has_tags=True, has_language=True)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            result = validator.validate_all(f.name)

        assert "basic" in result
        assert result["pac"] is None

    @patch.object(AccessibilityValidator, "validate_and_report")
    @patch.object(PAC3Validator, "is_available", return_value=False)
    def test_validate_all_generates_recommendations(self, mock_pac, mock_basic, validator):
        """validate_all sollte Empfehlungen generieren."""
        mock_basic.return_value = ValidationResult(has_tags=False, has_language=True)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            result = validator.validate_all(f.name)

        assert "recommendations" in result
        assert len(result["recommendations"]) > 0

    @patch.object(AccessibilityValidator, "validate_and_report")
    @patch.object(PAC3Validator, "is_available", return_value=False)
    def test_validate_all_recommends_manual_fix(self, mock_pac, mock_basic, validator):
        """validate_all sollte manuelle Nachbearbeitung empfehlen bei Warnungen."""
        mock_result = ValidationResult(has_tags=True, has_language=True)
        mock_result.warnings = ["Eine Warnung"]
        mock_basic.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            result = validator.validate_all(f.name)

        recommendations = result["recommendations"]
        assert any("Acrobat" in r or "QuickFix" in r for r in recommendations)
