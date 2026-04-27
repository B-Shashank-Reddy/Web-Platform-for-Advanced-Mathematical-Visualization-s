"""
graphing.py — Graphing & Conics module
Optimisations applied
─────────────────────
Python / algorithmic
  • Single shared sp.Symbol('x') and SYMPY_LOCALS constant — no repeated allocation
  • Expression cache (_expr_cache): sympify + lambdify results keyed by expression
    string, so repeated calls (safe_eval → find_intersections → symbolic block)
    never recompile the same expression
  • find_intersections: removed sp.simplify before sp.solve (expensive, not needed);
    numerical scan is now fully vectorised with np.where instead of a Python loop
  • _dedup: O(n log n) sort-based deduplication instead of O(n²) nested scan
  • scipy.optimize.brentq imported once at module level
  • parsed_exprs stores only the sympy expr (str key dropped)
  • Symbolic-expressions block reuses parsed_exprs instead of re-parsing

JS / rendering
  • canvas 2d context cached once outside the rAF loop
  • label text and measureText width pre-computed per intersection point at init time
  • getBoundingClientRect cached; only refreshed by ResizeObserver
  • Per-point virtual-cursor state stored in typed Float64Arrays for cache locality
  • rAF loop skips all work when mouse is outside the plot (realMx === -9999)
"""

from __future__ import annotations

import json
from typing import Optional

import numpy as np
import streamlit as st
import sympy as sp
import plotly.graph_objects as go
from itertools import combinations
from scipy.optimize import brentq

# ── module-level constants ────────────────────────────────────────────────────

_X = sp.Symbol("x")
SYMPY_LOCALS: dict = {"x": _X, "e": sp.E, "pi": sp.pi}
COLORS = ["#6C63FF", "#FF6B6B", "#3ECFCF", "#F5A623", "#A8FF78"]
DEFAULTS = ["x**2", "sin(x)", "cos(x)", "x**3", "exp(x)"]

# expression cache: str → (sympy_expr, numpy_callable)
_expr_cache: dict[str, tuple[sp.Expr, object]] = {}


# ── expression helpers ────────────────────────────────────────────────────────

def _compile(expr_str: str) -> tuple[sp.Expr, object]:
    """Return (sympy_expr, lambdified_fn) — cached by expression string."""
    if expr_str not in _expr_cache:
        expr = sp.sympify(expr_str, locals=SYMPY_LOCALS)
        fn   = sp.lambdify(_X, expr, modules=["numpy"])
        _expr_cache[expr_str] = (expr, fn)
    return _expr_cache[expr_str]


def safe_eval(expr_str: str, x_vals: np.ndarray) -> tuple[np.ndarray, sp.Expr]:
    expr, fn = _compile(expr_str)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = fn(x_vals)
    # lambdify may return a scalar for constant expressions
    if np.ndim(y) == 0:
        y = np.full_like(x_vals, float(y))
    return np.where(np.isfinite(y), y, np.nan), expr


def _fmt(v: float) -> str:
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else f"{v:.6g}"


# ── intersection finding ──────────────────────────────────────────────────────

def _dedup(pts: list[tuple[float, float]], tol: float = 1e-6) -> list[tuple[float, float]]:
    """O(n log n) deduplication by sorting on x then merging close neighbours."""
    if not pts:
        return pts
    pts_sorted = sorted(pts, key=lambda p: p[0])
    unique = [pts_sorted[0]]
    for p in pts_sorted[1:]:
        q = unique[-1]
        if abs(p[0] - q[0]) > tol or abs(p[1] - q[1]) > tol:
            unique.append(p)
    return unique


