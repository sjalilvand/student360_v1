// Student 360 - Staff workspace pages (education-expert).
import { useEffect, useState } from "react";
import { Card, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
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
      <input placeholder="جستجو (نام یا شماره دانشجویی)..."
             value={q} onChange={(e) => setQ(e.target.value)}
             style={{ width: "100%", padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", marginBottom: ".8rem", fontFamily: "inherit" }} />
      {filtered.length === 0 ? <Empty>دانشجویی یافت نشد</Empty> : (
        <table className="s360-table">
          <thead><tr><th>شماره</th><th>نام</th><th>رشته</th><th>وضعیت</th><th>GPA وزنی</th><th>واحد</th></tr></thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id}>
                <td>{r.student_number}</td>
                <td><b>{r.full_name || "-"}</b></td>
                <td>{r.program || "-"}</td>
                <td>{r.student_status || "-"}</td>
                <td>{r.weighted_gpa != null ? <b>{r.weighted_gpa}</b> : "-"}</td>
                <td>{r.total_credits ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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
      {items.length === 0 ? <Empty>داده تعاملی موجود نیست</Empty> : (
        <table className="s360-table">
          <thead><tr><th>#</th><th>کاربر</th><th>شاخص تعامل</th><th>رویدادها</th><th>روز فعال</th><th>تعامل عمیق</th><th>آخرین فعالیت</th></tr></thead>
          <tbody>
            {items.map((r, i) => (
              <tr key={r.student_ref}>
                <td>{i + 1}</td>
                <td><b>{r.student_ref}</b></td>
                <td><span style={{ color: color(r.score), fontWeight: 700 }}>{r.score}</span></td>
                <td>{r.events}</td>
                <td>{r.active_days}</td>
                <td>{r.deep_actions}</td>
                <td>{r.last_activity ? new Date(r.last_activity).toLocaleString("fa-IR") : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="s360-hint">منبع: event_log — شاخص ترکیبی از فراوانی، پیوستگی و عمق تعامل.</p>
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
      {items.length === 0 ? <Empty>دانشجویی موجود نیست</Empty> : (
        <table className="s360-table">
          <thead><tr><th>دانشجو</th><th>ریسک</th><th>GPA</th><th>مردودی</th><th>مشروطی</th><th>تعامل</th><th></th></tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.student_number}>
                <td><b>{r.student_name || "-"} ({r.student_number})</b></td>
                <td><span style={{ color: color(r.risk_level), fontWeight: 700 }}>
                  {r.risk_score} — {r.risk_level}</span></td>
                <td>{r.gpa ?? "-"}</td>
                <td>{r.failed_credits}</td>
                <td>{r.probation_count}</td>
                <td>{r.engagement_score}</td>
                <td><button onClick={() => setOpen(open === r.student_number ? null : r.student_number)}>
                  {open === r.student_number ? "بستن" : "جزئیات"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {items.filter((r) => open === r.student_number).map((r) => (
        <Card key={"d" + r.student_number} title={`دلایل ریسک — ${r.student_name || r.student_number}`}>
          {r.reasons?.length === 0 ? <p>عاملی یافت نشد ✅</p> : (
            <ul className="eng-recs">{r.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
          )}
          <b>اقدام پیشنهادی:</b>
          <ul className="eng-recs">{(r.suggested_actions || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
          <p className="s360-hint">{r.disclaimer}</p>
        </Card>
      ))}
    </div>
  );
}

export function StaffInterventionsPage() {
  const [items, setItems] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(null);
  const [form, setForm] = useState({ id: null, status: "reviewed", note: "" });

  const load = () =>
    fetch(`${API_BASE}/api/intervention/list`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  async function runScan() {
    setBusy(true); setMsg("");
    try {
      const j = await fetch(`${API_BASE}/api/intervention/run`, { method: "POST", headers: HEADERS() }).then((r) => r.json());
      setMsg("اسکن کامل شد — جدید: " + (j.created || []).length + " | موجود: " + (j.skipped || []).length);
      load();
    } catch { setMsg("خطا در اجرای اسکن"); }
    finally { setBusy(false); }
  }

  async function submitReview(id) {
    try {
      await fetch(`${API_BASE}/api/intervention/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...HEADERS() },
        body: JSON.stringify({ status: form.status, note: form.note, reviewer: localStorage.getItem("s360_student_number") || "staff" }),
      });
      setForm({ id: null, status: "reviewed", note: "" });
      setMsg("بررسی ثبت شد ✅");
      load();
    } catch { setMsg("خطا در ثبت بررسی"); }
  }

  const badge = (l) => (l === "بالا" ? "risk-high" : l === "متوسط" ? "risk-mid" : "risk-low");

  return (
    <div className="s360-page">
      <h2>🚨 مداخله‌های حمایتی</h2>
      <div style={{ display: "flex", gap: ".6rem", alignItems: "center", marginBottom: ".8rem", flexWrap: "wrap" }}>
        <button onClick={runScan} disabled={busy}>{busy ? "..." : "🔍 اسکن ریسک و تولید مداخله"}</button>
        {msg && <span className="s360-hint">{msg}</span>}
      </div>
      {!items ? <Loading /> : items.length === 0 ? <Empty>موردی نیست — دکمه اسکن را بزنید</Empty> : (
        <table className="s360-table">
          <thead><tr><th>دانشجو</th><th>ریسک</th><th>وضعیت</th><th>ثبت</th><th></th></tr></thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td><b>{it.student_name || "-"} ({it.student_number})</b></td>
                <td><span className={`risk-badge ${badge(it.risk_level)}`}>{it.risk_score} — {it.risk_level}</span></td>
                <td>{it.status_label}{it.reviewed_by ? ` (${it.reviewed_by})` : ""}</td>
                <td>{it.created_at ? new Date(it.created_at).toLocaleString("fa-IR") : "-"}</td>
                <td>
                  <button onClick={() => setOpen(open === it.id ? null : it.id)}>جزئیات</button>{" "}
                  <button onClick={() => setForm({ id: it.id, status: it.status === "open" ? "reviewed" : it.status, note: it.review_note || "" })}>بررسی</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {items && items.filter((it) => open === it.id).map((it) => (
        <Card key={"d" + it.id} title={"دلایل و اقدامات — " + (it.student_name || it.student_number)}>
          <b>دلایل:</b>
          <ul className="eng-recs">{(it.reasons || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
          <b>اقدامات پیشنهادی:</b>
          <ul className="eng-recs">{(it.suggested_actions || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
        </Card>
      ))}

      {form.id != null && items && items.filter((it) => it.id === form.id).map((it) => (
        <Card key={"f" + it.id} title={"ثبت بررسی — " + (it.student_name || it.student_number)}>
          <div className="interv-form">
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="in_progress">در حال پیگیری</option>
              <option value="reviewed">بررسی شد</option>
              <option value="closed">بسته شد</option>
              <option value="open">بازگشت به صف</option>
            </select>
            <textarea rows={2} placeholder="یادداشت بررسی (برای دانشجو نمایش داده می‌شود)"
                      value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <button onClick={() => submitReview(it.id)}>ثبت</button>
            <button className="interv-cancel" onClick={() => setForm({ id: null, status: "reviewed", note: "" })}>انصراف</button>
          </div>
          <p className="s360-hint">یادداشت شما در کارت «پیگیری کارشناس» دانشجو دیده می‌شود.</p>
        </Card>
      ))}
      <p className="s360-hint">مداخله‌ها صرفاً حمایتی هستند و مبنای هیچ تصمیم تنبیهی خودکار نیستند.</p>
    </div>
  );
}

export function StaffFeedbackPage() {
  const [q, setQ] = useState(null);
  const [insight, setInsight] = useState(null);
  const [busy, setBusy] = useState(false);
  const [days, setDays] = useState(30);

  const load = () =>
    fetch(`${API_BASE}/api/feedback/quality?days=${days}`, { headers: HEADERS() })
      .then((r) => r.json()).then(setQ).catch(() => setQ({ error: true }));
  useEffect(load, [days]);

  async function analyze() {
    setBusy(true);
    try {
      const j = await fetch(`${API_BASE}/api/feedback/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...HEADERS() },
        body: JSON.stringify({ days }),
      }).then((r) => r.json());
      setInsight(j);
    } catch { setInsight(null); }
    finally { setBusy(false); load(); }
  }

  const useLatest = !insight && q && q.latest_insight;
  const shown = insight || (useLatest ? { ...q.latest_insight, stats: q } : null);

  if (!q) return <Loading />;
  return (
    <div className="s360-page">
      <h2>💬 کیفیت پاسخ‌ها و بازخوردها</h2>
      <div style={{ display: "flex", gap: ".5rem", alignItems: "center", marginBottom: ".8rem", flexWrap: "wrap" }}>
        <select value={days} onChange={(e) => setDays(+e.target.value)}
                style={{ padding: ".4rem", borderRadius: 8, border: "1px solid #d1d5db", fontFamily: "inherit" }}>
          <option value={30}>۳۰ روز اخیر</option>
          <option value={60}>۶۰ روز اخیر</option>
          <option value={90}>۹۰ روز اخیر</option>
        </select>
        <button onClick={analyze} disabled={busy}>{busy ? "..." : "🤖 تحلیل هوشمند الگوها (LLM)"}</button>
        <span className="s360-hint">داده: {q.total_conversations} گفتگو | {q.ai_events} رویداد AI</span>
      </div>

      <div className="s360-grid-2">
        <Card title="😍 رضایت کاربران">
          <div className="s360-big-number">{q.satisfaction_pct != null ? q.satisfaction_pct + "٪" : "-"}</div>
          <div className="s360-kv"><span>👍 مفید:</span><b>{q.helpful}</b></div>
          <div className="s360-kv"><span>👎 غیرمفید:</span><b>{q.not_helpful}</b></div>
          <div className="s360-kv"><span>بدون بازخورد:</span><b>{q.total_conversations - q.with_feedback}</b></div>
        </Card>
        <Card title="⚠️ سیگنال‌های کیفیت">
          <div className="s360-kv"><span>پاسخ‌های کم‌اطمینان:</span><b>{q.low_confidence}</b></div>
          <div className="s360-kv"><span>رویداد AI کم‌اطمینان:</span><b>{q.ai_low_conf_events ?? "-"}</b></div>
          <div className="s360-kv"><span>مجموع گفتگوها:</span><b>{q.total_conversations}</b></div>
        </Card>
      </div>

      {shown && (
        <Card title={`🤖 بینش تحلیلی (${shown.engine === "llm" ? "LLM" : "قاعده‌محور"})`}>
          {shown.summary && <p><b>{shown.summary}</b></p>}
          {(shown.insight?.themes || []).length > 0 && (
            <>
              <b>مضمون‌های نارضایتی:</b>
              <div className="eng-chips" style={{ margin: ".4rem 0" }}>
                {shown.insight.themes.map((t, i) => (
                  <span key={i} className="mart-chip" title={t.example}>{t.theme}{t.count ? ` (${t.count})` : ""}</span>
                ))}
              </div>
            </>
          )}
          {(shown.insight?.recommendations || []).length > 0 && (
            <>
              <b>توصیه‌های محصولی:</b>
              <ul className="eng-recs">{shown.insight.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </>
          )}
        </Card>
      )}

      <Card title="👎 پرسش‌های نارضایتی‌ساز (جدیدترین)">
        {(q.disliked || []).length === 0 ? <Empty>بازخورد منفی ثبت نشده ✅</Empty> : (
          <table className="s360-table">
            <thead><tr><th>پرسش</th><th>دسته (قاعده‌محور)</th><th>زمان</th></tr></thead>
            <tbody>{q.disliked.slice().reverse().map((d, i) => (
              <tr key={i}><td>{d.q}</td><td>{d.cat}</td>
              <td>{d.at ? new Date(d.at).toLocaleString("fa-IR") : "-"}</td></tr>
            ))}</tbody>
          </table>
        )}
      </Card>

      {(q.low_conf_questions || []).length > 0 && (
        <Card title="🟡 پرسش‌های کم‌اطمینان (نیازمند مستندسازی)">
          <ul className="eng-recs">{q.low_conf_questions.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </Card>
      )}
    </div>
  );
}
