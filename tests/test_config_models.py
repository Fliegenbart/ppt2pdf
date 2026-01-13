"""Tests für Config und Models."""

import tempfile
from pathlib import Path

import pytest

from src.config import Config
from src.models import SlideContent, SlideImage, ValidationResult


class TestConfig:
    """Tests für Config-Klasse."""

    def test_default_config(self):
        """Default Config sollte sinnvolle Werte haben."""
        config = Config()

        assert config.ollama_url == "http://localhost:11434"
        assert config.vision_model == "llava"
        assert config.alt_text_language == "de"
        assert config.pdf_language == "de-DE"

    def test_drv_preset(self):
        """DRV-Preset sollte Behörden-Einstellungen haben."""
        config = Config.for_drv()

        assert config.alt_text_language == "de"
        assert config.pdf_language == "de-DE"
        assert config.pdf_creator == "Deutsche Rentenversicherung"
        assert config.skip_existing_alt_texts is False

    def test_cache_dir_default(self):
        """Cache-Verzeichnis sollte Standard-Pfad haben."""
        config = Config()
        assert config.cache_dir is not None
        assert "accessible-pptx-to-pdf" in str(config.cache_dir)


class TestConfigFromFile:
    """Tests für Config-Datei-Funktionen."""

    def test_from_file_not_found(self):
        """from_file sollte FileNotFoundError werfen."""
        with pytest.raises(FileNotFoundError):
            Config.from_file("/nonexistent/config.toml")

    def test_from_file_invalid_format(self):
        """from_file sollte ValueError bei ungültigem Format werfen."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b"{}")
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                Config.from_file(config_path)
        finally:
            config_path.unlink()

    def test_from_file_yaml(self):
        """from_file sollte YAML-Dateien laden."""
        yaml_content = """
ollama_url: http://custom:11434
vision_model: qwen2-vl
alt_text_language: en
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            config_path = Path(f.name)

        try:
            config = Config.from_file(config_path)
            assert config.ollama_url == "http://custom:11434"
            assert config.vision_model == "qwen2-vl"
            assert config.alt_text_language == "en"
        finally:
            config_path.unlink()

    def test_from_file_toml(self):
        """from_file sollte TOML-Dateien laden."""
        toml_content = """
ollama_url = "http://custom:11434"
vision_model = "llava"
verbose = false
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            config = Config.from_file(config_path)
            assert config.ollama_url == "http://custom:11434"
            assert config.verbose is False
        finally:
            config_path.unlink()

    def test_from_dict_ignores_unknown_keys(self):
        """_from_dict sollte unbekannte Keys ignorieren."""
        data = {
            "ollama_url": "http://test:11434",
            "unknown_key": "should be ignored",
        }
        config = Config._from_dict(data)
        assert config.ollama_url == "http://test:11434"
        assert not hasattr(config, "unknown_key")

    def test_from_dict_converts_cache_dir_to_path(self):
        """_from_dict sollte cache_dir zu Path konvertieren."""
        data = {"cache_dir": "/tmp/test_cache"}
        config = Config._from_dict(data)
        assert isinstance(config.cache_dir, Path)
        assert str(config.cache_dir) == "/tmp/test_cache"


class TestConfigToDict:
    """Tests für Config.to_dict()."""

    def test_to_dict_exports_all_fields(self):
        """to_dict sollte alle Felder exportieren."""
        config = Config(vision_model="test-model")
        data = config.to_dict()

        assert "vision_model" in data
        assert data["vision_model"] == "test-model"

    def test_to_dict_converts_path_to_string(self):
        """to_dict sollte Path zu String konvertieren."""
        config = Config(cache_dir=Path("/tmp/cache"))
        data = config.to_dict()

        assert isinstance(data["cache_dir"], str)
        assert data["cache_dir"] == "/tmp/cache"


class TestConfigSaveToml:
    """Tests für Config.save_toml()."""

    def test_save_toml_creates_file(self):
        """save_toml sollte TOML-Datei erstellen."""
        config = Config(vision_model="test-model")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.toml"
            config.save_toml(path)

            assert path.exists()
            content = path.read_text()
            assert "test-model" in content

    def test_save_toml_creates_parent_dirs(self):
        """save_toml sollte Parent-Verzeichnisse erstellen."""
        config = Config()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "config.toml"
            config.save_toml(path)

            assert path.exists()


class TestConfigFromAuto:
    """Tests für Config.from_auto()."""

    def test_from_auto_returns_default_without_file(self):
        """from_auto sollte Default-Config zurückgeben ohne Datei."""
        # In einem Verzeichnis ohne Config-Datei
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = Config.from_auto()
                assert config.vision_model == "llava"  # Default
            finally:
                os.chdir(old_cwd)


class TestSlideImage:
    """Tests für SlideImage-Klasse."""

    def test_has_alt_text_false(self):
        """Ohne Alt-Text sollte has_alt_text False sein."""
        img = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
        )
        assert img.has_alt_text is False

    def test_has_alt_text_with_current(self):
        """Mit current_alt_text sollte has_alt_text True sein."""
        img = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
            current_alt_text="Ein Bild",
        )
        assert img.has_alt_text is True

    def test_has_alt_text_with_generated(self):
        """Mit generated_alt_text sollte has_alt_text True sein."""
        img = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
            generated_alt_text="Ein generiertes Bild",
        )
        assert img.has_alt_text is True

    def test_effective_alt_text_prefers_generated(self):
        """Generated Alt-Text sollte Priorität haben."""
        img = SlideImage(
            slide_index=0,
            shape_index=0,
            image_bytes=b"test",
            current_alt_text="Original",
            generated_alt_text="Generiert",
        )
        assert img.effective_alt_text == "Generiert"


class TestSlideContent:
    """Tests für SlideContent-Klasse."""

    def test_image_count(self):
        """image_count sollte korrekt zählen."""
        slide = SlideContent(index=0)
        assert slide.image_count == 0

        slide.images.append(SlideImage(0, 0, b"test"))
        slide.images.append(SlideImage(0, 1, b"test2"))
        assert slide.image_count == 2

    def test_images_without_alt(self):
        """images_without_alt sollte nur Bilder ohne Alt-Text zurückgeben."""
        slide = SlideContent(index=0)

        img_with_alt = SlideImage(0, 0, b"test", current_alt_text="Alt")
        img_without_alt = SlideImage(0, 1, b"test2")

        slide.images = [img_with_alt, img_without_alt]

        assert len(slide.images_without_alt) == 1
        assert slide.images_without_alt[0] == img_without_alt


class TestValidationResult:
    """Tests für ValidationResult-Klasse."""

    def test_is_valid_all_good(self):
        """Mit Tags und Sprache sollte is_valid True sein."""
        result = ValidationResult(
            has_tags=True,
            has_language=True,
        )
        assert result.is_valid is True

    def test_is_valid_no_tags(self):
        """Ohne Tags sollte is_valid False sein."""
        result = ValidationResult(
            has_tags=False,
            has_language=True,
        )
        assert result.is_valid is False

    def test_is_valid_with_errors(self):
        """Mit Fehlern sollte is_valid False sein."""
        result = ValidationResult(
            has_tags=True,
            has_language=True,
            errors=["Ein Fehler"],
        )
        assert result.is_valid is False

    def test_score(self):
        """Score sollte korrekt berechnet werden."""
        result = ValidationResult(
            has_tags=True,
            has_language=True,
            has_title=True,
            display_doc_title=False,
        )
        assert result.score == 3

        result.display_doc_title = True
        assert result.score == 4
