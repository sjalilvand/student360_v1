// Student 360 - Access Control Panel (role x menu matrix).
import { useEffect, useState } from "react";
import { Card, Loading } from "./shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const HEADERS = () => ({
  "X-Student-Number": localStorage.getItem("s360_student_number") || "",
  "Content-Type": "application/json",
});
const ROLES = [
  { id: "student", label: "🎓 دانشجو" },
  { id: "staff", label: "👨‍💼 کارشناس" },
  { id: "professor", label: "👨‍🏫 استاد" },
];

export function AccessControlPage() {
  const [matrix, setMatrix] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    fetch(`${API_BASE}/api/permissions/matrix`, { headers: HEADERS() })
      .then((r) => r.json()).then(setMatrix).catch(() => setMatrix({ error: true }));
  useEffect(load, []);

  async function toggle(role, menuId, enabled) {
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/permissions/set`, {
        method: "PUT", headers: HEADERS(),
        body: JSON.stringify({ role, menu_id: menuId, enabled }) });
      setMatrix((m) => ({
        ...m,
        [role]: m[role].map((x) => (x.menu_id === menuId ? { ...x, enabled } : x)),
      }));
    } finally { setBusy(false); }
  }

  async function resetRole(role) {
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/permissions/reset`, {
        method: "POST", headers: HEADERS(),
        body: JSON.stringify({ role }) });
      setMsg("پیش‌فرض‌های نقش بازگردانده شد");
      load();
    } finally { setBusy(false); }
  }

  if (!matrix) return <Loading />;
  if (matrix.error) return <p className="s360-error">خطا در دریافت ماتریس</p>;

  return (
    <div className="s360-page">
      <h2>🎛 کنترل دسترسی و نمایش منوها</h2>
      {msg && <p className="s360-hint">{msg}</p>}
      {ROLES.map((r) => (
        <Card key={r.id} title={r.label}
              actions={<button onClick={() => resetRole(r.id)}
                               disabled={busy}>↺ پیش‌فرض</button>}>
          <table className="s360-table">
            <thead><tr><th>منو</th><th>نمایش</th></tr></thead>
            <tbody>
              {(matrix[r.id] || []).map((x) => (
                <tr key={x.menu_id}>
                  <td>{x.menu_id}{!x.known && <small className="s360-hint"> (خارج از منوی فعلی)</small>}</td>
                  <td>
                    <button className={x.enabled ? "risk-low" : "risk-high"}
                            style={{ borderRadius: 999, padding: ".2rem .8rem" }}
                            disabled={busy}
                            onClick={() => toggle(r.id, x.menu_id, !x.enabled)}>
                      {x.enabled ? "✅ فعال" : "⛔ غیرفعال"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}
      <p className="s360-hint">تغییرات بلافاصله در منوی کاربران آن نقش اعمال می‌شود (پس از رفرش صفحه آن‌ها).</p>
    </div>
  );
}
