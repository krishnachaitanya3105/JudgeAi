# JudgeAI - Quick Start Guide

Get JudgeAI running in 5 minutes!

## 🚀 Quick Setup (Local Development)

### Step 1: Backend Setup (2 minutes)

```bash
# Navigate to project root
cd d:\JudgeAI

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
# (Ask for SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY)
```

### Step 2: Frontend Setup (1 minute)

```bash
# In a new terminal, from frontend directory
cd d:\JudgeAI\frontend

# Install dependencies
npm install
```

### Step 3: Start the Servers

**Terminal 1 - Backend:**
```bash
cd d:\JudgeAI
venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd d:\JudgeAI\frontend
npm run dev
```

### Step 4: Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/redoc

---

## 📋 Required Environment Variables

Create `.env` file in project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_STORAGE_BUCKET=court-judgments
GROQ_API_KEY=your-groq-api-key
```

### Where to Get These?

1. **SUPABASE_URL & SUPABASE_KEY**
   - Go to https://app.supabase.com
   - Select your project
   - Settings → API → Project URL and anon key

2. **GROQ_API_KEY**
   - Go to https://console.groq.com
   - Create API key in dashboard

---

## 📁 Key Directories

```
backend/
├── main.py           # FastAPI entry point
├── config.py         # Configuration & Supabase client
├── routers/          # API endpoints
├── services/         # Business logic (PDF, LLM)
├── models/           # Pydantic schemas
└── utils/            # Helpers (audit, deadline)

frontend/src/
├── pages/            # Full-page components
├── components/       # Reusable components
├── lib/              # Utilities & API client
└── router.jsx        # React Router setup
```

---

## 🧪 Test the System

### 1. Check Backend is Running
```bash
curl http://localhost:8000/
# Should return: {"status": "operational", "service": "JudgeAI API", "version": "1.0.0"}
```

### 2. Upload a PDF (via Frontend)
- Go to http://localhost:5173
- Drag & drop a PDF file
- System will automatically extract data

### 3. Check API Documentation
- Visit http://localhost:8000/docs
- Try endpoints from Swagger UI

---

## 🎯 Main Features

| Feature | Where |
|---------|-------|
| Upload PDF | Frontend home page |
| Extract Data | Auto-triggered after upload |
| Review/Approve | `/verification` page |
| View Dashboard | `/officer-dashboard` |
| Admin Analytics | `/admin-dashboard` (if admin) |
| Case Details | Click case in verification |

---

## 🔧 Common Commands

### Backend
```bash
# Run with auto-reload
uvicorn backend.main:app --reload

# Run without reload
python -m uvicorn backend.main:app

# Check installed packages
pip list
```

### Frontend
```bash
# Development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

---

## 📊 API Endpoints

### Upload & Extraction
- `POST /api/upload-pdf` - Upload judgment PDF
- `POST /api/extract-actions` - Extract data from PDF

### Verification
- `POST /api/approve-action/{id}` - Approve
- `POST /api/edit-action/{id}` - Edit
- `POST /api/reject-action/{id}` - Reject

### Dashboards
- `GET /api/officer-dashboard` - Officer stats
- `GET /api/admin-dashboard` - Admin analytics
- `GET /api/cases` - Get all cases

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'backend'"
- Ensure you're running from project root (`d:\JudgeAI`)
- Check venv is activated: `venv\Scripts\activate`

### Port 8000 already in use
```bash
# Kill existing process
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### API returning 500 errors
- Check .env file is configured
- Verify Supabase URL and keys are correct
- Check backend logs for error messages

### Frontend can't connect to backend
- Ensure backend is running on http://localhost:8000
- Check CORS allows localhost:5173
- Clear browser cache and reload

---

## 📚 Documentation

- **Full Setup Guide**: See `SETUP_GUIDE.md`
- **Implementation Checklist**: See `IMPLEMENTATION_CHECKLIST.md`
- **Project README**: See `README.md`
- **API Docs**: http://localhost:8000/docs (when backend running)

---

## ✅ Next Steps

1. Set up environment variables
2. Start backend server
3. Start frontend server
4. Upload a PDF to test
5. Check dashboards for data
6. Deploy to cloud (Heroku, Vercel, etc.)

---

**Ready to build?** 🚀

```bash
# One-command startup (if both servers are configured)
start cmd /k "cd d:\JudgeAI && venv\Scripts\activate && uvicorn backend.main:app --reload"
start cmd /k "cd d:\JudgeAI\frontend && npm run dev"
```

---

**Questions?** Check the full `SETUP_GUIDE.md` for detailed information.
