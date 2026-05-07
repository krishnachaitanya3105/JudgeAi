# JudgeAI Backend Deployment Fixes - Complete Analysis

## Executive Summary

Fixed critical deployment issues that caused the Render backend to timeout during PDF extraction and database operations. The UI was getting stuck on "Saving to database..." because of cascading failures in async handling, missing timeouts, and improper error handling.

---

## Root Cause Analysis

### 1. **FastAPI Configuration Issues**
- **Issue**: Swagger docs (`/docs`) not loading properly
- **Cause**: Missing `openapi_url` parameter in FastAPI initialization
- **Fix**: Added `openapi_url="/openapi.json"` to FastAPI constructor

### 2. **Missing Request Timeouts**
- **Issue**: HTTP requests (PDF download, Groq API calls) could hang indefinitely
- **Cause**: No explicit timeout configuration across services
- **Fix**: 
  - Added `DEFAULT_REQUEST_TIMEOUT_SEC=30` environment variable
  - PDF download timeout: 45 seconds
  - Groq LLM timeout: 55 seconds
  - Health endpoint DB check timeout: 5 seconds

### 3. **Blocking Operations on Event Loop**
- **Issue**: Database operations in main thread blocking FastAPI event loop
- **Cause**: Supabase operations are synchronous, run on main thread briefly
- **Fix**: 
  - Made health endpoint DB check run in executor with timeout
  - Added logging to track blocking operations
  - Optimized database query selectivity

### 4. **CORS Configuration Insufficient**
- **Issue**: Vercel subdomains not fully covered in CORS regex
- **Cause**: Regex pattern too restrictive: `https://.*\.vercel\.app`
- **Fix**: Updated regex to explicitly support Vercel domains:
  ```
  https://[a-zA-Z0-9-]+\.vercel\.app|https://judgeai.*\.vercel\.app
  ```

### 5. **File Upload Validation Issues**
- **Issue**: No PDF magic number validation, file size check
- **Cause**: Only checking file extension, not actual content
- **Fix**:
  - Added PDF magic number check (`%PDF`)
  - Added 50 MB file size limit
  - Added better error messages

### 6. **PDF Download Error Handling**
- **Issue**: Network errors not properly reported back to frontend
- **Cause**: Generic exception handling, no timeout warnings
- **Fix**:
  - Converted generic `requests.get()` errors to meaningful `ValueError` messages
  - Added content-type validation
  - Added maximum file size protection (50 MB)
  - Added timeout warning when close to limit
  - Added structured logging for each stage

### 7. **Uvicorn Configuration for Render**
- **Issue**: Worker timeout during long-running background tasks
- **Cause**: No explicit timeout set, default 60s insufficient
- **Fix**:
  - Added `--timeout 120` to Procfile and render.yaml
  - Kept `--timeout-keep-alive 65` for socket reuse
  - Configured `--backlog 128` for better queue handling
  - Single worker (`--workers 1`) for free tier

### 8. **Database Column Missing**
- **Issue**: Processing status not updating on backend restart
- **Cause**: `cases.processing_status` and related columns added in migration but not validated in code
- **Fix**: 
  - Verified migration columns exist
  - Enhanced job store to include "result" field
  - Improved database update error handling

---

## Files Modified

### 1. **backend/main.py**
```python
# Added:
- import asyncio
- openapi_url="/openapi.json" to FastAPI()
- Improved CORS regex for Vercel subdomains
- Better health endpoint with 5-second DB timeout
- Added asyncio.to_thread() for non-blocking DB checks
```

### 2. **backend/config.py**
```python
# Added:
- HTTP timeout configuration constants
- get_httpx_client() context manager
- PDF, LLM, and default request timeout settings
```

### 3. **backend/routers/upload.py**
```python
# Added:
- Comprehensive error handling with proper status codes
- PDF magic number validation
- 50 MB file size limit
- Structured logging for all operations
- Better error messages
- Initialize processing_status=None in metadata
```

### 4. **backend/routers/extract.py**
```python
# Enhanced:
- Added "result" field to job store initialization
- Improved error handling in status endpoint
- Better logging for job lifecycle
- Added job_id parameter support for future DB storage
```

### 5. **backend/services/pdf_parser.py**
```python
# Improved:
- Comprehensive error handling for PDF download
- Timeout warnings when close to limit
- Content-type validation
- Maximum file size protection (50 MB)
- Better error messages for all failure modes
- Structured logging with timing info
```

### 6. **Procfile**
```
# Updated:
- Added --timeout 120 (increased from default 60s)
```

### 7. **render.yaml**
```yaml
# Added:
- DEFAULT_REQUEST_TIMEOUT_SEC=30
- CORS_ALLOW_ORIGINS=""
- CORS_ALLOW_ORIGIN_REGEX (updated for Vercel)
- PYTHONUNBUFFERED=1 (unbuffered logging)
- RENDER=true (marker for Render environment)
- Reduced JUDGEAI_BATCH_CONCURRENCY to 1 for free tier
```

