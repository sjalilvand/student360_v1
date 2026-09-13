// Student 360 - AI Assistant page (RAG + Guardrails + LLM).
import { useState } from "react";
import axios from "axios";
import { track } from "../../utils/eventTracker";
import "./ai-assistant.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function AiAssistantPage() {
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("regulations");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true); setError("");
    try {
      const sn = localStorage.getItem("s360_student_number");
      const res = await axios.post(
        `${API_BASE}/api/ai/ask`,
        { question, domain, student_ref: sn || null },
        { timeout: 120000 }
      );
      setResult(res.data);
      track("ai_asked", domain, { engine: res.data.engine, low_confidence: res.data.low_confidence });
    } catch (err) {
      setError(err.response?.data?.detail || "خطا در ارتباط با دستیار هوشمند");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="s360-page">
      <p className="s360-hint">
        پاسخ‌ها فقط بر اساس منابع داخلی سامانه تولید می‌شوند و همیشه «اولیه» هستند.
      </p>
      <form onSubmit={ask} className="ai-ask-form">
        <select value={domain} onChange={(e) => setDomain(e.target.value)}>
          <option value="regulations">آیین‌نامه‌ها و مقررات</option>
          <option value="study">تحصیل و برنامه‌ریزی</option>
        </select>
        <textarea
          placeholder="پرسش خود را بنویسید... مثلاً: شرایط انتقال چیست؟"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "در حال پردازش..." : "پرسش از دستیار هوشمند ✨"}
        </button>
      </form>

      {error && <p className="s360-error">{error}</p>}

      {result && (
        <div className="ai-result">
          <div className="ai-meta">
            <span className={`ai-badge ${result.engine}`}>
              موتور: {result.engine === "llm" ? "هوش مصنوعی (LLM)" : result.engine === "retrieval" ? "جستجوی منابع" : result.engine}
            </span>
            {result.low_confidence && <span className="ai-badge low">اطمینان پایین</span>}
            <span className="ai-latency">{result.latency_ms} ms</span>
          </div>
          <pre className="ai-answer">{result.answer}</pre>
          {result.sources?.length > 0 && (
            <div className="ai-sources">
              <h4>منابع استفاده‌شده:</h4>
              <ul>
                {result.sources.map((s, i) => (
                  <li key={i}>[{s.kind}] {s.title} <small>(score: {s.score})</small></li>
                ))}
              </ul>
            </div>
          )}
          <p className="ai-disclaimer">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
