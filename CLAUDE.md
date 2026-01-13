# Accessible PPTX to PDF Converter

Ein Tool zur Konvertierung von PowerPoint-Präsentationen zu barrierefreien PDFs mit lokaler KI-Unterstützung (Ollama).

## Projektübersicht

**Ziel:** PPTX → PDF mit:
- Automatisch generierten Alt-Texten via lokales LLM (Ollama/LLaVA)
- Korrekter PDF-Tag-Struktur für Screenreader
- PDF/UA-Konformität (soweit möglich)
- BITV 2.0 Compliance (relevant für DRV/Behörden)

**Tech Stack:**
- Python 3.10+
- python-pptx (PPTX lesen/schreiben)
- pikepdf (PDF-Metadaten)
- Ollama API (lokale Vision-LLMs)
- LibreOffice (PDF-Export mit Tags)

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

## Dateistruktur

```
accessible-pptx-to-pdf/
├── CLAUDE.md                 # Diese Datei
├── README.md                 # Nutzer-Dokumentation
├── requirements.txt          # Python-Dependencies
├── pyproject.toml           # Projekt-Metadaten (optional)
├── src/
│   ├── __init__.py
│   ├── cli.py               # Kommandozeilen-Interface
│   ├── pipeline.py          # Haupt-Pipeline
│   ├── analyzer.py          # PPTX-Analyse
│   ├── alt_text.py          # Ollama Alt-Text-Generierung
│   ├── modifier.py          # PPTX-Modifikation
│   ├── converter.py         # PDF-Konvertierung
│   └── validator.py         # Barrierefreiheits-Validierung
├── tests/
│   ├── __init__.py
│   ├── test_analyzer.py
│   ├── test_alt_text.py
│   └── fixtures/            # Test-PPTXs
└── examples/
    └── sample.pptx          # Beispiel-Präsentation
```

## Wichtige Konventionen

### Code Style
- Python 3.10+ mit Type Hints
- Docstrings für alle öffentlichen Funktionen (Google Style)
- Dataclasses für Datenstrukturen
- Keine globalen Variablen

### Error Handling
- Graceful degradation: Wenn Ollama nicht läuft → ohne Alt-Texte weitermachen
- Alle externen Calls (Ollama, LibreOffice) mit Timeout
- Aussagekräftige Fehlermeldungen auf Deutsch

### Logging
- `logging` Modul statt print()
- Levels: DEBUG für Entwicklung, INFO für User
- Emoji-Prefixes für bessere Lesbarkeit (📊, ✓, ⚠️, ❌)

## Aktuelle TODOs

### Hohe Priorität
- [ ] Refactoring in separate Module (aktuell alles in einer Datei)
- [ ] Bessere Alt-Text Injection (XML Namespace handling)
- [ ] Unit Tests schreiben
- [ ] CLI mit Click oder Typer

### Mittlere Priorität
- [ ] Batch-Verarbeitung (Ordner mit mehreren PPTXs)
- [ ] Progress Bar (tqdm oder rich)
- [ ] Config-File Support (YAML/TOML)
- [ ] Caching für Alt-Texte (gleiche Bilder nicht neu generieren)

### Nice to Have
- [ ] GUI (Tauri oder Electron)
- [ ] n8n Integration
- [ ] Docker Container
- [ ] OCR für Text in Bildern (Tesseract)
- [ ] Automatische Tabellen-Header-Erkennung

## Bekannte Probleme

1. **Alt-Text XML Injection**: Das aktuelle XML-Handling ist simpel. PowerPoint speichert Alt-Texte in `descr`-Attributen, aber die Namespace-Handhabung ist tricky.

2. **LibreOffice Tags**: Besser als MS Office, aber nicht perfekt. Charts und SmartArt werden oft nicht sauber getaggt.

3. **Lesereihenfolge**: Wird aktuell nicht angepasst – müsste man im PDF nachbearbeiten.

## Entwicklungsumgebung

```bash
# Projekt klonen/erstellen
cd accessible-pptx-to-pdf

# Virtuelle Umgebung (empfohlen)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Dependencies
pip install -r requirements.txt
pip install -e .  # Editable install

# Ollama starten (separates Terminal)
ollama serve
ollama pull llava

# Tests
pytest tests/
```

## Hilfreiche Befehle

```bash
# PPTX Struktur inspizieren
unzip -l präsentation.pptx
unzip -p präsentation.pptx ppt/slides/slide1.xml | xmllint --format -

# LibreOffice PDF Export testen
soffice --headless --convert-to pdf input.pptx

# PDF Tags inspizieren
pdftotext -layout output.pdf -  # Text-Extraktion
pdftk output.pdf dump_data      # Metadaten

# Ollama testen
curl http://localhost:11434/api/tags
```

## Kontext: rvEvolution / DRV

Dieses Tool entsteht im Kontext der Arbeit bei der Deutschen Rentenversicherung (rvEvolution-Projekt). Barrierefreiheit ist dort gesetzlich vorgeschrieben (BITV 2.0, EU-Richtlinie 2016/2102).

Anforderungen:
- PDF/UA Konformität
- Deutsche Sprache für Alt-Texte
- Behörden-konformer PDF-Titel
- Nachvollziehbarkeit der Generierung
