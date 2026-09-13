// Student 360 - Staff workspace pages (overview/students/engagement/risk/interventions/feedback/graph/votes).
import { useEffect, useMemo, useState } from "react";
import { Card, Loading, Empty } from "./shared";
import SurveyManagementPage from "./SurveyManagementPage";
import VoteStatsCard from "../../components/VoteStatsCard";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const HEADERS = () => ({ "X-Student-Number": localStorage.getItem("s360_student_number") || "" });

export function StaffOverviewPage() {
  const [ov, setOv] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/api/staff/overview`, { headers: HEADERS() })
      .then((r) => r.json()).then(setOv).catch(() => setOv({ error: true }));
  }, []);
  if (!ov) return <Loading />;
  const cards = [
    { t: "دانشجویان", v: ov.students, i: "👨‍🎓" },
    { t: "برنامه‌های تحصیلی", v: ov.programs, i: "📚" },
    { t: "هشدارها", v: ov.alerts, i: "🔔" },
    { t: "مغایرت‌های باز", v: ov.discrepancies_pending, i: "📝" },
    { t: "رویدادهای ۲۴ ساعت", v: ov.events_24h, i: "⚡" },
  ];
  return (
    <div className="s360-page">
      <h2>👨‍💼 میز کار کارشناس آموزش</h2>
      <div className="s360-grid-2">
        {cards.map((c) => (
          <Card key={c.t} title={`${c.i} ${c.t}`}>
            <div className="s360-big-number">{c.v ?? "-"}</div>
          </Card>
        ))}
      </div>
      <Card title="🔓 آخرین ورودها">
        {(ov.recent_logins || []).length === 0 ? <Empty>ورودی ثبت نشده</Empty> : (
          <table className="s360-table">
            <thead><tr><th>کاربر</th><th>روش</th><th>منبع</th><th>زمان</th></tr></thead>
            <tbody>
              {ov.recent_logins.map((l, i) => (
                <tr key={i}>
                  <td><b>{l.who || "-"}</b></td><td>{l.via || "-"}</td><td>{l.src}</td>
                  <td>{l.at ? new Date(l.at).toLocaleString("fa-IR") : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

export function StaffStudentsPage() {
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState("");
  useEffect(() => {
    fetch(`${API_BASE}/api/staff/students`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setRows(j.items || [])).catch(() => setRows([]));
  }, []);
  if (!rows) return <Loading />;
  const filtered = rows.filter((r) =>
    !q || (r.full_name || "").includes(q) || (r.student_number || "").includes(q));
  return (
    <div className="s360-page">
      <h2>👨‍🎓 دانشجویان</h2>
      <input placeholder="جستجو..." value={q} onChange={(e) => setQ(e.target.value)}
             style={{ width: "100%", padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", marginBottom: ".8rem", fontFamily: "inherit" }} />
      <table className="s360-table">
        <thead><tr><th>شماره</th><th>نام</th><th>رشته</th><th>وضعیت</th><th>GPA</th><th>واحد</th></tr></thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={r.id}>
              <td>{r.student_number}</td><td><b>{r.full_name || "-"}</b></td>
              <td>{r.program || "-"}</td><td>{r.student_status || "-"}</td>
              <td>{r.weighted_gpa != null ? <b>{r.weighted_gpa}</b> : "-"}</td>
              <td>{r.total_credits ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StaffEngagementPage() {
  const [items, setItems] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/api/behavior/ranking?days=30&limit=50`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  }, []);
  if (!items) return <Loading />;
  const color = (s) => (s >= 75 ? "#22c55e" : s >= 50 ? "#3b82f6" : s >= 25 ? "#f59e0b" : "#ef4444");
  return (
    <div className="s360-page">
      <h2>📈 تعامل دانشجویان (۳۰ روز)</h2>
      <table className="s360-table">
        <thead><tr><th>#</th><th>کاربر</th><th>شاخص</th><th>رویدادها</th><th>روز فعال</th><th>آخرین</th></tr></thead>
        <tbody>
          {items.map((r, i) => (
            <tr key={r.student_ref}>
              <td>{i + 1}</td><td><b>{r.student_ref}</b></td>
              <td style={{ color: color(r.score), fontWeight: 700 }}>{r.score}</td>
              <td>{r.events}</td><td>{r.active_days}</td>
              <td>{r.last_activity ? new Date(r.last_activity).toLocaleString("fa-IR") : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StaffRiskPage() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/api/risk/list?limit=50`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  }, []);
  if (!items) return <Loading />;
  const color = (l) => (l === "بالا" ? "#ef4444" : l === "متوسط" ? "#f59e0b" : "#22c55e");
  return (
    <div className="s360-page">
      <h2>⚠️ هشدار زودهنگام ریسک تحصیلی</h2>
      <table className="s360-table">
        <thead><tr><th>دانشجو</th><th>ریسک</th><th>GPA</th><th>مردودی</th><th>مشروطی</th><th>تعامل</th><th></th></tr></thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.student_number}>
              <td><b>{r.student_name || "-"} ({r.student_number})</b></td>
              <td><span style={{ color: color(r.risk_level), fontWeight: 700 }}>{r.risk_score} — {r.risk_level}</span></td>
              <td>{r.gpa ?? "-"}</td><td>{r.failed_credits}</td><td>{r.probation_count}</td><td>{r.engagement_score}</td>
              <td><button onClick={() => setOpen(open === r.student_number ? null : r.student_number)}>جزئیات</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.filter((r) => open === r.student_number).map((r) => (
        <Card key={"d" + r.student_number} title={`دلایل — ${r.student_name || r.student_number}`}>
          <ul className="eng-recs">{(r.reasons || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
          <b>اقدام پیشنهادی:</b>
          <ul className="eng-recs">{(r.suggested_actions || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
        </Card>
      ))}
    </div>
  );
}

export function StaffInterventionsPage() {
  const [items, setItems] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ id: null, status: "reviewed", note: "" });

  const load = () =>
    fetch(`${API_BASE}/api/intervention/list`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(load, []);

  async function runScan() {
    setBusy(true); setMsg("");
    try {
      const j = await fetch(`${API_BASE}/api/intervention/run`, { method: "POST", headers: HEADERS() }).then((r) => r.json());
      setMsg("اسکن شد — جدید: " + (j.created || []).length);
      load();
    } finally { setBusy(false); }
  }

  async function submitReview(id) {
    try {
      await fetch(`${API_BASE}/api/intervention/${id}/review`, {
        method: "POST", headers: { "Content-Type": "application/json", ...HEADERS() },
        body: JSON.stringify({ status: form.status, note: form.note, reviewer: localStorage.getItem("s360_student_number") || "staff" }) });
      setForm({ id: null, status: "reviewed", note: "" }); setMsg("✅ ثبت شد"); load();
    } catch { setMsg("خطا"); }
  }

  const badge = (l) => (l === "بالا" ? "risk-high" : l === "متوسط" ? "risk-mid" : "risk-low");
  return (
    <div className="s360-page">
      <h2>🚨 مداخله‌های حمایتی</h2>
      <div style={{ display: "flex", gap: ".6rem", alignItems: "center", marginBottom: ".8rem" }}>
        <button onClick={runScan} disabled={busy}>🔍 اسکن ریسک</button>
        {msg && <span className="s360-hint">{msg}</span>}
      </div>
      {!items ? <Loading /> : items.length === 0 ? <Empty>موردی نیست</Empty> : (
        <table className="s360-table">
          <thead><tr><th>دانشجو</th><th>ریسک</th><th>وضعیت</th><th></th></tr></thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td><b>{it.student_name || "-"} ({it.student_number})</b></td>
                <td><span className={`risk-badge ${badge(it.risk_level)}`}>{it.risk_score} — {it.risk_level}</span></td>
                <td>{it.status_label}{it.reviewed_by ? ` (${it.reviewed_by})` : ""}</td>
                <td><button onClick={() => setForm({ id: it.id, status: it.status === "open" ? "reviewed" : it.status, note: it.review_note || "" })}>بررسی</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {form.id != null && (
        <Card title="ثبت بررسی">
          <div className="interv-form">
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="in_progress">در حال پیگیری</option>
              <option value="reviewed">بررسی شد</option>
              <option value="closed">بسته شد</option>
            </select>
            <textarea rows={2} placeholder="یادداشت (برای دانشجو نمایش داده می‌شود)"
                      value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <button onClick={() => submitReview(form.id)}>ثبت</button>
          </div>
        </Card>
      )}
    </div>
  );
}

export function StaffFeedbackPage() {
  const [q, setQ] = useState(null);
  const [insight, setInsight] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () =>
    fetch(`${API_BASE}/api/feedback/quality?days=30`, { headers: HEADERS() })
      .then((r) => r.json()).then(setQ).catch(() => setQ({ error: true }));
  useEffect(load, []);
  if (!q) return <Loading />;
  return (
    <div className="s360-page">
      <h2>💬 کیفیت پاسخ‌ها</h2>
      <div className="s360-grid-2">
        <Card title="رضایت کاربران">
          <div className="s360-big-number">{q.satisfaction_pct != null ? q.satisfaction_pct + "٪" : "-"}</div>
          <div className="s360-kv"><span>👍 مفید:</span><b>{q.helpful}</b></div>
          <div className="s360-kv"><span>👎 غیرمفید:</span><b>{q.not_helpful}</b></div>
        </Card>
        <Card title="سیگنال‌های کیفیت">
          <div className="s360-kv"><span>پاسخ کم‌اطمینان:</span><b>{q.low_confidence}</b></div>
          <div className="s360-kv"><span>رویداد AI:</span><b>{q.ai_events}</b></div>
        </Card>
      </div>
      <Card title="👎 پرسش‌های نارضایتی‌ساز">
        {(q.disliked || []).length === 0 ? <Empty>بازخورد منفی ثبت نشده ✅</Empty> : (
          <table className="s360-table">
            <thead><tr><th>پرسش</th><th>دسته</th></tr></thead>
            <tbody>{q.disliked.map((d, i) => <tr key={i}><td>{d.q}</td><td>{d.cat}</td></tr>)}</tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

export function GraphExplorerPage() {
  const [stats, setStats] = useState(null);
  const [roots, setRoots] = useState([]);
  const [query, setQuery] = useState("");
  const [cluster, setCluster] = useState(null);
  const [pf, setPf] = useState({ from: "", to: "", res: null });
  useEffect(() => {
    fetch(`${API_BASE}/api/graph/stats`).then((r) => r.json()).then(setStats).catch(() => setStats({}));
    fetch(`${API_BASE}/api/graph/roots?limit=15`).then((r) => r.json()).then((j) => setRoots(j.items || [])).catch(() => {});
  }, []);
  async function lookup(code) {
    if (!code) return;
    const j = await fetch(`${API_BASE}/api/graph/course/${encodeURIComponent(code)}`).then((r) => r.json()).catch(() => ({ error: true }));
    setCluster(j);
  }
  async function findPath() {
    if (!pf.from || !pf.to) return;
    const j = await fetch(`${API_BASE}/api/graph/path?from=${encodeURIComponent(pf.from)}&to=${encodeURIComponent(pf.to)}`)
      .then((r) => r.json()).catch(() => ({ found: false }));
    setPf({ ...pf, res: j });
  }
  if (!stats) return <Loading />;
  return (
    <div className="s360-page">
      <h2>🕸️ گراف دانش دروس</h2>
      <div className="mart-chips">
        <span className="mart-chip">درس: {stats.courses}</span>
        <span className="mart-chip">یال پیش‌نیاز: {stats.prereq_edges}</span>
        <span className="mart-chip">ریشه: {stats.roots_count}</span>
      </div>
      <Card title="🔍 کاوش یک درس">
        <div className="s360-form-row">
          <input placeholder="کد یا عنوان درس..." value={query}
                 onChange={(e) => setQuery(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && lookup(query)} />
          <button onClick={() => lookup(query)}>کاوش</button>
        </div>
        {cluster && !cluster.error && (
          <div className="s360-guide">
            <h4>{cluster.code} — {cluster.title}</h4>
            <div className="s360-kv"><span>پیش‌نیاز مستقیم:</span><b>{cluster.direct_prereqs?.join("، ") || "-"}</b></div>
            <div className="s360-kv"><span>باز می‌کند:</span><b>{cluster.unlocks_count} درس</b></div>
            <div className="s360-kv"><span>مهارت‌ها:</span><b>{cluster.skills?.join("، ") || "-"}</b></div>
          </div>
        )}
        {cluster?.error && <p className="s360-error">درس یافت نشد</p>}
      </Card>
      <Card title="🧭 مسیر یادگیری">
        <div className="s360-form-row">
          <input placeholder="از..." value={pf.from} onChange={(e) => setPf({ ...pf, from: e.target.value })} />
          <input placeholder="تا..." value={pf.to} onChange={(e) => setPf({ ...pf, to: e.target.value })} />
          <button onClick={findPath}>یافتن مسیر</button>
        </div>
        {pf.res && pf.res.found && (
          <ol className="eng-recs">{pf.res.path.map((s) => <li key={s.i}><b>{s.title}</b> ({s.code})</li>)}</ol>
        )}
        {pf.res && !pf.res.found && <Empty>مسیری یافت نشد</Empty>}
      </Card>
      <Card title="🌱 دروس شروع">
        <table className="s360-table">
          <thead><tr><th>کد</th><th>درس</th><th>باز می‌کند</th></tr></thead>
          <tbody>{roots.map((r) => (
            <tr key={r.code}><td>{r.code}</td><td><b>{r.title}</b></td><td>{r.unlocks}</td></tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}

export function StaffVotesPage() {
  const [type, setType] = useState("request");
  const [term, setTerm] = useState("1405-1");
  const [all, setAll] = useState(null);
  const [active, setActive] = useState({});
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

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

  async function toggle(courseId) {
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/vote-polls/update`, {
        method: "PUT", headers: HEADERS(),
        body: JSON.stringify({ course_id: courseId, survey_type: type,
                               term, is_active: !active[courseId] }) });
      setActive((m) => ({ ...m, [courseId]: !active[courseId] }));
    } finally { setBusy(false); }
  }

  const filtered = useMemo(() => {
    const qn = q.trim().toLowerCase();
    if (!qn) return (all || []).slice(0, 60);
    return (all || []).filter((c) =>
      c.title.toLowerCase().includes(qn) || String(c.code).includes(qn)).slice(0, 60);
  }, [all, q]);

  const activeCount = Object.values(active).filter(Boolean).length;
  return (
    <div className="s360-page">
      <h2>⚙️ مدیریت نظرسنجی دروس</h2>
      <div className="s360-form-row" style={{ margin: ".6rem 0" }}>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="request">💡 پیشنهاد/درخواست درس</option>
          <option value="rating">⭐ امتیازدهی به برنامه</option>
        </select>
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="1405-1">ترم 1405-1</option>
          <option value="1404-2">ترم 1404-2</option>
        </select>
        <span className="mart-chip" style={{ color: "#15803d" }}>
          ✅ {activeCount} درس فعال از {all ? all.length : 0}
        </span>
      </div>
      <input placeholder="جستجوی درس..." value={q} onChange={(e) => setQ(e.target.value)}
             style={{ width: "100%", padding: ".5rem", borderRadius: 8,
                      border: "1px solid #d1d5db", marginBottom: ".8rem", fontFamily: "inherit" }} />
      <div className="sv-cards">
        {(filtered || []).map((c) => (
          <div key={c.id} className={"sv-card" + (active[c.id] ? " selected" : "")}>
            <div className="sv-card-head">
              <span className="sv-code">{c.code}</span>
              {active[c.id] && <span className="sv-badge sel">فعال</span>}
            </div>
            <h4>{c.title}</h4>
            <div className="hub-actions">
              <button className={active[c.id] ? "hub-del" : "hub-btn like"}
                      disabled={busy} onClick={() => toggle(c.id)}>
                {active[c.id] ? "⛔ لغو" : "✅ فعال‌سازی"}
              </button>
            </div>
          </div>
        ))}
      </div>
      <VoteStatsCard title="📊 آمار درخواست‌های ارائه" />
    </div>
  );
}
