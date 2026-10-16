import { http } from "../lib/http";
import type { JoineeDashboard } from "../types";

export const joineeApi = {
  dashboard: () => http<JoineeDashboard>("/joinee/dashboard"),
  setTaskStatus: (id: string, status: string, joinee_notes?: string) => http(`/tasks/${id}`, "PATCH", { status, joinee_notes }),
  setCertCompleted: (id: string, is_completed: boolean) => http(`/certifications/${id}`, "PATCH", { is_completed }),
  setConnectionStatus: (id: string, status: string) => http(`/connections/${id}`, "PATCH", { status }),
};
