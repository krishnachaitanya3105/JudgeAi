-- ═════════════════════════════════════════════════════════════════
-- JudgeAI Database Schema
-- ═════════════════════════════════════════════════════════════════
-- Supabase (PostgreSQL) schema for court judgment management system
-- ═════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;

-- ──────────────────────────────────────────────────────────────────
-- 1. USERS TABLE (if managing officers/admins)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('officer', 'admin', 'reviewer')),
    department VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- ──────────────────────────────────────────────────────────────────
-- 2. CASES TABLE
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number VARCHAR(255) UNIQUE NOT NULL,
    pdf_url TEXT NOT NULL,
    uploaded_by VARCHAR(255),
    department VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'archived')),
    processing_status TEXT DEFAULT NULL,
    processing_stage TEXT DEFAULT NULL,
    processing_error TEXT DEFAULT NULL,
    processing_job_id TEXT DEFAULT NULL,
    processing_started_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    processing_finished_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    processing_heartbeat_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    layout_blocks JSONB DEFAULT NULL,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_cases_case_number ON cases(case_number);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_department ON cases(department);
CREATE INDEX idx_cases_created_at ON cases(created_at DESC);
CREATE INDEX idx_cases_processing_status ON cases(processing_status);
CREATE INDEX idx_cases_processing_job_id ON cases(processing_job_id);
CREATE INDEX idx_cases_pdf_url ON cases(pdf_url);

-- ──────────────────────────────────────────────────────────────────
-- 3. EXTRACTED_ACTIONS TABLE (Main extraction results)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS extracted_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number VARCHAR(255),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    pdf_url TEXT,
    judgment_date DATE,
    department VARCHAR(255),
    deadline DATE,
    directive TEXT,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1.0),
    source_sentence TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'edited', 'rejected', 'completed')),
    rejection_reason TEXT,
    human_verified_values JSONB,
    action_plan JSONB DEFAULT NULL,
    action_plan_reasoning JSONB DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extracted_actions_case_number ON extracted_actions(case_number);
CREATE INDEX idx_extracted_actions_status ON extracted_actions(status);
CREATE INDEX idx_extracted_actions_department ON extracted_actions(department);
CREATE INDEX idx_extracted_actions_deadline ON extracted_actions(deadline);
CREATE INDEX idx_extracted_actions_created_at ON extracted_actions(created_at DESC);
CREATE INDEX idx_extracted_actions_confidence ON extracted_actions(confidence_score DESC);

-- ──────────────────────────────────────────────────────────────────
-- 4. AUDIT_LOGS TABLE (Change tracking)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    edited_by VARCHAR(255),
    notes TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_logs_case_id ON audit_logs(case_id);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_edited_by ON audit_logs(edited_by);

-- ──────────────────────────────────────────────────────────────────
-- 5. VERIFICATION_QUEUE TABLE (For officer workflow)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS verification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extracted_action_id UUID REFERENCES extracted_actions(id) ON DELETE CASCADE,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    department VARCHAR(255),
    priority VARCHAR(50) DEFAULT 'normal' CHECK (priority IN ('urgent', 'warning', 'normal')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed')),
    due_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_verification_queue_status ON verification_queue(status);
CREATE INDEX idx_verification_queue_assigned_to ON verification_queue(assigned_to);
CREATE INDEX idx_verification_queue_due_date ON verification_queue(due_date);
CREATE INDEX idx_verification_queue_priority ON verification_queue(priority);

-- ──────────────────────────────────────────────────────────────────
-- 6. NOTIFICATIONS TABLE
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    case_id VARCHAR(255),
    notification_type VARCHAR(100),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ──────────────────────────────────────────────────────────────────
-- 7. ROW LEVEL SECURITY (RLS) POLICIES
-- ──────────────────────────────────────────────────────────────────

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- ── USERS: Users can see only themselves unless admin ──
CREATE POLICY users_view_policy ON users
    FOR SELECT
    USING (auth.uid() = id OR auth.jwt() ->> 'role' = 'admin');

-- ── CASES: Officers see their department cases; admins see all ──
CREATE POLICY cases_select_policy ON cases
    FOR SELECT
    USING (
        auth.jwt() ->> 'role' = 'admin'
        OR department = (SELECT department FROM users WHERE id = auth.uid())
    );

-- ── EXTRACTED_ACTIONS: Officers see their department; admins see all ──
CREATE POLICY extracted_actions_select_policy ON extracted_actions
    FOR SELECT
    USING (
        auth.jwt() ->> 'role' = 'admin'
        OR department = (SELECT department FROM users WHERE id = auth.uid())
    );

CREATE POLICY extracted_actions_update_policy ON extracted_actions
    FOR UPDATE
    USING (
        auth.jwt() ->> 'role' = 'admin'
        OR department = (SELECT department FROM users WHERE id = auth.uid())
    );

-- ── AUDIT_LOGS: Admins see all; officers see their own edits ──
CREATE POLICY audit_logs_select_policy ON audit_logs
    FOR SELECT
    USING (
        auth.jwt() ->> 'role' = 'admin'
        OR edited_by = (SELECT email FROM users WHERE id = auth.uid())
    );

-- ── NOTIFICATIONS: Users see only their own ──
CREATE POLICY notifications_select_policy ON notifications
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY notifications_update_policy ON notifications
    FOR UPDATE
    USING (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- 8. TRIGGER: Update updated_at timestamp
-- ──────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER users_updated_at_trigger BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER cases_updated_at_trigger BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER extracted_actions_updated_at_trigger BEFORE UPDATE ON extracted_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ──────────────────────────────────────────────────────────────────
-- 9. VIEWS (Optional: for common queries)
-- ──────────────────────────────────────────────────────────────────

-- Dashboard view: Cases by status
CREATE OR REPLACE VIEW cases_by_status AS
SELECT
    status,
    COUNT(*) as count,
    department
FROM cases
GROUP BY status, department
ORDER BY department, status;

-- Dashboard view: Pending approvals
CREATE OR REPLACE VIEW pending_approvals AS
SELECT
    ea.id,
    ea.case_number,
    ea.department,
    ea.deadline,
    ea.confidence_score,
    ca.created_at,
    (ea.deadline - CURRENT_DATE)::INTEGER as days_until_deadline
FROM extracted_actions ea
LEFT JOIN cases ca ON ea.case_id = ca.id
WHERE ea.status = 'pending'
    AND ea.deadline > CURRENT_DATE
ORDER BY ea.deadline ASC, ea.confidence_score DESC;

-- ══════════════════════════════════════════════════════════════════
-- END OF SCHEMA
-- ══════════════════════════════════════════════════════════════════
