// Student 360 - Feedback hub v2.4 (my votes list + delete own vote/proposal).
import { useEffect, useMemo, useState } from "react";
import { Card, Disclaimer } from "./shared";
import VoteStatsCard from "../../components/VoteStatsCard";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const HEADERS = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});
const TERMS = ["1405-1", "1404-2", "1404-1"];
const ST_MAP = { pending: "در انتظار بررسی", approved: "تایید شده", rejected: "رد شده" };
const VT_MAP = { like: "👍 می‌خواهم", request: "📌 درخواست ارائه" };

export default function StudentFeedbackHub() {
  const [tab, setTab] = useState("vote");
  const [courses, setCourses] = useState([]);
  const [studentId, setStudentId] = useState(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(null);
  const [term, setTerm] = useState(TERMS[0]);
  const [desc, setDesc] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [statsKey, setStatsKey] = useState(0);
  const [mine, setMine] = useState([]);
  const [myVotes, setMyVotes] = useState([]);

  const refreshMine = () => {
    fetch(`${API_BASE}/api/proposals/mine`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setMine(j.items || [])).catch(() => {});
    fetch(`${API_BASE}/api/votes/mine`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setMyVotes(j.items || [])).catch(() => {});
  };

  useEffect(() => {
    fetch(`${API_BASE}/api/proposals/course-options`, { headers: HEADERS() })
      .then((r) => r.json())
      .then((d) => setCourses((d.items || []).filter((c) => c.id != null)))
      .catch(() => setErr("خطا در دریافت لیست دروس"));
    fetch(`${API_BASE}/api/votes/me-id`, { headers: HEADERS() })
      .then((r) => r.json())
      .then((j) => { if (j.student_id) setStudentId(j.student_id); })
      .catch(() => {});
    refreshMine();
  }, []);

  const filtered = useMemo(() => {
    const qn = q.trim().toLowerCase();
    if (!qn) return courses.slice(0, 40);
    return courses.filter((c) =>
      c.title.toLowerCase().includes(qn) || String(c.code).includes(qn)
    ).slice(0, 40);
  }, [courses, q]);

  async function submit(url, body) {
    if (!studentId) { setErr("شناسه دانشجو هنوز آماده نیست"); return false; }
    setBusy(true); setErr(""); setMsg("");
    try {
      const sep = url.includes("?") ? "&" : "?";
      const r = await fetch(`${url}${sep}student_id=${studentId}`, {
        method: "POST", headers: HEADERS(), body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        const det = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j);
        throw new Error(det || ("HTTP " + r.status));
      }
      setStatsKey((k) => k + 1);
      refreshMine();
      setMsg("✅ با موفقیت ثبت شد.");
      return true;
    } catch (e) {
      setErr("خطا: " + (e.message || ""));
      return false;
    } finally { setBusy(false); }
  }

  async function remove(url, id, what) {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await fetch(`${url}/${id}`, {
        method: "DELETE", headers: HEADERS(),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        const det = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j);
        throw new Error(det || ("HTTP " + r.status));
      }
      setMsg(`✅ ${what} حذف شد.`);
      setStatsKey((k) => k + 1);
      refreshMine();
    } catch (e) {
      setErr("خطا: " + (e.message || ""));
    } finally { setBusy(false); }
  }

  async function doVote(kind) {
    if (!picked) { setErr("اول درس را انتخاب کنید"); return; }
    const ok = await submit(`${API_BASE}/api/votes/`,
      { course_id: picked.id, vote_type: kind, term });
    if (ok) setMsg(`✅ رأی «${kind === "like" ? "می‌خواهم" : "ارائه شود"}» برای ${picked.title} ثبت شد.`);
  }

  async function doPropose() {
    if (!picked) { setErr("اول درس را انتخاب کنید"); return; }
    const ok = await submit(`${API_BASE}/api/proposals/`,
      { term, course_ids: [picked.id], description: desc });
    if (ok) { setMsg("✅ پیشنهاد شما ثبت شد."); setDesc(""); }
  }

  return (
    <div className="s360-page">
      <h2>🗳 نظرسنجی و بازخورد دروس</h2>
      <Disclaimer text="نظرات شما فقط برای برنامه‌ریزی آموزش استفاده می‌شود و به‌تنهایی موجب قطعیِ ارائه درس نمی‌گردد." />

      <div className="s360-tabs-row">
        <button className={tab === "vote" ? "active" : ""}
                onClick={() => setTab("vote")}>👍 رأی به درس</button>
        <button className={tab === "proposal" ? "active" : ""}
                onClick={() => setTab("proposal")}>💡 پیشنهاد درس</button>
        <button className={tab === "rating" ? "active" : ""}
                onClick={() => setTab("rating")}>⭐ امتیاز کلاس</button>
      </div>

      {(msg || err) && <div className={err ? "s360-error" : "hub-ok"}>{err || msg}</div>}

      {tab !== "rating" && (
        <Card title="1️⃣ انتخاب درس (جستجو کنید)">
          <div className="hub-picker">
            <input placeholder="نام یا کد درس را بنویسید..."
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
            <select value={term} onChange={(e) => setTerm(e.target.value)}>
              {TERMS.map((t) => <option key={t} value={t}>ترم {t}</option>)}
            </select>
            {picked && <span className="mart-chip">انتخاب‌شده: {picked.title}</span>}
          </div>
        </Card>
      )}

      {tab === "vote" && (
        <>
          <Card title="2️⃣ رأی شما درباره این درس">
            <div className="hub-actions">
              <button className="hub-btn like" disabled={busy || !studentId || !picked}
                      onClick={() => doVote("like")}>👍 این درس را می‌خواهم</button>
              <button className="hub-btn req" disabled={busy || !studentId || !picked}
                      onClick={() => doVote("request")}>📌 ارائه‌اش را درخواست می‌کنم</button>
            </div>
          </Card>
          <VoteStatsCard refreshKey={statsKey} title="📊 آمار رأی‌های ثبت‌شده" />
          <Card title="🗳 رأی‌های من">
            {myVotes.length === 0 ? (
              <p className="s360-hint">هنوز رأیی ثبت نکرده‌اید.</p>
            ) : (
              <table className="s360-table">
                <thead><tr><th>درس</th><th>نوع رأی</th><th>ترم</th><th>زمان</th><th></th></tr></thead>
                <tbody>
                  {myVotes.map((v) => (
                    <tr key={v.id}>
                      <td><b>{v.course_title || "-"}</b> <small>({v.course_code})</small></td>
                      <td>{VT_MAP[v.vote_type] || v.vote_type}</td>
                      <td>{v.term}</td>
                      <td>{v.created_at ? new Date(v.created_at).toLocaleString("fa-IR") : "-"}</td>
                      <td><button className="hub-del"
                                  disabled={busy}
                                  onClick={() => remove("/api/votes", v.id, "رأی")}>🗑</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}

      {tab === "proposal" && (
        <>
          <Card title="2️⃣ توضیح پیشنهاد شما">
            <textarea rows={3} placeholder="چرا این درس باید ارائه شود؟ (اختیاری)"
                      value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div className="hub-actions">
              <button className="hub-btn like" disabled={busy || !studentId || !picked}
                      onClick={doPropose}>📨 ثبت پیشنهاد</button>
            </div>
          </Card>
          <Card title="📋 پیشنهادهای من">
            {mine.length === 0 ? (
              <p className="s360-hint">هنوز پیشنهادی ثبت نکرده‌اید.</p>
            ) : (
              <table className="s360-table">
                <thead><tr><th>ترم</th><th>دروس پیشنهادی</th><th>توضیح</th><th>وضعیت</th><th>زمان</th><th></th></tr></thead>
                <tbody>
                  {mine.map((m) => (
                    <tr key={m.id}>
                      <td>{m.term}</td>
                      <td><b>{m.courses_display}</b></td>
                      <td>{m.description || "-"}</td>
                      <td>{ST_MAP[m.status] || m.status}</td>
                      <td>{m.created_at ? new Date(m.created_at).toLocaleString("fa-IR") : "-"}</td>
                      <td><button className="hub-del"
                                  disabled={busy}
                                  onClick={() => remove("/api/proposals", m.id, "پیشنهاد")}>🗑</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}

      {tab === "rating" && (
        <Card title="⭐ امتیازدهی به کلاس‌ها">
          <p className="s360-hint">
            امتیازدهی به کلاس‌های برگزارشده پس از نهایی‌شدن برنامه هفتگی فعال می‌شود.
          </p>
        </Card>
      )}
    </div>
  );
}
