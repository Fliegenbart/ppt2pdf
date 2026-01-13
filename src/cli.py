"""
Kommandozeilen-Interface für den Accessible PDF Converter.
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .config import Config
from .pipeline import AccessiblePDFPipeline

console = Console()


def setup_logging(verbose: bool = False):
    """Konfiguriert Logging mit Rich."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                show_time=False,
                show_path=False,
                markup=True,
            )
        ],
    )


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Konfigurationsdatei (YAML/TOML)",
)
@click.pass_context
def cli(ctx, config: Path | None):
    """
    Accessible PPTX to PDF Converter

    Konvertiert PowerPoint-Präsentationen zu barrierefreien PDFs
    mit lokaler KI-Unterstützung für Alt-Texte.
    """
    ctx.ensure_object(dict)

    # Lade Konfiguration: explizite Datei > Auto-Suche > Defaults
    if config:
        ctx.obj["config"] = Config.from_file(config)
    else:
        ctx.obj["config"] = Config.from_auto()


@cli.command()
@click.argument("input_pptx", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    help="Ausgabe-PDF (default: <input>_accessible.pdf)",
)
@click.option(
    "--model",
    default=None,
    help="Ollama Vision-Modell (default: aus Config)",
)
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["de", "en"]),
    help="Sprache für Alt-Texte (default: aus Config)",
)
@click.option(
    "--title",
    default=None,
    help="PDF-Titel (default: aus Präsentation)",
)
@click.option(
    "--no-alt",
    is_flag=True,
    help="Alt-Text-Generierung überspringen",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Alt-Text-Cache deaktivieren",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Ausführliche Ausgabe",
)
@click.pass_context
def convert(
    ctx,
    input_pptx: Path,
    output: Path | None,
    model: str | None,
    lang: str | None,
    title: str | None,
    no_alt: bool,
    no_cache: bool,
    verbose: bool,
):
    """
    Konvertiert eine PPTX zu barrierefreiem PDF.

    Beispiele:

        a11y-pdf convert präsentation.pptx

        a11y-pdf convert input.pptx -o output.pdf --model qwen2-vl

        a11y-pdf convert input.pptx --lang en --no-alt
    """
    setup_logging(verbose)

    # Output-Pfad
    if output is None:
        output = input_pptx.parent / f"{input_pptx.stem}_accessible.pdf"

    # Start mit Config aus Datei/Auto, überschreibe mit CLI-Optionen
    base_config: Config = ctx.obj["config"]
    config = Config(
        ollama_url=base_config.ollama_url,
        vision_model=model or base_config.vision_model,
        ollama_timeout=base_config.ollama_timeout,
        alt_text_language=lang or base_config.alt_text_language,
        alt_text_max_length=base_config.alt_text_max_length,
        pdf_title=title if title is not None else base_config.pdf_title,
        pdf_language=(
            ("de-DE" if lang == "de" else "en-US") if lang else base_config.pdf_language
        ),
        pdf_creator=base_config.pdf_creator,
        skip_existing_alt_texts=False if no_alt else base_config.skip_existing_alt_texts,
        use_cache=False if no_cache else base_config.use_cache,
        cache_dir=base_config.cache_dir,
        verbose=verbose or base_config.verbose,
    )

    # Pipeline
    pipeline = AccessiblePDFPipeline(config)
    result = pipeline.convert(input_pptx, output)

    # Exit Code
    sys.exit(0 if result.success else 1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("-v", "--verbose", is_flag=True, help="Ausführliche Ausgabe")
@click.pass_context
def validate(ctx, pdf_path: Path, verbose: bool):
    """
    Validiert eine PDF auf Barrierefreiheit.

    Beispiel:

        a11y-pdf validate dokument.pdf
    """
    setup_logging(verbose)

    from .validator import AccessibilityValidator

    config: Config = ctx.obj["config"]
    validator = AccessibilityValidator(config)

    result = validator.validate_and_report(pdf_path)

    if result.is_valid:
        console.print("\n[green]✓ Grundlegende Barrierefreiheit gegeben[/green]")
    else:
        console.print("\n[yellow]⚠️  Verbesserungen empfohlen[/yellow]")

    console.print(f"\nScore: {result.score}/4")


@cli.command("init-config")
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default="a11y-pdf.toml",
    help="Ausgabepfad (default: a11y-pdf.toml)",
)
@click.option(
    "--preset",
    type=click.Choice(["default", "drv"]),
    default="default",
    help="Konfigurations-Preset",
)
def init_config(output: Path, preset: str):
    """
    Erstellt eine Beispiel-Konfigurationsdatei.

    Beispiele:

        a11y-pdf init-config

        a11y-pdf init-config -o ~/.config/a11y-pdf/config.toml

        a11y-pdf init-config --preset drv
    """
    if preset == "drv":
        config = Config.for_drv()
    else:
        config = Config()

    config.save_toml(output)
    console.print(f"[green]✓ Konfiguration erstellt: {output}[/green]")


