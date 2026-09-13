// Student 360 - Adaptive Quiz with LLM (Phase 2 / category 3).
import { useEffect, useState } from "react";
import { Card, Disclaimer, Loading, Empty } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});

const COURSES = [
  { code: "CS101", label: "مبانی کامپیوتر (CS101)" },
  { code: "CS201", label: "ساختمان داده (CS201)" },
  { code: "CS301", label: "سیستم‌عامل (CS301)" },
];

export default function AdaptiveQuizPage() {
  const [course, setCourse] = useState("CS201");
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = () =>
    fetch(`${API_BASE}/api/adaptive-quiz/history`, { headers: HEADERS() })
      .then((r) => r.json()).then((j) => setHistory(j.items || [])).catch(() => {});
  useEffect(loadHistory, []);

  async function generate() {
    setLoading(true); setError(""); setResult(null); setQuiz(null); setAnswers({});
    try {
      const r = await fetch(`${API_BASE}/api/adaptive-quiz/next`, {
        method: "POST", headers: HEADERS(),
        body: JSON.stringify({ course_code: course }),
      }).then((r) => r.json());
      if (r.error) throw new Error(r.error);
      setQuiz(r);
    } catch (e) { setError("خطا در تولید کوییز: " + (e.message || "")); }
    finally { setLoading(false); }
  }

  async function submit() {
    if (!quiz) return;
    setLoading(true); setError("");
    try {
      const arr = quiz.questions.map((q) => (answers[q.index] ?? null));
      const r = await fetch(`${API_BASE}/api/adaptive-quiz/${quiz.quiz_id}/submit`, {
        method: "POST", headers: HEADERS(),
        body: JSON.stringify({ answers: arr }),
      }).then((r) => r.json());
      if (r.error) throw new Error(r.error);
      setResult(r); loadHistory();
    } catch (e) { setError("خطا در ثبت پاسخ‌ها: " + (e.message || "")); }
    finally { setLoading(false); }
  }

  const scoreColor = (s) => (s >= 80 ? "#22c55e" : s >= 50 ? "#f59e0b" : "#ef4444");

  return (
    <div className="s360-page">
      <h2>🎯 کوییز تطبیقی (AI)</h2>
      <Disclaimer text="سؤالات با هوش مصنوعی و بر اساس منابع درس تولید می‌شوند؛ سطح بعدی بر اساس نتیجه شما تنظیم می‌گردد." />

      <Card title="شروع کوییز">
        <div className="s360-form-row">
          <select value={course} onChange={(e) => setCourse(e.target.value)}>
            {COURSES.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
          </select>
          <button onClick={generate} disabled={loading}>
            {loading ? "..." : result ? "کوییز بعدی (سطح جدید)" : "تولید کوییز ✨"}
          </button>
        </div>
        {error && <p className="s360-error">{error}</p>}
      </Card>

      {quiz && !result && (
        <Card title={`کوییز ${quiz.course_code} — سطح: ${quiz.level_label}`}>
          <span className="ai-tagline">
            {quiz.source === "llm" ? "✨ تولید با هوش مصنوعی" : "⚙️ تولید خودکار (بدون LLM)"}
          </span>
          {quiz.questions.map((q) => (
            <div key={q.index} className="aquiz-q">
              <b>{q.index + 1}. {q.question}</b>
              {q.options.map((o, oi) => (
                <label key={oi} className={"aquiz-opt" + (answers[q.index] === oi ? " sel" : "")}>
                  <input type="radio" name={"q" + q.index}
                         checked={answers[q.index] === oi}
                         onChange={() => setAnswers({ ...answers, [q.index]: oi })} />
                  {o}
                </label>
              ))}
            </div>
          ))}
          <button onClick={submit} disabled={loading}>ثبت و تصحیح</button>
        </Card>
      )}

      {result && (
        <Card title="نتیجه">
          <div className="risk-row">
            <span className="risk-badge" style={{ background: scoreColor(result.score_pct), color: "#fff" }}>
              {result.score_pct}٪ — {result.correct_count} از {result.total}
            </span>
            <span>سطح این آزمون: <b>{result.level_label}</b></span>
            <span>سطح بعدی: <b>{result.next_level_label}</b></span>
          </div>
          {result.feedback.map((f) => (
            <div key={f.index} className={"aquiz-fb " + (f.is_correct ? "ok" : "bad")}>
              <b>{f.is_correct ? "✅" : "❌"} {f.index + 1}. {f.question}</b>
              <div>پاسخ شما: {f.your_answer ?? "—"} | پاسخ درست: <b>{f.correct_answer}</b></div>
              {f.explanation && <small>💡 {f.explanation}</small>}
            </div>
          ))}
          <p className="s360-hint">برای سطح جدید، دکمه «کوییز بعدی» را بزنید.</p>
        </Card>
      )}

      <Card title="تاریخچه آزمون‌ها">
        {history.length === 0 ? <Empty>آزمونی ثبت نشده</Empty> : (
          <table className="s360-table">
            <thead><tr><th>درس</th><th>سطح</th><th>نمره</th><th>صحیح</th><th>زمان</th></tr></thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.course_code}</td><td>{h.level}</td>
                  <td><b style={{ color: scoreColor(h.score_pct || 0) }}>{h.score_pct}٪</b></td>
                  <td>{h.correct_count}/{h.total}</td>
                  <td>{h.created_at ? new Date(h.created_at).toLocaleString("fa-IR") : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
