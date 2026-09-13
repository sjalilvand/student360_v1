// Student 360 - portal shell v4: 3 roles + dynamic permission-filtered menus.
import { useEffect, useState } from "react";
import { getReminders } from "../../api/student360Api";
import LoginPage from "./LoginPage";
import AiAssistantPage from "./AiAssistantPage";
import BehaviorPage from "./BehaviorPage";
import StudyPathPage from "./StudyPathPage";
import AdaptiveQuizPage from "./AdaptiveQuizPage";
import CareerPage from "./CareerPage";
import TwinPage from "./TwinPage";
import VoteManagement from "../VoteManagement";
import {
  StaffOverviewPage, StaffStudentsPage, StaffEngagementPage,
  StaffRiskPage, StaffInterventionsPage, StaffFeedbackPage,
  GraphExplorerPage,
} from "./StaffPages";
import { AccessControlPage } from "./AccessControlPage";
import { ProfessorDashboardPage, ProfessorProposalsPage,
  ProfessorAvailabilityPage, ProfessorPasswordPage } from "./ProfessorPortalPages";
import { track, trackPage } from "../../utils/eventTracker";
import {
  ProfilePage, RegulationsPage, GuidesPage, SelectionPage,
  GraduationPage, CalendarPage, AlertsPage, QuizPage, ProfessorPage,
} from "./Student360Pages";
import "./student360.css";

const STUDENT_MENU = [
  { id: "profile", icon: "👤", label: "پروفایل هوشمند" },
  { id: "behavior", icon: "🧠", label: "بینش‌های رفتاری" },
  { id: "studypath", icon: "🗺️", label: "مسیر تحصیلی من" },
  { id: "regulations", icon: "📜", label: "دستیار آیین‌نامه‌ای" },
  { id: "guides", icon: "🗂️", label: "راهنمای فرایندها" },
  { id: "selection", icon: "🧭", label: "دستیار انتخاب واحد" },
  { id: "graduation", icon: "🎓", label: "بررسی فارغ‌التحصیلی" },
  { id: "calendar", icon: "🗓️", label: "تقویم و یادآوری" },
  { id: "alerts", icon: "🔔", label: "هشدارها" },
  { id: "quiz", icon: "🧪", label: "کوییز هوشمند" },
  { id: "adaptivequiz", icon: "🎯", label: "کوییز تطبیقی (AI)" },
  { id: "professor", icon: "🤖", label: "استاد هوشمند" },
  { id: "career", icon: "💼", label: "پروفایل شغلی" },
  { id: "twin", icon: "🧊", label: "شبیه‌ساز چه می‌شود اگر" },
  { id: "ai", icon: "✨", label: "دستیار هوشمند (AI)" },
];

const STAFF_MENU = [
  { id: "overview", icon: "📊", label: "میز کار کارشناس" },
  { id: "students", icon: "👨‍🎓", label: "دانشجویان" },
  { id: "engagement", icon: "📈", label: "تعامل دانشجویان" },
  { id: "risk", icon: "⚠️", label: "هشدار ریسک تحصیلی" },
  { id: "interventions", icon: "🚨", label: "مداخله‌های حمایتی" },
  { id: "feedback", icon: "💬", label: "کیفیت پاسخ‌ها" },
  { id: "graph", icon: "🕸", label: "گراف دروس" },
  { id: "votes", icon: "🗳", label: "نظرسنجی دروس" },
  { id: "access", icon: "🎛", label: "کنترل دسترسی" },
  { id: "ai", icon: "✨", label: "دستیار هوشمند (AI)" },
];

const PROF_MENU = [
  { id: "profdash", icon: "👨‍🏫", label: "پورتال استاد" },
  { id: "profproposals", icon: "📝", label: "پیشنهاد دروس من" },
  { id: "profavail", icon: "🗓️", label: "دسترس‌بازی من" },
  { id: "profpass", icon: "🔑", label: "تغییر رمز عبور" },
  { id: "ai", icon: "✨", label: "دستیار هوشمند (AI)" },
];

function isStaffRole(role) {
  const r = (role || "").toLowerCase();
  return r.includes("expert") || r.includes("staff") || r.includes("admin") || r.includes("manager");
}
function isProfRole(role) {
  return (role || "").toLowerCase().includes("professor");
}

