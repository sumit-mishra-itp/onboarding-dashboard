import { http } from "../lib/http";
import type { InfoEntry, InfoEntryInput } from "../types";

export const infoHubApi = {
  list: (search = "", includeInactive = false) =>
    http<InfoEntry[]>(`/info-hub?${new URLSearchParams({ search, include_inactive: String(includeInactive) })}`),
  create: (body: InfoEntryInput) => http<InfoEntry>("/info-hub", "POST", body),
  update: (id: string, body: InfoEntryInput) => http<InfoEntry>(`/info-hub/${id}`, "PUT", body),
  remove: (id: string) => http<void>(`/info-hub/${id}`, "DELETE"),
};
