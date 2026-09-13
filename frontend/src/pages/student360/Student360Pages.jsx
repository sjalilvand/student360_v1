// Student 360 — student portal pages.
import { useEffect, useState, useCallback } from "react";
import {
  getProfile, getWeeklySchedule, reportDiscrepancy, getDiscrepancies,
  askRegulations, sendRegulationFeedback, getRegulationHistory,
  getGuides, getGuide,
  getSelectionAssistant, getCourseAnalysis, saveScenario, getScenarios,
  getGraduationCheck,
  getCalendar, getReminders, getChannels, updateChannels,
  getAlerts, requestCounseling,
  generateQuiz, submitQuiz, getQuizHistory,
  askProfessor, getExercise, getProfessorHistory,
} from "../../api/student360Api";
import {
  STATUS_COLORS, SEVERITY_COLORS, DAY_NAMES,
  Badge, Card, Disclaimer, Empty, Loading,
} from "./shared";

// ====================================================================
// Profile
// ====================================================================
export function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [showDiscrepancy, setShowDiscrepancy] = useState(false);
  const [disc, setDisc] = useState({ field: "", claimed_value: "", description: "" });
  const [discList, setDiscList] = useState([]);
  const [msg, setMsg] = useState("");
  const [martGpa, setMartGpa] = useState(null);

  useEffect(() => {
    getProfile().then(setProfile).catch(() => {});
    getDiscrepancies().then(setDiscList).catch(() => {});
    const sn0 = localStorage.getItem("s360_student_number");
    fetch("http://127.0.0.1:8000/api/student360/profile/gpa-mart", { headers: { "X-Student-Number": sn0 || "" } })
      .then((r) => r.json())
      .then((m) => { if (m && m.found) setMartGpa(m); })
      .catch(() => {});
  }, []);

  if (!profile) return <Loading />;

  async function submitDiscrepancy() {
    try {
      await reportDiscrepancy(disc);
      setMsg("اعلام شما ثبت شد و توسط آموزش بررسی می‌شود.");
      setDisc({ field: "", claimed_value: "", description: "" });
      getDiscrepancies().then(setDiscList);
    } catch {
      setMsg("خطا در ثبت اعلام مغایرت");
    }
  }

  return (
    <div className="s360-page">
      <h2>👤 پروفایل هوشمند دانشجو</h2>
      <Disclaimer text={profile.disclaimer} />

      <div className="s360-grid-2">
        <Card title="اطلاعات هویتی">
          <div className="s360-kv"><span>نام:</span><b>{profile.identity.full_name}</b></div>
          <div className="s360-kv"><span>شماره دانشجویی:</span><b>{profile.identity.student_number}</b></div>
          <div className="s360-kv"><span>ایمیل:</span><b>{profile.identity.email || "-"}</b></div>
          <div className="s360-kv"><span>تلفن:</span><b>{profile.identity.phone || "-"}</b></div>
        </Card>
        <Card title="اطلاعات آموزشی">
          <div className="s360-kv"><span>رشته:</span><b>{profile.academic.program}</b></div>
          <div className="s360-kv"><span>مقطع:</span><b>{profile.academic.level}</b></div>
          <div className="s360-kv"><span>گرایش:</span><b>{profile.academic.orientation || "-"}</b></div>
          <div className="s360-kv"><span>ورودی:</span><b>{profile.academic.entry_term}</b></div>
          <div className="s360-kv">
            <span>وضعیت تحصیلی:</span>
            <b>{profile.academic.academic_status === "normal" ? "عادی" : profile.academic.academic_status}</b>
          </div>
        </Card>
        <Card title="معدل">
          <div className="s360-big-number">{(martGpa || profile.gpa?.mart)?.weighted_gpa ?? profile.gpa.overall}</div>
          {(martGpa || profile.gpa?.mart) && (
            <p className="s360-hint">GPA وزنی از Data Mart — {(martGpa || profile.gpa?.mart).total_credits} واحد، {(martGpa || profile.gpa?.mart).graded_courses} درس</p>
          )}
          <p>معدل کل</p>
          {Object.entries(profile.gpa.by_term).map(([term, gpa]) => (
            <div className="s360-kv" key={term}><span>{term}:</span><b>{gpa}</b></div>
          ))}
        </Card>
        <Card title="واحدها">
          <div className="s360-kv"><span>کل موردنیاز:</span><b>{profile.units.total_required}</b></div>
          <div className="s360-kv"><span>اخذشده:</span><b>{profile.units.taken}</b></div>
          <div className="s360-kv"><span>گذرانده:</span><b>{profile.units.passed}</b></div>
          <div className="s360-kv"><span>مردود:</span><b>{profile.units.failed}</b></div>
          <div className="s360-kv"><span>جاری:</span><b>{profile.units.in_progress}</b></div>
          <div className="s360-kv"><span>باقی‌مانده:</span><b>{profile.units.remaining}</b></div>
        </Card>
      </div>

      <Card title="دروس جاری نیمسال">
        {profile.current_courses.length === 0 ? (
          <Empty>درسی در نیمسال جاری ثبت نشده است.</Empty>
        ) : (
          <table className="s360-table">
            <thead>
              <tr><th>درس</th><th>واحد</th><th>روز</th><th>ساعت</th><th>استاد</th></tr>
            </thead>
            <tbody>
              {profile.current_courses.map((c) => (
                <tr key={c.course_code}>
                  <td>{c.course_title}</td>
                  <td>{c.credits}</td>
                  <td>{DAY_NAMES[c.day] || "-"}</td>
                  <td>{c.start_time} - {c.end_time}</td>
                  <td>{c.instructor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="هشدارها و مهلت‌های مهم">
        {profile.upcoming_events.length === 0
          ? <Empty>مهلت نزدیکی وجود ندارد.</Empty>
          : profile.upcoming_events.map((ev, i) => (
            <div className="s360-event-row" key={i}>
              <b>{ev.title}</b>
              <span>{ev.date}</span>
            </div>
          ))}
      </Card>

      <Card title="آخرین به‌روزرسانی داده"
            actions={<button className="s360-btn-ghost"
                     onClick={() => setShowDiscrepancy(!showDiscrepancy)}>
                     اعلام مغایرت
                   </button>}>
        <p>🕒 {profile.last_data_update || "-"}</p>
        {msg && <p className="s360-success">{msg}</p>}

        {showDiscrepancy && (
          <div className="s360-form-row">
            <input placeholder="فیلد موردنظر (مثلاً national_id)"
                   value={disc.field}
                   onChange={(e) => setDisc({ ...disc, field: e.target.value })} />
            <input placeholder="مقدار صحیح"
                   value={disc.claimed_value}
                   onChange={(e) => setDisc({ ...disc, claimed_value: e.target.value })} />
            <input placeholder="توضیح"
                   value={disc.description}
                   onChange={(e) => setDisc({ ...disc, description: e.target.value })} />
            <button onClick={submitDiscrepancy}>ثبت اعلام مغایرت</button>
          </div>
        )}

        {discList.length > 0 && (
          <table className="s360-table">
            <thead><tr><th>فیلد</th><th>مقدار اعلامی</th><th>وضعیت</th></tr></thead>
            <tbody>
              {discList.map((d) => (
                <tr key={d.id}>
                  <td>{d.field}</td>
                  <td>{d.claimed_value}</td>
                  <td>{d.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="s360-hint">داده‌های رسمی فقط از سامانه آموزش تغییر می‌کند؛ اعلام شما صرفاً برای بررسی است.</p>
      </Card>
    </div>
  );
}

// ====================================================================
// Regulations assistant
// ====================================================================
export function RegulationsPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = useCallback(() => {
    getRegulationHistory().then(setHistory).catch(() => {});
  }, []);
  useEffect(loadHistory, [loadHistory]);

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await askRegulations(question);
      setResult(res);
      loadHistory();
    } catch (err) {
      setResult({ answer: err.response?.data?.detail || "خطا در پاسخ‌گویی",
                  sources: [], is_low_confidence: true });
    } finally {
      setLoading(false);
    }
  }

  async function feedback(id, value) {
    await sendRegulationFeedback(id, value);
    setResult((r) => (r?.conversation_id === id ? { ...r, feedback: value } : r));
  }

  return (
    <div className="s360-page">
      <h2>📜 دستیار آیین‌نامه‌ای</h2>
      <Disclaimer text="پاسخ‌ها فقط بر اساس منابع تأییدشده دانشگاه است و به‌منزله مجوز یا تصمیم قطعی آموزشی نیست." />

      <Card title="سؤال خود را بپرسید">
        <div className="s360-ask-row">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && ask()}
                 placeholder="مثلاً: حداکثر واحد در وضعیت مشروطی چند است؟" />
          <button onClick={ask} disabled={loading}>
            {loading ? "..." : "پرسش"}
          </button>
        </div>

        {result && (
          <div className="s360-answer">
            {result.is_low_confidence && (
              <div className="s360-low-conf">پاسخ با اطمینان پایین — توصیه می‌شود با کارشناس آموزش تماس بگیرید.</div>
            )}
            {result.requires_expert_referral && (
              <div className="s360-referral">
                📮 این سؤال نیازمند بررسی کارشناس آموزش است.
              </div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            <p className="s360-answer-text">{result.answer}</p>
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع:</b>
                {result.sources.map((s, i) => (
                  <div key={i} className="s360-source">
                    📖 {s.source_name} — {s.title}، ماده {s.article}
                    {s.clause ? `، تبصره ${s.clause}` : ""}
                    (اعتبار: {s.valid_from} تا {s.valid_to || "اکنون"})
                  </div>
                ))}
              </div>
            )}
            {result.conversation_id && (
              <div className="s360-feedback">
                آیا این پاسخ مفید بود؟
                <button className={result.feedback === "helpful" ? "active" : ""}
                        onClick={() => feedback(result.conversation_id, "helpful")}>👍</button>
                <button className={result.feedback === "not-helpful" ? "active" : ""}
                        onClick={() => feedback(result.conversation_id, "not-helpful")}>👎</button>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title="سوابق پرسش‌ها">
        {history.length === 0 ? <Empty>سابقه‌ای وجود ندارد.</Empty> : history.slice(0, 10).map((h) => (
          <div className="s360-history-row" key={h.id}>
            <b>س:</b> {h.question}
            <div className="s360-history-meta">
              اطمینان: {Math.round(h.confidence * 100)}٪
              {h.feedback && ` — بازخورد: ${h.feedback === "helpful" ? "مفید" : "غیرمفید"}`}
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

// ====================================================================
// Process guides
// ====================================================================
export function GuidesPage() {
  const [guides, setGuides] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => { getGuides().then(setGuides).catch(() => {}); }, []);

  async function open(slug) {
    const g = await getGuide(slug);
    setSelected(g);
  }

  return (
    <div className="s360-page">
      <h2>🗂️ راهنمای فرایندهای اداری</h2>
      <div className="s360-grid-2">
        <Card title="فهرست فرایندها">
          {guides.map((g) => (
            <button key={g.slug}
                    className={`s360-list-item ${selected?.slug === g.slug ? "active" : ""}`}
                    onClick={() => open(g.slug)}>
              {g.title}
            </button>
          ))}
        </Card>
        <Card title={selected ? selected.title : "جزئیات"}>
          {!selected ? <Empty>یک فرایند را انتخاب کنید.</Empty> : (
            <div className="s360-guide">
              <h4>شرایط استفاده</h4><p>{selected.conditions}</p>
              <h4>مدارک موردنیاز</h4>
              <ul>{selected.required_documents.map((d, i) => <li key={i}>{d}</li>)}</ul>
              <h4>مراحل انجام</h4>
              <ol>{selected.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
              <div className="s360-kv"><span>واحد مسئول:</span><b>{selected.responsible_unit}</b></div>
              <div className="s360-kv"><span>مهلت ثبت درخواست:</span><b>{selected.deadline}</b></div>
              <div className="s360-kv"><span>سامانه:</span><b>{selected.system_url}</b></div>
              <div className="s360-kv"><span>زمان رسیدگی:</span><b>{selected.processing_time}</b></div>
              <div className="s360-kv"><span>قوانین مرتبط:</span><b>{selected.related_rules}</b></div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

// ====================================================================
// Course selection assistant
// ====================================================================
export function SelectionPage() {
  const [term, setTerm] = useState("1404-2");
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState([]);
  const [scenarioName, setScenarioName] = useState("");
  const [scenarioMsg, setScenarioMsg] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [analysis, setAnalysis] = useState(null);

  const load = useCallback(() => {
    getSelectionAssistant(term).then((d) => {
      setData(d);
      setSelected(d.suggested_course_codes || []);
    }).catch(() => {});
    getScenarios().then(setScenarios).catch(() => {});
  }, [term]);
  useEffect(load, [load]);

  function toggle(code) {
    setSelected((s) => s.includes(code) ? s.filter((c) => c !== code) : [...s, code]);
  }

  async function showAnalysis(code) {
    const a = await getCourseAnalysis(code);
    setAnalysis(a);
  }

  async function saveScenarioNow() {
    if (!selected.length) return;
    const res = await saveScenario(term, scenarioName || "سناریوی من", selected);
    setScenarioMsg(res);
    getScenarios().then(setScenarios);
  }

  if (!data) return <Loading />;

  const selectedUnits = data.courses
    .filter((c) => selected.includes(c.course_code))
    .reduce((s, c) => s + c.credits, 0);

  return (
    <div className="s360-page">
      <h2>🧭 دستیار انتخاب واحد</h2>
      <Disclaimer text={data.note} />

      <div className="s360-selection-summary">
        <span>نیمسال هدف: <b>{data.target_term}</b></span>
        <span>معدل: <b>{data.gpa}</b></span>
        <span>سقف واحد: <b>{data.max_units}</b> ({data.max_units_reason})</span>
        <span>انتخاب شما: <b>{selectedUnits}</b> واحد / {selected.length} درس</span>
      </div>

      <Card title="دروس پیشنهادی سامانه" >
        <div className="s360-chip-row">
          {data.suggested_course_codes.map((c) => <span className="s360-chip" key={c}>{c}</span>)}
        </div>
      </Card>

      <Card title="فهرست دروس و وضعیت">
        <table className="s360-table">
          <thead>
            <tr><th>انتخاب</th><th>درس</th><th>واحد</th><th>وضعیت</th><th>دلیل</th><th>تحلیل</th></tr>
          </thead>
          <tbody>
            {data.courses.map((c) => (
              <tr key={c.course_code}>
                <td>
                  <input type="checkbox" checked={selected.includes(c.course_code)}
                         onChange={() => toggle(c.course_code)} />
                </td>
                <td>{c.course_title} <small>({c.course_code})</small></td>
                <td>{c.credits}</td>
                <td><Badge color={STATUS_COLORS[c.status]}>{c.status}</Badge></td>
                <td className="s360-reasons">{c.reasons.join("؛ ") || "—"}</td>
                <td><button className="s360-btn-ghost"
                            onClick={() => showAnalysis(c.course_code)}>تحلیل پیش‌نیاز</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="ساخت سناریو (STU-CRS-10)"
            actions={<button onClick={saveScenarioNow}>ذخیره سناریو</button>}>
        <input placeholder="نام سناریو" value={scenarioName}
               onChange={(e) => setScenarioName(e.target.value)} className="s360-inline-input" />
        {scenarioMsg && (
          <div className={`s360-scenario-result ${scenarioMsg.validation.valid ? "ok" : "err"}`}>
            <b>{scenarioMsg.validation.valid ? "✅ سناریو معتبر است" : "❌ سناریو دارای ایراد است"}</b>
            <ul>
              {scenarioMsg.validation.errors.map((e, i) => <li key={i}>{e}</li>)}
              {scenarioMsg.validation.warnings.map((w, i) => <li key={i}>⚠️ {w}</li>)}
            </ul>
            <p>{scenarioMsg.message}</p>
          </div>
        )}

        <h4>سناریوهای ذخیره‌شده</h4>
        {scenarios.length === 0 ? <Empty>سناریویی ذخیره نشده است.</Empty> : scenarios.map((s) => (
          <div className="s360-scenario-row" key={s.id}>
            <b>{s.name}</b> — {s.term} — {s.total_units} واحد
            <span className="s360-scenario-codes">{s.selected_course_codes.join("، ")}</span>
            {s.validations?.valid === false && <Badge color="#ef4444">دارای ایراد</Badge>}
            {s.validations?.valid === true && <Badge color="#22c55e">معتبر</Badge>}
          </div>
        ))}
      </Card>

      {analysis && (
        <Card title={`تحلیل پیش‌نیاز: ${analysis.course_title}`}
              actions={<button className="s360-btn-ghost" onClick={() => setAnalysis(null)}>بستن</button>}>
          <div className="s360-kv">
            <span>وضعیت:</span>
            <b>{analysis.allowed ? "مجاز" : "غیرمجاز"}</b>
            {analysis.has_exception && <Badge color="#3b82f6">دارای استثنا</Badge>}
          </div>
          {analysis.prerequisites.length > 0 && (
            <table className="s360-table">
              <thead><tr><th>پیش‌نیاز</th><th>وضعیت</th><th>نمره</th><th>حداقل لازم</th><th>تأمین</th></tr></thead>
              <tbody>
                {analysis.prerequisites.map((p) => (
                  <tr key={p.course_code}>
                    <td>{p.course_code}</td>
                    <td>{p.status === "passed" ? "گذرانده" : p.status === "in-progress" ? "جاری" : "گذرانده‌نشده"}</td>
                    <td>{p.grade ?? "-"}</td>
                    <td>{p.min_grade ?? "-"}</td>
                    <td>{p.met ? "✅" : "❌"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {analysis.corequisites.length > 0 && (
            <p>هم‌نیازها: {analysis.corequisites.map((c) => `${c.course_code} ${c.met ? "✅" : "❌"}`).join("، ")}</p>
          )}
          {analysis.reasons.length > 0 && (
            <ul>{analysis.reasons.map((r, i) => <li key={i}>❌ {r}</li>)}</ul>
          )}
          {analysis.exception && <p>استثنا: {analysis.exception}</p>}
          {analysis.impact_if_not_taken.length > 0 && (
            <ul>{analysis.impact_if_not_taken.map((r, i) => <li key={i}>⏳ {r}</li>)}</ul>
          )}
        </Card>
      )}
    </div>
  );
}

// ====================================================================
// Graduation check
// ====================================================================
export function GraduationPage() {
  const [report, setReport] = useState(null);
  useEffect(() => { getGraduationCheck().then(setReport).catch(() => {}); }, []);
  if (!report) return <Loading />;

  return (
    <div className="s360-page">
      <h2>🎓 بررسی شرایط فارغ‌التحصیلی</h2>
      <Disclaimer text={report.warning} />

      <Card title="نتیجه بررسی"
            actions={<button onClick={() => window.print()}>🖨️ چاپ گزارش</button>}>
        <div className="s360-big-result">
          {report.eligible ? "✅" : "⚠️"} {report.result}
        </div>
        <div className="s360-kv"><span>رشته:</span><b>{report.program}</b></div>
        <div className="s360-kv"><span>نسخه سرفصل:</span><b>{report.curriculum_version}</b></div>
        <div className="s360-kv">
          <span>واحد گذرانده:</span>
          <b>{report.total_passed_units} از {report.total_required_units}</b>
        </div>
        <div className="s360-kv"><span>معدل کل:</span><b>{report.gpa} (حداقل لازم: {report.gpa_ok ? "✅" : "❌"} ۱۲)</b></div>
        <div className="s360-kv">
          <span>سنوات:</span>
          <b>ترم {report.current_term_estimate} از {report.max_allowed_terms} {report.tenure_ok ? "✅" : "❌"}</b>
        </div>
      </Card>

      <div className="s360-grid-2">
        <Card title="واحدهای هر گروه درسی">
          {Object.entries(report.group_units).map(([g, u]) => (
            <div className="s360-kv" key={g}><span>{g}:</span><b>{u} واحد</b></div>
          ))}
        </Card>
        <Card title="کسری واحدها">
          <div className="s360-kv"><span>کسر عمومی:</span><b>{report.short_general_units}</b></div>
          <div className="s360-kv"><span>کسر اختیاری:</span><b>{report.short_elective_units}</b></div>
        </Card>
      </div>

      {report.remaining_obligatory.length > 0 && (
        <Card title="دروس الزامی باقی‌مانده">
          <table className="s360-table">
            <thead><tr><th>درس</th><th>واحد</th><th>ترم پیشنهادی چارت</th></tr></thead>
            <tbody>
              {report.remaining_obligatory.map((c) => (
                <tr key={c.course_code}>
                  <td>{c.course_title} <small>({c.course_code})</small></td>
                  <td>{c.credits}</td>
                  <td>{c.suggested_term}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {report.out_of_curriculum_courses.length > 0 && (
        <Card title="مغایرت تطبیق (دروس خارج از چارت)">
          <p>{report.out_of_curriculum_courses.join("، ")}</p>
        </Card>
      )}

      {report.expert_referral && (
        <div className="s360-referral">
          📮 برای بررسی نهایی به کارشناس آموزش مراجعه کنید.
        </div>
      )}
    </div>
  );
}

// ====================================================================
// Calendar & reminders & channels
// ====================================================================
export function CalendarPage() {
  const [events, setEvents] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [channels, setChannels] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getCalendar().then(setEvents).catch(() => {});
    getReminders().then(setReminders).catch(() => {});
    getChannels().then(setChannels).catch(() => {});
  }, []);

  async function toggleChannel(key) {
    const next = { ...channels, [key]: !channels[key] };
    setChannels(next);
    await updateChannels({ [key]: next[key] });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="s360-page">
      <h2>🗓️ تقویم و یادآوری</h2>

      {reminders.length > 0 && (
        <Card title="🔔 یادآوری‌های نزدیک">
          {reminders.map((r) => (
            <div className="s360-event-row urgent" key={r.id}>
              <b>{r.title}</b>
              <span>{r.date} — {r.days_left} روز مانده</span>
            </div>
          ))}
        </Card>
      )}

      <Card title="رویدادهای آموزشی">
        <table className="s360-table">
          <thead><tr><th>رویداد</th><th>نیمسال</th><th>تاریخ</th><th>نوع</th></tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td>{e.term}</td>
                <td>{e.date}</td>
                <td><small>{e.event_type}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="کانال‌های اطلاع‌رسانی">
        {channels ? (
          <>
            {[
              ["in_app", "اعلان داخل سامانه"],
              ["sms", "پیامک"],
              ["email", "پست الکترونیکی"],
              ["mobile_push", "اعلان موبایل"],
            ].map(([key, label]) => (
              <label className="s360-check-row" key={key}>
                <input type="checkbox" checked={!!channels[key]}
                       onChange={() => toggleChannel(key)} />
                {label}
              </label>
            ))}
            {saved && <p className="s360-success">ذخیره شد ✓</p>}
          </>
        ) : <Loading />}
      </Card>
    </div>
  );
}

// ====================================================================
// Alerts & counseling
// ====================================================================
export function AlertsPage() {
  const [alerts, setAlerts] = useState(null);
  const [counselMsg, setCounselMsg] = useState("");

  const load = useCallback(() => {
    getAlerts().then(setAlerts).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function counsel(alertId) {
    await requestCounseling(alertId, "درخواست مشاوره از سامانه");
    setCounselMsg("درخواست مشاوره ثبت شد.");
    load();
  }

  if (!alerts) return <Loading />;

  return (
    <div className="s360-page">
      <h2>🔔 هشدارهای آموزشی</h2>
      <Disclaimer text="هشدارها برای حمایت آموزشی هستند و هیچ تصمیم تنبیهی خودکاری در پی ندارند." />
      {counselMsg && <p className="s360-success">{counselMsg}</p>}

      {alerts.length === 0 ? <Empty>هشدار فعالی وجود ندارد.</Empty> : alerts.map((a) => (
        <div className="s360-alert" key={a.id}
             style={{ borderRightColor: SEVERITY_COLORS[a.severity] }}>
          <div className="s360-alert-head">
            <Badge color={SEVERITY_COLORS[a.severity]}>
              {a.severity === "critical" ? "بحرانی" : a.severity === "warning" ? "هشدار" : "اطلاعی"}
            </Badge>
            <span className="s360-alert-code">{a.rule_code}</span>
            {a.status !== "open" && <small>وضعیت: {a.status}</small>}
          </div>
          <p><b>دلیل:</b> {a.reason}</p>
          <p><b>اقدام پیشنهادی:</b> {a.recommended_action}</p>
          {a.status === "open" && (
            <button onClick={() => counsel(a.id)}>درخواست مشاوره</button>
          )}
        </div>
      ))}
    </div>
  );
}

// ====================================================================
// Smart quiz
// ====================================================================
export function QuizPage() {
  const [course, setCourse] = useState("CS201");
  const [difficulty, setDifficulty] = useState("medium");
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  const loadHistory = useCallback(() => {
    getQuizHistory().then(setHistory).catch(() => {});
  }, []);
  useEffect(loadHistory, [loadHistory]);

  async function start() {
    setError(""); setResult(null); setAnswers({});
    try {
      const q = await generateQuiz(course, difficulty, 3);
      setQuiz(q);
    } catch (err) {
      setError(err.response?.data?.detail || "خطا در تولید آزمون");
    }
  }

  async function submit() {
    const res = await submitQuiz(quiz.quiz_id, answers);
    setResult(res);
    setQuiz(null);
    loadHistory();
  }

  return (
    <div className="s360-page">
      <h2>🧪 کوییز هوشمند</h2>
      <Disclaimer text="سؤالات فقط از منابع تأییدشده درس تولید می‌شوند." />

      <Card title="آزمون جدید">
        <div className="s360-form-row">
          <select value={course} onChange={(e) => setCourse(e.target.value)}>
            <option value="CS101">مبانی کامپیوتر (CS101)</option>
            <option value="CS201">ساختمان داده (CS201)</option>
            <option value="CS301">سیستم‌عامل (CS301)</option>
          </select>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="easy">آسان</option>
            <option value="medium">متوسط</option>
            <option value="hard">دشوار</option>
          </select>
          <button onClick={start}>شروع آزمون</button>
        </div>
        {error && <p className="s360-error">{error}</p>}

        {quiz && (
          <div className="s360-quiz">
            {quiz.questions.map((q, qi) => (
              <div className="s360-question" key={q.id}>
                <b>{qi + 1}. {q.question_text}</b>
                {q.options?.map((opt, oi) => (
                  <label key={oi} className="s360-check-row">
                    <input type="radio" name={`q${q.id}`}
                           checked={answers[q.id] === opt}
                           onChange={() => setAnswers({ ...answers, [q.id]: opt })} />
                    {opt}
                  </label>
                ))}
              </div>
            ))}
            <button onClick={submit}>ثبت پاسخ‌ها</button>
          </div>
        )}

        {result && (
          <div className="s360-quiz-result">
            <h3>نتیجه: {result.score} از {result.max_score} ({result.percent}٪)</h3>
            {result.weak_topics.length > 0 && (
              <p>نقاط ضعف: {result.weak_topics.join("، ")}</p>
            )}
            {result.study_recommendations.map((r, i) => (
              <p key={i}>📚 {r.action}</p>
            ))}
            {result.results.map((r, i) => (
              <div key={i} className="s360-answer-review">
                {r.correct ? "✅" : "❌"} پاسخ صحیح: <b>{r.correct_answer}</b>
                <p>{r.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="سابقه آزمون‌ها">
        {history.length === 0 ? <Empty>سابقه‌ای وجود ندارد.</Empty> : history.map((h) => (
          <div className="s360-history-row" key={h.attempt_id}>
            <b>{h.course_code}</b> — {h.score}/{h.max_score}
            {h.weak_topics.length > 0 && <span> — نقاط ضعف: {h.weak_topics.join("، ")}</span>}
            <div className="s360-history-meta">{h.taken_at?.slice(0, 10)}</div>
          </div>
        ))}
      </Card>
    </div>
  );
}

// ====================================================================
// Smart professor
// ====================================================================
export function ProfessorPage() {
  const [course, setCourse] = useState("CS201");
  const [mode, setMode] = useState("simple");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [exercise, setExercise] = useState(null);
  const [error, setError] = useState("");

  const loadHistory = useCallback(() => {
    getProfessorHistory().then(setHistory).catch(() => {});
  }, []);
  useEffect(loadHistory, [loadHistory]);

  async function ask() {
    if (!question.trim()) return;
    setError("");
    try {
      const res = await askProfessor(course, question, mode);
      setResult(res);
      loadHistory();
    } catch (err) {
      setError(err.response?.data?.detail || "خطا در پاسخ‌گویی");
    }
  }

  async function makeExercise() {
    const res = await getExercise(course);
    setExercise(res);
  }

  return (
    <div className="s360-page">
      <h2>🤖 استاد هوشمند</h2>
      <Disclaimer text="پاسخ‌ها فقط از منابع تأییدشده درس است؛ برای تکالیف ارزیابی‌شونده پاسخ قطعی داده نمی‌شود." />

      <Card title="پرسش از درس">
        <div className="s360-form-row">
          <select value={course} onChange={(e) => setCourse(e.target.value)}>
            <option value="CS101">مبانی کامپیوتر (CS101)</option>
            <option value="CS201">ساختمان داده (CS201)</option>
            <option value="CS301">سیستم‌عامل (CS301)</option>
          </select>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="simple">توضیح ساده</option>
            <option value="advanced">توضیح پیشرفته</option>
          </select>
        </div>
        <div className="s360-ask-row">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && ask()}
                 placeholder="سؤال خود را از درس بپرسید..." />
          <button onClick={ask}>پرسش</button>
        </div>
        {error && <p className="s360-error">{error}</p>}

        {result && (
          <div className="s360-answer">
            {result.is_low_confidence && (
              <div className="s360-low-conf">اطمینان پاسخ پایین است؛ در صورت ابهام از استاد درس بپرسید.</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            {result.ai_engine === "llm" && (
              <div className="ai-tagline">✨ پاسخ تولیدشده با هوش مصنوعی{result.ai_low_confidence ? " — اطمینان پایین" : ""}</div>
            )}
            <p className="s360-answer-text">{result.answer}</p>
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.ai_sources?.length > 0 && (
              <div className="s360-sources">
                <b>منابع AI (RAG):</b>
                {result.ai_sources.map((s, i) => (
                  <div key={"ai" + i} className="s360-source">🔹 [{s.kind}] {s.title}</div>
                ))}
              </div>
            )}
            {result.sources?.length > 0 && (
              <div className="s360-sources">
                <b>منبع:</b>
                {result.sources.map((s, i) => (
                  <div key={i}>📖 {s.title} — {s.section}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title="طراحی تمرین" actions={<button onClick={makeExercise}>تمرین جدید</button>}>
        {!exercise ? <Empty>برای درس انتخابی تمرین بسازید.</Empty> : (
          <div className="s360-guide">
            <h4>{exercise.topic}</h4>
            <ol>{exercise.exercise.map((s) => (
              <li key={s.step}><b>{s.task}</b><br /><small>💡 {s.hint}</small></li>
            ))}</ol>
            <p className="s360-hint">منبع: {exercise.source_ref}</p>
          </div>
        )}
      </Card>

      <Card title="سوابق پرسش‌ها">
        {history.length === 0 ? <Empty>سابقه‌ای وجود ندارد.</Empty> : history.slice(0, 10).map((h) => (
          <div className="s360-history-row" key={h.id}>
            <b>{h.course_code}:</b> {h.question}
          </div>
        ))}
      </Card>
    </div>
  );
}






