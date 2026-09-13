// Student 360 - Personalized Study Path (Phase 2 / category 2).
import { useEffect, useState } from "react";
import { Card, Disclaimer, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({ "X-Student-Number": localStorage.getItem("s360_student_number") || "" });

function PathBar({ p }) {
  const total = Math.max(1, p.total_required || 0);
  const w1 = Math.min(100, (p.passed_units / total) * 100);
  const w2 = Math.min(100 - w1, (p.in_progress_units / total) * 100);
  return (
    <div className="path-bar">
      <div className="path-seg passed" style={{ width: w1 + "%" }} title={"گذرانده: " + p.passed_units} />
      <div className="path-seg inprog" style={{ width: w2 + "%" }} title={"جاری: " + p.in_progress_units} />
      <div className="path-legend">
        <span>✅ گذرانده: <b>{p.passed_units}</b></span>
        <span>🔄 جاری: <b>{p.in_progress_units}</b></span>
        <span>⬜ باقی‌مانده: <b>{p.remaining_units}</b></span>
        <span>📈 پیشرفت: <b>{p.progress_pct}٪</b></span>
      </div>
    </div>
  );
}

export default function StudyPathPage() {
  const [p, setP] = useState(null);
  const [tab, setTab] = useState("plan");

  useEffect(() => {
    fetch(`${API_BASE}/api/studypath/me`, { headers: HEADERS() })
      .then((r) => r.json()).then(setP).catch(() => setP({ error: true }));
  }, []);

  if (!p) return <Loading />;
  if (p.error) return <p className="s360-error">خطا در دریافت مسیر تحصیلی</p>;

  const riskBadge = p.risk_level === "بالا" ? "risk-high" : p.risk_level === "متوسط" ? "risk-mid" : "risk-low";

  return (
    <div className="s360-page">
      <h2>🗺️ مسیر تحصیلی من</h2>
      <Disclaimer text={p.disclaimer} />

      <div className="s360-grid-2">
        <Card title="📊 وضعیت کلی">
          <PathBar p={p.summary} />
          <div className="s360-kv"><span>رشته:</span><b>{p.program || "-"}</b></div>
          <div className="s360-kv"><span>کل واحدهای دوره:</span><b>{p.summary.total_required ?? "-"}</b></div>
        </Card>
        <Card title="⚙️ سقف واحد ترم آینده">
          <div className="s360-big-number">{p.max_units_next_term.value}</div>
          <span className={`risk-badge ${riskBadge}`}>ریسک: {p.risk_level}</span>
          <ul className="eng-recs">
            {p.max_units_next_term.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </Card>
      </div>

      <div className="s360-tabs-row">
        <button className={tab === "plan" ? "active" : ""} onClick={() => setTab("plan")}>🗺️ برنامه ترم‌های آینده</button>
        <button className={tab === "lists" ? "active" : ""} onClick={() => setTab("lists")}>📋 جزئیات دروس</button>
      </div>

      {tab === "plan" && (
        <>
          {p.plan.length === 0 ? <Empty>ترم پیشنهادی‌ای ساخته نشد</Empty> : p.plan.map((t) => (
            <Card key={t.label} title={`${t.label} — ${t.units} واحد (سقف: ${p.max_units_next_term.value})`}>
              <table className="s360-table">
                <thead><tr><th>کد</th><th>درس</th><th>واحد</th></tr></thead>
                <tbody>
                  {t.courses.map((c) => (
                    <tr key={c.code}><td>{c.code}</td><td><b>{c.title}</b></td><td>{c.credits}</td></tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ))}
          {p.blocked?.length > 0 && (
            <Card title="🔒 دروس قفل‌شده (پیش‌نیاز ناقص)">
              <table className="s360-table">
                <thead><tr><th>درس</th><th>پیش‌نیازهای ناقص</th></tr></thead>
                <tbody>
                  {p.blocked.map((b) => (
                    <tr key={b.code}><td><b>{b.title}</b> ({b.code})</td><td>{b.missing_prereqs.join("، ")}</td></tr>
                  ))}
                </tbody>
              </table>
              <p className="s360-hint">این دروس بعد از گذراندن پیش‌نیازها به برنامه اضافه می‌شوند.</p>
            </Card>
          )}
          {p.pending_unscheduled?.length > 0 && (
            <p className="s360-hint">دروس برنامه‌نشده (سقف واحد یا ترتیب): {p.pending_unscheduled.join("، ")}</p>
          )}
        </>
      )}

      {tab === "lists" && (
        <>
          <Card title="✅ گذرانده‌ها">
            {p.detail.passed.length === 0 ? <Empty>نمره‌ای ثبت نشده</Empty> : (
              <table className="s360-table">
                <thead><tr><th>کد</th><th>درس</th><th>واحد</th><th>ترم</th><th>نمره</th></tr></thead>
                <tbody>{p.detail.passed.map((c) => (
                  <tr key={c.code}><td>{c.code}</td><td>{c.title}</td><td>{c.credits}</td><td>{c.term}</td><td><b>{c.grade}</b></td></tr>
                ))}</tbody>
              </table>
            )}
          </Card>
          <Card title="🔄 در حال اخذ">
            {p.detail.in_progress.length === 0 ? <Empty>درسی در جاری نیست</Empty> : (
              <table className="s360-table">
                <thead><tr><th>کد</th><th>درس</th><th>واحد</th></tr></thead>
                <tbody>{p.detail.in_progress.map((c) => (
                  <tr key={c.code}><td>{c.code}</td><td>{c.title}</td><td>{c.credits}</td></tr>
                ))}</tbody>
              </table>
            )}
          </Card>
          <Card title="⬜ باقی‌مانده برنامه مصوب">
            {p.detail.remaining.length === 0 ? <Empty>باقی‌مانده‌ای نیست 🎉</Empty> : (
              <table className="s360-table">
                <thead><tr><th>کد</th><th>درس</th><th>واحد</th><th>پیش‌نیاز</th></tr></thead>
                <tbody>{p.detail.remaining.map((c) => (
                  <tr key={c.code}><td>{c.code}</td><td>{c.title}</td><td>{c.credits}</td><td>{c.prereqs?.join("، ") || "-"}</td></tr>
                ))}</tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
