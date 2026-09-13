// frontend/src/utils/eventTracker.js
// Tiny tracker: session ref + student ref + page views. Never throws.
import { sendEvent } from "../api/eventApi";

const SESSION_KEY = "evt_session_ref";

function getSessionRef() {
  try {
    let ref = sessionStorage.getItem(SESSION_KEY);
    if (!ref) {
      ref = "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sessionStorage.setItem(SESSION_KEY, ref);
    }
    return ref;
  } catch (e) { return "s-anon"; }
}

function extractRef(v) {
  if (typeof v === "string" || typeof v === "number") return String(v);
  if (v && typeof v === "object") {
    const cand = v.student_number || v.student_ref || v.username || v.sub;
    if (cand) return String(cand);
  }
  return null;
}

function getStudentRef() {
  try {
    const keys = ["s360_student_number", "student_number", "s360_user", "user"];
    for (const k of keys) {
      const raw = localStorage.getItem(k);
      if (!raw) continue;
      try { const r = extractRef(JSON.parse(raw)); if (r) return r; }
      catch (e) { if (raw.length < 50) return raw; }
    }
  } catch (e) {}
  return null;
}

export function track(eventType, eventName = null, payload = null) {
  return sendEvent({
    event_type: eventType,
    event_name: eventName,
    student_ref: getStudentRef(),
    session_ref: getSessionRef(),
    source: "web",
    payload: payload || undefined,
  });
}

export function trackPage(pageId, extra) {
  return track("page_view", pageId, extra);
}

export default { track, trackPage };
