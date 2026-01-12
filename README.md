# PPTX to Accessible PDF Converter

An AI-powered web application that converts PowerPoint presentations to fully accessible PDFs with PDF/UA compliance.

## Features

- **AI-Powered Alt-Text Generation**: Uses Claude Vision to automatically generate descriptive alt-text for images
- **Smart Reading Order Detection**: AI analyzes slide layouts to determine optimal reading order for screen readers
- **PDF/UA Compliance**: Generates tagged PDFs that meet accessibility standards
- **Interactive Editing**: Review and edit alt-text and reading order before conversion
- **Accessibility Report**: Comprehensive analysis with score and issue detection
- **Color Contrast Checking**: WCAG-compliant contrast ratio analysis
- **Language Detection**: Automatic language tagging for multilingual presentations
- **Chart Accessibility**: Extracts chart data and generates text descriptions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Anthropic API key (for AI features)

### Running with Docker

1. Clone the repository and navigate to the project directory:
   ```bash
   cd pptx2pdf-accessible
   ```

2. Create a `.env` file with your Anthropic API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. Start the application:
   ```bash
   docker-compose up --build
   ```

4. Open http://localhost:3000 in your browser

### Development Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
python main.py
```

Backend runs at http://localhost:8000

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

## Architecture

```
pptx2pdf-accessible/
├── backend/               # FastAPI Python backend
│   ├── api/              # API routes and models
│   ├── core/             # Core processing modules
│   │   ├── pptx_parser.py      # PPTX file parsing
│   │   ├── ai_analyzer.py      # Claude AI integration
│   │   ├── structure_builder.py # Document structure
│   │   ├── pdf_generator.py    # PDF creation
│   │   └── accessibility.py    # Accessibility checking
│   └── utils/            # Utility functions
├── frontend/             # React TypeScript frontend
│   └── src/
│       ├── components/   # React components
│       ├── hooks/        # Custom hooks
│       └── types/        # TypeScript types
└── docker-compose.yml    # Docker configuration
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload PPTX file |
| `/api/analyze` | POST | Start AI analysis |
| `/api/job/{id}` | GET | Get job status |
| `/api/job/{id}/slides` | GET | Get slides data |
| `/api/job/{id}/report` | GET | Get accessibility report |
| `/api/job/{id}/update` | POST | Update element properties |
| `/api/convert` | POST | Generate PDF |
| `/api/download/{id}` | GET | Download PDF |

## Accessibility Standards

This tool helps create PDFs that comply with:

- **PDF/UA (ISO 14289-1)**: Universal Accessibility standard for PDF
- **WCAG 2.1**: Web Content Accessibility Guidelines
- **Section 508**: US federal accessibility requirements

## Key Technologies

- **Backend**: Python, FastAPI, python-pptx, ReportLab, pikepdf
- **Frontend**: React, TypeScript, Tailwind CSS, dnd-kit
- **AI**: Anthropic Claude API (claude-sonnet-4-20250514)

## License

MIT License
