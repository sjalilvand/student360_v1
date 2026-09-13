// frontend/src/api/eventApi.js
// Event Tracking client (STU-EVT) - fire & forget, never throws.
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const client = axios.create({ baseURL: API_BASE, timeout: 5000 });

export function sendEvent(body) {
  return client.post("/api/events", body).then((r) => r.data).catch(() => null);
}

export function fetchEventSummary(days = 30, studentRef = null) {
  const q = studentRef
    ? `?days=${days}&student_ref=${encodeURIComponent(studentRef)}`
    : `?days=${days}`;
  return client.get(`/api/events/summary${q}`).then((r) => r.data).catch(() => null);
}

export default { sendEvent, fetchEventSummary };
