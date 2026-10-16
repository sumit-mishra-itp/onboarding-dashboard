-- Own auth (passwords, invites, lockout, session revocation) and UI-managed Info Hub.

ALTER TABLE app_user ADD COLUMN IF NOT EXISTS password_hash TEXT;              -- NULL until the invite is accepted
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS session_version INT NOT NULL DEFAULT 0;  -- bump = sign out everywhere
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS failed_logins INT NOT NULL DEFAULT 0;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

ALTER TABLE app_user DROP CONSTRAINT IF EXISTS app_user_role_check;
ALTER TABLE app_user ADD CONSTRAINT app_user_role_check CHECK (role IN ('ADMIN', 'HR', 'MANAGER', 'JOINEE'));
CREATE INDEX IF NOT EXISTS idx_app_user_manager ON app_user (manager_id);

-- One-time links for invites and password resets. Only the SHA-256 of the token is stored.
CREATE TABLE IF NOT EXISTS auth_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    purpose TEXT NOT NULL CHECK (purpose IN ('INVITE', 'RESET')),
    created_by UUID REFERENCES app_user(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_auth_token_user ON auth_token (user_id);

-- Info Hub is now edited in the app; the seed JSON is loaded once into an empty table.
ALTER TABLE info_resource ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE info_resource ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE info_resource ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES app_user(id) ON DELETE SET NULL;
