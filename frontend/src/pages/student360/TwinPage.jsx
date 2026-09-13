// Student 360 - Digital Twin what-if simulator (Phase 3 kickoff).
import { useState } from "react";
import { Card, Disclaimer, Loading } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});

const deltaColor = (d, goodUp = true) => {
  if (d == null || d === 0) return "#64748b";
  const good = goodUp ? d > 0 : d < 0;
  return good ? "#22c55e" : "#ef4444";
};

export default function TwinPage() {
  const [rows, setRows] = useState([
    { title: "", credits: 3, expected_grade: 15 },
    { title: "", credits: 3, expected_grade: 15 },
  ]);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function setRow(i, k, v) {
    setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  }

  async function run() {
    setLoading(true); setError(""); setRes(null);
    try {
      const courses = rows
        .filter((r) => +r.credits > 0)
        .map((r) => ({ title: r.title || "درس", credits: +r.credits,
                       expected_grade: +r.expected_grade }));
      const j = await fetch(`${API_BASE}/api/twin/simulate`, {
        method: "POST", headers: HEADERS(),
        body: JSON.stringify({ courses }),
      }).then((r) => r.json());
      if (j.error) throw new Error(j.error);
      setRes(j);
    } catch (e) { setError("خطا در شبیه‌سازی: " + (e.message || "")); }
    finally { setLoading(false); }
  }

  const Badge = ({ label, before, after, goodUp = true, unit = "" }) => {
    const d = (typeof before === "number" && typeof after === "number") ? +(after - before).toFixed(2) : null;
    return (
      <div className="twin-metric">
        <span>{label}</span>
        <span className="twin-vals">
          <b>{before ?? "-"}{unit}</b>
          <span style={{ color: deltaColor(d, goodUp) }}>
            {d != null && d !== 0 ? ` ${d > 0 ? "▲" : "▼"} ${Math.abs(d)}${unit}` : " ="}
          </span>
        </span>
        <b className="twin-after" style={{ color: deltaColor(d, goodUp) }}>{after ?? "-"}{unit}</b>
      </div>
    );
  };

  return (
    <div className="s360-page">
      <h2>🧊 شبیه‌ساز «چه می‌شود اگر؟» (Digital Twin)</h2>
      <Disclaimer text="سناریوی ترم بعد را بسازید تا اثر آن بر GPA، مشروطی، ریسک و سقف واحد — بدون ثبت هیچ داده‌ای — شبیه‌سازی شود." />

      <Card title="🎓 سناریوی ترم بعد" actions={
        <button onClick={() => setRows([...rows, { title: "", credits: 3, expected_grade: 15 }])}>
          + افزودن درس
        </button>
      }>
        {rows.map((r, i) => (
          <div className="twin-row" key={i}>
            <input placeholder="نام درس (برای مهارت)" value={r.title}
                   onChange={(e) => setRow(i, "title", e.target.value)} />
            <input type="number" min="1" max="24" title="واحد" value={r.credits}
                   onChange={(e) => setRow(i, "credits", +e.target.value)} />
            <input type="number" min="0" max="20" step="0.25" title="نمره مورد انتظار" value={r.expected_grade}
                   onChange={(e) => setRow(i, "expected_grade", +e.target.value)} />
            {rows.length > 1 && (
              <button className="interv-cancel" onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</button>
            )}
          </div>
        ))}
        <div className="twin-hint-row">
          <small className="s360-hint">ستون‌ها: نام درس | واحد | نمره مورد انتظار</small>
          <button onClick={run} disabled={loading}>{loading ? "..." : "🔮 شبیه‌سازی کن"}</button>
        </div>
        {error && <p className="s360-error">{error}</p>}
      </Card>

      {res && (
        <>
          <Card title="📊 مقایسه قبل ⟷ بعد">
            <Badge label="GPA کل" before={res.before.gpa} after={res.after.gpa} unit="" />
            <Badge label="ریسک تحصیلی" before={res.before.risk_score} after={res.after.risk_score} goodUp={false} />
            <Badge label="سقف واحد ترم بعد" before={res.before.max_units} after={res.after.max_units} unit="" />
            <Badge label="مشروطی‌ها" before={res.before.probation_count} after={res.after.probation_count} goodUp={false} />
            <Badge label="واحد مردودی" before={res.before.failed_credits} after={res.after.failed_credits} goodUp={false} />
            <div className="s360-kv"><span>معدل ترم شبیه‌سازی:</span><b>{res.scenario.term_gpa}</b> (واحد: {res.scenario.units})</div>
            <div className="s360-kv">
              <span>سطح ریسک:</span>
              <b>{res.before.risk_level} → {res.after.risk_level}</b>
            </div>
          </Card>

          {res.warnings?.length > 0 && (
            <Card title="⚠️ هشدارهای شبیه‌سازی">
              <ul className="eng-recs">{res.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </Card>
          )}

          {Object.keys(res.skill_preview || {}).length > 0 && (
            <Card title="🧩 مهارت‌هایی که این ترم اضافه می‌کند">
              <div className="eng-chips">
                {Object.entries(res.skill_preview).map(([t, sks]) => (
                  <span key={t} className="mart-chip">{t}: {sks.join("، ")}</span>
                ))}
              </div>
            </Card>
          )}

          <p className="s360-hint">{res.disclaimer}</p>
        </>
      )}
    </div>
  );
}
