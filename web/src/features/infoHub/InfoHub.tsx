import BlurTitle from "../../components/BlurTitle";
import { useEffect, useState } from "react";
import { fmtDate } from "../../lib/format";
import { infoHubApi } from "../../services/infoHub";
import type { InfoEntry as Entry } from "../../types";

export default function InfoHub() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Entry[] | null>(null);
  const [cat, setCat] = useState<string | null>(null);
  useEffect(() => {
    const t = setTimeout(() => infoHubApi.list(q).then(setItems), 200);
    return () => clearTimeout(t);
  }, [q]);
  if (!items) return null;

  const categories = [...new Set(items.map((i) => i.category))];
  const active = q ? null : cat ?? categories[0];
  const shown = active ? items.filter((i) => i.category === active) : items;

  return (
    <section>
      <div className="page-head">
        <div>
          <BlurTitle text="Info Hub" />
          <p className="lede">Where to get IT access, accounts, pay and workplace help, without raising a ticket first.</p>
        </div>
      </div>
      <input className="search" type="search" placeholder="Search, for example “VPN” or “leave”" value={q}
        onChange={(e) => setQ(e.target.value)} aria-label="Search the Info Hub" />

      <div className="hub">
        {!q && (
          <nav className="hub-nav" aria-label="Categories">
            {categories.map((c) => (
              <button key={c} className={c === active ? "on" : ""} aria-current={c === active} onClick={() => setCat(c)}>{c}</button>
            ))}
          </nav>
        )}
        <div className="hub-list">
          {q && <p className="muted">{shown.length ? `${shown.length} result${shown.length === 1 ? "" : "s"} for “${q}”` : `Nothing matches “${q}”. Try a shorter word, or ask your manager.`}</p>}
          {shown.map((i) => (
            <details key={i.id} className="entry" open={!!q}>
              <summary>
                <span>{i.title}</span>
                {q && <span className="muted small">{i.category}</span>}
              </summary>
              {/* ponytail: shown as plain text; add a markdown renderer when entries need real formatting */}
              <p className="body">{i.body_md}</p>
              <div className="entry-foot">
                {i.contact_email && <a href={`mailto:${i.contact_email}`}>{i.contact_email}</a>}
                {i.link_url && <a href={i.link_url} target="_blank" rel="noreferrer">Open page</a>}
                <span className="muted small">Last checked {fmtDate(i.last_reviewed_date)}</span>
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
