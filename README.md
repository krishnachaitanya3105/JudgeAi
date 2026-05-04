# ⚖️ JudgeAI

> AI-powered legal governance assistant for court judgment analysis and action extraction.

---

## 🏗️ Architecture

```
judgeai/
 ├── backend/
 │   ├── main.py              # FastAPI application entry point
 │   ├── config.py             # Environment config + Supabase client
 │   ├── routers/
 │   │   ├── upload.py         # POST /upload-pdf
 │   │   └── extract.py        # POST /extract-actions
 │   ├── services/
 │   │   ├── pdf_parser.py     # PyMuPDF + EasyOCR extraction
 │   │   └── llm_extractor.py  # Groq LLaMA3-8B pipeline
 │   ├── models/
 │   │   └── schemas.py        # Pydantic validation schemas
 │   └── utils/
 │       └── helpers.py        # Shared utility functions
 │
 ├── frontend/                 # React + Tailwind + shadcn/ui
 │   ├── src/
 │   └── components/
 │
 ├── .env                      # Environment variables
 ├── requirements.txt          # Python dependencies
 └── README.md
```

## 🚀 Tech Stack

| Layer     | Technology                         |
| --------- | ---------------------------------- |
| Backend   | FastAPI, Python 3.11+              |
| Frontend  | React, Vite, Tailwind CSS, shadcn/ui |
| Database  | Supabase (PostgreSQL)              |
| Storage   | Supabase Storage                   |
| AI/LLM    | Groq LLaMA3-8B                     |
| OCR       | PyMuPDF + EasyOCR                  |

## 📦 Setup

### Backend

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=court-judgments
GROQ_API_KEY=your_groq_api_key
```

## 🔌 API Endpoints

### `POST /api/upload-pdf`

Upload a court judgment PDF to Supabase Storage.

**Request:** `multipart/form-data`
- `file` — PDF file (required)
- `uploaded_by` — uploader name (default: `"system"`)

**Response:**
```json
{
  "message": "PDF uploaded successfully",
  "case_number": "CASE-A1B2C3D4E5",
  "pdf_url": "https://...",
  "metadata": { ... }
}
```

### `POST /api/extract-actions`

Extract structured data from a court judgment.

**Request:**
```json
{
  "pdf_url": "https://your-supabase-url/storage/v1/object/public/court-judgments/..."
}
```

**Response:**
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
  "status": "pending"
}
```

## 🗄️ Supabase Tables

### `cases`
| Column       | Type      | Description              |
| ------------ | --------- | ------------------------ |
| id           | uuid (PK) | Auto-generated           |
| case_number  | text      | Unique case identifier   |
| pdf_url      | text      | Public storage URL       |
| uploaded_by  | text      | Uploader name            |
| created_at   | timestamp | Upload timestamp         |

### `extracted_actions`
| Column           | Type      | Description                |
| ---------------- | --------- | -------------------------- |
| id               | uuid (PK) | Auto-generated             |
| case_number      | text      | Extracted case number      |
| judgment_date    | text      | Date of judgment           |
| department       | text      | Responsible department     |
| deadline         | text      | Compliance deadline        |
| directive        | text      | Required action/order      |
| confidence_score | float     | Extraction confidence 0-1  |
| pdf_url          | text      | Source PDF URL             |
| status           | text      | Processing status          |
| created_at       | timestamp | Extraction timestamp       |

## 📜 License

MIT © JudgeAI Team
