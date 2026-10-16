import { http } from "../lib/http";
import type { AdminUserRow, Role, User } from "../types";

export const adminApi = {
  listUsers: () => http<AdminUserRow[]>("/admin/users"),
  createUser: (body: { email: string; full_name: string; role: Role }) =>
    http<{ user: User; invite_path: string }>("/admin/users", "POST", body),
  updateUser: (id: string, patch: Partial<Pick<User, "full_name" | "role" | "is_active">>) =>
    http<User>(`/admin/users/${id}`, "PATCH", patch),
  resetLink: (id: string) => http<{ reset_path: string }>(`/admin/users/${id}/reset-link`, "POST"),
};