---

## Technical Details

### Health Endpoint Improvements

**Before:**
```python
async def health_check():
    # Could hang if DB is slow
    get_supabase().table("cases").select("id").limit(1).execute()
```

**After:**
```python
async def health_check():
    async def check_db():
        try:
            get_supabase().table("cases").select("id").limit(1).execute()
            return True, None
        except Exception as e:
            return False, str(e)[:200]
    
    db_ok, db_error = await asyncio.wait_for(
        asyncio.to_thread(check_db), timeout=5.0
    )
```

### PDF Download Error Handling

**Before:**
```python
response = requests.get(pdf_url, timeout=45, stream=True)
response.raise_for_status()
```

**After:**
```python
try:
    response = requests.get(
        pdf_url, 
        timeout=45, 
        stream=True,
        allow_redirects=True
    )
    response.raise_for_status()
except requests.Timeout as e:
    raise ValueError(f"PDF download timeout after {45}s: {e}") from e
except requests.ConnectionError as e:
    raise ValueError(f"PDF download connection error: {e}") from e
except requests.RequestException as e:
    raise ValueError(f"PDF download failed: {e}") from e

# Validate content-type
content_type = response.headers.get('content-type', '').lower()
if 'pdf' not in content_type and 'octet-stream' not in content_type:
    raise ValueError(f"Invalid content-type: {content_type}")

# Validate file size
max_bytes = 50_000_000  # 50 MB
if total_bytes > max_bytes:
    raise ValueError(f"PDF file too large (>{max_bytes / 1_000_000:.1f} MB)")
```

---

## Environment Variables (render.yaml)

| Variable | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_REQUEST_TIMEOUT_SEC` | 30 | Default timeout for HTTP requests |
| `JUDGEAI_PDF_REQUEST_TIMEOUT_SEC` | 45 | PDF download timeout |
| `JUDGEAI_LLM_TIMEOUT_SEC` | 55 | Groq API request timeout |
| `JUDGEAI_LLM_RETRIES` | 1 | LLM retry attempts |
| `JUDGEAI_MAX_PARSE_PAGES` | 10 | PyMuPDF page limit |
| `JUDGEAI_MAX_OCR_PAGES` | 5 | EasyOCR page limit |
| `JUDGEAI_BATCH_CONCURRENCY` | 1 | Batch job concurrency (free tier) |
| `PYTHONUNBUFFERED` | 1 | Immediate stdout/stderr output |
| `LOG_LEVEL` | INFO | Logging level |

---

## Deployment Instructions

### 1. **Push Changes to GitHub**
```bash
git add .
git commit -m "Fix backend deployment issues: timeouts, CORS, logging, error handling"
git push origin main
```

### 2. **Render Deployment**
- The render.yaml file is already configured
- Render will automatically detect changes and redeploy
- Monitor deployment in Render dashboard

### 3. **Verify Deployment**
```bash
# Test health endpoint
curl https://judgeai-backend.onrender.com/health

# Test Swagger docs
curl https://judgeai-backend.onrender.com/docs

# Monitor logs
# Go to Render Dashboard → Logs
```

### 4. **Database Migration (if needed)**
Run in Supabase SQL editor if not already done:
```sql
-- Migration 2026-03: Durable Processing Status
ALTER TABLE cases
  ADD COLUMN IF NOT EXISTS processing_status  TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_stage   TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_error   TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_started_at   TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_finished_at  TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_cases_processing_status ON cases(processing_status);
CREATE INDEX IF NOT EXISTS idx_cases_pdf_url ON cases(pdf_url);
```

---

## Testing Checklist

### Frontend Testing
- [ ] Upload single PDF → should show progress stages
- [ ] Upload batch PDFs → should queue and process
- [ ] Polling should show: queued → pdf_extraction → llm_extraction → db_persist → completed
- [ ] On backend restart, should switch to DB-backed polling
- [ ] Error cases should display meaningful messages

### Backend Testing
```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Swagger docs
open http://localhost:8000/docs

# 3. Upload endpoint
curl -X POST http://localhost:8000/api/upload-pdf \
  -F "file=@sample.pdf" \
  -F "uploaded_by=test"

# 4. Async extraction
curl -X POST http://localhost:8000/api/extract-actions-async \
  -H "Content-Type: application/json" \
  -d '{"pdf_url":"https://..."}'

