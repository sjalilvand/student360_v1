// Student 360 - Career & Skills profile (Phase 2 / category 13).
import { useEffect, useState } from "react";
import { Card, Disclaimer, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});

const LEVEL_COLOR = { "قوی": "#22c55e", "متوسط": "#3b82f6", "پایه": "#f59e0b", "در حال یادگیری": "#8b5cf6" };

export default function CareerPage() {
  const [prof, setProf] = useState(null);
  const [recs, setRecs] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () =>
    fetch(`${API_BASE}/api/career/skills`, { headers: HEADERS() })
      .then((r) => r.json()).then(setProf).catch(() => setProf({ error: true }));
  useEffect(load, []);

  async function loadRecs(track) {
    setRecs(null);
    const j = await fetch(`${API_BASE}/api/career/recommend?track=${encodeURIComponent(track)}`,
      { headers: HEADERS() }).then((r) => r.json()).catch(() => ({ items: [] }));
    setRecs(j.items || []);
  }

  async function enrich() {
    setBusy(true); setMsg("");
    try {
      const j = await fetch(`${API_BASE}/api/career/enrich`, {
        method: "POST", headers: HEADERS(), body: JSON.stringify({ limit: 6 }),
      }).then((r) => r.json());
      setMsg("تحلیل هوشمند انجام شد — " + (j.enriched || []).length + " درس با AI نگاشت شد. ✨");
      load();
    } catch { setMsg("خطا در تحلیل هوشمند"); }
    finally { setBusy(false); }
  }

  if (!prof) return <Loading />;
  if (prof.error) return <p className="s360-error">خطا در دریافت پروفایل شغلی</p>;

  return (
    <div className="s360-page">
      <h2>💼 پروفایل شغلی و مهارت‌ها</h2>
      <Disclaimer text={prof.disclaimer} />

      <Card title="🧩 مهارت‌های شما (از کارنامه و دروس جاری)" actions={
        <button onClick={enrich} disabled={busy}>{busy ? "..." : "⚡ تحلیل هوشمند (LLM)"}</button>
      }>
        {msg && <p className="s360-hint">{msg}</p>}
        {prof.skills.length === 0 ? <Empty>مهارتی شناسایی نشد — با گذراندن دروس تکمیل می‌شود</Empty> : (
          <div className="eng-chips">
            {prof.skills.map((s) => (
              <span key={s.name} className="skill-chip"
                    style={{ borderColor: LEVEL_COLOR[s.level] }}>
                {s.name}
                <small style={{ color: LEVEL_COLOR[s.level] }}>{s.level}{s.avg_grade ? ` (${s.avg_grade})` : ""}</small>
              </span>
            ))}
          </div>
        )}
        <p className="s360-hint">دکمه «⚡ تحلیل هوشمند» دروس بی‌برچسب را با LLM نگاشت می‌کند.</p>
      </Card>

      {prof.top_track && (
        <Card title={`🏆 مسیر پیشنهادی شما: ${prof.top_track.name} (${prof.top_track.readiness_pct}٪)`}>
          <p className="s360-hint">بر اساس تطبیق مهارت‌های فعلی با الزامات مسیرها</p>
        </Card>
      )}

      <Card title="🛣️ آمادگی مسیرهای شغلی">
        {prof.tracks.map((t) => (
          <div key={t.name} className="track-row">
            <b>{t.name}</b>
            <div className="track-bar">
              <div style={{ width: t.readiness_pct + "%",
                            background: t.readiness_pct >= 70 ? "#22c55e" : t.readiness_pct >= 40 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <b className="track-pct">{t.readiness_pct}٪</b>
            <button onClick={() => loadRecs(t.name)}>دروس پیشنهادی</button>
          </div>
        ))}
      </Card>

      {recs !== null && (
        <Card title="📚 دروس پیشنهادی برای پر کردن شکاف">
          {recs.length === 0 ? <Empty>شکاف قابل پرکردن با دروس برنامه یافت نشد</Empty> : (
            <table className="s360-table">
              <thead><tr><th>کد</th><th>درس</th><th>مهارتی که می‌دهد</th></tr></thead>
              <tbody>{recs.map((r) => (
                <tr key={r.code}><td>{r.code}</td><td><b>{r.title}</b></td><td>{r.gives.join("، ")}</td></tr>
              ))}</tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