def find_intersections(
    expr_str_a: str,
    expr_str_b: str,
    x_min: float,
    x_max: float,
) -> list[tuple[float, float]]:
    """
    Return (x, y) intersection points of two expressions over [x_min, x_max].
    Strategy:
      1. Symbolic solve (exact, fast for polynomials / simple trig)
      2. Vectorised sign-change scan + Brent's method (handles transcendental pairs)
    """
    expr_a, fn_a = _compile(expr_str_a)
    expr_b, fn_b = _compile(expr_str_b)
    diff_expr    = expr_a - expr_b          # no simplify — solve handles it fine
    points: list[tuple[float, float]] = []

    # ── 1. symbolic ──────────────────────────────────────────
    try:
        sols = sp.solve(diff_expr, _X)
        sym_pts = []
        for sol in sols:
            if not sol.is_real:
                continue
            xv = float(sol)
            if x_min <= xv <= x_max:
                try:
                    yv = float(expr_a.subs(_X, sol))
                    if np.isfinite(yv):
                        sym_pts.append((xv, yv))
                except Exception:
                    pass
        if sym_pts:
            return _dedup(sym_pts)
    except Exception:
        pass

    # ── 2. numerical (vectorised scan + Brent) ───────────────
    try:
        xs = np.linspace(x_min, x_max, 2000)
        with np.errstate(divide="ignore", invalid="ignore"):
            ya = fn_a(xs)
            yb = fn_b(xs)
        # scalar guard
        if np.ndim(ya) == 0: ya = np.full_like(xs, float(ya))
        if np.ndim(yb) == 0: yb = np.full_like(xs, float(yb))

        diff_vals = np.where(np.isfinite(ya) & np.isfinite(yb), ya - yb, np.nan)

        # indices where a sign change occurs between consecutive finite samples
        finite   = np.isfinite(diff_vals)
        sign_chg = np.where(
            finite[:-1] & finite[1:] & (diff_vals[:-1] * diff_vals[1:] < 0)
        )[0]

        diff_fn = sp.lambdify(_X, diff_expr, modules=["numpy"])

        for k in sign_chg:
            try:
                xr = brentq(diff_fn, xs[k], xs[k + 1], xtol=1e-10)
                yr = float(fn_a(xr))
                if np.isfinite(yr):
                    points.append((xr, yr))
            except Exception:
                pass
    except Exception:
        pass

    return _dedup(points)


# ── JS overlay ────────────────────────────────────────────────────────────────

def _intersection_overlay(overlay_points: list[dict]) -> None:
    """
    Inject a <script> directly into the Streamlit page DOM (same document as
    Plotly — avoids iframe isolation).  Pre-computes per-point label text and
    caches the canvas context outside the rAF loop.
    """
    payload = json.dumps(overlay_points)
    script = f"""
<script>
(function() {{
  const PTS       = {payload};
  const SNAP_PX   = 48;
  const PULL_SPD  = 0.11;
  const RESET_PX  = 62;
  const TWO_PI    = Math.PI * 2;

  function init() {{
    const plots = document.querySelectorAll('.js-plotly-plot');
    if (!plots.length) {{ setTimeout(init, 400); return; }}
    const gd = plots[plots.length - 1];

    // ── canvas (created once) ─────────────────────────────
    const old = gd.parentElement.querySelector('canvas.__ix');
    if (old) old.remove();
    const cv = document.createElement('canvas');
    cv.className = '__ix';
    cv.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:9999;';
    gd.parentElement.style.position = 'relative';
    gd.parentElement.appendChild(cv);

    // cache context — never call getContext inside rAF
    const ctx = cv.getContext('2d');

    // cached bounding rect — refreshed only on resize
    let rect = gd.getBoundingClientRect();
    function resize() {{
      rect = gd.getBoundingClientRect();
      cv.width  = rect.width;
      cv.height = rect.height;
    }}
    resize();
    new ResizeObserver(resize).observe(gd);

    // ── pre-compute per-point label text & width ──────────
    // avoids measureText + split on every draw frame
    const labels = PTS.map(pt => pt.label.split('\\n')[0]);
    ctx.font = '11px monospace';
    const labelWidths = labels.map(t => ctx.measureText(t).width);

    // ── typed arrays for virtual-cursor state ─────────────
    const n   = PTS.length;
    const vcx = new Float64Array(n);
    const vcy = new Float64Array(n);
    const inZone   = new Uint8Array(n);
    const resisted = new Uint8Array(n);
    const active   = new Uint8Array(n);

    let realMx = -9999, realMy = -9999;

    // ── data → pixel (inline, no allocation) ─────────────
    function toPixel(xd, yd, out) {{
      try {{
        const xa = gd._fullLayout.xaxis;
        const ya = gd._fullLayout.yaxis;
        out[0] = xa.l2p(xd) + xa._offset;
        out[1] = ya.l2p(yd) + ya._offset;
        return true;
      }} catch(e) {{ return false; }}
    }}
    const _pxBuf = new Float64Array(2);   // reusable output buffer

    // ── draw one highlight (ctx state already set up) ─────
    function drawHighlight(cx, cy, idx) {{
      // glow
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 24);
      g.addColorStop(0,   'rgba(108,99,255,0.62)');
      g.addColorStop(0.4, 'rgba(108,99,255,0.22)');
      g.addColorStop(1,   'rgba(108,99,255,0)');
      ctx.beginPath();
      ctx.arc(cx, cy, 24, 0, TWO_PI);
      ctx.fillStyle = g;
      ctx.fill();

      // ring
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, TWO_PI);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth   = 2;
      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur  = 14;
      ctx.stroke();
      ctx.shadowBlur  = 0;

      // centre
      ctx.beginPath();
      ctx.arc(cx, cy, 2.5, 0, TWO_PI);
      ctx.fillStyle = '#ffffff';
      ctx.fill();

      // label pill (pre-computed width)
      const tw = labelWidths[idx];
      const pad = 5, bh = 17;
      const bx = cx + 12, by = cy - 9;
      ctx.fillStyle   = 'rgba(13,13,13,0.92)';
      ctx.strokeStyle = 'rgba(255,255,255,0.20)';
      ctx.lineWidth   = 0.8;
      ctx.beginPath();
      ctx.roundRect(bx, by, tw + pad * 2, bh, 4);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#e8e4dc';
      ctx.font      = '11px monospace';
      ctx.fillText(labels[idx], bx + pad, by + 12);
    }}

    // ── rAF loop ──────────────────────────────────────────
    function frame() {{
      requestAnimationFrame(frame);

      // skip entirely when mouse is outside the plot
      if (realMx === -9999) {{
        ctx.clearRect(0, 0, cv.width, cv.height);
        return;
      }}

      ctx.clearRect(0, 0, cv.width, cv.height);

      for (let i = 0; i < n; i++) {{
        if (!toPixel(PTS[i].x, PTS[i].y, _pxBuf)) continue;
        const px = _pxBuf[0], py = _pxBuf[1];
        const dx = realMx - px, dy = realMy - py;
        const dist = Math.sqrt(dx * dx + dy * dy);   // hypot without allocation

        if (dist < SNAP_PX && !resisted[i]) {{
          if (!inZone[i]) {{
            inZone[i] = 1; active[i] = 1;
            vcx[i] = realMx; vcy[i] = realMy;
          }}
          if (active[i]) {{
            vcx[i] += (px - vcx[i]) * PULL_SPD;
            vcy[i] += (py - vcy[i]) * PULL_SPD;
            const sd = Math.sqrt((vcx[i]-px)**2 + (vcy[i]-py)**2);
            if (sd < 1) {{ vcx[i] = px; vcy[i] = py; }}
            drawHighlight(vcx[i], vcy[i], i);
          }}
        }} else {{
          if (inZone[i]) {{
            const sd = Math.sqrt((vcx[i]-px)**2 + (vcy[i]-py)**2);
            if (active[i] && sd > 5) resisted[i] = 1;
            inZone[i] = 0; active[i] = 0;
          }}
          if (dist > RESET_PX) resisted[i] = 0;
        }}
      }}
    }}
    requestAnimationFrame(frame);

    // ── mouse events ──────────────────────────────────────
    gd.addEventListener('mousemove', e => {{
      realMx = e.clientX - rect.left;
      realMy = e.clientY - rect.top;
    }});
    gd.addEventListener('mouseleave', () => {{
      realMx = -9999; realMy = -9999;
      inZone.fill(0); active.fill(0); resisted.fill(0);
    }});
  }}

  setTimeout(init, 800);
}})();
</script>
"""
    st.markdown(script, unsafe_allow_html=True)


