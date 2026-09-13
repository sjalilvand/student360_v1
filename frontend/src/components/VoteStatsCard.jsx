// components/VoteStatsCard.jsx - aggregated vote counts per course.
import { useEffect, useState } from "react";
import { Card, Empty, Loading } from "../pages/student360/shared";

const API_BASE = import.meta.env.VITE_API_BASE || "";

export default function VoteStatsCard({ refreshKey = 0, title = "📊 آمار رأی‌های ثبت‌شده" }) {
  const [items, setItems] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/votes/stats-all`)
      .then((r) => r.json())
      .then((j) => setItems(j.items || []))
      .catch(() => setItems([]));
  }, [refreshKey]);

  if (!items) return <Loading />;
  const max = Math.max(1, ...items.map((i) => i.total));

  return (
    <Card title={title}>
      {items.length === 0 ? <Empty>هنوز رأیی ثبت نشده</Empty> : (
        <table className="s360-table">
          <thead><tr><th>درس</th><th>کد</th><th>👍 می‌خواهم</th><th>📌 درخواست ارائه</th><th>جمع</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.course_id}>
                <td><b>{i.title || "-"}</b></td>
                <td>{i.code || "-"}</td>
                <td style={{ color: "#16a34a", fontWeight: 700 }}>{i.likes}</td>
                <td style={{ color: "#2563eb", fontWeight: 700 }}>{i.requests}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: ".4rem" }}>
                    <div style={{ flex: 1, height: 8, background: "#f1f5f9", borderRadius: 999 }}>
                      <div style={{ width: (i.total / max) * 100 + "%", height: "100%",
                                    background: "#6366f1", borderRadius: 999 }} />
                    </div>
                    <b>{i.total}</b>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
