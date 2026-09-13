// Student 360 - Survey Hub v3: three surveys (before/mid/after planning).
import { useEffect, useMemo, useState } from "react";
import { Card, Disclaimer, Loading } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const AUTH = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});
const TERMS = ["1405-1", "1404-2", "1404-1"];

/* ---------- Survey 1: request course offering (cards like legacy) ---------- */
function RequestSurvey() {
  const [items, setItems] = useState(null);
  const [term, setTerm] = useState(TERMS[0]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    fetch(`${API_BASE}/api/vote-polls/active?survey_type=request&term=${term}`,
          { headers: AUTH() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(load, [term]);

  async function request(course) {
    setBusy(true); setMsg("");
    try {
      const r = await fetch(`${API_BASE}/api/votes/?student_id=${localStorage.getItem("s360_student_number")}`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ course_id: course.course_id, vote_type: "request", term }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "خطا");
      setMsg(`✅ درخواست ارائه «${course.title}» ثبت شد.`);
      load();
    } catch (e) { setMsg("خطا: " + e.message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <div className="sv-filters">
        <label>سال تحصیلی</label>
        <select><option>1406 - 1405</option></select>
        <label>نیمسال</label>
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="1405-1">مهر (نیمسال اول)</option>
          <option value="1404-2">بهمن (نیمسال دوم)</option>
        </select>
      </div>
      {msg && <div className={msg.startsWith("✅") ? "hub-ok" : "s360-error"}>{msg}</div>}
      {!items ? <Loading /> : items.length === 0 ? (
        <Card title="درس فعال"><p className="s360-hint">فعلاً درسی برای نظرسنجی فعال نشده است.</p></Card>
      ) : (
        <div className="sv-cards">
          {items.map((c) => (
            <div key={c.course_id} className={"sv-card" + (c.my_request ? " selected" : "")}>
              <div className="sv-card-head">
                <span className="sv-code">{c.code}</span>
                {c.my_request ? <span className="sv-badge sel">لغو انتخاب شده</span>
                              : <span className="sv-badge">فعال</span>}
              </div>
              <h4>{c.title}</h4>
              <div className="sv-meta">
                <span>گروه: <b>{c.code}</b></span>
                <span>ظرفیت: <b>{c.capacity ?? 30}</b></span>
                <span>مقاطع: <b>-</b></span>
              </div>
              <div className="sv-req-row">
                <span>📝 درخواست‌ها: <b>{c.requests}</b></span>
              </div>
              <button className="sv-btn" disabled={busy}
                      onClick={() => request(c)}>
                {c.my_request ? "↺ لغو درخواست ارائه" : "✋ درخواست ارائه"}
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/* ---------- Survey 2: rate mid-term courses (stars) ---------- */
function Stars({ value, onChange, readOnly }) {
  return (
    <div className="sv-stars">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= value ? "on" : ""}
              onClick={() => !readOnly && onChange(i)}>
          {i <= value ? "★" : "☆"}
        </span>
      ))}
    </div>
  );
}

function RateSurvey() {
  const [items, setItems] = useState(null);
  const [term, setTerm] = useState(TERMS[0]);
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () =>
    fetch(`${API_BASE}/api/ratings/my-courses?term=${term}`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => setItems(j.items || [])).catch(() => setItems([]));
  useEffect(load, [term]);

  async function rate(course) {
    const d = drafts[course.course_id] || {};
    if (!d.rating) { setMsg("⚠️ اول امتیاز ستاره‌ای را انتخاب کنید"); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/ratings/rate`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ course_id: course.course_id, rating: d.rating,
                               comment: d.comment || null, term }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg(`✅ امتیاز «${course.title}» ثبت شد.`);
      load();
    } catch (e) { setMsg("خطا: " + e.message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <div className="sv-filters">
        <label>سال تحصیلی</label>
        <select><option>1406 - 1405</option></select>
      </div>
      {msg && <div className={msg.startsWith("✅") ? "hub-ok" : "s360-error"}>{msg}</div>}
      {!items ? <Loading /> : items.length === 0 ? (
        <Card title="امتیازدهی"><p className="s360-hint">فعلاً درسی برای امتیازدهی فعال نشده است.</p></Card>
      ) : (
        <p className="s360-hint" style={{ margin: ".4rem 0" }}>
          به برنامه‌های درسی که تجربه کرده‌اید، امتیاز دهید و نظر خود را بنویسید
        </p>
      )}
      {items && items.length > 0 && (
        <div className="sv-cards">
          {items.map((c) => {
            const d = drafts[c.course_id] || { rating: c.my_rating || 0, comment: c.my_comment || "" };
            return (
              <div key={c.course_id} className="sv-card">
                <div className="sv-card-head">
                  <span className="sv-code">{c.code}</span>
                  {c.my_rating && <span className="sv-badge sel">ثبت شده</span>}
                </div>
                <h4>{c.title}</h4>
                <div className="sv-meta"><span>امتیاز شما:</span><Stars value={d.rating}
                  onChange={(v) => setDrafts({ ...drafts, [c.course_id]: { ...d, rating: v } })} /></div>
                <textarea rows={2} placeholder="نظر شما (اختیاری)..."
                          value={d.comment}
                          onChange={(e) => setDrafts({ ...drafts, [c.course_id]: { ...d, comment: e.target.value } })} />
                <button className="sv-btn" disabled={busy}
                        onClick={() => rate({ ...c, ...d })}>📝 ثبت امتیاز</button>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

/* ---------- Survey 3: term program feedback ---------- */
function TermFeedback() {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/surveys/term-feedback?term=1405-1`, { headers: AUTH() })
      .then((r) => r.json()).then((j) => {
        if (j.feedback) { setRating(j.feedback.rating || 0); setComment(j.feedback.comment || ""); }
      }).catch(() => {});
  }, []);

  async function submit() {
    if (!rating) { setMsg("⚠️ اول امتیاز را انتخاب کنید"); return; }
    setBusy(true); setMsg("");
    try {
      const r = await fetch(`${API_BASE}/api/surveys/term-feedback`, {
        method: "POST", headers: AUTH(),
        body: JSON.stringify({ term: "1405-1", rating, comment: comment || null }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || "خطا");
      setMsg("✅ نظر شما درباره برنامه ترم ثبت شد.");
    } catch (e) { setMsg("خطا: " + e.message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <p className="s360-hint" style={{ margin: ".4rem 0" }}>
        به برنامه‌ریزی درسی این ترم امتیاز دهید و نظر خود را بنویسید
      </p>
      {(msg) && <div className={msg.startsWith("✅") ? "hub-ok" : "s360-error"}>{msg}</div>}
      <Card title="نظر شما درباره برنامه ترم جاری">
        <div className="sv-meta" style={{ margin: ".4rem 0" }}><span>امتیاز شما:</span>
          <Stars value={rating} onChange={setRating} /></div>
        <textarea rows={3} placeholder="نظر شما در مورد این برنامه (اختیاری)..."
                  value={comment} onChange={(e) => setComment(e.target.value)}
                  style={{ width: "100%", padding: ".5rem", borderRadius: 8, border: "1px solid #d1d5db", fontFamily: "inherit" }} />
        <div className="hub-actions">
          <button className="hub-btn like" disabled={busy} onClick={submit}>📨 ثبت نظر</button>
        </div>
      </Card>
    </>
  );
}

/* ---------- Hub ---------- */
export default function StudentFeedbackHub() {
  const [tab, setTab] = useState("s1");
  return (
    <div className="s360-page">
      <h2>🗳 نظرسنجی‌های آموزشی</h2>
      <div className="s360-tabs-row">
        <button className={tab === "s1" ? "active" : ""}
                onClick={() => setTab("s1")}>💡 پیشنهاد درس</button>
        <button className={tab === "s2" ? "active" : ""}
                onClick={() => setTab("s2")}>⭐ امتیازدهی به برنامه</button>
        <button className={tab === "s3" ? "active" : ""}
                onClick={() => setTab("s3")}>💬 نظر برنامه ترم</button>
      </div>
      {tab === "s1" && <RequestSurvey />}
      {tab === "s2" && <RateSurvey />}
      {tab === "s3" && <TermFeedback />}
    </div>
  );
}
