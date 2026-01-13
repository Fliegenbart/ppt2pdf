"""Tests für Alt-Text Generierung."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.alt_text import CachedAltTextGenerator, LocalAltTextGenerator
from src.config import Config


class TestLocalAltTextGenerator:
    """Tests für LocalAltTextGenerator-Klasse."""

    @pytest.fixture
    def config(self):
        """Standard-Konfiguration."""
        return Config(
            ollama_url="http://localhost:11434",
            vision_model="llava",
            alt_text_language="de",
            ollama_timeout=30,
        )

    @pytest.fixture
    def generator(self, config):
        """Generator-Instanz."""
        return LocalAltTextGenerator(config)

    def test_init(self, generator, config):
        """Generator sollte korrekt initialisiert werden."""
        assert generator.config == config
        assert generator._available is None

    @patch("requests.Session.get")
    def test_is_available_success(self, mock_get, generator):
        """is_available sollte True zurückgeben wenn Modell vorhanden."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llava:latest"}]
        }
        mock_get.return_value = mock_response

        assert generator.is_available() is True
        assert generator._available is True

    @patch("requests.Session.get")
    def test_is_available_model_not_found(self, mock_get, generator):
        """is_available sollte False zurückgeben wenn Modell fehlt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:latest"}]
        }
        mock_get.return_value = mock_response

        assert generator.is_available() is False

    @patch("requests.Session.get")
    def test_is_available_connection_error(self, mock_get, generator):
        """is_available sollte False zurückgeben bei Verbindungsfehler."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")

        assert generator.is_available() is False

    @patch("requests.Session.get")
    def test_is_available_cached(self, mock_get, generator):
        """is_available sollte Ergebnis cachen."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llava"}]}
        mock_get.return_value = mock_response

        # Erster Aufruf
        generator.is_available()
        # Zweiter Aufruf - sollte nicht erneut API aufrufen
        generator.is_available()

        assert mock_get.call_count == 1

    @patch.object(LocalAltTextGenerator, "is_available", return_value=False)
    def test_generate_not_available(self, mock_available, generator):
        """generate sollte None zurückgeben wenn nicht verfügbar."""
        result = generator.generate(b"test_image_data")
        assert result is None

    @patch.object(LocalAltTextGenerator, "is_available", return_value=True)
    @patch("requests.Session.post")
    def test_generate_success(self, mock_post, mock_available, generator):
        """generate sollte Alt-Text bei erfolgreichem API-Call zurückgeben."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Ein Diagramm zeigt Quartalszahlen."
        }
        mock_post.return_value = mock_response

        result = generator.generate(b"test_image_data", context="Finanzbericht")

        assert result is not None
        assert "Diagramm" in result

    @patch.object(LocalAltTextGenerator, "is_available", return_value=True)
    @patch("requests.Session.post")
    def test_generate_timeout(self, mock_post, mock_available, generator):
        """generate sollte None bei Timeout zurückgeben."""
        import requests
        mock_post.side_effect = requests.Timeout()

        result = generator.generate(b"test_image_data")
        assert result is None

    @patch.object(LocalAltTextGenerator, "is_available", return_value=True)
    @patch("requests.Session.post")
    def test_generate_truncates_long_text(self, mock_post, mock_available):
        """generate sollte zu langen Text abschneiden."""
        config = Config(alt_text_max_length=50)
        generator = LocalAltTextGenerator(config)

        long_response = "A" * 100  # Länger als max_length
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": long_response}
        mock_post.return_value = mock_response

        result = generator.generate(b"test_image_data")

        assert result is not None
        assert len(result) == 50
        assert result.endswith("...")


