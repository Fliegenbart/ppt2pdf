"""
API Routes - FastAPI endpoints for the PPTX to PDF converter.
"""
import os
import uuid
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import aiofiles

from api.models import (
    UploadResponse, AnalysisRequest, ConversionRequest, UpdateRequest,
    ConversionJob, Presentation, AccessibilityReport, ElementUpdate
)
from core.pptx_parser import PPTXParser
from core.ai_analyzer import AIAnalyzer
from core.pdf_generator import AccessiblePDFGenerator
from core.accessibility import AccessibilityChecker

router = APIRouter()

# In-memory job storage (use Redis/DB in production)
jobs: dict[str, ConversionJob] = {}
presentations: dict[str, Presentation] = {}

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "outputs")

# Initialize components
parser = PPTXParser()
pdf_generator = AccessiblePDFGenerator()
accessibility_checker = AccessibilityChecker()


def get_ai_analyzer() -> Optional[AIAnalyzer]:
    """Get AI analyzer if API key is available."""
    try:
        return AIAnalyzer()
    except ValueError:
        return None


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a PPTX file for processing."""
    # Validate file type
    if not file.filename.endswith(('.pptx', '.PPTX')):
        raise HTTPException(
            status_code=400,
            detail="Only PPTX files are supported"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}.pptx")

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # Create job
    job = ConversionJob(
        job_id=job_id,
        status="uploaded",
        progress=10.0,
        current_step="File uploaded successfully",
    )
    jobs[job_id] = job

    # Parse the file immediately
    try:
        job.status = "parsing"
        job.current_step = "Parsing PowerPoint file..."
        presentation = parser.parse(file_path)
        presentations[job_id] = presentation
        job.status = "parsed"
        job.progress = 30.0
        job.current_step = "File parsed successfully"
    except Exception as e:
        job.status = "error"
        job.error_message = f"Failed to parse PPTX: {str(e)}"
        raise HTTPException(status_code=400, detail=str(e))

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        message="File uploaded and parsed successfully"
    )


@router.post("/analyze")
async def analyze_presentation(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze presentation with AI for accessibility improvements."""
    job_id = request.job_id

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_id not in presentations:
        raise HTTPException(status_code=400, detail="Presentation not parsed yet")

    job = jobs[job_id]
    presentation = presentations[job_id]

    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        job_id,
        presentation,
        request.generate_alt_text,
        request.analyze_reading_order,
        request.check_contrast,
        request.detect_languages,
    )

    job.status = "analyzing"
    job.progress = 35.0
    job.current_step = "Starting AI analysis..."

    return {"job_id": job_id, "message": "Analysis started"}


async def run_analysis(
    job_id: str,
    presentation: Presentation,
    generate_alt_text: bool,
    analyze_reading_order: bool,
    check_contrast: bool,
    detect_languages: bool,
):
    """Run AI analysis on presentation."""
    job = jobs[job_id]

    try:
        analyzer = get_ai_analyzer()

        if analyzer:
            job.current_step = "Running AI analysis..."
            job.progress = 40.0

            # Run AI analysis
            await analyzer.analyze_presentation(
                presentation,
                generate_alt_text=generate_alt_text,
                analyze_reading_order=analyze_reading_order,
                detect_languages=detect_languages,
            )

            job.progress = 70.0

        # Run accessibility checks
        job.current_step = "Checking accessibility..."
        issues = accessibility_checker.check_presentation(presentation)
        presentation.accessibility_issues = issues

        job.progress = 80.0
        job.status = "analyzed"
        job.current_step = "Analysis complete"
        job.presentation = presentation

    except Exception as e:
        job.status = "error"
        job.error_message = f"Analysis failed: {str(e)}"


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a conversion job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Include presentation summary
    response = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "error_message": job.error_message,
    }

    if job_id in presentations:
        pres = presentations[job_id]
        response["presentation"] = {
            "title": pres.title,
            "author": pres.author,
            "slide_count": len(pres.slides),
            "analyzed": pres.analyzed,
            "default_language": pres.default_language,
        }

    return response


@router.get("/job/{job_id}/slides")
async def get_slides(job_id: str):
    """Get all slides with their elements for editing."""
    if job_id not in presentations:
        raise HTTPException(status_code=404, detail="Presentation not found")

    presentation = presentations[job_id]

    # Return slides with elements (excluding binary image data)
    slides = []
    for slide in presentation.slides:
        slide_data = {
            "slide_number": slide.slide_number,
            "title": slide.title,
            "speaker_notes": slide.speaker_notes,
            "reading_order_analyzed": slide.reading_order_analyzed,
            "reading_order_confidence": slide.reading_order_confidence,
            "elements": [],
        }

        for elem in sorted(slide.elements, key=lambda e: e.reading_order):
            elem_data = {
                "id": elem.id,
                "element_type": elem.element_type.value,
                "reading_order": elem.reading_order,
                "bounds": {
                    "x": elem.bounds.x,
                    "y": elem.bounds.y,
                    "width": elem.bounds.width,
                    "height": elem.bounds.height,
                },
            }

            # Add type-specific data
            if elem.paragraphs:
                elem_data["text"] = " ".join(
                    run.text
                    for para in elem.paragraphs
                    for run in para.runs
                )
                elem_data["heading_level"] = elem.heading_level

            if elem.element_type.value == "image":
                elem_data["alt_text"] = elem.alt_text
                elem_data["alt_text_generated"] = elem.alt_text_generated
                elem_data["is_decorative"] = elem.is_decorative
                elem_data["content_type"] = elem.content_type.value
                # Include thumbnail URL (could be base64 or endpoint)
                elem_data["has_image"] = bool(elem.image_base64)

            if elem.element_type.value == "chart" and elem.chart_data:
                elem_data["chart_type"] = elem.chart_data.chart_type
                elem_data["chart_title"] = elem.chart_data.title
                elem_data["chart_summary"] = elem.chart_data.summary

            if elem.element_type.value == "table" and elem.table_data:
                elem_data["table_rows"] = len(elem.table_data.rows)
                elem_data["table_cols"] = len(elem.table_data.rows[0]) if elem.table_data.rows else 0

            elem_data["language"] = elem.language

            slide_data["elements"].append(elem_data)

        slides.append(slide_data)

    return {"slides": slides}


