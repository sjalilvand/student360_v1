// components/MartDashboard.jsx - Analytics overlay over Data Marts (Phase 1) + Jalali calendar.
import { useEffect, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  LineChart, Line, Legend,
} from "recharts";
import "./mart-dashboard.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const WEEKDAYS_FA = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
const VIEW_LABELS = {
  v_event_daily: "رویدادها بر اساس روز",
  v_event_totals: "مجموع رویدادها بر اساس نوع",
  v_student_gpa: "معدل وزنی دانشجویان",
  v_course_demand: "پیش‌بینی تقاضای دروس",
  v_term_enrollment: "روند ثبت‌نام ترم‌ها",
};

function JalaliCalendarCard({ onYear, onMonth, cal }) {
  if (!cal) return <section className="mart-card"><h3>تقویم شمسی رویدادها</h3><p className="mart-empty">...</p></section>;
  const blanks = cal.days.length ? cal.days[0].weekday_index : 0;
  const maxCount = Math.max(1, ...cal.days.map((d) => d.count));
  return (
    <section className="mart-card">
      <h3>📅 تقویم شمسی رویدادها — {cal.month_name} {cal.year}</h3>
      <div className="jal-nav">
        <button onClick={() => onMonth(cal.year, cal.month === 1 ? 12 : cal.month - 1)}>‹ ماه قبل</button>
        <span>امروز: {cal.today_jalali} | مجموع رویداد ماه: {cal.total_events}</span>
        <button onClick={() => onMonth(cal.year, cal.month === 12 ? 1 : cal.month + 1)}>ماه بعد ›</button>
      </div>
      <div className="jal-grid">
        {WEEKDAYS_FA.map((w) => <div key={w} className="jal-head">{w}</div>)}
        {Array.from({ length: blanks }).map((_, i) => <div key={"b" + i} className="jal-cell empty" />)}
        {cal.days.map((d) => {
          const intensity = d.count === 0 ? 0 : 0.25 + 0.75 * (d.count / maxCount);
          return (
            <div key={d.day}
                 className={"jal-cell" + (d.is_today ? " today" : "") + (d.count ? " has" : "")}
                 style={d.count ? { background: `rgba(99,102,241,${intensity})`, color: "#fff" } : {}}
                 title={`${d.count} رویداد`}>
              {d.day}{d.count > 0 && <small>{d.count}</small>}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function MartDashboard({ onClose }) {
  const [status, setStatus] = useState([]);
  const [data, setData] = useState({});
  const [jalDaily, setJalDaily] = useState([]);
  const [cal, setCal] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function runDemand() {
    setErr(""); setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/demand/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ semester: "mehr" }),
      });
      const j = await r.json();
      if (!r.ok || j.ok === false) throw new Error(j.detail || "unknown error");
    } catch (e) {
      setErr("پیش‌بینی تقاضا ناموفق بود: " + (e.message || ""));
    } finally { setBusy(false); loadAll(true); }
  }

  async function loadAll(refresh, calYear = 0, calMonth = 0) {
    setErr(""); setBusy(true);
    try {
      if (refresh) await fetch(`${API_BASE}/api/marts/refresh`, { method: "POST" });
      const st = await (await fetch(`${API_BASE}/api/marts/status`)).json();
      setStatus(st);
      const out = {};
      for (const s of st) {
        try {
          const r = await (await fetch(`${API_BASE}/api/marts/${s.view}/sample?limit=200`)).json();
          out[s.view] = r.rows || [];
        } catch { out[s.view] = []; }
      }
      setData(out);
      const jd = await (await fetch(`${API_BASE}/api/events/daily-jalali?days=14`)).json();
      setJalDaily(jd.items || []);
      const jc = await (await fetch(`${API_BASE}/api/events/calendar-jalali?year=${calYear}&month=${calMonth}`)).json();
      setCal(jc);
    } catch {
      setErr("خطا در دریافت داده‌ها - بک‌اند در دسترس نیست");
    } finally { setBusy(false); }
  }

  useEffect(() => { loadAll(false); }, []);

  const totals = (data.v_event_totals || []).map((r) => ({
    name: r.event_type, رویداد: r.events, دانشجو: r.students,
  })).slice(0, 10);

  const demand = (data.v_course_demand || [])
    .filter((r) => (r.demand_prediction || 0) > 0)
    .sort((a, b) => (b.demand_prediction || 0) - (a.demand_prediction || 0))
    .slice(0, 12)
    .map((r) => ({
      name: (r.title || r.course_code || "").slice(0, 18),
      پیش‌بینی: Math.round(r.demand_prediction || 0),
      ثبت‌نام: Math.round(r.enrollment_count || 0),
      ظرفیت: r.estimated_capacity ?? 0,
    }));

  const terms = (data.v_term_enrollment || []).map((r) => ({
    name: r.term, ثبت‌نام: r.enrollments, دانشجو: r.students,
  }));

  return (
    <div className="mart-overlay">
      <div className="mart-panel">
        <header className="mart-header">
          <h2>📊 داشبورد تحلیل (Data Marts)</h2>
          <div className="mart-actions">
            <button onClick={runDemand} disabled={busy}>🤖 پیش‌بینی تقاضا</button>
            <button onClick={() => loadAll(true)} disabled={busy}>
              {busy ? "..." : "🔄 به‌روزرسانی مارت‌ها"}
            </button>
            <button className="mart-close" onClick={onClose}>✕ بستن</button>
          </div>
        </header>

        {err && <p className="mart-error">{err}</p>}

        <div className="mart-chips">
          {status.map((s) => (
            <span key={s.view} className="mart-chip" title={VIEW_LABELS[s.view] || s.view}>
              {s.view}: {s.rows} ردیف
            </span>
          ))}
        </div>

        <div className="mart-grid">
          <JalaliCalendarCard cal={cal}
            onMonth={(y, m) => loadAll(false, y, m)} />

          <section className="mart-card">
            <h3>روند رویدادها (۱۴ روز اخیر - شمسی)</h3>
            {jalDaily.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={jalDaily}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="jalali" fontSize={10} />
                  <YAxis fontSize={11} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" name="رویداد" stroke="#6366f1" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="mart-empty">داده‌ای نیست</p>}
          </section>

          <section className="mart-card">
            <h3>رویدادها بر اساس نوع</h3>
            {totals.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={totals}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={10} />
                  <YAxis fontSize={11} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="رویداد" fill="#6366f1" />
                  <Bar dataKey="دانشجو" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="mart-empty">داده‌ای نیست</p>}
          </section>

          <section className="mart-card">
            <h3>پیش‌بینی تقاضا vs ثبت‌نام (۱۲ درس برتر)</h3>
            {demand.length ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={demand} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" fontSize={11} />
                  <YAxis type="category" dataKey="name" width={120} fontSize={10} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="پیش‌بینی" fill="#f59e0b" />
                  <Bar dataKey="ثبت‌نام" fill="#3b82f6" />
                  <Bar dataKey="ظرفیت" fill="#94a3b8" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="mart-empty">پیش‌بینی تقاضا هنوز محاسبه نشده (مرحله Workflow)</p>}
          </section>

          <section className="mart-card">
            <h3>معدل وزنی دانشجویان <small className="mart-src">(منبع: مارت v_student_gpa)</small></h3>
            {(data.v_student_gpa || []).length ? (
              <table className="mart-table">
                <thead><tr><th>دانشجو</th><th>درس</th><th>واحد</th><th>میانگین</th><th>GPA وزنی</th></tr></thead>
                <tbody>
                  {data.v_student_gpa.map((r) => (
                    <tr key={r.student_id}>
                      <td>{r.full_name} ({r.student_number})</td>
                      <td>{r.graded_courses}</td>
                      <td>{r.total_credits}</td>
                      <td>{r.avg_score}</td>
                      <td><b>{r.weighted_gpa}</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="mart-empty">داده نمره‌ای موجود نیست</p>}
          </section>

          {terms.length > 0 && (
            <section className="mart-card">
              <h3>ثبت‌نام ترم‌ها</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={terms}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={10} />
                  <YAxis fontSize={11} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="ثبت‌نام" fill="#8b5cf6" />
                  <Bar dataKey="دانشجو" fill="#06b6d4" />
                </BarChart>
              </ResponsiveContainer>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

