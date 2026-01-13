# Accessible PPTX to PDF Converter

Konvertiert PowerPoint-Präsentationen zu barrierefreien PDFs mit lokaler KI-Unterstützung für Alt-Text-Generierung.

## Features

- 🤖 **Lokale KI für Alt-Texte** – Ollama mit Vision-Modellen (LLaVA, Qwen2-VL)
- 🏷️ **Tagged PDFs** – LibreOffice exportiert saubere Strukturen
- 🌍 **Mehrsprachig** – Deutsche und englische Alt-Texte
- ✅ **Validierung** – Automatische Barrierefreiheits-Checks
- 🔒 **100% Lokal** – Keine Cloud, alle Daten bleiben bei dir
- ⚡ **Caching** – Gleiche Bilder werden nicht neu analysiert

## Installation

```bash
# Repository klonen
git clone https://github.com/yourusername/accessible-pptx-to-pdf.git
cd accessible-pptx-to-pdf

# Virtuelle Umgebung (empfohlen)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Dependencies installieren
pip install -e .

# Ollama installieren und Modell laden
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llava
```

## Quick Start

```bash
# Einzelne Datei konvertieren
a11y-pdf convert präsentation.pptx

# Mit Optionen
a11y-pdf convert input.pptx -o output.pdf --model qwen2-vl

# Batch-Konvertierung
a11y-pdf batch ./präsentationen/ -o ./pdfs/

# PDF validieren
a11y-pdf validate dokument.pdf

# System-Check
a11y-pdf check
```

## Nutzung als Library

```python
from src.pipeline import AccessiblePDFPipeline
from src.config import Config

# Einfache Konvertierung
pipeline = AccessiblePDFPipeline()
result = pipeline.convert("input.pptx", "output.pdf")

# Mit Konfiguration
config = Config(
    vision_model="qwen2-vl",
    alt_text_language="de",
    pdf_title="Meine Präsentation",
)
pipeline = AccessiblePDFPipeline(config)
result = pipeline.convert("input.pptx", "output.pdf")

print(f"Erfolg: {result.success}")
print(f"Alt-Texte: {result.analysis.images_alt_generated}")
print(f"A11y Score: {result.validation.score}/4")
```

## CLI Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `convert` | Konvertiert PPTX zu barrierefreiem PDF |
| `validate` | Prüft PDF auf Barrierefreiheit |
| `batch` | Konvertiert alle PPTXs in einem Ordner |
| `check` | Prüft System-Abhängigkeiten |

### convert

```bash
a11y-pdf convert INPUT.pptx [OPTIONS]

Options:
  -o, --output PATH   Ausgabe-PDF
  --model TEXT        Ollama Modell (default: llava)
  --lang [de|en]      Sprache für Alt-Texte (default: de)
  --title TEXT        PDF-Titel
  --no-alt            Alt-Text-Generierung überspringen
  --no-cache          Caching deaktivieren
  -v, --verbose       Ausführliche Ausgabe
```

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    AccessiblePDFPipeline                    │
├─────────────────────────────────────────────────────────────┤
│  PPTXAnalyzer          │  Extrahiert Folien, Bilder, Text   │
│  LocalAltTextGenerator │  Ollama API für Bildbeschreibungen │
│  PPTXModifier          │  Injiziert Alt-Texte in XML        │
│  PDFConverter          │  LibreOffice Export + Metadaten    │
│  AccessibilityValidator│  Prüft Tags, Sprache, Titel        │
└─────────────────────────────────────────────────────────────┘
```

## Abhängigkeiten

### Python Packages
- python-pptx – PPTX lesen/schreiben
- pikepdf – PDF-Metadaten
- requests – Ollama API
- click – CLI
- rich – Terminal-Ausgabe

### Externe Tools
- **LibreOffice** – PDF-Export mit Tags
- **Ollama** – Lokale LLMs für Alt-Texte

## Barrierefreiheits-Checks

Der Validator prüft:
- ✓ PDF ist getaggt (Strukturinformationen)
- ✓ Dokumentsprache gesetzt
- ✓ Titel in Metadaten
- ✓ DisplayDocTitle aktiviert

Für vollständige PDF/UA-Validierung empfehlen wir zusätzlich:
- [PAC 2024](https://www.pdfua.foundation/de/pac/) (Windows)
- Adobe Acrobat Pro
- axesPDF QuickFix

## Entwicklung

```bash
# Dev-Dependencies
pip install -e ".[dev]"

# Tests
pytest tests/

# Formatierung
black src/ tests/
ruff check src/ tests/

# Type Checking
mypy src/
```

## Lizenz

MIT

---

*Entwickelt für barrierefreie Dokumentation im Behördenumfeld (BITV 2.0).*