@router.get("/job/{job_id}/element/{element_id}/image")
async def get_element_image(job_id: str, element_id: str):
    """Get the image data for a specific element."""
    if job_id not in presentations:
        raise HTTPException(status_code=404, detail="Presentation not found")

    presentation = presentations[job_id]

    for slide in presentation.slides:
        for elem in slide.elements:
            if elem.id == element_id and elem.image_base64:
                return {
                    "element_id": element_id,
                    "image_base64": elem.image_base64,
                    "content_type": elem.content_type.value,
                }

    raise HTTPException(status_code=404, detail="Element or image not found")


@router.post("/job/{job_id}/update")
async def update_elements(job_id: str, request: UpdateRequest):
    """Update element properties (alt-text, reading order, etc.)."""
    if job_id not in presentations:
        raise HTTPException(status_code=404, detail="Presentation not found")

    presentation = presentations[job_id]
    updated = []

    for update in request.updates:
        # Find the element
        for slide in presentation.slides:
            if slide.slide_number != update.slide_number:
                continue

            for elem in slide.elements:
                if elem.id != update.element_id:
                    continue

                # Apply updates
                if update.alt_text is not None:
                    elem.alt_text = update.alt_text
                    elem.alt_text_generated = False  # Mark as manually edited

                if update.reading_order is not None:
                    elem.reading_order = update.reading_order

                if update.is_decorative is not None:
                    elem.is_decorative = update.is_decorative

                if update.heading_level is not None:
                    elem.heading_level = update.heading_level

                updated.append(update.element_id)
                break

    return {"updated": updated, "count": len(updated)}


@router.get("/job/{job_id}/report", response_model=AccessibilityReport)
async def get_accessibility_report(job_id: str):
    """Get detailed accessibility report."""
    if job_id not in presentations:
        raise HTTPException(status_code=404, detail="Presentation not found")

    presentation = presentations[job_id]
    report = accessibility_checker.generate_report(presentation, job_id)

    return report


@router.post("/convert")
async def convert_to_pdf(request: ConversionRequest, background_tasks: BackgroundTasks):
    """Convert the analyzed presentation to accessible PDF."""
    job_id = request.job_id

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_id not in presentations:
        raise HTTPException(status_code=400, detail="Presentation not found")

    job = jobs[job_id]
    presentation = presentations[job_id]

    # Start conversion in background
    background_tasks.add_task(
        run_conversion,
        job_id,
        presentation,
        request.include_speaker_notes,
        request.pdf_ua_compliant,
    )

    job.status = "converting"
    job.progress = 85.0
    job.current_step = "Generating accessible PDF..."

    return {"job_id": job_id, "message": "PDF conversion started"}


async def run_conversion(
    job_id: str,
    presentation: Presentation,
    include_speaker_notes: bool,
    pdf_ua_compliant: bool,
):
    """Run PDF conversion."""
    job = jobs[job_id]

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")

        # Generate PDF
        pdf_generator.generate(
            presentation,
            output_path,
            include_speaker_notes=include_speaker_notes,
            pdf_ua_compliant=pdf_ua_compliant,
        )

        job.status = "complete"
        job.progress = 100.0
        job.current_step = "PDF generated successfully"
        job.output_path = output_path

    except Exception as e:
        job.status = "error"
        job.error_message = f"PDF generation failed: {str(e)}"


@router.get("/download/{job_id}")
async def download_pdf(job_id: str):
    """Download the generated PDF."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.status != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"PDF not ready. Current status: {job.status}"
        )

    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Get original filename
    filename = "accessible.pdf"
    if job_id in presentations:
        original = presentations[job_id].filename
        filename = original.rsplit('.', 1)[0] + "_accessible.pdf"

    return FileResponse(
        job.output_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    upload_path = os.path.join(UPLOAD_DIR, f"{job_id}.pptx")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")

    for path in [upload_path, output_path]:
        if os.path.exists(path):
            os.remove(path)

    # Remove from memory
    if job_id in jobs:
        del jobs[job_id]
    if job_id in presentations:
        del presentations[job_id]

    return {"message": "Job deleted successfully"}