@cli.command()
@click.option("--model", default=None, help="Zu testendes Modell (default: aus Config)")
@click.pass_context
def check(ctx, model: str | None):
    """
    Prüft ob alle Abhängigkeiten verfügbar sind.

    Beispiel:

        a11y-pdf check --model qwen2-vl
    """
    setup_logging(False)

    base_config: Config = ctx.obj["config"]
    check_model = model or base_config.vision_model

    console.print("\n[bold]Abhängigkeits-Check[/bold]\n")

    # Python Packages
    console.print("[bold]Python Packages:[/bold]")

    packages = [
        ("python-pptx", "pptx"),
        ("pikepdf", "pikepdf"),
        ("Pillow", "PIL"),
        ("requests", "requests"),
        ("click", "click"),
        ("rich", "rich"),
        ("pyyaml", "yaml"),
    ]

    for name, module in packages:
        try:
            __import__(module)
            console.print(f"  ✓ {name}")
        except ImportError:
            console.print(f"  ✗ {name} [red](nicht installiert)[/red]")

    # TOML Support
    try:
        import tomllib  # noqa: F401
        console.print("  ✓ tomllib (builtin)")
    except ImportError:
        try:
            import tomli  # noqa: F401
            console.print("  ✓ tomli")
        except ImportError:
            console.print("  ✗ tomli [yellow](optional, für TOML-Config)[/yellow]")

    console.print("\n[bold]Externe Tools:[/bold]")

    # LibreOffice
    from .converter import PDFConverter
    converter = PDFConverter(base_config)
    if converter.is_available():
        console.print("  ✓ LibreOffice")
    else:
        console.print("  ✗ LibreOffice [red](nicht gefunden)[/red]")

    # Ollama
    from .alt_text import LocalAltTextGenerator
    test_config = Config(vision_model=check_model)
    generator = LocalAltTextGenerator(test_config)

    if generator.is_available():
        console.print(f"  ✓ Ollama ({check_model})")
    else:
        console.print(f"  ✗ Ollama [red]({check_model} nicht verfügbar)[/red]")
        console.print(f"    [dim]Tipp: ollama pull {check_model}[/dim]")

    console.print("")


