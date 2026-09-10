"""Render knowledge graph as a self-contained HTML visualization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
KG_HTML_PATH = ROOT / "out" / "knowledge-graph.html"

# Utility tool palette (avoid purple / cream / broadsheet defaults)
TYPE_COLORS = {
    "Source": "#3d6b8c",
    "Topic": "#2a7a6a",
    "Athlete": "#b07a2a",
    "Entity": "#6b6358",
    "QueryHint": "#3f7a3f",
    "Year": "#2f6f8f",
    "Template": "#9a5a2a",
}


def render_knowledge_graph_html(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, ensure_ascii=False)
    colors = json.dumps(TYPE_COLORS, ensure_ascii=False)
    node_count = len(graph.get("nodes") or [])
    edge_count = len(graph.get("edges") or [])
    generated = graph.get("generated_at") or ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>INBOX Knowledge Graph</title>
  <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg: #12161a;
      --panel: #1a2128;
      --text: #e8eee9;
      --muted: #8a9690;
      --line: #2a343c;
      --accent: #3d8f7a;
      --focus: #c4a35a;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      height: 100%;
      background: var(--bg);
      color: var(--text);
      font-family: "IBM Plex Sans", "Hiragino Sans", "Noto Sans JP", sans-serif;
    }}
    body {{
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 100%;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1rem;
      align-items: center;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #1a2229 0%, #141a1f 100%);
    }}
    header h1 {{
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    header .meta {{
      color: var(--muted);
      font-size: 0.8rem;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
      margin-left: auto;
    }}
    input[type="search"] {{
      min-width: 12rem;
      padding: 0.4rem 0.6rem;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--panel);
      color: var(--text);
    }}
    input[type="search"]:focus {{
      outline: 2px solid var(--accent);
      outline-offset: 1px;
    }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
    }}
    .filters label {{
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.2rem 0.45rem;
      border: 1px solid var(--line);
      border-radius: 4px;
      font-size: 0.75rem;
      color: var(--muted);
      cursor: pointer;
      user-select: none;
    }}
    .filters label.on {{
      color: var(--text);
      border-color: var(--accent);
    }}
    .filters input {{ margin: 0; }}
    main {{
      display: grid;
      grid-template-columns: 1fr minmax(16rem, 22rem);
      min-height: 0;
    }}
    #network {{
      min-height: 0;
      height: 100%;
      border-right: 1px solid var(--line);
      background:
        radial-gradient(ellipse at 20% 10%, rgba(61, 143, 122, 0.08), transparent 45%),
        radial-gradient(ellipse at 80% 90%, rgba(196, 163, 90, 0.05), transparent 40%),
        var(--bg);
    }}
    aside {{
      padding: 1rem;
      overflow: auto;
      background: var(--panel);
    }}
    aside h2 {{
      margin: 0 0 0.5rem;
      font-size: 0.95rem;
    }}
    aside .hint {{
      color: var(--muted);
      font-size: 0.85rem;
      line-height: 1.45;
      white-space: pre-wrap;
    }}
    aside .empty {{
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.1rem 0.4rem;
      border-radius: 3px;
      font-size: 0.7rem;
      color: #0e1214;
      font-weight: 600;
    }}
    ul.refs {{
      margin: 0.5rem 0 0;
      padding-left: 1.1rem;
      font-size: 0.8rem;
      line-height: 1.5;
      word-break: break-all;
    }}
    ul.refs li {{ margin-bottom: 0.25rem; }}
    .stats {{
      margin-top: 1rem;
      padding-top: 0.75rem;
      border-top: 1px solid var(--line);
      font-size: 0.75rem;
      color: var(--muted);
    }}
    @media (max-width: 800px) {{
      main {{
        grid-template-columns: 1fr;
        grid-template-rows: minmax(55vh, 1fr) auto;
      }}
      #network {{ border-right: none; border-bottom: 1px solid var(--line); }}
      .controls {{ margin-left: 0; width: 100%; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>INBOX Knowledge Graph</h1>
      <div class="meta" id="kg-meta">{node_count} nodes · {edge_count} edges · {generated}</div>
    </div>
    <div class="controls">
      <input id="kg-search" type="search" placeholder="検索（label / hint / refs）" aria-label="検索" />
      <div class="filters" id="kg-filters" aria-label="ノード種別フィルタ"></div>
    </div>
  </header>
  <main>
    <div id="network" role="img" aria-label="ナレッジグラフ可視化"></div>
    <aside id="kg-detail">
      <p class="empty">ノードをクリックすると hint と refs を表示します。</p>
      <div class="stats" id="kg-stats"></div>
    </aside>
  </main>
  <script id="kg-data" type="application/json">{payload}</script>
  <script id="kg-colors" type="application/json">{colors}</script>
  <script>
    (function () {{
      const graph = JSON.parse(document.getElementById("kg-data").textContent);
      const colors = JSON.parse(document.getElementById("kg-colors").textContent);
      const types = [...new Set((graph.nodes || []).map((n) => n.type))].sort();
      const enabled = Object.fromEntries(types.map((t) => [t, true]));

      const filterRoot = document.getElementById("kg-filters");
      types.forEach((t) => {{
        const label = document.createElement("label");
        label.className = "on";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = true;
        cb.dataset.type = t;
        const swatch = document.createElement("span");
        swatch.className = "badge";
        swatch.style.background = colors[t] || "#888";
        swatch.textContent = t;
        label.appendChild(cb);
        label.appendChild(swatch);
        filterRoot.appendChild(label);
        cb.addEventListener("change", () => {{
          enabled[t] = cb.checked;
          label.classList.toggle("on", cb.checked);
          redraw();
        }});
      }});

      const byId = Object.fromEntries((graph.nodes || []).map((n) => [n.id, n]));
      let query = "";

      function visibleIds() {{
        const q = query.trim().toLowerCase();
        const ids = new Set();
        for (const n of graph.nodes || []) {{
          if (!enabled[n.type]) continue;
          if (!q) {{
            ids.add(n.id);
            continue;
          }}
          const blob = [n.id, n.label, n.hint, ...(n.topics || []), ...(n.refs || [])]
            .join(" ")
            .toLowerCase();
          if (blob.includes(q)) ids.add(n.id);
        }}
        return ids;
      }}

      function toVis(ids) {{
        const nodes = [...ids].map((id) => {{
          const n = byId[id];
          return {{
            id: n.id,
            label: n.label || n.id,
            title: (n.hint || "") + "\\n" + (n.refs || []).join("\\n"),
            color: {{
              background: colors[n.type] || "#666",
              border: "#0e1214",
              highlight: {{ background: colors[n.type] || "#666", border: "#c4a35a" }},
            }},
            font: {{ color: "#0e1214", size: 12, face: "IBM Plex Sans" }},
            shape: n.type === "Topic" ? "box" : n.type === "Source" ? "dot" : "ellipse",
            size: n.type === "Topic" ? 18 : n.type === "Athlete" ? 14 : 12,
          }};
        }});
        const edges = (graph.edges || [])
          .filter((e) => ids.has(e.from) && ids.has(e.to))
          .map((e, i) => ({{
            id: "e" + i,
            from: e.from,
            to: e.to,
            label: e.rel,
            font: {{ size: 8, color: "#8a9690", strokeWidth: 0 }},
            color: {{ color: "#3a4650", highlight: "#c4a35a" }},
            arrows: "to",
            smooth: {{ type: "continuous" }},
          }}));
        return {{ nodes, edges }};
      }}

      const container = document.getElementById("network");
      const network = new vis.Network(
        container,
        {{ nodes: new vis.DataSet([]), edges: new vis.DataSet([]) }},
        {{
          interaction: {{ hover: true, tooltipDelay: 120, multiselect: false }},
          physics: {{
            barnesHut: {{ gravitationalConstant: -12000, springLength: 120, springConstant: 0.02 }},
            stabilization: {{ iterations: 120 }},
          }},
          edges: {{ width: 1 }},
        }}
      );

      function redraw() {{
        const ids = visibleIds();
        const data = toVis(ids);
        network.setData({{
          nodes: new vis.DataSet(data.nodes),
          edges: new vis.DataSet(data.edges),
        }});
        document.getElementById("kg-stats").textContent =
          "表示中: " + data.nodes.length + " nodes / " + data.edges.length + " edges";
      }}

      function showDetail(id) {{
        const n = byId[id];
        const aside = document.getElementById("kg-detail");
        if (!n) {{
          aside.innerHTML = '<p class="empty">ノードが見つかりません。</p><div class="stats" id="kg-stats"></div>';
          return;
        }}
        const refs = (n.refs || [])
          .map((r) => "<li><code>" + escapeHtml(r) + "</code></li>")
          .join("");
        aside.innerHTML =
          '<h2>' +
          escapeHtml(n.label || n.id) +
          ' <span class="badge" style="background:' +
          (colors[n.type] || "#888") +
          '">' +
          escapeHtml(n.type) +
          "</span></h2>" +
          '<div class="hint">' +
          escapeHtml(n.hint || "(hint なし)") +
          "</div>" +
          (refs ? '<ul class="refs">' + refs + "</ul>" : '<p class="empty">refs なし</p>') +
          '<div class="stats" id="kg-stats"></div>';
      }}

      function escapeHtml(s) {{
        return String(s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }}

      network.on("click", (params) => {{
        if (params.nodes && params.nodes[0]) showDetail(params.nodes[0]);
      }});

      document.getElementById("kg-search").addEventListener("input", (ev) => {{
        query = ev.target.value || "";
        redraw();
      }});

      redraw();
    }})();
  </script>
</body>
</html>
"""


def write_knowledge_graph_html(graph: dict[str, Any], path: Path | None = None) -> Path:
    path = path or KG_HTML_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_knowledge_graph_html(graph), encoding="utf-8")
    return path
