# JudgeAI - Complete Setup & Deployment Guide

## Overview

This document provides complete setup instructions for deploying the JudgeAI system, including backend, frontend, database schema, and RLS policies.

## Architecture

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│   React     │       │   FastAPI    │       │  Supabase    │
│  Frontend   │◄────►│   Backend    │◄────►│  PostgreSQL  │
│  (Vite)     │       │ (Python)     │       │   + Auth     │
└─────────────┘       └──────────────┘       └──────────────┘
                             │
                             │
                       ┌─────▼──────┐
                       │ Groq LLM   │
                       │ LLaMA3-8B  │
                       └────────────┘
```

## Prerequisite

Setup: Backend

### 1. Install Python Dependencies

```bash
cd d:\JudgeAI
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create .env File

```bash
# In d:\JudgeAI\.env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_STORAGE_BUCKET=court-judgments
GROQ_API_KEY=your-groq-api-key
```

**Get these values:**
- SUPABASE_URL & SUPABASE_KEY: From [Supabase Dashboard](https://app.supabase.com)
- GROQ_API_KEY: From [Groq Console](https://console.groq.com)

### 3. Setup Supabase Database Schema

1. Go to Supabase Dashboard → SQL Editor
2. Create a new query and paste contents from `backend/db_schema.sql`
3. Run the query
4. Enable RLS on all tables (already included in schema)

### 4. Create Storage Bucket

1. Go to Supabase Dashboard → Storage
2. Create a new bucket named `court-judgments`
3. Set it to **Public** for file access

### 5. Run Backend Server

```bash
cd d:\JudgeAI
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000/api`

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Part 2: Frontend Setup

### 1. Install Node Dependencies

```bash
cd d:\JudgeAI\frontend
npm install
```

### 2. Create .env.local (Optional)

```bash
# frontend/.env.local
VITE_API_URL=http://localhost:8000/api
```

### 3. Run Development Server

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

---

## Part 3: Supabase Configuration Details

### Database Schema Overview

#### users
Stores user information (officers, admins, reviewers)
```sql
- id: UUID (primary key)
- email: VARCHAR (unique)
- full_name: VARCHAR
- role: VARCHAR (officer|admin|reviewer)
- department: VARCHAR
- is_active: BOOLEAN
```

#### cases
Stores uploaded court judgment metadata
```sql
- id: UUID (primary key)
- case_number: VARCHAR (unique)
- pdf_url: TEXT
- uploaded_by: VARCHAR
- department: VARCHAR
- status: VARCHAR (pending|processing|completed|archived)
```

#### extracted_actions
Stores AI-extracted judgment data
```sql
- id: UUID (primary key)
- case_number: VARCHAR
- judgment_date: DATE
- department: VARCHAR
- deadline: DATE
- directive: TEXT
- confidence_score: DECIMAL (0.0 - 1.0)
- status: VARCHAR (pending|approved|edited|rejected|completed)
- source_sentence: TEXT
```

#### audit_logs
Tracks all changes and approvals
```sql
- id: UUID (primary key)
- case_id: VARCHAR
- action_type: VARCHAR
- old_value: TEXT
- new_value: TEXT
- edited_by: VARCHAR
- timestamp: TIMESTAMP WITH TIME ZONE
```

#### verification_queue
Workflow queue for officer verification
```sql
- id: UUID (primary key)
- extracted_action_id: UUID (FK)
- assigned_to: UUID (FK)
- priority: VARCHAR (urgent|warning|normal)
- status: VARCHAR (pending|in_progress|completed)
- due_date: DATE
```

### Row Level Security (RLS) Policies

All tables have RLS enabled. Key policies:

**Officers see only their department data:**
```sql
SELECT: department = current_user_department
UPDATE: department = current_user_department
```

**Admins see all data:**
```sql
SELECT: role = 'admin'
UPDATE: role = 'admin'
```

---

## API Endpoints

### Upload & Extraction

- `POST /api/upload-pdf` - Upload judgment PDF
- `POST /api/extract-actions` - Extract judgment data

### Verification

- `POST /api/approve-action/{id}` - Approve extracted action
- `POST /api/edit-action/{id}` - Edit and update action
- `POST /api/reject-action/{id}` - Reject action with reason

### Dashboards

- `GET /api/officer-dashboard` - Officer dashboard data
- `GET /api/admin-dashboard` - Admin analytics
- `GET /api/cases` - Get cases (paginated, filterable)

### Status Codes

- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Processing error
- `500 Internal Server Error` - Server error

---

## Frontend Pages & Components

### Pages

| Page | Route | Role | Description |
|------|-------|------|-------------|
| Home | `/` | Public | Upload interface |
| Verification | `/verification` | Officer | Review & approve extractions |
| Officer Dashboard | `/officer-dashboard` | Officer | Dashboard with stats |
| Admin Dashboard | `/admin-dashboard` | Admin | Analytics & monitoring |
| Case Details | `/case/:id` | Officer/Admin | Full case review |

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| UploadCard | `components/UploadCard.jsx` | PDF upload with progress |
| ExtractionResults | `components/ExtractionResults.jsx` | Show extraction results |
| ConfidenceIndicator | `components/ConfidenceIndicator.jsx` | Display confidence score |
| Navbar | `components/Navbar.jsx` | Navigation & routing |
| Hero | `components/Hero.jsx` | Landing page intro |

---

## Deployment Checklist

### Backend (FastAPI)

- [ ] Virtual environment created with all dependencies
- [ ] .env file configured with real API keys
- [ ] Supabase database schema loaded
- [ ] Supabase storage bucket created
- [ ] CORS configured for frontend URL
- [ ] Backend running without errors
- [ ] API documentation accessible at `/docs`

### Frontend (React/Vite)

- [ ] Node modules installed
- [ ] API base URL configured
- [ ] React Router working
- [ ] All pages loading correctly
- [ ] Navigation links functional
- [ ] Build passes: `npm run build`

### Database (Supabase)

- [ ] All tables created
- [ ] Indexes created for performance
- [ ] RLS policies enabled
- [ ] Triggers set up for updated_at
- [ ] Views created for dashboards
- [ ] Test user accounts created

### Production Deployment

1. **Backend**
   ```bash
   # Use Gunicorn for production
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 backend.main:app
   ```

2. **Frontend**
   ```bash
   npm run build
   # Serve with your hosting provider (Netlify, Vercel, etc.)
   ```

3. **Environment Variables**
   - Keep sensitive keys in environment only
   - Use different keys for dev/staging/production
   - Rotate keys regularly

---

## Testing the System

### 1. Upload Test PDF

```bash
curl -X POST http://localhost:8000/api/upload-pdf \
  -F "file=@test.pdf" \
  -F "uploaded_by=test_officer"
```

### 2. Extract Actions

```bash
curl -X POST http://localhost:8000/api/extract-actions \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "https://your-storage-url/path/to/pdf.pdf"}'
```

### 3. Approve Action

```bash
curl -X POST http://localhost:8000/api/approve-action/action-id \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "officer_name"}'
```

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError: No module named 'backend'"**
- Run commands from project root (d:\JudgeAI)
- Ensure venv is activated

**"SUPABASE_URL not found"**
- Check .env file exists in project root
- Verify env variable names match exactly
- Reload backend after changing .env

**PDF extraction fails**
- Check PDF is valid and not corrupted
- Try with PyMuPDF first, then EasyOCR fallback
- Increase timeout if file is large

### Frontend Issues

**"API call failed: localhost:8000"**
- Ensure backend is running on 8000
- Check CORS configuration in FastAPI
- Use http:// not https:// for local dev

**Router not working**
- React Router is installed and imported
- All page components are created
- Run `npm list react-router-dom` to verify

**Styles not loading**
- Ensure Tailwind CSS is configured in vite.config.js
- Check tailwind.config.js exists
- Run `npm install` again

### Database Issues

**"RLS policy denies INSERT"**
- Check RLS policies are correctly set
- Ensure user has correct role in users table
- Test policies in Supabase SQL editor

**"Storage bucket not found"**
- Create bucket named exactly `court-judgments`
- Set bucket to Public
- Verify bucket name in config.py

---

## Next Steps

1. **User Authentication**: Integrate Supabase Auth
2. **Email Notifications**: Set up notification system
3. **Export Reports**: Add case report generation
4. **Analytics**: Enhanced dashboard metrics
5. **Mobile App**: React Native version

---

## Support & Documentation

- **FastAPI Docs**: http://localhost:8000/docs
- **Supabase Docs**: https://supabase.com/docs
- **Groq API**: https://console.groq.com/docs
- **React Router**: https://reactrouter.com

---

**Last Updated**: March 2024
**Version**: 1.0.0
