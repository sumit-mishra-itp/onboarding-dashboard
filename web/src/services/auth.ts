import { http } from "../lib/http";
import type { User } from "../types";

export const authApi = {
  me: () => http<User>("/auth/me"),
  login: (email: string, password: string) => http<User>("/auth/login", "POST", { email, password }),
  logout: () => http("/auth/logout", "POST"),
  /** Accept an invite or reset link. Signs the user in. */
  setPassword: (token: string, password: string) => http<User>("/auth/set-password", "POST", { token, password }),
  changePassword: (current_password: string, new_password: string) =>
    http("/auth/change-password", "POST", { current_password, new_password }),
};
