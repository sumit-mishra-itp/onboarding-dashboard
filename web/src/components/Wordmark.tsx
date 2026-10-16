export default function Wordmark() {
  return (
    <span className="wordmark">
      <svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true">
        <line x1="2" y1="6" x2="26" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".35" />
        <circle cx="4" cy="6" r="3" fill="var(--done)" /><circle cx="14" cy="6" r="3" fill="var(--done)" />
        <circle cx="24" cy="6" r="3" fill="var(--progress)" />
      </svg>
      Onboarding
    </span>
  );
}
