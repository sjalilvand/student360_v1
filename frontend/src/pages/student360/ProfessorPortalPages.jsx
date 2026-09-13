// Student 360 - Professor Portal v2 (rich UI: KPI gradient cards + weekly availability grid).
import { useEffect, useMemo, useState } from "react";
import { GraduationCap, ClipboardList, CalendarDays, BookOpen, Plus, Trash2, KeyRound, Check } from "lucide-react";
import { Card, Disclaimer, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const AUTH = () => ({
  "Authorization": "Bearer " + (localStorage.getItem("s360_token") || ""),
  "Content-Type": "application/json",
});
const DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه شنبه", "چهارشنبه", "پنجشنبه"];
const SLOTS = [
  { label: "۰۸-۱۰", start: "08:00", end: "10:00" },
  { label: "۱۰-۱۲", start: "10:00", end: "12:00" },
  { label: "۱۲-۱۴", start: "12:00", end: "14:00" },
  { label: "۱۴-۱۶", start: "14:00", end: "16:00" },
  { label: "۱۶-۱۸", start: "16:00", end: "18:00" },
];
const ST_MAP = { pending: "در انتظار بررسی", approved: "تایید شده", rejected: "رد شده" };

function useMe() {
  const [me, setMe] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/api/professor/me`, { headers: AUTH() })
      .then((r) => r.json()).then(setMe).catch(() => setMe({ error: true }));
  }, []);
  return me;
}

/* ---------- Dashboard: gradient KPI cards ---------- */
export function ProfessorDashboardPage() {
  const me = useMe();
  if (!me) return <Loading />;
  if (me.error) return <p className="s360-error">خطا در دریافت اطلاعات</p>;
  const s = me.stats || {};
  const kpis = [
    { t: "پیشنهادهای من", v: s.proposals_total ?? 0, icon: <ClipboardList size={26} />, g: "pf-kpi-indigo" },
    { t: "در انتظار بررسی", v: s.proposals_pending ?? 0, icon: <CalendarDays size={26} />, g: "pf-kpi-amber" },
    { t: "بازه‌های دسترس‌بازی", v: s.availability_slots ?? 0, icon: <CalendarDays size={26} />, g: "pf-kpi-green" },
    { t: "سقف واحدها", v: s.max_units ?? "-", icon: <BookOpen size={26} />, g: "pf-kpi-sky" },
  ];
  return (
    <div className="s360-page">
      <div className="pf-hero">
        <GraduationCap size={34} />
        <div>
          <h2>خوش آمدید، {me.user?.full_name}</h2>
          <small>کد استاد: {me.user?.instructor_code || "-"}</small>
        </div>
      </div>
      <div className="pf-kpi-grid">
        {kpis.map((k) => (
          <div key={k.t} className={`pf-kpi ${k.g}`}>
            {k.icon}
            <div className="pf-kpi-num">{k.v}</div>
            <div className="pf-kpi-t">{k.t}</div>
          </div>
        ))}
      </div>
      <Disclaimer text="این پنل برای ثبت پیشنهاد ارائه درس و دسترس‌بازی شماست؛ تصمیم نهایی با گروه آموزشی است." />
    </div>
  );
}

/* ---------- Availability: weekly clickable grid ---------- */
export function ProfessorAvailabilityPage() {
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    fetch(`${API_BASE}/api/professor/availability`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(load, []);

  const has = (day, slot) =>
    (items || []).some((s) => s.day === day && s.start_time === slot.start);

  async function toggle(day, slot) {
    if (busy) return;
    setBusy(true); setErr(""); setMsg("");
    const on = has(day, slot);
    try {
      if (on) {
        const target = items.find((s) => s.day === day && s.start_time === slot.start);
        const r = await fetch(`${API_BASE}/api/professor/availability/${target.id}`,
          { method: "DELETE", headers: AUTH() });
        if (!r.ok) throw new Error("حذف ناموفق");
        setMsg(`بازه ${day} ${slot.label} حذف شد`);
      } else {
        const r = await fetch(`${API_BASE}/api/professor/availability`, {
          method: "POST", headers: AUTH(),
          body: JSON.stringify({ day, start_time: slot.start, end_time: slot.end }) });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.detail || "ثبت ناموفق");
        setMsg(`بازه ${day} ${slot.label} ثبت شد`);
      }
      load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="s360-page">
      <h2>🗓️ دسترس‌بازی هفتگی من</h2>
      <Disclaimer text="روی خانه‌ها کلیک کنید تا بازه‌های آماده تدریس شما ثبت یا حذف شود." />
      {(msg || err) && <div className={err ? "s360-error" : "hub-ok"}>{err || msg}</div>}
      {!items ? <Loading /> : (
        <Card title="آماده تدریس هستم در...">
          <table className="pf-grid">
            <thead>
              <tr><th></th>{DAYS.map((d) => <th key={d}>{d}</th>)}</tr>
            </thead>
            <tbody>
              {SLOTS.map((slot) => (
                <tr key={slot.label}>
                  <td className="pf-slot-label">{slot.label}</td>
                  {DAYS.map((d) => {
                    const on = has(d, slot);
                    return (
                      <td key={d}>
                        <button className={"pf-cell" + (on ? " on" : "")}
                                disabled={busy}
                                onClick={() => toggle(d, slot)}
                                title={on ? "حذف بازه" : "افزودن بازه"}>
                          {on ? <Check size={15} /> : ""}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="s360-hint">🟩 = آماده تدریس • کلیک = تغییر وضعیت</p>
        </Card>
      )}
    </div>
  );
}

/* ---------- Proposals ---------- */
export function ProfessorProposalsPage() {
  const [items, setItems] = useState(null);
  const [courses, setCourses] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(null);
  const [day, setDay] = useState("");
  const [st, setSt] = useState("");
  const [et, setEt] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    fetch(`${API_BASE}/api/professor/proposals`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(() => {
    load();
    fetch(`${API_BASE}/api/professor/course-options`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => setCourses(j.items || [])).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const qn = q.trim().toLowerCase();
    if (!qn) return courses.slice(0, 40);
    return courses.filter((c) =>
      c.title.toLowerCase().includes(qn) || String(c.code).includes(qn)).slice(0, 40);
  }, [courses, q]);

  async function create() {
    if (!picked) { setErr("اول درس را انتخاب کنید"); return; }
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await fetch(`${API_BASE}/api/professor/proposals`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ course_code: picked.code, term_code: "14051",
                               day_of_week: day, start_time: st, end_time: et, notes }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "خطا");
      setMsg(j.message || "✅ ثبت شد"); setPicked(null); setNotes("");
      setDay(""); setSt(""); setEt(""); load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function del(id) {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/professor/proposals/${id}`,
        { method: "DELETE", headers: AUTH() });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg("✅ حذف شد"); load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="s360-page">
      <h2>📝 پیشنهاد ارائه دروس</h2>
      {(msg || err) && <div className={err ? "s360-error" : "hub-ok"}>{err || msg}</div>}

      <Card title="➕ پیشنهاد درس جدید">
        <div className="hub-picker">
          <input placeholder="نام یا کد درس را جستجو کنید..."
                 value={picked ? `${picked.title} (${picked.code})` : q}
                 onFocus={() => { setPicked(null); setOpen(true); }}
                 onChange={(e) => { setQ(e.target.value); setOpen(true); }} />
          {open && !picked && (
            <div className="hub-list">
              {filtered.length === 0 && <div className="hub-empty">درسی یافت نشد</div>}
              {filtered.map((c) => (
                <div key={c.id} className="hub-item"
                     onClick={() => { setPicked(c); setOpen(false); }}>
                  <b>{c.title}</b> <small>({c.code})</small>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="s360-form-row" style={{ marginTop: ".6rem" }}>
          <select value={day} onChange={(e) => setDay(e.target.value)}>
            <option value="">روز (اختیاری)</option>
            {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <input type="time" value={st} onChange={(e) => setSt(e.target.value)} title="ساعت شروع" />
          <input type="time" value={et} onChange={(e) => setEt(e.target.value)} title="ساعت پایان" />
        </div>
        <input placeholder="یادداشت (اختیاری)" value={notes}
               onChange={(e) => setNotes(e.target.value)}
               style={{ width: "100%", marginTop: ".5rem", padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", fontFamily: "inherit" }} />
        <div className="hub-actions">
          <button className="hub-btn like" disabled={busy || !picked}
                  onClick={create}>📨 ثبت پیشنهاد</button>
        </div>
      </Card>

      <Card title={`📋 پیشنهادهای من (${items?.length ?? 0})`}>
        {!items ? <Loading /> : items.length === 0 ? <Empty>پیشنهادی ثبت نشده</Empty> : (
          <table className="s360-table">
            <thead><tr><th>کد</th><th>درس</th><th>روز</th><th>ساعت</th><th>وضعیت</th><th>یادداشت</th><th></th></tr></thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>{p.unique_course_code}</td>
                  <td><b>{p.course_name}</b></td>
                  <td>{p.day_of_week || "-"}</td>
                  <td>{p.start_time ? p.start_time + "-" + (p.end_time || "?") : "-"}</td>
                  <td>{ST_MAP[p.status] || p.status}</td>
                  <td>{p.notes || "-"}</td>
                  <td><button className="hub-del" disabled={busy}
                              onClick={() => del(p.id)}><Trash2 size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

/* ---------- Change password ---------- */
export function ProfessorPasswordPage() {
  const [oldp, setOldp] = useState("");
  const [newp, setNewp] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function change() {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await fetch(`${API_BASE}/api/professor/change-password`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ old_password: oldp, new_password: newp }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg("✅ رمز عبور تغییر کرد"); setOldp(""); setNewp("");
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="s360-page">
      <h2>🔑 تغییر رمز عبور</h2>
      <Card title="تغییر رمز عبور استاد">
        <div className="interv-form">
          <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
            <KeyRound size={18} />
            <input type="password" placeholder="رمز فعلی" value={oldp}
                   onChange={(e) => setOldp(e.target.value)} autoComplete="current-password"
                   style={{ flex: 1, padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", fontFamily: "inherit" }} />
          </div>
          <input type="password" placeholder="رمز جدید (حداقل ۴ کاراکتر)" value={newp}
                 onChange={(e) => setNewp(e.target.value)} autoComplete="new-password"
                 style={{ padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", fontFamily: "inherit" }} />
          <button className="hub-btn like" onClick={change} disabled={busy}>ثبت</button>
        </div>
        {msg && <p className="s360-success">{msg}</p>}
        {err && <p className="s360-error">{err}</p>}
      </Card>
    </div>
  );
}
