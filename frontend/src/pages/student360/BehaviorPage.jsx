// Student 360 - Behavioral Insights page + risk preview (Phase 2).
import { useEffect, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { Card, Disclaimer, Loading } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({ "X-Student-Number": localStorage.getItem("s360_student_number") || "" });

const COMP_LABELS = {
  frequency: "فراوانی", consistency: "پیوستگی", diversity: "تنوع",
  depth: "عمق تعامل", recency: "تازگی",
};
const RISK_COLOR = { "پایین": "#22c55e", "متوسط": "#f59e0b", "بالا": "#ef4444" };

export default function BehaviorPage() {
  const [ins, setIns] = useState(null);
  const [risk, setRisk] = useState(null);
  const [interv, setInterv] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/behavior/insights?days=30`, { headers: HEADERS() })
      .then((r) => r.json()).then(setIns).catch(() => setIns({ error: true }));
    fetch(`${API_BASE}/api/risk/me`, { headers: HEADERS() })
      .then((r) => r.json()).then(setRisk).catch(() => {});
    fetch(`${API_BASE}/api/intervention/me`, { headers: HEADERS() })
      .then((r) => r.json()).then(setInterv).catch(() => {});
  }, []);

  if (!ins) return <Loading />;
  if (ins.error || !ins.engagement) return <p className="s360-error">خطا در دریافت بینش‌ها</p>;

  const eng = ins.engagement;
  const scoreColor = eng.score >= 75 ? "#22c55e" : eng.score >= 50 ? "#3b82f6" : eng.score >= 25 ? "#f59e0b" : "#ef4444";

  return (
    <div className="s360-page">
      <h2>🧠 بینش‌های رفتاری من</h2>
      <Disclaimer text="این تحلیل از رفتار شما در همین سامانه (۳۰ روز اخیر) ساخته شده و صرفاً برای بهبود تجربه شماست." />

      {risk && risk.risk_level && (
        <Card title="⚠️ پیش‌بینی وضعیت تحصیلی (هشدار زودهنگام)">
          <div className="risk-row">
            <span className={`risk-badge risk-${risk.risk_level === "بالا" ? "high" : risk.risk_level === "متوسط" ? "mid" : "low"}`}>
              ریسک {risk.risk_level}: {risk.risk_score}
            </span>
            {risk.reasons?.length === 0 && <b>وضعیت تحصیلی شما مطلوب است ✅</b>}
          </div>
          {risk.reasons?.length > 0 && (
            <>
              <ul className="eng-recs">
                {risk.reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
              <b>اقدام پیشنهادی:</b>
              <ul className="eng-recs">
                {risk.suggested_actions.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </>
          )}
          <p className="s360-hint">{risk.disclaimer}</p>
        </Card>
      )}

      {interv && interv.items?.length > 0 && (
        <Card title="🚨 پیگیری کارشناس آموزش">
          {interv.items.map((it) => (
            <div key={it.id} className="interv-row">
              <span className="risk-badge risk-low">{it.status_label}</span>
              <span>{it.review_note || "در انتظار بررسی کارشناس"}</span>
              {it.reviewed_at && <small className="s360-hint">{new Date(it.reviewed_at).toLocaleString("fa-IR")}</small>}
            </div>
          ))}
          <p className="s360-hint">وضعیت پیگیری حمایتی شما — جزئیات فقط از کارشناس آموزش.</p>
        </Card>
      )}

      <div className="s360-grid-2">
        <Card title="شاخص تعامل (Engagement Index)">
          <div className="s360-big-number" style={{ color: scoreColor }}>{eng.score}</div>
          <p>سطح: <b>{eng.level}</b></p>
          <p className="s360-hint">{eng.total_events} رویداد | {eng.active_days} روز فعال | {eng.deep_actions} تعامل عمیق</p>
          {Object.entries(eng.components).map(([k, v]) => (
            <div key={k} className="eng-comp">
              <span>{COMP_LABELS[k] || k}</span>
              <div className="eng-bar"><div style={{ width: `${Math.min(100, (v / 30) * 100)}%`, background: scoreColor }} /></div>
              <b>{v}</b>
            </div>
          ))}
        </Card>

        <Card title="الگوی فعالیت">
          <div className="s360-kv"><span>🔥 روزهای متوالی فعال:</span><b>{ins.streak_days}</b></div>
          <div className="s360-kv"><span>⏰ ساعت اوج:</span><b>{ins.peak_hour != null ? ins.peak_hour + ":۰۰" : "-"}</b></div>
          <div className="s360-kv"><span>📈 روند:</span>
            <b>{ins.trend === "up" ? "صعودی ↗" : ins.trend === "down" ? "نزولی ↘" : "ثابت →"}</b>
          </div>
          <div style={{ marginTop: ".6rem" }}>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={ins.by_hour}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" fontSize={9} />
                <YAxis fontSize={9} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" name="رویداد" fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="قابلیت‌های پرکاربرد شما">
        {ins.top_features.length === 0 ? <p className="s360-hint">هنوز فعالیتی ثبت نشده</p> : (
          <div className="eng-chips">
            {ins.top_features.map((f) => (
              <span key={f.type} className="mart-chip">{f.type}: {f.count}</span>
            ))}
          </div>
        )}
      </Card>

      <Card title="💡 پیشنهادهای شخصی‌سازی‌شده">
        <ul className="eng-recs">
          {ins.recommendations.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      </Card>
    </div>
  );
}

