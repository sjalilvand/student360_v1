// components/GraphView.jsx - live course-graph visualization (react-flow).
import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const HEADERS = () => ({ "X-Student-Number": localStorage.getItem("s360_student_number") || "" });

export default function GraphView({ code, depth = 2 }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!code) return;
    setLoading(true); setErr("");
    fetch(`${API_BASE}/api/graph/neighbors?code=${encodeURIComponent(code)}&depth=${depth}`,
          { headers: HEADERS() })
      .then((r) => r.json())
      .then((j) => {
        if (j.error) { setErr(j.error); setNodes([]); setEdges([]); return; }
        const laidOut = j.nodes.map((n, i) => {
          const isCenter = n.id === j.center;
          const isSkill = n.type === "skill";
          return {
            id: n.id,
            position: {
              x: (i % 5) * 190 + (isSkill ? 60 : 0),
              y: Math.floor(i / 5) * 110,
            },
            data: { label: `${n.label}${n.conditions?.length ? "\n(" + n.conditions[0] + ")" : ""}` },
            style: {
              background: isCenter ? "#6366f1" : isSkill ? "#fef3c7" : "#ffffff",
              color: isCenter ? "#fff" : "#1e293b",
              border: `1.5px solid ${isCenter ? "#4338ca" : isSkill ? "#f59e0b" : "#94a3b8"}`,
              borderRadius: 10,
              padding: 8,
              fontSize: 11,
              width: 170,
              whiteSpace: "pre-wrap",
            },
          };
        });
        const e = j.edges.map((ed, i) => ({
          id: "e" + i,
          source: ed.source,
          target: ed.target,
          animated: ed.kind === "prereq",
          style: { stroke: ed.kind === "prereq" ? "#6366f1" : "#f59e0b", width: 1.5 },
          label: ed.kind === "gives" ? "مهارت" : "",
          fontSize: 9,
        }));
        setNodes(laidOut);
        setEdges(e);
      })
      .catch(() => setErr("خطا در دریافت گراف"))
      .finally(() => setLoading(false));
  }, [code, depth]);

  if (!code) return null;
  if (loading) return <p className="s360-hint">در حال بارگذاری گراف...</p>;
  if (err) return <p className="s360-error">{err}</p>;
  if (!nodes.length) return null;

  return (
    <div style={{ width: "100%", height: 420, border: "1px solid #e2e8f0",
                  borderRadius: 12, overflow: "hidden", direction: "ltr" }}>
      <ReactFlow nodes={nodes} edges={edges} fitView
                 nodesDraggable nodesConnectable={false} elementsSelectable>
        <Background color="#f1f5f9" gap={18} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable style={{ width: 130, height: 90 }} />
      </ReactFlow>
    </div>
  );
}
