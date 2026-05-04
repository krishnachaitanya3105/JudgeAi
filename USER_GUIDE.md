# JudgeAI User Guide

**Version:** 1.0  
**Last Updated:** May 2, 2026  
**Audience:** Government Officers, Administrators, Verification Staff

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Roles & Permissions](#user-roles--permissions)
3. [Main Features](#main-features)
4. [Step-by-Step Workflows](#step-by-step-workflows)
5. [Understanding Results](#understanding-results)
6. [Admin Tasks](#admin-tasks)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- **Browser:** Chrome, Firefox, Safari, or Edge (latest versions)
- **Internet:** Stable connection required for PDF uploads and extraction
- **OS:** Windows, macOS, or Linux
- **JavaScript:** Enabled in browser

### Accessing JudgeAI

1. Open your browser
2. Navigate to: **http://localhost:5173** (development) or your deployment URL
3. You'll see the **JudgeAI Home Page** with upload and login options

### First Login

1. Click **Login** in the top navigation
2. Enter your email and password (provided by administrator)
3. Click **Sign In**
4. You'll be redirected to your role-specific dashboard

---

## User Roles & Permissions

### 1. **Government Officer** (Default User Role)

**Primary Task:** Review extracted information and verify judgments

**Access:**
- Officer Dashboard (view and filter cases)
- Verification Queue (approve, edit, or reject extractions)
- Case Details page (view full information and explainability)
- Download case documents

**What You Can Do:**
- ✅ View pending cases for review
- ✅ Approve AI extraction as accurate
- ✅ Edit extracted fields with corrections
- ✅ Reject extractions and provide feedback
- ✅ View confidence scores and reasoning
- ✅ Search for specific cases
- ✅ Download PDFs for reference

---

### 2. **Administrator** (Admin Role)

**Primary Task:** Manage system, upload documents, monitor quality

**Access:**
- Everything Officers can do
- Admin Dashboard (system-wide analytics)
- Upload interface (single & batch PDF upload)
- Officer management (create/remove users)
- Analytics and reporting
- System statistics and health

**What You Can Do:**
- ✅ All Officer permissions
- ✅ Upload PDF judgment files
- ✅ Create new officer accounts
- ✅ View system-wide analytics
- ✅ Download analytics reports (CSV)
- ✅ Monitor extraction quality metrics
- ✅ View confidence fusion statistics

---

## Main Features

### Feature 1: Upload Judgments

**What it does:** Import PDF files containing court judgments into the system

**How to access:**
- Home page (public) → Upload section
- Admin Dashboard → "Upload" button
- Admin Dashboard → "Create Officer" modal (officer management)

**Single Upload:**
1. Click "Choose File" button
2. Select a PDF judgment file from your computer
3. Click "Upload"
4. Wait for confirmation (typically 5-30 seconds)
5. Case will appear in verification queue when extraction completes

**Batch Upload:**
1. Select multiple PDF files (Ctrl+Click or Shift+Click)
2. Click "Upload"
3. System processes files sequentially
4. Track job status via unique job ID

**File Requirements:**
- Format: PDF only
- Size: Up to 50MB recommended
- Content: Court judgment documents (not other legal docs)
- Quality: Clear, readable text (OCR-friendly)

---

### Feature 2: Officer Dashboard

**What it does:** Central view of all cases for verification workflow

**How to access:** Login as Officer → Auto-redirected to dashboard

**Dashboard Sections:**

**A. Quick Stats Cards (Top)**
- Pending Cases: Number awaiting your review
- Approved Cases: You've verified
- Completed Cases: Fully processed
- Urgent Deadlines: Cases within 7 days
- Total Extracted: System-wide count

**B. Recent Uploads**
- Latest files uploaded to system
- Case numbers and upload dates
- Direct link to case details

**C. Department Pending Breakdown**
- Cases pending per department
- Ministry of Finance, Transport, Health, etc.
- Click to filter by department

**D. Filter & Search**
- Search by Case Number
- Filter by Status (pending, approved, rejected, edited)
- Filter by Department
- Sort by Upload Date or Deadline

**E. Case List**
- Displays cases matching your filters
- Shows: Case #, Department, Deadline, Priority, Status
- Click row → Opens Case Details

---

### Feature 3: Verification Queue

**What it does:** Dedicated page for reviewing and approving extracted information

**How to access:** Top navigation → "Verification" (or "Verification Queue")

**Workflow:**

1. **View Pending Case**
   - Page shows one case at a time
   - Extracted fields displayed in clear layout
   - Color-coded priority: RED (High), YELLOW (Medium), GREEN (Low)

2. **Review Extracted Data**
   - Case Number, Judgment Date, Department
   - Deadline, Directive (court order)
   - Recommended action type
   - Appeal recommendation

3. **Take Action**
   - **Approve:** Confirms extraction is correct
     - Click "✓ Approve" button
     - Case marked as `approved` in system
   
   - **Edit:** Modify one or more fields
     - Click "✎ Edit" button
     - Modal opens with all editable fields
     - Make corrections
     - Click "Save Changes"
     - Case marked as `edited` with user notation
   
   - **Reject:** Extraction cannot be salvaged
     - Click "✗ Reject" button
     - Enter rejection reason (required)
     - Case marked as `rejected` for re-extraction

4. **Move to Next Case**
   - After action, automatically loads next pending case
   - Or click "← Back to Queue" to see list view

**Keyboard Shortcuts:**
- `A` → Approve current case
- `E` → Open edit modal
- `R` → Open reject dialog
- `N` → Next case

---

### Feature 4: Case Details Page

**What it does:** Deep dive into a single case with full context and explainability

**How to access:**
- Click case row from Officer Dashboard
- Click case row from Verification Queue
- Direct URL: `/cases/{case_id}`

**Page Layout:**

**Left Column:**

**Case Information Card:**
- Case Number (unique identifier)
- Judgment Date (when court issued decision)
- Department (responsible ministry/authority)
- Deadline (action must complete by this date)
- Action Type (compliance, appeal review, etc.)
- Priority Level (HIGH, MEDIUM, LOW)

**Confidence Score Gauge:**
- Visual circular meter (0-100%)
- Color: GREEN (70%+), YELLOW (40-69%), RED (<40%)
- Label: HIGH/MEDIUM/LOW CONFIDENCE
- **Subtitle: "Final Confidence Score"** (fused, not LLM-only)

**Fusion Transparency Table:**
- Shows how confidence was calculated
- Columns:
  - Subsystem (LLM, Timeline Parser, Department Classifier, Appeal Recommender)
  - Raw signal (original score from each AI component)
  - Effective (clamped to 0-1 range)
  - Weight (% contribution to final score)
  - Weighted term (contribution amount)
  - Imputed? (was data estimated vs. extracted?)

**PDF Viewer (with Highlights):**
- Original judgment PDF displayed
- Color highlights show key information:
  - 🟨 **Yellow** = Directive (court order)
  - 🟦 **Blue** = Deadline (dates, time references)
  - 🟩 **Green** = Party names (petitioner, respondent)
- Hover over highlight for tooltip
- Can pan and zoom PDF
- Download button for full PDF

**Government Action Plan Card:**
- Department (responsible authority)
- Compliance Deadline (date to complete action)
- Appeal Recommended? (YES/NO/REVIEW)
- Appeal Window Ends (deadline to file appeal)
- Responsible Role (officer type needed)

**AI Explainability Section:**
- **Why appeal recommended:** Shows appeal classifier reasoning
- **Why department selected:** Explains department assignment logic
- **Why deadline inferred:** Shows how deadline was calculated
- Each field includes confidence level and data sources

**Directive Card:**
- Full text of court order/directive

**Source Sentence Card:**
- Key sentence that triggered extraction
- Highlighted for reference

**Audit/Activity Log (Right Column):**
- All changes to this case
- Timestamp, operator name, action taken
- Before/after values for edits
- Rejection reasons
- Approval confirmations

---

### Feature 5: Admin Dashboard

**What it does:** System-wide view of operations, quality metrics, and officer management

**How to access:** Login as Admin → Click "Admin" in navigation

**Dashboard Sections:**

**A. System Overview Cards**
- Total Cases: All judgments in system
- Active Departments: Entities with pending cases
- Pending Verification: Awaiting officer review
- Verification Accuracy: % approved vs. total

**B. Government Decision Intelligence Widgets**
- Appeal Recommended Cases (list with deadlines)
- Compliance Required (action-needed cases)
- Upcoming Deadlines (7-day window alerts)
- Department Pending Backlog (queue per ministry)

**C. Confidence Fusion Analytics**
- Exact Statistics: Count, mean, min, max, std dev of final scores
- Reference Information: Neutral imputation value, default weights
- Subsystem Breakdown: Individual confidence stats per AI component
- Per-Action Snapshots: Fusion details for each case

**D. Performance Analytics (Charts)**
- **Status Distribution (Pie Chart):** Pending, Approved, Edited, Rejected breakdown
- **Verification Stats (Bar Chart):** Counts for each status
- **Cases per Department (Horizontal Bar):** Volume distribution
- **Accuracy Trend (Area Chart):** Approval rate over time

**E. Officer Management**
- "Create Officer" button (top right)
- Form to add new verification staff
- Email, password, full name required

**F. Export Data**
- "Export CSV" button (top right)
- Downloads analytics report with:
  - Summary statistics
  - Per-action fusion breakdown
  - Reference values
  - Importable to Excel/analytics tools

---

### Feature 6: Semantic Search

**What it does:** Find cases by meaning/context, not just keywords

**How to use:**
1. Navigate to search bar (top navigation or dashboard)
2. Enter query: "appeal limitation compliance deadline"
3. System returns ranked cases matching that meaning
4. Results show case number, similarity score, PDF link

**Queries That Work Well:**
- "Ministry of Finance budget allocation appeal"
- "compliance deadline infrastructure project"
- "limitation period appeal review judgment"
- "party names petitioner respondent"

**Results Include:**
- Case Number
- Similarity Score (0-1, higher = better match)
- PDF Download Link
- Creation Date

---

## Step-by-Step Workflows

### Workflow A: Upload & Verify a Single Judgment

**Time:** ~15 minutes

**Steps:**

1. **Login**
   - Go to http://localhost:5173
   - Click "Login" → Enter credentials

2. **Upload PDF** (if Admin)
   - Click "Admin" → "Upload" button (or Home → Upload section)
   - Select judgment PDF file
   - Click "Upload"
   - Wait for success notification

3. **View in Dashboard**
   - Go to Officer Dashboard (Auto-redirect or click "Dashboard")
   - See newly uploaded case in "Recent Uploads"
   - Or search by case number

4. **Open Verification Queue**
   - Click "Verification" in top nav
   - System shows first pending case
   - Review extracted data

5. **Review & Verify**
   - Read case information
   - Check extracted fields against PDF
   - Compare with Case Details page highlights

6. **Take Action**
   - If correct: Click "✓ Approve"
   - If errors: Click "✎ Edit" → Fix fields → "Save Changes"
   - If unusable: Click "✗ Reject" → Explain reason

7. **Next Case**
   - Queue automatically loads next pending case
   - Repeat steps 5-6

---

### Workflow B: Batch Upload Multiple Judgments

**Time:** ~30 minutes (for 20 files)

**Steps:**

1. **Prepare Files**
   - Gather all PDF files in one folder
   - Organize by naming (e.g., `Case_001.pdf`, `Case_002.pdf`)

2. **Navigate to Upload**
   - Admin Dashboard → "Upload" button
   - OR Home page → Upload section

3. **Select Multiple Files**
   - Click "Choose Files" button
   - Hold `Ctrl` (Windows) or `Cmd` (Mac)
   - Click each file you want to upload
   - OR hold `Shift` and click first + last file to select range

4. **Start Upload**
   - Click "Upload" or "Start Upload" button
   - System queues files for processing

5. **Track Progress**
   - You'll see a job ID (e.g., `job-abc123def456`)
   - Can check status in background
   - Email notification when batch completes (optional)

6. **Verify Uploaded Cases**
   - Cases appear in Officer Dashboard as they complete
   - Create verification queue for team

---

### Workflow C: Find & Edit a Case

**Time:** ~5 minutes

**Steps:**

1. **Search or Filter**
   - Dashboard → Search by Case Number
   - OR Dashboard → Filter by Department/Status

2. **Open Case Details**
   - Click case row
   - Full details page opens

3. **View All Information**
   - Read extracted data
   - Check confidence fusion breakdown
   - Review PDF highlights
   - Read AI explainability

4. **Edit If Needed**
   - Click "✎ Edit" button
   - Modal opens with all editable fields
   - Modify as needed
   - Click "Save Changes"

5. **Track Changes**
   - Activity log (right side) updates immediately
   - Shows: timestamp, operator, action, before/after

6. **Export/Share**
   - Click "Download PDF" button
   - Or copy case number to share

---

### Workflow D: Monitor System Health (Admin)

**Time:** ~10 minutes daily

**Steps:**

1. **Login as Admin**
   - Go to dashboard → Click "Admin"

2. **Check Quick Stats**
   - Pending Verification: Any backlog?
   - Verification Accuracy: Above 70%? (good)
   - Urgent Deadlines: Any critical cases?

3. **Review Department Backlog**
   - Check each ministry for pending cases
   - Identify bottlenecks

4. **Check Analytics**
   - Scroll to "Confidence Fusion Analytics"
   - Mean confidence score: Should be 0.75+
   - Look for subsystems with low scores

5. **Review Charts**
   - Status distribution: Most approved or edited?
   - Accuracy trend: Improving or declining?

6. **Export Report**
   - Click "Export CSV"
   - Download for stakeholder reporting
   - Share with management

---

## Understanding Results

### Confidence Score Explained

**What It Means:** How confident the AI is in its extraction (0-100%)

**Components:**
- **35% from LLM Extraction:** Quality of text parsing by language model
- **25% from Timeline Parser:** Success in extracting deadline information
- **20% from Department Classifier:** Quality of department assignment
- **20% from Appeal Recommender:** Confidence in appeal prediction

**Interpretation:**
- **80-100% (Green):** HIGH confidence - likely accurate
- **50-79% (Yellow):** MEDIUM confidence - review carefully
- **0-49% (Red):** LOW confidence - verify thoroughly before approval

**Example:**
```
Final = 0.35×(0.92) + 0.25×(0.88) + 0.20×(0.85) + 0.20×(0.78)
      = 0.322 + 0.220 + 0.170 + 0.156
      = 0.868 (86.8%) → HIGH CONFIDENCE
```

---

### Explainability: Why Decisions Were Made

**Three Key Explanations Provided:**

**1. Why Appeal Recommended?**
- Shows classifier confidence
- Explains limitation period (days from judgment)
- Example: "Classifier says YES (85% confident); 90-day appeal window from judgment date"

**2. Why Department Selected?**
- Embedding-based classifier suggestion
- LLM department hint
- How decision made (merged vs. overridden)
- Example: "Embedding suggested Finance (92%); LLM hinted Finance; kept LLM suggestion"

**3. Why Deadline Inferred?**
- Timeline parser match (did it find a date phrase?)
- Offset detected (e.g., "30 days" → 30)
- Fallback behavior
- Example: "Parser found 'within 30 days' (88% confident); compliance date = judgment + 30 days"

---

### Highlight Colors in PDF

| Color | Meaning | What to Look For |
|-------|---------|------------------|
| 🟨 Yellow | Directive | The court order - what action is required |
| 🟦 Blue | Deadline | Dates, "within X days", "forthwith" |
| 🟩 Green | Party Names | Petitioner, Respondent, Appellant names |

**How to Use:**
1. Open case details
2. Scroll to PDF viewer
3. Colored regions show what AI extracted
4. If highlights incorrect → Mark case for editing

---

## Admin Tasks

### Task 1: Create a New Officer Account

**Steps:**

1. Go to Admin Dashboard
2. Click "Create Officer" button (top right)
3. Fill in form:
   - **Full Name:** Officer's actual name
   - **Email:** Unique email address (used for login)
   - **Password:** Minimum 6 characters (send securely to officer)
4. Click "Create Officer"
5. New account active immediately
6. Send login credentials to officer via secure channel

---

### Task 2: Download Analytics Report

**Steps:**

1. Go to Admin Dashboard
2. Click "Export CSV" button (top right)
3. File downloads: `judgeai-analytics-YYYY-MM-DD.csv`
4. Open in Excel or analysis tool
5. Includes:
   - Summary statistics
   - Per-action fusion breakdown
   - Department performance
   - Verification rates
   - Reference values (weights, imputation)

---

### Task 3: Investigate Low Confidence Cases

**Steps:**

1. Go to Case Details
2. Check "Final Confidence Score" gauge
3. If RED (<50%):
   - Review Fusion Transparency table
   - Identify which subsystem scored low
   - Check Explainability section for details

4. Possible Issues:
   - **Low LLM score:** Poor PDF quality, unclear judgment text
   - **Low Timeline score:** Deadline phrase unclear or missing
   - **Low Department score:** Government body not in classifier training
   - **Low Appeal score:** Limited appeal indicators in text

5. Action:
   - Edit case with correct information
   - Or reject and re-upload cleaner PDF
   - Track pattern for future improvement

---

## Troubleshooting

### Issue 1: PDF Upload Fails

**Symptoms:** "Upload failed" message, file doesn't process

**Possible Causes:**
- File is not PDF format
- File size exceeds 50MB
- Network connection dropped
- Server temporarily unavailable

**Solutions:**
1. Check file format: Should be `.pdf` (not `.doc`, `.txt`, etc.)
2. Check file size: If >50MB, compress or split
3. Try again: Refresh page and retry
4. Check internet: Open another website to confirm connection
5. Contact admin if persistent: Server may be down

---

### Issue 2: Extraction Shows Blank/Wrong Fields

**Symptoms:** Case details show "N/A" or obviously incorrect data

**Possible Causes:**
- PDF has poor quality (scanned/OCR'd poorly)
- Judgment format unusual (not standard court document)
- Language not English (system supports English only currently)
- Missing key sections in document

**Solutions:**
1. Check PDF quality: Open PDF directly, is text readable?
2. Edit fields manually: Click "Edit", fill in correct information
3. Check OCR: If scanned, re-scan at higher resolution
4. Reject and re-upload: If not salvageable, reject case

---

### Issue 3: Can't Login

**Symptoms:** "Invalid credentials" or page won't load after login attempt

**Possible Causes:**
- Wrong email or password
- Account not created yet
- Browser cookies disabled
- Session expired

**Solutions:**
1. Check credentials: Verify email and password are correct
2. Contact admin: Ask if account was created
3. Clear cookies: Browser → Settings → Clear browsing data
4. Try incognito: Open private/incognito window and retry
5. Try different browser: Chrome, Firefox, Safari, etc.

---

### Issue 4: Case Doesn't Appear After Upload

**Symptoms:** Uploaded file but case not in dashboard or queue

**Possible Causes:**
- Extraction still processing (can take 1-2 minutes)
- PDF couldn't be read (corrupted file)
- File was processed but case filtered out by current view

**Solutions:**
1. Wait 2-3 minutes: Processing takes time for large files
2. Refresh page: Press F5 or Ctrl+R
3. Check filters: Dashboard might be filtering by department/status
4. Clear filters: Click "Reset Filters" or "Show All"
5. Search directly: Use search by file name or case number
6. Check browser console: Open DevTools (F12) for error messages

---

### Issue 5: Confidence Score Seems Too Low/High

**Symptoms:** Score of 30% for clear judgment, or 95% for unclear one

**Possible Causes:**
- Subsystem had missing data (used neutral imputation = ~29%)
- Score reflects uncertainty in specific component
- Model not trained on this document type

**Solutions:**
1. Check Fusion Table: Which subsystem scored low?
2. Review Explainability: Why did that component score that way?
3. Edit fields: Provide correct data if missing
4. Accept anyway: Officer judgment > AI confidence (verify manually)

---

### Issue 6: "AI Explainability" Shows Fallback Text

**Symptoms:** See "No stored narrative..." or generic explanation

**Possible Causes:**
- Case extracted with older pipeline (reasoning not generated)
- Re-extraction never happened
- Field was deleted/cleared

**Solutions:**
1. Re-run extraction: Delete case and re-upload
2. Manual entry: Click "Edit" and add your own notes
3. Check database: Ask admin if reasoning stored but not displaying

---

### Issue 7: Highlights Don't Show on PDF

**Symptoms:** PDF displays but no colored highlights visible

**Possible Causes:**
- CSS styles not loaded
- PDF viewer plugin issue
- Highlights generated but not matching text location
- Browser zoom level causing coordinate mismatch

**Solutions:**
1. Refresh page: F5 (forces CSS reload)
2. Try different browser: Chrome vs. Firefox
3. Clear browser cache: Settings → Clear cache → Retry
4. Zoom to 100%: PDF viewer zoom, then check highlights
5. Contact admin: UI may have rendering issue

---

### Issue 8: Performance is Slow / Page Lags

**Symptoms:** Dashboard takes long to load, clicks slow to respond

**Possible Causes:**
- Large number of cases (>10,000 loaded at once)
- Filters too broad (showing all departments)
- Browser running low on memory
- Network latency

**Solutions:**
1. Apply filters: Filter by status/department to reduce records
2. Use search: Search specific case instead of browsing all
3. Close other tabs: Free up browser memory
4. Restart browser: Close and reopen
5. Try different internet: Test on different network

---

## Tips & Best Practices

### For Officers

✅ **DO:**
- Review Case Details page fully before approving
- Check PDF highlights match extracted text
- Edit cases instead of rejecting when corrections are minor
- Use Explainability section to understand AI reasoning
- Flag unusual patterns to administrator

❌ **DON'T:**
- Approve without checking confidence score
- Ignore extremely low confidence (<30%) cases
- Guess on missing fields (reject or ask admin)
- Forget to save edits (confirm "Save Changes" button)

---

### For Administrators

✅ **DO:**
- Check Admin Dashboard daily for backlog
- Review confidence fusion statistics weekly
- Export analytics for stakeholder reports
- Create officer accounts with clear passwords
- Monitor for system errors in browser console

❌ **DON'T:**
- Assume all uploads succeeded (check dashboard)
- Let verification backlog exceed ~50 cases
- Ignore low confidence trends (<60% average)
- Share officer passwords via insecure channels

---

## Frequently Asked Questions

**Q: How long does extraction take?**
A: Usually 30 seconds to 2 minutes per PDF, depending on file size and quality.

**Q: Can I upload non-English documents?**
A: Not currently. System is optimized for English court judgments only.

**Q: What if the deadline is unclear in the judgment?**
A: Timeline parser will use neutral imputation (~0.294 confidence). Editor should manually confirm or correct.

**Q: Can I change my password?**
A: Contact your administrator. Password reset not yet available in UI (in roadmap).

**Q: How do I know if a case is urgent?**
A: Check Priority Level (RED = HIGH). Admin Dashboard shows "Urgent Deadlines" widget for next 7 days.

**Q: Can I download my audit log?**
A: Only full case audit logs are exportable. Full system audit available to admins via CSV export.

**Q: What does "Imputed?" = Yes mean?**
A: That subsystem had no data, so system used a neutral placeholder value (0.294) to keep score calculable.

**Q: Why was my edit flagged?**
A: All edits create audit log entries. Not "flagged" per se - just tracked for transparency.

**Q: How do I report a bug?**
A: Contact your system administrator with:
   - What you were doing
   - What happened (error message, screenshot)
   - When it happened (date/time)
   - Your browser and OS

---

## Quick Reference Card

### Common Actions & Shortcuts

| Action | Location | Shortcut |
|--------|----------|----------|
| Go to Dashboard | Top nav "Dashboard" | — |
| Go to Verification Queue | Top nav "Verification" | — |
| Go to Admin Panel | Top nav "Admin" | — |
| Open Case Details | Click case row | — |
| Approve Case | Verification page | `A` |
| Edit Case | Verification page | `E` |
| Reject Case | Verification page | `R` |
| Next Case | Verification page | `N` |
| Search Cases | Top nav search box | Ctrl+K or Cmd+K |
| Download PDF | Case Details page | — |
| Export Analytics | Admin Dashboard | — |
| Create Officer | Admin Dashboard | — |

---

## Support & Contact

**Technical Issues:**
- Contact: System Administrator
- Email: admin@judgeai.local (if configured)
- Include: Error message, browser, OS, steps to reproduce

**Feature Requests:**
- Contact: Product Manager
- Provide: Description, use case, priority

**Training & Onboarding:**
- Attend: Weekly user training sessions (if scheduled)
- Read: This guide + ANALYSIS_AND_FIXES.md
- Practice: Test environment available (ask admin)

---

## Additional Resources

- **Technical Architecture:** See `ANALYSIS_AND_FIXES.md`
- **Setup Instructions:** See `SETUP_GUIDE.md`
- **Testing Handbook:** See `build_test_pdf.py` (in backend/scripts)
- **Database Schema:** See `db_schema.sql` (in backend)
- **API Documentation:** Visit `http://localhost:8000/docs` (FastAPI Swagger)

---

**Last Updated:** May 2, 2026  
**Next Review:** August 2, 2026
