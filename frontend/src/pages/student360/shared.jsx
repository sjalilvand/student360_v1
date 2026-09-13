// Student 360 — shared UI helpers and small components.
export const STATUS_COLORS = {
  "قابل اخذ": "#22c55e",
  "قابل اخذ با اخطار": "#f59e0b",
  "نیازمند تأیید آموزش": "#3b82f6",
  "غیرقابل اخذ": "#ef4444",
  "پیشنهادشده": "#8b5cf6",
  "ضروری برای جلوگیری از تأخیر تحصیلی": "#dc2626",
};

export const SEVERITY_COLORS = {
  info: "#3b82f6",
  warning: "#f59e0b",
  critical: "#ef4444",
};

export const DAY_NAMES = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];

export function Badge({ color, children }) {
  return (
    <span className="s360-badge" style={{ background: color }}>
      {children}
    </span>
  );
}

export function Card({ title, children, actions }) {
  return (
    <div className="s360-card">
      <div className="s360-card-head">
        <h3>{title}</h3>
        {actions}
      </div>
      <div className="s360-card-body">{children}</div>
    </div>
  );
}

export function Disclaimer({ text }) {
  if (!text) return null;
  return <div className="s360-disclaimer">⚠️ {text}</div>;
}

export function Empty({ children }) {
  return <p className="s360-empty">{children}</p>;
}

export function Loading() {
  return (
    <div className="s360-loading">
      <div className="spinner" />
      <p>در حال بارگذاری...</p>
    </div>
  );
}
