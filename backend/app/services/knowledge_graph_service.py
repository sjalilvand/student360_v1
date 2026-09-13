# app/services/knowledge_graph_service.py
# Course Knowledge Graph (Phase 3 / category 12). Built from
# offered_courses.prerequisite + stu_course_skills. Uses networkx.
from __future__ import annotations

import json
import re

import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import guardrails as gr
from app.services.skills_service import ensure_course_skills, keyword_skills

_G = None  # cached graph


def _parse_pre(val):
    if not val:
        return []
    s = str(val).strip()
    if s.lower() in ("", "-", "0", "none", "null", "nan"):
        return []
    try:
        j = json.loads(s)
        if isinstance(j, list):
            return [str(x).strip() for x in j if str(x).strip()]
    except Exception:
        pass
    for sep in (",", "،", ";", "؛", "|"):
        s = s.replace(sep, ",")
    return [x.strip() for x in s.split(",") if x.strip() and x.strip() != "-"]


def _norm(s):
    return (s or "").lower().replace("\u200c", " ").strip()


def build_graph(db: Session) -> nx.DiGraph:
    """ Directed: prereq -> course ; course -> skill node """
    G = nx.DiGraph()

    oc = db.execute(text(
        "SELECT unique_code, unique_title, prerequisite FROM offered_courses")).mappings().all()
    title_by_code = {}
    pre_pairs = []
    for r in oc:
        code = str(r["unique_code"] or "").strip()
        if not code:
            continue
        title_by_code[code] = str(r["unique_title"] or code).strip()
        for p in _parse_pre(r["prerequisite"]):
            pre_pairs.append((p, code))

    # resolve prereq names (titles or codes) against known codes
    title_lookup = {_norm(t): c for c, t in title_by_code.items()}
    import re as _re
    _cond_pat = _re.compile(r"پس از|حداقل|واحد|شرط")
    for pre, course in pre_pairs:
        if _norm(pre) == "nan":
            continue
        G.add_node(course)
        if _cond_pat.search(pre) and _norm(pre) not in title_lookup:
            # unit/term condition, not a course - attach to the course node
            G.nodes[course].setdefault("conditions", [])
            if pre not in G.nodes[course]["conditions"]:
                G.nodes[course]["conditions"].append(pre)
            continue
        pre_code = title_lookup.get(_norm(pre), pre)
        G.add_edge(pre_code, course, kind="prereq")

    for code, title in title_by_code.items():
        if code not in G:
            G.add_node(code)
        G.nodes[code]["title"] = title
        for sk in ensure_course_skills(db, code, title)[0]:
            sk_node = f"SKILL::{sk}"
            G.add_node(sk_node, title=sk, kind="skill")
            G.add_edge(code, sk_node, kind="gives")

    for n_ in list(G.nodes):
        if _norm(n_) == "nan":
            G.remove_node(n_)

    return G


def get_graph(db: Session) -> nx.DiGraph:
    global _G
    if _G is None:
        _G = build_graph(db)
    return _G


def invalidate():
    global _G
    _G = None


def stats(db: Session) -> dict:
    G = get_graph(db)
    course_nodes = [n for n in G.nodes if not str(n).startswith("SKILL::")]
    skill_nodes = [n for n in G.nodes if str(n).startswith("SKILL::")]
    prereq_edges = sum(1 for _, _, d in G.edges(data=True) if d.get("kind") == "prereq")
    roots = [n for n in course_nodes if G.in_degree(n) == 0]
    return {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "courses": len(course_nodes), "skills": len(skill_nodes),
        "prereq_edges": prereq_edges,
        "roots": sorted(roots)[:20], "roots_count": len(roots),
        "components": nx.number_weakly_connected_components(G) if G.number_of_nodes() else 0,
    }


def _label(G, n):
    return G.nodes[n].get("title") or str(n)


def course_cluster(db: Session, code: str) -> dict:
    code = str(code).strip()
    G = get_graph(db)
    if code not in G:
        # try title match
        t = _norm(code)
        for n in G.nodes:
            if not str(n).startswith("SKILL::") and _norm(_label(G, n)) == t:
                code = n
                break
        else:
            return {"error": "course not in graph", "code": str(code)}

    direct_pre = [p for p in G.predecessors(code)
                  if not str(p).startswith("SKILL::")]
    dependents = [d for d in G.successors(code)
                  if not str(d).startswith("SKILL::")]

    # recursive ancestors (all prereqs, BFS upstream)
    ancestors = set()
    stack = list(direct_pre)
    while stack:
        n = stack.pop()
        if n in ancestors:
            continue
        ancestors.add(n)
        stack.extend(p for p in G.predecessors(n) if not str(p).startswith("SKILL::"))
    descendants = set()
    stack = list(dependents)
    while stack:
        n = stack.pop()
        if n in descendants:
            continue
        descendants.add(n)
        stack.extend(d for d in G.successors(n) if not str(d).startswith("SKILL::"))

    skills = [str(s).replace("SKILL::", "") for s in G.successors(code)
              if str(s).startswith("SKILL::")]
    return {
        "code": code, "title": _label(G, code),
        "conditions": G.nodes[code].get("conditions", []),
        "direct_prereqs": sorted(direct_pre),
        "all_prereqs_recursive": sorted(ancestors - {code}),
        "direct_dependents": sorted(dependents),
        "unlocks_count": len(descendants),
        "skills": skills,
    }


def learning_path(db: Session, frm: str, to: str) -> dict:
    G = get_graph(db)
    f, t = str(frm).strip(), str(to).strip()
    resolve = {}
    for n in G.nodes:
        if str(n).startswith("SKILL::"):
            continue
        resolve[_norm(_label(G, n))] = n
    def _fuzzy(qv):
        qn = _norm(qv)
        if qn in resolve:
            return resolve[qn]
        for lab, code_ in resolve.items():
            if qn and (qn in lab or lab in qn):
                return code_
        return None
    f = _fuzzy(f) or f
    t = _fuzzy(t) or t
    if f not in G or t not in G:
        return {"error": "node not found", "from": f, "to": t}
    try:
        path = nx.shortest_path(G, source=f, target=t)
    except nx.NetworkXNoPath:
        return {"found": False, "from": f, "to": t,
                "note": "هیچ مسیر پیش‌نیازی بین این دو درس نیست"}
    steps = [{"i": i, "code": n, "title": _label(G, n)} for i, n in enumerate(path)]
    return {"found": True, "from": f, "to": t, "length": len(path), "path": steps}


def roots_for_term(db: Session, limit: int = 30) -> list:
    G = get_graph(db)
    course_nodes = [n for n in G.nodes if not str(n).startswith("SKILL::")]
    out = []
    for n in course_nodes:
        if G.in_degree(n) == 0:
            out.append({"code": n, "title": _label(G, n),
                        "unlocks": G.out_degree(n)})
    out.sort(key=lambda x: -x["unlocks"])
    return out[: max(1, min(int(limit), 100))]
