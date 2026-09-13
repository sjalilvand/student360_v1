// Student 360 - login (STU-AUTH): OTP + SSO + Staff + Professor.
import { useState } from "react";
import axios from "axios";
import { otpRequest, otpVerify, ssoLogin } from "../../api/student360Api";
import { track } from "../../utils/eventTracker";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState("otp");
  const [studentNumber, setStudentNumber] = useState("");
  const [code, setCode] = useState("");
  const [ssoToken, setSsoToken] = useState("");
  const [staffUser, setStaffUser] = useState("");
  const [staffPass, setStaffPass] = useState("");
  const [devCode, setDevCode] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function saveUser(username, role, displayName) {
    localStorage.setItem("s360_student_number", username);
    localStorage.setItem("s360_role", role);
    localStorage.setItem("s360_display_name", displayName || "");
    track("login", role, { user: username });
    onLogin({ username, role });
  }

  async function handleOtpRequest(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await otpRequest(studentNumber);
      setDevCode(res.dev_code);
    } catch (err) {
      setError(err.response?.data?.detail || "خطا در درخواست رمز");
    } finally { setLoading(false); }
  }

  async function handleOtpVerify(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await otpVerify(studentNumber, code);
      saveUser(res.username, res.role, res.display_name);
    } catch (err) {
      setError(err.response?.data?.detail || "کد نامعتبر است");
    } finally { setLoading(false); }
  }

  async function handleSso(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await ssoLogin(ssoToken);
      saveUser(res.username, res.role, res.display_name);
    } catch (err) {
      setError(err.response?.data?.detail || "ورود SSO ناموفق بود");
    } finally { setLoading(false); }
  }

  async function handleStaffLogin(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/student360/auth/login`,
        { username: staffUser, password: staffPass }).then((r) => r.data);
      localStorage.setItem("s360_student_number", res.username);
      localStorage.setItem("s360_role", res.role || "education-expert");
      localStorage.setItem("s360_display_name", res.display_name || "");
      localStorage.setItem("s360_token", res.token || "");
      track("login", "staff", { user: res.username });
      onLogin({ username: res.username, role: res.role || "education-expert" });
    } catch (err) {
      setError(err.response?.data?.detail || "ورود کارشناس ناموفق بود");
    } finally { setLoading(false); }
  }

  async function handleProfLogin(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/professor/login`,
        { username: staffUser, password: staffPass }).then((r) => r.data);
      localStorage.setItem("s360_student_number", res.username);
      localStorage.setItem("s360_role", "professor");
      localStorage.setItem("s360_display_name", res.user?.full_name || res.username);
      localStorage.setItem("s360_token", res.token || "");
      track("login", "professor", { user: res.username });
      onLogin({ username: res.username, role: "professor" });
    } catch (err) {
      setError(err.response?.data?.detail || "ورود استاد ناموفق بود");
    } finally { setLoading(false); }
  }

  return (
    <div className="s360-login">
      <div className="s360-login-card">
        <h1>🎓 دانشجو ۳۶۰</h1>
        <p className="s360-login-sub">سامانه یکپارچه خدمات دانشجویی</p>

        <div className="s360-login-tabs">
          <button className={mode === "otp" ? "active" : ""} onClick={() => setMode("otp")}>ورود دانشجویی</button>
          <button className={mode === "sso" ? "active" : ""} onClick={() => setMode("sso")}>SSO دانشگاه</button>
          <button className={mode === "staff" ? "active" : ""} onClick={() => setMode("staff")}>👨‍💼 کارشناس</button>
          <button className={mode === "prof" ? "active" : ""} onClick={() => setMode("prof")}>👨‍🏫 استاد</button>
        </div>

        {mode === "otp" && !devCode && (
          <form onSubmit={handleOtpRequest}>
            <input placeholder="شماره دانشجویی" value={studentNumber}
                   onChange={(e) => setStudentNumber(e.target.value)} required />
            <button type="submit" disabled={loading}>{loading ? "..." : "دریافت رمز یک‌بارمصرف"}</button>
          </form>
        )}
        {mode === "otp" && devCode && (
          <form onSubmit={handleOtpVerify}>
            <p className="s360-dev-code">کد پایلوت: <b>{devCode}</b></p>
            <input placeholder="رمز یک‌بارمصرف" value={code}
                   onChange={(e) => setCode(e.target.value)} required />
            <button type="submit" disabled={loading}>ورود</button>
          </form>
        )}

        {mode === "sso" && (
          <form onSubmit={handleSso}>
            <input placeholder="شناسه SSO (مثلاً a.mohammadi)" value={ssoToken}
                   onChange={(e) => setSsoToken(e.target.value)} required />
            <button type="submit" disabled={loading}>ورود با SSO</button>
          </form>
        )}

        {(mode === "staff" || mode === "prof") && (
          <form onSubmit={mode === "staff" ? handleStaffLogin : handleProfLogin}>
            <input placeholder="نام کاربری" value={staffUser}
                   onChange={(e) => setStaffUser(e.target.value)} autoComplete="username" required />
            <input type="password" placeholder="رمز عبور" value={staffPass}
                   onChange={(e) => setStaffPass(e.target.value)} autoComplete="current-password" required />
            <button type="submit" disabled={loading}>{loading ? "..." : mode === "staff" ? "ورود کارشناس" : "ورود استاد"}</button>
          </form>
        )}

        {error && <p className="s360-error">{error}</p>}

        <p className="s360-login-hint">
          پایلوت دانشجو: <b>402101001</b> یا SSO با <b>a.mohammadi</b><br />
          کارشناس: <b>staff-admin / admin123</b>
        </p>
      </div>
    </div>
  );
}
