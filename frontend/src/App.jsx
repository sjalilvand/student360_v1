import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import Student360Portal from "./pages/student360/Student360Portal";
import MartDashboard from "./components/MartDashboard";
import "./style.css";

function App() {
  // سوئیچ بین سامانه مدیریت (ادمین) و پورتال دانشجویی (دانشجو ۳۶۰)
  const [mode, setMode] = useState(() =>
    localStorage.getItem("app_mode") || "student"
  );
  const [showMarts, setShowMarts] = useState(false);

  function switchMode(next) {
    setMode(next);
    localStorage.setItem("app_mode", next);
  }

  return (
    <>
      {mode === "student" ? (
        <Student360Portal onExit={() => switchMode("admin")} />
      ) : (
        <>
          <button
            onClick={() => switchMode("student")}
            style={{
              position: "fixed",
              bottom: "1rem",
              insetInlineStart: "1rem",
              zIndex: 9999,
              background: "#6366f1",
              color: "#fff",
              border: "none",
              borderRadius: "999px",
              padding: "0.55rem 1.1rem",
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(99, 102, 241, 0.4)",
              fontFamily: "inherit",
              fontSize: "0.85rem",
            }}
          >
            🎓 ورود به دانشجو ۳۶۰
          </button>
          <button
            onClick={() => setShowMarts(true)}
            style={{
              position: "fixed",
              bottom: "4.2rem",
              insetInlineStart: "1rem",
              zIndex: 9999,
              background: "#0ea5e9",
              color: "#fff",
              border: "none",
              borderRadius: "999px",
              padding: "0.55rem 1.1rem",
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(14, 165, 233, 0.4)",
              fontFamily: "inherit",
              fontSize: "0.85rem",
            }}
          >
            📊 داشبورد تحلیل
          </button>
          <Dashboard />
          {showMarts && <MartDashboard onClose={() => setShowMarts(false)} />}
        </>
      )}
    </>
  );
}

export default App;
