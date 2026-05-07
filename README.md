# ⚖️ JudgeAI

> AI-powered legal governance assistant for court judgment analysis and action extraction.

---

## 🌐 Live Demo

Frontend: https://judge-ai-nu.vercel.app/login

Backend API Docs: https://judgeai-x9c6.onrender.com/docs

GitHub Repository: https://github.com/krishnachaitanya3105/JudgeAi

---

## 📌 Overview

JudgeAI is an AI-powered legal analysis platform designed to process court judgment PDFs and extract structured legal insights automatically. The system uses OCR, NLP, and Large Language Models to analyze legal documents and generate actionable summaries, compliance directives, deadlines, and analytics.

The platform helps simplify legal document review by transforming unstructured court judgments into structured and searchable information.

---

## 🏗️ Project Architecture

```text
judgeai/
 ├── backend/
 │   ├── main.py              # FastAPI application entry point
 │   ├── config.py            # Environment configuration
 │   ├── routers/
 │   │   ├── upload.py        # PDF upload APIs
 │   │   └── extract.py       # AI extraction APIs
 │   ├── services/
 │   │   ├── pdf_parser.py    # PDF text extraction
 │   │   └── llm_extractor.py # Groq LLM processing
 │   ├── models/
 │   │   └── schemas.py       # Pydantic schemas
 │   └── utils/
 │       └── helpers.py       # Utility functions
 │
 ├── frontend/
 │   ├── src/
 │   └── components/
 │
 ├── requirements.txt
 ├── .env
 └── README.md
```

---

## 🚀 Features

- Upload and analyze court judgment PDFs
- AI-generated legal summaries
- Action and directive extraction
- Deadline identification
- Confidence score generation
- OCR-based PDF text extraction
- Structured legal analytics dashboard
- FastAPI backend with Swagger documentation
- Responsive React frontend UI

---

## 🛠️ Tech Stack

### Frontend
- React.js
- Vite
- Tailwind CSS
- shadcn/ui

### Backend
- FastAPI
- Python 3.11+

### AI & NLP
- Groq LLaMA3-8B
- NLP-based legal analysis

### OCR & PDF Processing
- PyMuPDF
- EasyOCR

### Database & Deployment
- Supabase
- Render
- Vercel

---

# ⚙️ Installation & Setup

## Prerequisites

Make sure the following are installed:

- Node.js (v18 or above)
- Python 3.10+
- pip
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/krishnachaitanya3105/JudgeAi.git
cd JudgeAi
```

---

# 🔧 Backend Setup

## Navigate to Backend

```bash
cd backend
```

## Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Backend Dependencies

```bash
pip install -r requirements.txt
```

---

## Backend Environment Variables

Create a `.env` file inside the backend folder and add:

```env
PORT=5000
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_STORAGE_BUCKET=court-judgments
GROQ_API_KEY=your_groq_api_key
```

---

## Run Backend Server

```bash
uvicorn main:app --reload --port 5000
```

Backend will run at:

```text
http://localhost:5000
```

Swagger API Docs:

```text
http://localhost:5000/docs
```

---

# 🎨 Frontend Setup

## Navigate to Frontend

```bash
cd frontend
```

---

## Install Frontend Dependencies

```bash
npm install
```

---

## Frontend Environment Variables

Create a `.env` file inside the frontend folder and add:

```env
VITE_API_BASE_URL=http://localhost:5000
```

---

## Run Frontend

```bash
npm run dev
```

Frontend will run at:

```text
http://localhost:5173
```

---

# 📄 API Endpoints

## POST `/api/upload-pdf`

Uploads a court judgment PDF.

### Request
- Content-Type: `multipart/form-data`

### Parameters
- `file` → PDF file
- `uploaded_by` → uploader name

### Response

```json
{
  "message": "PDF uploaded successfully",
  "case_number": "CASE-A1B2C3D4E5",
  "pdf_url": "https://example.com/sample.pdf"
}
```

---

## POST `/api/extract-actions`

Extracts structured legal information from uploaded judgments.

### Request

```json
{
  "pdf_url": "https://your-storage-url/sample.pdf"
}
```

### Response

```json
{
  "extracted_data": {
    "case_number": "WP(C) 12345/2024",
    "judgment_date": "2024-03-15",
    "department": "Ministry of Environment",
    "deadline": "2024-06-15",
    "directive": "Submit compliance report within 90 days",
    "confidence_score": 0.85
  },
  "status": "success"
}
```

---

# 🗄️ Database Schema

## `cases` Table

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary Key |
| case_number | text | Unique case number |
| pdf_url | text | Uploaded PDF URL |
| uploaded_by | text | Uploader name |
| created_at | timestamp | Upload timestamp |

---

## `extracted_actions` Table

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary Key |
| case_number | text | Extracted case number |
| judgment_date | text | Judgment date |
| department | text | Concerned department |
| deadline | text | Compliance deadline |
| directive | text | Legal directive |
| confidence_score | float | AI confidence score |
| pdf_url | text | Source PDF |
| status | text | Extraction status |
| created_at | timestamp | Timestamp |

---

# 🧪 Testing the Application

1. Start backend server
2. Start frontend application
3. Open frontend in browser
4. Upload a court judgment PDF
5. Wait for AI analysis
6. View extracted summaries and analytics

---

# 🚀 Deployment

## Frontend
- Vercel

## Backend
- Render

## Database & Storage
- Supabase

---

# 📷 Demo

Frontend Demo:
https://judge-ai-nu.vercel.app/login

Backend API Docs:
https://judgeai-x9c6.onrender.com/docs

---

# 📜 License

MIT License © JudgeAI Team
