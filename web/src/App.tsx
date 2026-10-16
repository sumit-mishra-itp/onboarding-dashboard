import { useEffect, useState, type ReactNode } from "react";
import ThemeToggle from "./components/ThemeToggle";
import Wordmark from "./components/Wordmark";
import Users from "./features/admin/Users";
import Account from "./features/auth/Account";
import Login from "./features/auth/Login";
import SetPassword from "./features/auth/SetPassword";
import InfoHub from "./features/infoHub/InfoHub";
import InfoHubEditor from "./features/infoHub/InfoHubEditor";
import JoineeDashboard from "./features/joinee/JoineeDashboard";
import JoineeList from "./features/manager/JoineeList";
import { setUnauthorizedHandler } from "./lib/http";
import { useReveal } from "./lib/useReveal";
import { authApi } from "./services/auth";
import type { Role, User } from "./types";

type Screen = { key: string; title: string; render: (u: User) => ReactNode };

const S = {
  joinees: { key: "joinees", title: "My joinees", render: () => <JoineeList /> },
  plan: { key: "plan", title: "My plan", render: (u) => <JoineeDashboard user={u} /> },
  users: { key: "users", title: "Users", render: (u) => <Users me={u} /> },
  hub: { key: "hub", title: "Info Hub", render: () => <InfoHub /> },
  hubEdit: { key: "hubEdit", title: "Edit Info Hub", render: () => <InfoHubEditor /> },
  account: { key: "account", title: "Account", render: (u) => <Account user={u} /> },
} satisfies Record<string, Screen>;

// What each role can reach; the first entry is their home. The API enforces the same rules server-side.
const NAV: Record<Role, Screen[]> = {
  ADMIN: [S.users, S.hubEdit, S.hub, S.account],
  HR: [S.hubEdit, S.hub, S.account],
  MANAGER: [S.joinees, S.hub, S.account],
  JOINEE: [S.plan, S.hub, S.account],
};

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [tab, setTab] = useState("");

  const signedIn = (u: User | null) => { setUser(u); setTab(""); };
  useReveal(".block, .panel:not(.form), .joinees > li, .hub-list > .entry");
  useEffect(() => {
    setUnauthorizedHandler(() => signedIn(null)); // session expired or revoked mid-use
    if (window.location.pathname !== "/set-password") authApi.me().then(signedIn, () => signedIn(null));
  }, []);

  const bare = (page: ReactNode) => (
    <>
      <header className="top bare"><Wordmark /><div className="who"><ThemeToggle /></div></header>
      {page}
    </>
  );
  if (window.location.pathname === "/set-password" && !user) return bare(<SetPassword onDone={signedIn} />);
  if (user === undefined) return null;
  if (user === null) return bare(<Login onDone={signedIn} />);

  const screens = NAV[user.role];
  const current = screens.find((s) => s.key === tab) ?? screens[0];

  return (
    <>
      <header className="top">
        <Wordmark />
        <nav aria-label="Main">
          {screens.map((s) => (
            <button key={s.key} className={s === current ? "tab on" : "tab"} aria-current={s === current ? "page" : undefined}
              onClick={() => setTab(s.key)}>{s.title}</button>
          ))}
        </nav>
        <div className="who">
          <span>{user.full_name}</span>
          <ThemeToggle />
          <button className="link" onClick={() => authApi.logout().finally(() => signedIn(null))}>Sign out</button>
        </div>
      </header>
      <main>{current.render(user)}</main>
    </>
  );
}
