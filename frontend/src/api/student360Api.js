// Student 360 — API client for the student portal.
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/student360",
});

api.interceptors.request.use((config) => {
  const sn = localStorage.getItem("s360_student_number");
  const user = localStorage.getItem("s360_user");
  if (sn) config.headers["X-Student-Number"] = sn;
  if (user) config.headers["X-User"] = user;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    console.error("S360 API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ===== Auth =====
export const otpRequest = (studentNumber) =>
  api.post("/auth/otp/request", { student_number: studentNumber }).then(r => r.data);
export const otpVerify = (studentNumber, code) =>
  api.post("/auth/otp/verify", { student_number: studentNumber, code }).then(r => r.data);
export const ssoLogin = (token) =>
  api.post("/auth/sso", { sso_token: token }).then(r => r.data);

// ===== Profile =====
export const getProfile = () => api.get("/profile").then(r => r.data);
export const getWeeklySchedule = () => api.get("/profile/weekly-schedule").then(r => r.data);
export const reportDiscrepancy = (data) =>
  api.post("/profile/discrepancy", data).then(r => r.data);
export const getDiscrepancies = () => api.get("/profile/discrepancies").then(r => r.data);

// ===== Regulations =====
export const askRegulations = (question) =>
  api.post("/regulations/ask", { question }).then(r => r.data);
export const sendRegulationFeedback = (id, feedback) =>
  api.post(`/regulations/${id}/feedback`, { feedback }).then(r => r.data);
export const getRegulationHistory = () =>
  api.get("/regulations/history").then(r => r.data);

// ===== Guides =====
export const getGuides = () => api.get("/guides").then(r => r.data);
export const getGuide = (slug) => api.get(`/guides/${slug}`).then(r => r.data);

// ===== Selection =====
export const getSelectionAssistant = (term) =>
  api.get("/selection/assistant", { params: { term } }).then(r => r.data);
export const getCourseAnalysis = (code) =>
  api.get(`/selection/courses/${code}/analysis`).then(r => r.data);
export const saveScenario = (term, name, course_codes) =>
  api.post("/selection/scenarios", { term, name, course_codes }).then(r => r.data);
export const getScenarios = () => api.get("/selection/scenarios").then(r => r.data);

// ===== Graduation =====
export const getGraduationCheck = () =>
  api.get("/graduation/check").then(r => r.data);

// ===== Calendar & notifications =====
export const getCalendar = () => api.get("/calendar").then(r => r.data);
export const getReminders = () => api.get("/calendar/reminders").then(r => r.data);
export const getChannels = () => api.get("/notifications/channels").then(r => r.data);
export const updateChannels = (data) =>
  api.put("/notifications/channels", data).then(r => r.data);

// ===== Alerts =====
export const getAlerts = () => api.get("/alerts").then(r => r.data);
export const requestCounseling = (alert_id, message) =>
  api.post("/alerts/counseling", { alert_id, message }).then(r => r.data);

// ===== Quiz =====
export const generateQuiz = (course_code, difficulty = "medium", count = 3) =>
  api.post("/quiz/generate", { course_code, difficulty, count }).then(r => r.data);
export const submitQuiz = (quizId, answers) =>
  api.post(`/quiz/${quizId}/submit`, { answers }).then(r => r.data);
export const getQuizHistory = () => api.get("/quiz/history").then(r => r.data);

// ===== Smart professor =====
export const askProfessor = (course_code, question, mode = "simple") =>
  api.post("/professor/ask", { course_code, question, mode }).then(r => r.data);
export const getExercise = (course_code, topic = null) =>
  api.post("/professor/exercise", { course_code, topic }).then(r => r.data);
export const getProfessorHistory = () =>
  api.get("/professor/history").then(r => r.data);