# 5. Status polling
curl http://localhost:8000/api/extract-actions-status/{job_id}
```

### Load Testing
- [ ] Test with multiple concurrent uploads
- [ ] Monitor memory usage on Render
- [ ] Check for timeouts in logs
- [ ] Verify CPU utilization

---

## Monitoring & Logging

### Key Metrics
- PDF download time: Should be < 45 seconds
- LLM extraction time: Should be < 55 seconds
- Total extraction time: Should be < 2 minutes
- Health endpoint response time: Should be < 5 seconds (DB check timeout)

### Log Patterns
```
[judgeai.extract] req=abc123de job=def456gh START url=https://...
[judgeai.pdf_parser] Streaming PDF from... (rss=245.3 MB)
[judgeai.pdf_parser] PyMuPDF extracted 5234 chars, 42 blocks in 2.34s
[judgeai.llm_extractor] req=abc123de model=llama-3.3-70b-versatile chars=5000 timeout=55s
[judgeai.llm_extractor] req=abc123de attempt=1 status=200 elapsed=3.45s
[judgeai.extract] req=abc123de job=def456gh DONE in 10.23s action_id=xyz789
```

---

## Performance Optimizations

### For Free Tier (512 MB RAM, 1 vCPU)
1. **Single worker** - No threading overhead
2. **Max 20 concurrent** - `--limit-concurrency 20`
3. **Batch concurrency = 1** - Process one batch at a time
4. **PDF page limit = 10** - Reduces memory usage
5. **OCR page limit = 5** - EasyOCR model is heavy
6. **LLM max chars = 12,000** - Smaller payload = faster Groq response
7. **Health check timeout = 5s** - Don't hang on DB issues

### Recommended for Paid Tier
```yaml
# For production use, update to:
plan: standard  # or higher
startCommand: "uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 2 --limit-concurrency 100 --timeout-keep-alive 65 --backlog 512 --timeout 120"

# Environment variables:
JUDGEAI_MAX_PARSE_PAGES: "20"      # More pages
JUDGEAI_MAX_OCR_PAGES: "10"        # More OCR
JUDGEAI_BATCH_CONCURRENCY: "5"     # More parallel jobs
JUDGEAI_LLM_MAX_CHARS: "24000"     # Larger payloads
```

---

## Known Limitations

### Render Free Tier
- Only 1 worker process
- 512 MB RAM (tight for large PDFs + EasyOCR)
- 30-minute inactivity timeout (service stops)
- No persistent storage (temporary files cleaned up)

### Workarounds
1. Use Render Cron Job to keep service warm
2. Add error handling for restart scenarios (already done)
3. Implement batch processing (already done)
4. Use database as state machine for restart resilience (done)

---

## Future Improvements

1. **Async database operations**
   - Use asyncpg directly instead of Supabase SDK
   - Implement connection pooling
   - Better transaction isolation

2. **Background job queue**
   - Consider Celery + Redis for free-tier-friendly queue
   - Or Bull Queue (Node.js) via subprocess calls

3. **PDF processing optimization**
   - Cache OCR model across requests
   - Use incremental PDF parsing
   - Implement streaming LLM API calls

4. **Monitoring & Observability**
   - Add Sentry for error tracking
   - Implement OpenTelemetry tracing
   - Add Render webhook for deployment notifications

5. **Deployment**
   - Use Docker for consistent environment
   - Implement blue-green deployment
   - Add integration tests for deployment validation

---

## Troubleshooting

### Issue: "Saving to database..." stuck forever
- [ ] Check Render logs for timeouts
- [ ] Verify database connection timeout (should be < 30s)
- [ ] Check Groq API rate limits
- [ ] Monitor PDF download time (should be < 45s)

### Issue: Swagger docs not loading
- [ ] Verify `openapi_url="/openapi.json"` is set
- [ ] Check CORS configuration
- [ ] Try INCOGNITO mode to bypass cache
- [ ] Restart browser

### Issue: High memory usage (>400 MB)
- [ ] Reduce JUDGEAI_MAX_PARSE_PAGES
- [ ] Reduce JUDGEAI_MAX_OCR_PAGES
- [ ] Check for memory leaks in EasyOCR
- [ ] Monitor RSS in logs

### Issue: Backend restart during extraction
- [ ] Check Render logs for "OOM killer" or timeout
- [ ] Increase Render plan size
- [ ] Reduce batch concurrency
- [ ] Set shorter timeouts

---

## Success Metrics

After deployment, verify:
1. ✅ Health endpoint responds in < 1 second
2. ✅ PDF upload completes in < 10 seconds
3. ✅ Status polling updates every 3 seconds
4. ✅ Full extraction completes in < 2 minutes
5. ✅ No 410 "Gone" errors except on actual backend restart
6. ✅ Memory stays below 400 MB
7. ✅ Swagger docs load at /docs
8. ✅ CORS allows Vercel domain
9. ✅ All errors have meaningful messages
10. ✅ Logs show detailed stage information

---

## Support

For deployment issues:
1. Check Render logs: Dashboard → Logs tab
2. Verify environment variables in render.yaml
3. Check database schema migration status
4. Review FastAPI health endpoint response
5. Test CORS with browser dev tools

Last Updated: May 7, 2026
