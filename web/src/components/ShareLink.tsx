import { useState } from "react";
import { absoluteUrl } from "../lib/format";

/** A one-time invite/reset link for the user to pass on (there is no email integration). */
export default function ShareLink({ path, who, onClose }: { path: string; who: string; onClose?: () => void }) {
  const url = absoluteUrl(path);
  const [copied, setCopied] = useState(false);
  const copy = () => navigator.clipboard.writeText(url).then(() => setCopied(true));
  return (
    <div className="panel hint" role="status">
      <p>Send this one-time link to {who}. It lets them set their password and sign in. Anyone with the link can use it, so share it privately.</p>
      <div className="row">
        <input readOnly value={url} aria-label="Sign-up link" onFocus={(e) => e.target.select()} />
        <button onClick={copy}>{copied ? "Copied" : "Copy link"}</button>
        {onClose && <button className="link" onClick={onClose}>Done</button>}
      </div>
    </div>
  );
}
