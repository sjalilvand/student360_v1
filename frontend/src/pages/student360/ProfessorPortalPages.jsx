// Student 360 - Professor portal pages (Phase C).
import { useEffect, useMemo, useState } from "react";
import { Card, Disclaimer, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const AUTH = () => ({
  "Authorization": "Bearer " + (localStorage.getItem("s360_token") || ""),
  "Content-Type": "application/json",
});
const DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه شنبه", "چهارشنبه", "پنجشنبه", "جمعه"];
const ST_MAP = { pending: "در انتظار بررسی", approved: "تایید شده", rejected: "رد شده" };

function useMe() {
  const [me, setMe] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/api/professor/me`, { headers: AUTH() })
      .then((r) => r.json()).then(setMe).catch(() => setMe({ error: true }));
  }, []);
  return me;
}

export function ProfessorDashboardPage() {
  const me = useMe();
  if (!me) return <Loading />;
  if (me.error) return <p className="s360-error">خطا در دریافت اطلاعات</p>;
  const s = me.stats || {};
  const cards = [
    { t: "پیشنهادهای من", v: s.proposals_total, i: "📝" },
    { t: "در انتظار بررسی", v: s.proposals_pending, i: "⏳" },
    { t: "بازه‌های دسترس‌بازی", v: s.availability_slots, i: "🗓️" },
    { t: "سقف واحدها", v: s.max_units ?? "-", i: "📚" },
  ];
  return (
    <div className="s360-page">
      <h2>👨‍🏫 پورتال استاد</h2>
      <Disclaimer text="این پنل برای ثبت پیشنهاد ارائه درس و دسترس‌بازی شماست؛ تصمیم نهایی با گروه آموزشی است." />
      <div className="s360-grid-2">
        {cards.map((c) => (
          <Card key={c.t} title={`${c.i} ${c.t}`}>
            <div className="s360-big-number">{c.v}</div>
          </Card>
        ))}
      </div>
      <p className="s360-hint">خوش آمدید {me.user?.full_name} — کد استاد: {me.user?.instructor_code || "-"}</p>
    </div>
  );
}

export function ProfessorProposalsPage() {
  const me = useMe();
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
      const b = { course_code: picked.code, term_code: "14051",
                  day_of_week: day, start_time: st, end_time: et, notes };
      const r = await fetch(`${API_BASE}/api/professor/proposals`, {
        method: "POST", headers: AUTH(), body: JSON.stringify(b) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "خطا");
      setMsg(j.message || "✅ ثبت شد"); setPicked(null); setNotes(""); setDay(""); setSt(""); setEt("");
      load();
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
      setMsg("✅ پیشنهاد حذف شد"); load();
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
                              onClick={() => del(p.id)}>🗑</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

export function ProfessorAvailabilityPage() {
  const [items, setItems] = useState(null);
  const [day, setDay] = useState("شنبه");
  const [st, setSt] = useState("08:00");
  const [et, setEt] = useState("12:00");
  const [pr, setPr] = useState(2);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    fetch(`${API_BASE}/api/professor/availability`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(load, []);

  async function create() {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await fetch(`${API_BASE}/api/professor/availability`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ day, start_time: st, end_time: et, priority: +pr }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg("✅ بازه ثبت شد"); load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function del(id) {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/professor/availability/${id}`,
        { method: "DELETE", headers: AUTH() });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg("✅ حذف شد"); load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="s360-page">
      <h2>🗓️ دسترس‌بازی من</h2>
      {(msg || err) && <div className={err ? "s360-error" : "hub-ok"}>{err || msg}</div>}

      <Card title="➕ افزودن بازه دسترس‌بازی">
        <div className="s360-form-row">
          <select value={day} onChange={(e) => setDay(e.target.value)}>
            {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <input type="time" value={st} onChange={(e) => setSt(e.target.value)} />
          <input type="time" value={et} onChange={(e) => setEt(e.target.value)} />
          <select value={pr} onChange={(e) => setPr(+e.target.value)} title="اولویت">
            <option value={1}>اولویت ۱ (بالا)</option>
            <option value={2}>اولویت ۲</option>
            <option value={3}>اولویت ۳</option>
          </select>
          <button className="hub-btn like" disabled={busy} onClick={create}>➕ ثبت بازه</button>
        </div>
      </Card>

      <Card title="بازه‌های من">
        {!items ? <Loading /> : items.length === 0 ? <Empty>بازه‌ای ثبت نشده</Empty> : (
          <table className="s360-table">
            <thead><tr><th>روز</th><th>از</th><th>تا</th><th>بازه</th><th>اولویت</th><th></th></tr></thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td><b>{s.day}</b></td>
                  <td>{s.start_time}</td>
                  <td>{s.end_time}</td>
                  <td>{s.time_group || "-"}</td>
                  <td>{s.priority}</td>
                  <td><button className="hub-del" disabled={busy}
                              onClick={() => del(s.id)}>🗑</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

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
        method: "POST", headers: AUTH(), body: JSON.stringify({ old_password: oldp, new_password: newp }) });
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
          <input type="password" placeholder="رمز فعلی" value={oldp}
                 onChange={(e) => setOldp(e.target.value)} autoComplete="current-password" />
          <input type="password" placeholder="رمز جدید (حداقل ۴ کاراکتر)" value={newp}
                 onChange={(e) => setNewp(e.target.value)} autoComplete="new-password" />
          <button onClick={change} disabled={busy}>{busy ? "..." : "ثبت"}</button>
        </div>
        {msg && <p className="s360-success">{msg}</p>}
        {err && <p className="s360-error">{err}</p>}
      </Card>
    </div>
  );
}
