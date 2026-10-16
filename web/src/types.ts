/** Shapes of what the API returns. Mirrors backend/app/core.py and the repositories' SELECTs. */
export type Role = "ADMIN" | "HR" | "MANAGER" | "JOINEE";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  start_date: string | null;
  job_title: string | null;
  team: string | null;
  is_active: boolean;
  last_login_at: string | null;
};
export type AdminUserRow = User & { has_password: boolean };

export type Task = {
  id?: string;
  title: string;
  description: string;
  category: string;
  week_no: number;
  day_offset: number;
  priority: string;
  subtasks: string[];
  is_ai_generated: boolean;
  is_modified_by_manager: boolean;
  status?: string;
  due_date?: string | null;
  joinee_notes?: string | null;
};
export type Cert = { id?: string; name: string; provider: string; url: string; deadline: string; is_mandatory: boolean; is_completed?: boolean };
export type Conn = { id?: string; contact_name: string; contact_email: string; contact_title: string; reason: string; status?: string; met_date?: string | null };
export type Metrics = {
  task_completion_percentage: number | null;
  completed_tasks: number;
  total_tasks: number;
  completed_mandatory_certs: number;
  total_mandatory_certs: number;
  met_connections: number;
  total_connections: number;
  total_overdue_items: number;
};
export type Plan = {
  id: string; joinee_id: string; status: string; duration_days: number;
  full_name?: string; email?: string; job_title?: string; team?: string; start_date?: string;
};
export type Bundle = { plan: Plan; tasks: Task[]; certifications: Cert[]; connections: Conn[]; metrics: Metrics };
export type JoineeRow = Plan & { metrics: Metrics; tasks: Task[] };
export type JoineeDashboard = (Bundle & { current_week: number }) | { plan: null };

export type InfoEntry = {
  id: string;
  category: string;
  title: string;
  body_md: string;
  contact_email: string | null;
  link_url: string | null;
  display_order: number;
  last_reviewed_date: string;
  is_active: boolean;
  updated_at: string;
};
export type InfoEntryInput = Omit<InfoEntry, "id" | "last_reviewed_date" | "updated_at">;

export const CATEGORIES = ["TECHNICAL_SETUP", "ACCESS_AND_TOOLS", "COMPLIANCE", "TEAM_AND_PROCESS", "ROLE_RAMP_UP", "ADMIN"];
export const PRIORITIES = ["HIGH", "MEDIUM", "LOW"];
export const TASK_STATUSES = ["TO_DO", "IN_PROGRESS", "DONE", "BLOCKED"];
export const CONN_STATUSES = ["PENDING", "SCHEDULED", "MET"];
export const STAFF_ROLES: Role[] = ["MANAGER", "HR", "ADMIN"];
