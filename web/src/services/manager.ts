import { http } from "../lib/http";
import type { Bundle, Cert, Conn, JoineeRow, Task } from "../types";

export type NewJoinee = { full_name: string; email: string; job_title: string; team: string; start_date: string };
export type PlanContents = { tasks: Task[]; certifications: Cert[]; connections: Conn[] };

export const managerApi = {
  listJoinees: () => http<JoineeRow[]>("/manager/joinees"),
  addJoinee: (body: NewJoinee) =>
    http<{ joinee_id: string; plan_id: string; invite_path: string }>("/manager/joinees", "POST", body),
  getPlan: (planId: string) => http<Bundle>(`/plans/${planId}`),
  savePlan: (planId: string, body: PlanContents) => http<Bundle>(`/plans/${planId}`, "PUT", body),
  assignPlan: (planId: string) => http<Bundle>(`/plans/${planId}/assign`, "POST"),
  draftTasks: (planId: string, brief: string) => http<{ tasks: Task[] }>(`/plans/${planId}/ai-draft`, "POST", { brief }),
  reinvite: (planId: string) => http<{ invite_path: string }>(`/plans/${planId}/invite`, "POST"),
};
