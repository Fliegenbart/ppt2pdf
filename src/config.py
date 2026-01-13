"""
Konfiguration für den Accessible PDF Converter.
"""

import logging
import os
from dataclasses import dataclass, fields
from pathlib import Path

logger = logging.getLogger(__name__)

# Standard-Konfigurationspfade
DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "a11y-pdf.toml",
    Path.cwd() / "a11y-pdf.yaml",
    Path.cwd() / "a11y-pdf.yml",
    Path.cwd() / ".a11y-pdf.toml",
    Path.cwd() / ".a11y-pdf.yaml",
    Path.home() / ".config" / "a11y-pdf" / "config.toml",
    Path.home() / ".config" / "a11y-pdf" / "config.yaml",
]


@dataclass
class Config:
    """Zentrale Konfiguration für die Konvertierung."""

    # Ollama Einstellungen
    ollama_url: str = "http://localhost:11434"
    vision_model: str = "llava"
    ollama_timeout: int = 60

    # Alt-Text Einstellungen
    alt_text_language: str = "de"
    alt_text_max_length: int = 250
    skip_existing_alt_texts: bool = True

    # PDF Einstellungen
    pdf_title: str = ""
    pdf_language: str = "de-DE"
    pdf_creator: str = "Accessible PPTX Converter"

    # Verarbeitung
    verbose: bool = True
    use_cache: bool = True
    cache_dir: Path | None = None

    def __post_init__(self):
        if self.cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "accessible-pptx-to-pdf"

    @classmethod
    def from_env(cls) -> "Config":
        """Erstellt Config aus Umgebungsvariablen."""
        return cls(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            vision_model=os.getenv("OLLAMA_MODEL", "llava"),
            alt_text_language=os.getenv("ALT_TEXT_LANG", "de"),
            pdf_language=os.getenv("PDF_LANG", "de-DE"),
            verbose=os.getenv("VERBOSE", "1") == "1",
        )

    @classmethod
    def from_file(cls, config_path: str | Path) -> "Config":
        """
        Lädt Konfiguration aus YAML- oder TOML-Datei.

        Args:
            config_path: Pfad zur Konfigurationsdatei

        Returns:
            Config-Objekt mit Werten aus Datei

        Raises:
            FileNotFoundError: Wenn Datei nicht existiert
            ValueError: Bei ungültigem Dateiformat
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")

        suffix = config_path.suffix.lower()

        if suffix == ".toml":
            data = cls._load_toml(config_path)
        elif suffix in (".yaml", ".yml"):
            data = cls._load_yaml(config_path)
        else:
            raise ValueError(
                f"Ungültiges Konfigurationsformat: {suffix}. "
                "Unterstützt: .toml, .yaml, .yml"
            )

        return cls._from_dict(data)

    @classmethod
    def from_auto(cls) -> "Config":
        """
        Sucht automatisch nach Konfigurationsdatei in Standardpfaden.

        Reihenfolge:
        1. ./a11y-pdf.toml
        2. ./a11y-pdf.yaml
        3. ./.a11y-pdf.toml
        4. ~/.config/a11y-pdf/config.toml

        Returns:
            Config aus gefundener Datei oder Default-Config
        """
        for config_path in DEFAULT_CONFIG_PATHS:
            if config_path.exists():
                logger.info(f"Konfiguration geladen aus: {config_path}")
                return cls.from_file(config_path)

        logger.debug("Keine Konfigurationsdatei gefunden, verwende Defaults")
        return cls()

    @classmethod
    def _load_toml(cls, path: Path) -> dict:
        """Lädt TOML-Datei."""
        try:
            # Python 3.11+ hat tomllib eingebaut
            import tomllib

            with open(path, "rb") as f:
                return tomllib.load(f)
        except ImportError:
            pass

        # Fallback für Python 3.10: tomli
        try:
            import tomli

            with open(path, "rb") as f:
                return tomli.load(f)
        except ImportError:
            raise ImportError(
                "Für TOML-Support wird Python 3.11+ oder das 'tomli' Paket benötigt. "
                "Installation: pip install tomli"
            )

    @classmethod
    def _load_yaml(cls, path: Path) -> dict:
        """Lädt YAML-Datei."""
        try:
            import yaml

            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            raise ImportError(
                "Für YAML-Support wird das 'pyyaml' Paket benötigt. "
                "Installation: pip install pyyaml"
            )

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Erstellt Config aus Dictionary."""
        # Nur bekannte Felder übernehmen
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {}

        for key, value in data.items():
            if key in valid_fields:
                # Spezialbehandlung für Path-Felder
                if key == "cache_dir" and value is not None:
                    value = Path(value)
                filtered_data[key] = value
            else:
                logger.warning(f"Unbekannte Konfigurationsoption ignoriert: {key}")

        return cls(**filtered_data)

    def to_dict(self) -> dict:
        """Exportiert Config als Dictionary."""
        result = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, Path):
                value = str(value)
            result[field.name] = value
        return result

    def save_toml(self, path: str | Path) -> None:
        """
        Speichert Konfiguration als TOML-Datei.

        Args:
            path: Zielpfad für die Datei
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["# Accessible PPTX to PDF Converter - Konfiguration\n\n"]

        sections = {
            "ollama": ["ollama_url", "vision_model", "ollama_timeout"],
            "alt_text": ["alt_text_language", "alt_text_max_length", "skip_existing_alt_texts"],
            "pdf": ["pdf_title", "pdf_language", "pdf_creator"],
            "processing": ["verbose", "use_cache", "cache_dir"],
        }

        for section, keys in sections.items():
            lines.append(f"[{section}]\n")
            for key in keys:
                value = getattr(self, key)
                if isinstance(value, Path):
                    value = str(value)
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"\n')
                elif isinstance(value, bool):
                    lines.append(f"{key} = {str(value).lower()}\n")
                else:
                    lines.append(f"{key} = {value}\n")
            lines.append("\n")

        path.write_text("".join(lines), encoding="utf-8")
        logger.info(f"Konfiguration gespeichert: {path}")

    @classmethod
    def for_drv(cls) -> "Config":
        """Preset für Deutsche Rentenversicherung / Behörden."""
        return cls(
            alt_text_language="de",
            pdf_language="de-DE",
            pdf_creator="Deutsche Rentenversicherung",
            skip_existing_alt_texts=False,  # Immer neu generieren für Konsistenz
        )
