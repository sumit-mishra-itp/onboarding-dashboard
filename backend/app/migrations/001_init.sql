-- Baseline schema (TSD §6.1, minus proof uploads and audit_event). IF NOT EXISTS so it adopts databases
-- created before the migration runner existed. Never edit an applied migration: add a new numbered file.

CREATE TABLE IF NOT EXISTS app_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('MANAGER', 'JOINEE')),
    manager_id UUID REFERENCES app_user(id),
    job_title TEXT,
    team TEXT,
    start_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ponytail: one plan per joinee (UNIQUE joinee_id); drop the constraint if re-onboarding is ever needed.
CREATE TABLE IF NOT EXISTS onboarding_plan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    joinee_id UUID NOT NULL UNIQUE REFERENCES app_user(id),
    manager_id UUID NOT NULL REFERENCES app_user(id),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'COMPLETED')),
    duration_days INT NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS plan_task (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES onboarding_plan(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description VARCHAR(500) NOT NULL DEFAULT '',
    category TEXT NOT NULL CHECK (category IN ('TECHNICAL_SETUP', 'ACCESS_AND_TOOLS', 'COMPLIANCE',
                                               'TEAM_AND_PROCESS', 'ROLE_RAMP_UP', 'ADMIN')),
    week_no INT NOT NULL CHECK (week_no BETWEEN 1 AND 4),
    day_offset INT NOT NULL CHECK (day_offset BETWEEN 0 AND 30),
    due_date DATE,
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    status TEXT NOT NULL DEFAULT 'TO_DO' CHECK (status IN ('TO_DO', 'IN_PROGRESS', 'DONE', 'BLOCKED')),
    subtasks JSONB NOT NULL DEFAULT '[]'::jsonb,
    joinee_notes TEXT,
    completed_at TIMESTAMPTZ,
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    is_modified_by_manager BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS certification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES onboarding_plan(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    url TEXT NOT NULL,
    deadline DATE NOT NULL,
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Free text on purpose (BR-16): contacts may be people outside the app.
CREATE TABLE IF NOT EXISTS connection_contact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES onboarding_plan(id) ON DELETE CASCADE,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_title TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SCHEDULED', 'MET')),
    met_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS info_resource (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    body_md TEXT NOT NULL,
    contact_email TEXT,
    link_url TEXT,
    display_order INT NOT NULL DEFAULT 0,
    last_reviewed_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    tsv_search TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body_md, ''))
    ) STORED
);
CREATE INDEX IF NOT EXISTS idx_info_resource_search ON info_resource USING GIN (tsv_search);

CREATE TABLE IF NOT EXISTS ai_run_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES onboarding_plan(id) ON DELETE CASCADE,
    manager_id UUID NOT NULL REFERENCES app_user(id),
    prompt_version TEXT NOT NULL,
    model_identifier TEXT NOT NULL,
    input_brief TEXT NOT NULL,
    raw_output JSONB,
    validation_passed BOOLEAN NOT NULL,
    validation_errors TEXT,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms BIGINT NOT NULL,
    is_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Postgres does not index foreign keys on its own; these back every per-plan / per-manager lookup.
CREATE INDEX IF NOT EXISTS idx_plan_task_plan ON plan_task (plan_id);
CREATE INDEX IF NOT EXISTS idx_certification_plan ON certification (plan_id);
CREATE INDEX IF NOT EXISTS idx_connection_contact_plan ON connection_contact (plan_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_plan_manager ON onboarding_plan (manager_id);
CREATE INDEX IF NOT EXISTS idx_ai_run_log_plan ON ai_run_log (plan_id, created_at);
