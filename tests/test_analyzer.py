"""Tests für PPTXAnalyzer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer import PPTXAnalyzer
from src.config import Config
from src.models import AnalysisResult


class TestPPTXAnalyzer:
    """Tests für PPTXAnalyzer-Klasse."""

    @pytest.fixture
    def config(self):
        """Standard-Konfiguration für Tests."""
        return Config(use_cache=False)

    @pytest.fixture
    def analyzer(self, config):
        """PPTXAnalyzer-Instanz."""
        return PPTXAnalyzer(config)

    def test_init_without_cache(self, config):
        """Analyzer sollte LocalAltTextGenerator ohne Cache verwenden."""
        from src.alt_text import LocalAltTextGenerator

        analyzer = PPTXAnalyzer(config)
        assert isinstance(analyzer.alt_generator, LocalAltTextGenerator)

    def test_init_with_cache(self):
        """Analyzer sollte CachedAltTextGenerator mit Cache verwenden."""
        from src.alt_text import CachedAltTextGenerator

        config = Config(use_cache=True)
        analyzer = PPTXAnalyzer(config)
        assert isinstance(analyzer.alt_generator, CachedAltTextGenerator)

    def test_analyze_file_not_found(self, analyzer):
        """analyze sollte FileNotFoundError werfen bei nicht existierender Datei."""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/file.pptx")

    @patch("src.analyzer.Presentation")
    def test_analyze_empty_presentation(self, mock_presentation, analyzer):
        """analyze sollte leere Präsentation korrekt verarbeiten."""
        # Mock Präsentation ohne Folien
        mock_prs = MagicMock()
        mock_prs.slides = []
        mock_presentation.return_value = mock_prs

        # Pfad mocken
        with patch.object(Path, "exists", return_value=True):
            result = analyzer.analyze("test.pptx")

        assert isinstance(result, AnalysisResult)
        assert result.total_slides == 0
        assert result.images_total == 0
        assert len(result.slides) == 0

    @patch("src.analyzer.Presentation")
    def test_analyze_extracts_title(self, mock_presentation, analyzer):
        """analyze sollte Präsentationstitel extrahieren."""
        # Mock erste Folie mit Titel
        mock_title_shape = MagicMock()
        mock_title_shape.text = "Test Präsentation"

        mock_slide = MagicMock()
        mock_slide.shapes.title = mock_title_shape
        mock_slide.shapes.__iter__ = lambda self: iter([mock_title_shape])
        mock_slide.has_notes_slide = False

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs

        with patch.object(Path, "exists", return_value=True):
            result = analyzer.analyze("test.pptx")

        assert result.presentation_title == "Test Präsentation"

    @patch("src.analyzer.Presentation")
    def test_analyze_counts_tables_and_charts(self, mock_presentation, analyzer):
        """analyze sollte Tabellen und Charts zählen."""
        mock_table_shape = MagicMock()
        mock_table_shape.has_table = True
        mock_table_shape.has_chart = False
        mock_table_shape.has_text_frame = False
        mock_table_shape.shape_type = None

        mock_chart_shape = MagicMock()
        mock_chart_shape.has_table = False
        mock_chart_shape.has_chart = True
        mock_chart_shape.has_text_frame = False
        mock_chart_shape.shape_type = None

        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = lambda self: iter([mock_table_shape, mock_chart_shape])
        mock_slide.has_notes_slide = False

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs

        with patch.object(Path, "exists", return_value=True):
            result = analyzer.analyze("test.pptx")

        assert result.tables == 1
        assert result.charts == 1


class TestExtractPresentationTitle:
    """Tests für _extract_presentation_title Methode."""

    @pytest.fixture
    def analyzer(self):
        return PPTXAnalyzer(Config(use_cache=False))

    def test_empty_slides(self, analyzer):
        """Leere Präsentation sollte leeren Titel liefern."""
        mock_prs = MagicMock()
        mock_prs.slides = []

        result = analyzer._extract_presentation_title(mock_prs)
        assert result == ""

    def test_title_from_title_shape(self, analyzer):
        """Titel sollte aus Title-Shape extrahiert werden."""
        mock_title = MagicMock()
        mock_title.text = "Mein Titel"

        mock_slide = MagicMock()
        mock_slide.shapes.title = mock_title

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        result = analyzer._extract_presentation_title(mock_prs)
        assert result == "Mein Titel"

    def test_title_truncated_to_100_chars(self, analyzer):
        """Titel sollte auf 100 Zeichen begrenzt werden."""
        long_title = "A" * 150
        mock_title = MagicMock()
        mock_title.text = long_title

        mock_slide = MagicMock()
        mock_slide.shapes.title = mock_title

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        result = analyzer._extract_presentation_title(mock_prs)
        assert len(result) == 100

    def test_fallback_to_first_text(self, analyzer):
        """Ohne Title-Shape sollte erster Text verwendet werden."""
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text = "Fallback Text"

        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = lambda self: iter([mock_shape])

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        result = analyzer._extract_presentation_title(mock_prs)
        assert result == "Fallback Text"