# ── main module ───────────────────────────────────────────────────────────────

def graphing_module() -> None:
    st.title("∿ Graphing & Conics")
    st.markdown(
        "Plot functions interactively — **scroll to zoom**, **drag to pan**. "
        "Move near an intersection to feel it snap and see the exact coordinates."
    )
    st.info(
        "**Syntax:** Use `x` as variable. "
        "Examples: `x**2`, `sin(x)`, `exp(-x)*cos(x)`, `1/x`, `sqrt(4 - x**2)`"
    )

    # ── inputs ────────────────────────────────────────────────
    num_funcs = st.number_input("Number of functions", min_value=1, max_value=5, value=1, step=1)

    func_inputs: list[str] = []
    labels:      list[str] = []

    for i in range(int(num_funcs)):
        c1, c2 = st.columns([3, 1])
        with c1:
            fi = st.text_input(f"f{i+1}(x)", value=DEFAULTS[i % 5], key=f"func_{i}")
        with c2:
            lb = st.text_input("Label", value=f"f{i+1}(x)", key=f"label_{i}")
        func_inputs.append(fi)
        labels.append(lb)

    st.markdown("#### Initial View")
    c1, c2, c3, c4 = st.columns(4)
    x_min = c1.number_input("x min", value=-10.0, format="%.2f")
    x_max = c2.number_input("x max", value=10.0,  format="%.2f")
    y_min = c3.number_input("y min", value=-10.0, format="%.2f")
    y_max = c4.number_input("y max", value=10.0,  format="%.2f")

    c5, c6, c7 = st.columns(3)
    show_grid         = c5.checkbox("Show grid",                  value=True)
    show_deriv        = c6.checkbox("Show derivative expressions", value=True)
    show_intersections= c7.checkbox("Show intersections",         value=True)

    if not st.button("Plot", type="primary"):
        return

    if x_min >= x_max:
        st.error("x min must be less than x max.")
        return

    # ── evaluate functions ────────────────────────────────────
    x_vals = np.linspace(x_min, x_max, 1500)
    fig    = go.Figure()
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.12)", width=1))
    fig.add_vline(x=0, line=dict(color="rgba(255,255,255,0.12)", width=1))

    # parsed_exprs: index → sympy expr (reused for intersections + derivatives)
    parsed_exprs: dict[int, sp.Expr] = {}
    plotted = 0

    for i, (fs, lb) in enumerate(zip(func_inputs, labels)):
        fs = fs.strip()
        if not fs:
            continue
        try:
            y_vals, expr = safe_eval(fs, x_vals)
            parsed_exprs[i] = expr
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines",
                name=lb,
                line=dict(color=COLORS[i % len(COLORS)], width=2.5),
                connectgaps=False,
                marker=dict(size=4, color=COLORS[i % len(COLORS)]),
                hovertemplate="(%{x:.2f}, %{y:.2f})<extra></extra>",
            ))
            plotted += 1
        except Exception as e:
            st.warning(f"Could not plot f{i+1}: {e}")

    if plotted == 0:
        st.error("No valid functions to plot.")
        return

    # ── intersections ─────────────────────────────────────────
    all_intersections: list[dict] = []
    overlay_points:    list[dict] = []

    if show_intersections and len(parsed_exprs) >= 2:
        pairs    = list(combinations(parsed_exprs.keys(), 2))
        progress = st.progress(0, text="Finding intersections…")

        for step, (i, j) in enumerate(pairs):
            li, lj = labels[i], labels[j]
            # reuse already-compiled expression strings from the cache key
            fs_i = func_inputs[i].strip()
            fs_j = func_inputs[j].strip()
            try:
                pts = find_intersections(fs_i, fs_j, x_min, x_max)
            except Exception:
                pts = []

            for xv, yv in pts:
                lbl = f"({_fmt(xv)}, {_fmt(yv)})\n{li} ∩ {lj}"
                overlay_points.append({"x": xv, "y": yv, "label": lbl})
                all_intersections.append({"Functions": f"{li} ∩ {lj}",
                                          "x": _fmt(xv), "y": _fmt(yv)})

            progress.progress((step + 1) / len(pairs), text="Finding intersections…")

        progress.empty()
        if not overlay_points:
            st.info("No intersections found in the current view window.")

    # ── layout ────────────────────────────────────────────────
    axis_common = dict(
        showgrid=show_grid, gridcolor="#1e1e1e", gridwidth=1,
        zeroline=False, fixedrange=False,
        color="#555", tickfont=dict(color="#555"),
    )
    fig.update_layout(
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#111111",
        font=dict(family="Inter, sans-serif", color="#e8e4dc", size=12),
        xaxis=dict(**axis_common, range=[x_min, x_max],
                   title=dict(text="x", font=dict(color="#666"))),
        yaxis=dict(**axis_common, range=[y_min, y_max],
                   title=dict(text="y", font=dict(color="#666"))),
        legend=dict(bgcolor="rgba(17,17,17,0.85)", bordercolor="#252525",
                    borderwidth=1, font=dict(color="#e8e4dc")),
        hovermode="closest",
        hoverdistance=30,
        hoverlabel=dict(bgcolor="#1a1a1a", bordercolor="#333",
                        font=dict(family="Inter, monospace", size=11, color="#e8e4dc"),
                        namelength=0),
        margin=dict(l=48, r=24, t=32, b=48),
        height=540,
        dragmode="pan",
        modebar=dict(bgcolor="rgba(0,0,0,0)", color="#555", activecolor="#6C63FF"),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
            "modeBarButtonsToAdd": ["resetScale2d"],
            "toImageButtonOptions": {"format": "png", "scale": 2},
        },
    )

    if show_intersections and overlay_points:
        _intersection_overlay(overlay_points)

    st.caption("🖱 Scroll to zoom · Drag to pan · Double-click to reset · Move near an intersection to snap")

    if show_intersections and all_intersections:
        st.markdown("#### Intersection Points")
        st.dataframe(all_intersections, use_container_width=True, hide_index=True)

    # ── symbolic expressions (reuse parsed_exprs — no re-parse) ──
    if show_deriv:
        st.markdown("#### Symbolic Expressions")
        for i, fs in enumerate(func_inputs):
            fs = fs.strip()
            if not fs or i not in parsed_exprs:
                continue
            try:
                expr  = parsed_exprs[i]
                deriv = sp.diff(expr, _X)
                st.latex(
                    rf"f_{{{i+1}}}(x) = {sp.latex(expr)}, \quad "
                    rf"f'_{{{i+1}}}(x) = {sp.latex(deriv)}"
                )
            except Exception:
                pass
