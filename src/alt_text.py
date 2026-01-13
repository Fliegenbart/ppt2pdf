"""
Alt-Text Generierung mit lokalen Vision-LLMs via Ollama.
"""

import base64
import hashlib
import json
import logging
from pathlib import Path

import requests

from .config import Config

logger = logging.getLogger(__name__)


class LocalAltTextGenerator:
    """Generiert Alt-Texte für Bilder via Ollama."""

    PROMPT_TEMPLATES = {
        "de": """Beschreibe dieses Bild für eine blinde Person in einem barrierefreien PDF.
Die Beschreibung soll:
- Kurz und prägnant sein (max. 2-3 Sätze)
- Den wesentlichen Inhalt erfassen
- Keine Formulierungen wie "Das Bild zeigt" verwenden
- Direkt beschreiben, was zu sehen ist

Kontext: Dieses Bild ist Teil einer Präsentation zum Thema "{context}".

Antworte NUR mit der Bildbeschreibung, ohne Einleitung oder Erklärung.""",
        "en": """Describe this image for a blind person in an accessible PDF.
The description should:
- Be concise (max 2-3 sentences)
- Capture the essential content
- Not use phrases like "The image shows"
- Describe directly what is visible

Context: This image is part of a presentation about "{context}".

Reply ONLY with the image description, no introduction or explanation.""",
    }

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.ollama_timeout
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Prüft ob Ollama erreichbar ist und das Modell vorhanden."""
        if self._available is not None:
            return self._available

        try:
            response = self.session.get(
                f"{self.config.ollama_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Prüfe ob unser Modell dabei ist (mit oder ohne :latest tag)
                model_base = self.config.vision_model.split(":")[0]
                self._available = any(model_base in m for m in models)

                if not self._available:
                    logger.warning(
                        f"Modell '{self.config.vision_model}' nicht in Ollama gefunden. "
                        f"Verfügbar: {models}"
                    )
            else:
                self._available = False
        except requests.RequestException as e:
            logger.warning(f"Ollama nicht erreichbar: {e}")
            self._available = False

        return self._available

    def generate(self, image_bytes: bytes, context: str = "") -> str | None:
        """
        Generiert Alt-Text für ein Bild.

        Args:
            image_bytes: Bild als Bytes
            context: Optionaler Kontext (z.B. Folientitel)

        Returns:
            Generierter Alt-Text oder None bei Fehler
        """
        if not self.is_available():
            return None

        # Bild zu Base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Prompt erstellen
        lang = self.config.alt_text_language
        prompt_template = self.PROMPT_TEMPLATES.get(lang, self.PROMPT_TEMPLATES["en"])
        prompt = prompt_template.format(context=context or "unbekannt")

        # Ollama API Request
        payload = {
            "model": self.config.vision_model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 200,
            },
        }

        try:
            response = self.session.post(
                f"{self.config.ollama_url}/api/generate",
                json=payload,
                timeout=self.config.ollama_timeout,
            )

            if response.status_code == 200:
                result = response.json()
                alt_text = result.get("response", "").strip()

                # Nachbearbeitung
                alt_text = self._clean_alt_text(alt_text)

                # Länge begrenzen
                if len(alt_text) > self.config.alt_text_max_length:
                    alt_text = alt_text[: self.config.alt_text_max_length - 3] + "..."

                logger.debug(f"Alt-Text generiert: {alt_text[:50]}...")
                return alt_text

            logger.error(f"Ollama API Fehler: {response.status_code}")

        except requests.Timeout:
            logger.error("Ollama Timeout bei Alt-Text Generierung")
        except requests.RequestException as e:
            logger.error(f"Ollama Request Fehler: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Ollama Response Parsing Fehler: {e}")

        return None

    def _clean_alt_text(self, text: str) -> str:
        """Bereinigt generierten Alt-Text."""
        # Entferne typische LLM-Präfixe
        prefixes_to_remove = [
            "Das Bild zeigt ",
            "The image shows ",
            "Bildbeschreibung: ",
            "Description: ",
            "Alt-Text: ",
        ]

        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix) :]

        # Entferne Anführungszeichen am Anfang/Ende
        text = text.strip('"\'')

        return text.strip()


class CachedAltTextGenerator:
    """Alt-Text Generator mit Caching für wiederholte Bilder."""

    def __init__(self, config: Config):
        self.config = config
        self.generator = LocalAltTextGenerator(config)
        self.cache_dir = config.cache_dir
        self._memory_cache: dict[str, str] = {}

    def _get_image_hash(self, image_bytes: bytes) -> str:
        """Berechnet Hash für ein Bild."""
        return hashlib.sha256(image_bytes).hexdigest()[:16]

    def _get_cache_path(self, image_hash: str) -> Path:
        """Gibt Pfad zur Cache-Datei zurück."""
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return self.cache_dir / f"{image_hash}.txt"
        return Path(f"/tmp/a11y_cache_{image_hash}.txt")

    def generate(self, image_bytes: bytes, context: str = "") -> str | None:
        """Generiert Alt-Text mit Caching."""
        if not self.config.use_cache:
            return self.generator.generate(image_bytes, context)

        image_hash = self._get_image_hash(image_bytes)

        # Memory Cache
        if image_hash in self._memory_cache:
            logger.debug(f"Alt-Text aus Memory-Cache: {image_hash}")
            return self._memory_cache[image_hash]

        # Disk Cache
        cache_path = self._get_cache_path(image_hash)
        if cache_path.exists():
            logger.debug(f"Alt-Text aus Disk-Cache: {image_hash}")
            alt_text = cache_path.read_text(encoding="utf-8")
            self._memory_cache[image_hash] = alt_text
            return alt_text

        # Neu generieren
        generated_text = self.generator.generate(image_bytes, context)

        if generated_text:
            self._memory_cache[image_hash] = generated_text
            try:
                cache_path.write_text(generated_text, encoding="utf-8")
            except OSError:
                pass  # Cache-Fehler sind nicht kritisch

        return generated_text

    def is_available(self) -> bool:
        return self.generator.is_available()

    def clear_cache(self):
        """Löscht den Cache."""
        self._memory_cache.clear()
        if self.cache_dir and self.cache_dir.exists():
            for f in self.cache_dir.glob("*.txt"):
                f.unlink()
