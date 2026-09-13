// Staff - Survey management (activate courses per survey type).
import { useEffect, useMemo, useState } from "react";
import { Card, Loading } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const HEADERS = () => ({ "Content-Type": "application/json" });
const TYPES = [
  { id: "request", label: "💡 نظرسنجی پیشنهاد/درخواست درس" },
  { id: "rating", label: "⭐ نظرسنجی امتیازدهی به برنامه" },
];

export function SurveyManagementPage() {
  const [type, setType] = useState("request");
  const [all, setAll] = useState(null);
  const [active, setActive] = useState({});
  const [term, setTerm] = useState("1405-1");
  const [q, setQ] = useState("");

  const load = () => {
    fetch(`${API_BASE}/api/professor/course-options`).then((r) => r.json())
      .then((j) => setAll(j.items || [])).catch(() => setAll([]));
    fetch(`${API_BASE}/api/vote-polls/active?survey_type=${type}&term=${term}`)
      .then((r) => r.json()).then((j) => {
        const m = {};
        (j.items || []).forEach((i) => { m[i.course_id] = true; });
        setActive(m);
      }).catch(() => setActive({}));
  };
  useEffect(load, [type, term]);

  const filtered = useMemo(() => {
    const qn = q.trim().toLowerCase();
    if (!qn) return (all || []).slice(0, 60);
    return (all || []).filter((c) =>
      c.title.toLowerCase().includes(qn) || String(c.code).includes(qn)).slice(0, 60);
  }, [all, q]);

  async function toggle(courseId) {
    const willBeActive = !active[courseId];
    await fetch(`${API_BASE}/api/vote-polls/update`, {
      method: "PUT", headers: HEADERS(),
      body: JSON.stringify({ course_id: courseId, survey_type: type,
                             term, is_active: willBeActive }) });
    setActive((m) => ({ ...m, [courseId]: willBeActive }));
  }

  if (!all) return <Loading />;
  const activeCount = Object.values(active).filter(Boolean).length;

  return (
    <div className="s360-page">
      <h2>⚙️ مدیریت نظرسنجی دروس</h2>
      <div className="s360-form-row" style={{ margin: ".6rem 0" }}>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="1405-1">ترم 1405-1</option>
          <option value="1404-2">ترم 1404-2</option>
        </select>
        <span className="mart-chip" style={{ color: "#15803d" }}>
          ✅ {activeCount} درس فعال
        </span>
        <span className="s360-hint">از {all.length} درس کل</span>
      </div>
      <input placeholder="جستجوی درس..." value={q}
             onChange={(e) => setQ(e.target.value)}
             style={{ width: "100%", padding: ".5rem", borderRadius: 8,
                      border: "1px solid #d1d5db", marginBottom: ".8rem", fontFamily: "inherit" }} />
      <div className="sv-cards">
        {filtered.map((c) => (
          <div key={c.id} className={"sv-card" + (active[c.id] ? " selected" : "")}>
            <div className="sv-card-head">
              <span className="sv-code">{c.code}</span>
              {active[c.id] && <span className="sv-badge sel">فعال برای نظرسنجی</span>}
            </div>
            <h4>{c.title}</h4>
            <div className="hub-actions">
              <button className={active[c.id] ? "hub-del" : "hub-btn like"}
                      onClick={() => toggle(c.id)}>
                {active[c.id] ? "⛔ لغو فعال‌سازی" : "✅ انتخاب برای نظرسنجی"}
              </button>
            </div>
          </div>
        ))}
      </div>
      <p className="s360-hint">درس‌های فعال‌شده بلافاصله در هاب نظرسنجی دانشجویان ظاهر می‌شوند.</p>
    </div>
  );
}


export default SurveyManagementPage;