@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Ausgabe-Verzeichnis (default: gleicher Ordner)",
)
@click.option("--model", default=None, help="Ollama Vision-Modell (default: aus Config)")
@click.option("--lang", default=None, type=click.Choice(["de", "en"]))
@click.option(
    "-p", "--parallel",
    default=1,
    type=click.IntRange(1, 8),
    help="Anzahl paralleler Worker (1-8, default: 1)",
)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def batch(
    ctx,
    directory: Path,
    output_dir: Path | None,
    model: str | None,
    lang: str | None,
    parallel: int,
    verbose: bool,
):
    """
    Konvertiert alle PPTX-Dateien in einem Verzeichnis.

    Beispiele:

        a11y-pdf batch ./präsentationen/ -o ./pdfs/

        a11y-pdf batch ./präsentationen/ --parallel 4
    """
    setup_logging(verbose)

    pptx_files = list(directory.glob("*.pptx"))

    if not pptx_files:
        console.print(f"[yellow]Keine PPTX-Dateien in {directory}[/yellow]")
        return

    mode_text = f"parallel ({parallel} Worker)" if parallel > 1 else "sequentiell"
    console.print(
        f"\n[bold]Batch-Konvertierung: {len(pptx_files)} Dateien ({mode_text})[/bold]\n"
    )

    output_dir = output_dir or directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Merge base config with CLI options
    base_config: Config = ctx.obj["config"]
    config = Config(
        ollama_url=base_config.ollama_url,
        vision_model=model or base_config.vision_model,
        ollama_timeout=base_config.ollama_timeout,
        alt_text_language=lang or base_config.alt_text_language,
        alt_text_max_length=base_config.alt_text_max_length,
        pdf_language=(
            ("de-DE" if lang == "de" else "en-US") if lang else base_config.pdf_language
        ),
        pdf_creator=base_config.pdf_creator,
        skip_existing_alt_texts=base_config.skip_existing_alt_texts,
        use_cache=base_config.use_cache,
        cache_dir=base_config.cache_dir,
        verbose=verbose or base_config.verbose,
    )

    if parallel > 1:
        success_count = _batch_parallel(pptx_files, output_dir, config, parallel)
    else:
        success_count = _batch_sequential(pptx_files, output_dir, config)

    console.print(f"\n[bold]Ergebnis:[/bold] {success_count}/{len(pptx_files)} erfolgreich")


def _batch_sequential(
    pptx_files: list[Path],
    output_dir: Path,
    config: Config,
) -> int:
    """Sequentielle Batch-Verarbeitung."""
    pipeline = AccessiblePDFPipeline(config)
    success_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Konvertiere...", total=len(pptx_files))

        for pptx_file in pptx_files:
            progress.update(task, description=f"Konvertiere {pptx_file.name}...")

            output_pdf = output_dir / f"{pptx_file.stem}_accessible.pdf"
            result = pipeline.convert(pptx_file, output_pdf)

            if result.success:
                success_count += 1

            progress.advance(task)

    return success_count


def _convert_single_file(
    pptx_file: Path,
    output_dir: Path,
    config: Config,
) -> tuple[Path, bool]:
    """Konvertiert eine einzelne Datei (für parallele Verarbeitung)."""
    # Jeder Worker braucht eigene Pipeline-Instanz
    pipeline = AccessiblePDFPipeline(config)
    output_pdf = output_dir / f"{pptx_file.stem}_accessible.pdf"
    result = pipeline.convert(pptx_file, output_pdf)
    return pptx_file, result.success


def _batch_parallel(
    pptx_files: list[Path],
    output_dir: Path,
    config: Config,
    max_workers: int,
) -> int:
    """Parallele Batch-Verarbeitung mit ThreadPoolExecutor."""
    success_count = 0
    failed_files: list[Path] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Konvertiere mit {max_workers} Workern...",
            total=len(pptx_files),
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit alle Jobs
            futures = {
                executor.submit(_convert_single_file, pptx_file, output_dir, config): pptx_file
                for pptx_file in pptx_files
            }

            # Verarbeite Ergebnisse sobald sie fertig sind
            for future in as_completed(futures):
                pptx_file = futures[future]
                try:
                    _, success = future.result()
                    if success:
                        success_count += 1
                        progress.update(task, description=f"✓ {pptx_file.name}")
                    else:
                        failed_files.append(pptx_file)
                        progress.update(task, description=f"✗ {pptx_file.name}")
                except Exception as e:
                    failed_files.append(pptx_file)
                    progress.update(task, description=f"✗ {pptx_file.name}: {e}")

                progress.advance(task)

    # Zeige fehlgeschlagene Dateien
    if failed_files:
        console.print("\n[yellow]Fehlgeschlagen:[/yellow]")
        for f in failed_files:
            console.print(f"  • {f.name}")

    return success_count


def main():
    """Entry Point."""
    cli()


if __name__ == "__main__":
    main()