class TestCleanAltText:
    """Tests für _clean_alt_text Methode."""

    @pytest.fixture
    def generator(self):
        return LocalAltTextGenerator(Config())

    def test_removes_german_prefix(self, generator):
        """Sollte deutsche Präfixe entfernen."""
        text = "Das Bild zeigt ein Haus"
        result = generator._clean_alt_text(text)
        assert result == "ein Haus"

    def test_removes_english_prefix(self, generator):
        """Sollte englische Präfixe entfernen."""
        text = "The image shows a house"
        result = generator._clean_alt_text(text)
        assert result == "a house"

    def test_removes_quotes(self, generator):
        """Sollte Anführungszeichen entfernen."""
        text = '"Ein schönes Bild"'
        result = generator._clean_alt_text(text)
        assert result == "Ein schönes Bild"

    def test_strips_whitespace(self, generator):
        """Sollte Whitespace trimmen."""
        text = "  Ein Text mit Spaces  "
        result = generator._clean_alt_text(text)
        assert result == "Ein Text mit Spaces"


class TestCachedAltTextGenerator:
    """Tests für CachedAltTextGenerator-Klasse."""

    @pytest.fixture
    def config(self):
        """Config mit temporärem Cache-Verzeichnis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Config(use_cache=True, cache_dir=Path(tmpdir))

    @pytest.fixture
    def generator(self, config):
        return CachedAltTextGenerator(config)

    def test_get_image_hash(self, generator):
        """Hash sollte konsistent und 16 Zeichen lang sein."""
        image_bytes = b"test_image_data"
        hash1 = generator._get_image_hash(image_bytes)
        hash2 = generator._get_image_hash(image_bytes)

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_different_images_different_hash(self, generator):
        """Verschiedene Bilder sollten verschiedene Hashes haben."""
        hash1 = generator._get_image_hash(b"image1")
        hash2 = generator._get_image_hash(b"image2")

        assert hash1 != hash2

    @patch.object(LocalAltTextGenerator, "generate", return_value="Generated Alt")
    @patch.object(LocalAltTextGenerator, "is_available", return_value=True)
    def test_generate_caches_result(self, mock_available, mock_generate, generator):
        """generate sollte Ergebnis im Memory-Cache speichern."""
        image_bytes = b"test_image"

        # Erster Aufruf - generiert
        result1 = generator.generate(image_bytes)
        # Zweiter Aufruf - aus Cache
        result2 = generator.generate(image_bytes)

        assert result1 == "Generated Alt"
        assert result2 == "Generated Alt"
        # Generator sollte nur einmal aufgerufen werden
        assert mock_generate.call_count == 1

    @patch.object(LocalAltTextGenerator, "generate", return_value="Generated Alt")
    @patch.object(LocalAltTextGenerator, "is_available", return_value=True)
    def test_generate_uses_disk_cache(self, mock_available, mock_generate, generator):
        """generate sollte Disk-Cache nutzen."""
        image_bytes = b"test_image"

        # Generieren und in Cache schreiben
        generator.generate(image_bytes)

        # Neuer Generator mit gleichem Cache-Verzeichnis
        generator2 = CachedAltTextGenerator(generator.config)
        result = generator2.generate(image_bytes)

        # Sollte aus Disk-Cache kommen, nicht neu generiert
        assert result == "Generated Alt"
        # Nur einmal generiert (erster Generator)
        assert mock_generate.call_count == 1

    def test_clear_cache(self, generator):
        """clear_cache sollte Memory- und Disk-Cache leeren."""
        # Füge etwas zum Memory-Cache hinzu
        generator._memory_cache["test"] = "value"

        # Erstelle Cache-Datei
        cache_path = generator._get_cache_path("test")
        cache_path.write_text("cached value")

        generator.clear_cache()

        assert len(generator._memory_cache) == 0
        assert not cache_path.exists()

    def test_generate_without_cache_enabled(self):
        """Ohne Cache sollte direkt generiert werden."""
        config = Config(use_cache=False)
        generator = CachedAltTextGenerator(config)

        with patch.object(generator.generator, "generate", return_value="Direct") as mock:
            with patch.object(generator.generator, "is_available", return_value=True):
                result = generator.generate(b"test")

        assert result == "Direct"
        mock.assert_called_once()