export default function Student360Portal({ onExit }) {
  const [user, setUser] = useState(() => {
    const sn = localStorage.getItem("s360_student_number");
    return sn ? { username: sn, role: localStorage.getItem("s360_role") || "" } : null;
  });
  const prof = isProfRole(user?.role);
  const staff = isStaffRole(user?.role);
  const roleKey = prof ? "professor" : staff ? "staff" : "student";

  // allowed menus MUST be declared before MENU (fixes TDZ ReferenceError)
  const [allowedMenus, setAllowedMenus] = useState(null);

  const BASE_MENU = prof ? PROF_MENU : staff ? STAFF_MENU : STUDENT_MENU;
  const MENU = allowedMenus
    ? BASE_MENU.filter((m) => allowedMenus.includes(m.id))
    : BASE_MENU;

  const [page, setPage] = useState(prof ? "profdash" : staff ? "overview" : "profile");
  const [reminders, setReminders] = useState(0);

  useEffect(() => {
    if (!user) return;
    fetch(`http://127.0.0.1:8000/api/permissions/menu/${roleKey}`)
      .then((r) => r.json())
      .then((j) => setAllowedMenus(j.menus || null))
      .catch(() => setAllowedMenus(null));
  }, [user, roleKey]);

  useEffect(() => {
    if (!user || staff) return;
    getReminders().then((r) => setReminders(r.length)).catch(() => {});
  }, [user, page, staff]);

  useEffect(() => {
    if (user) trackPage((prof ? "prof:" : staff ? "staff:" : "student:") + page);
  }, [page, user, prof, staff]);

  if (!user) return <LoginPage onLogin={setUser} />;

  function logout() {
    track("logout");
    ["s360_student_number", "s360_role", "s360_display_name", "s360_token"].forEach((k) => localStorage.removeItem(k));
    setUser(null);
  }

  const profPages = {
    profdash: <ProfessorDashboardPage />,
    profproposals: <ProfessorProposalsPage />,
    profavail: <ProfessorAvailabilityPage />,
    profpass: <ProfessorPasswordPage />,
    ai: <AiAssistantPage />,
  };
  const staffPages = {
    overview: <StaffOverviewPage />,
    students: <StaffStudentsPage />,
    engagement: <StaffEngagementPage />,
    risk: <StaffRiskPage />,
    interventions: <StaffInterventionsPage />,
    feedback: <StaffFeedbackPage />,
    graph: <GraphExplorerPage />,
    votes: <VoteManagement />,
    access: <AccessControlPage />,
    ai: <AiAssistantPage />,
  };
  const studentPages = {
    profile: <ProfilePage />,
    behavior: <BehaviorPage />,
    studypath: <StudyPathPage />,
    regulations: <RegulationsPage />,
    guides: <GuidesPage />,
    selection: <SelectionPage />,
    graduation: <GraduationPage />,
    calendar: <CalendarPage />,
    alerts: <AlertsPage />,
    quiz: <QuizPage />,
    adaptivequiz: <AdaptiveQuizPage />,
    professor: <ProfessorPage />,
    career: <CareerPage />,
    twin: <TwinPage />,
    ai: <AiAssistantPage />,
  };
  const pages = prof ? profPages : staff ? staffPages : studentPages;
  const displayName = localStorage.getItem("s360_display_name") || user.username;

  return (
    <div className="s360-portal">
      <aside className="s360-sidebar">
        <div className="s360-logo">
          <span className="s360-logo-icon">{prof ? "👨‍🏫" : staff ? "👨‍💼" : "🎓"}</span>
          <div>
            <h2>{prof ? "پورتال استاد" : staff ? "میز کار کارشناس" : "دانشجو ۳۶۰"}</h2>
            <p>{prof ? "پنل اساتید" : staff ? "پنل آموزش" : "سامانه خدمات دانشجویی"}</p>
          </div>
        </div>
        <nav className="s360-nav">
          {MENU.map((m) => (
            <button key={m.id}
                    className={page === m.id ? "active" : ""}
                    onClick={() => setPage(m.id)}>
              <span>{m.icon}</span> {m.label}
              {!staff && m.id === "calendar" && reminders > 0 && (
                <span className="s360-nav-badge">{reminders}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="s360-sidebar-footer">
          <p>👋 {displayName}</p>
          <button onClick={logout}>خروج</button>
          <button onClick={onExit} className="s360-exit">بازگشت به سامانه مدیریت</button>
        </div>
      </aside>
      <main className="s360-main">
        <header className="s360-header">
          <h1>{MENU.find((m) => m.id === page)?.label || "..."}</h1>
        </header>
        <div className="s360-content">{pages[page]}</div>
      </main>
    </div>
  );
}
