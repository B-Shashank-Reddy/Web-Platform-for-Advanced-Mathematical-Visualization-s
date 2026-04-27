"""
area.py — Area Visualizer
New features
────────────
• Double-click between two intersection points → shades + shows area of that sub-region
• Draw mode: freehand-draw a closed region on the canvas → shoelace area shown instantly
• 2-4 curves, optional bounds, pairwise shading, ratios, intersection table
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
import streamlit as st
import sympy as sp
import plotly.graph_objects as go
from scipy.optimize import brentq
from scipy import integrate as sci_int

# ── constants ─────────────────────────────────────────────────────────────────
_X = sp.Symbol("x")
_LOCALS: dict = {"x": _X, "e": sp.E, "pi": sp.pi}
CURVE_COLORS = ["#6C63FF", "#FF6B6B", "#3ECFCF", "#F5A623"]
REGION_COLORS = [
    "rgba(108,99,255,0.18)", "rgba(255,107,107,0.18)",
    "rgba(62,207,207,0.18)",  "rgba(245,166,35,0.18)",
    "rgba(168,255,120,0.18)", "rgba(255,200,100,0.18)",
]
_cache: dict[str, tuple[sp.Expr, object]] = {}

# ── math helpers ──────────────────────────────────────────────────────────────
def _compile(s: str) -> tuple[sp.Expr, object]:
    if s not in _cache:
        expr = sp.sympify(s, locals=_LOCALS)
        fn   = sp.lambdify(_X, expr, modules=["numpy"])
        _cache[s] = (expr, fn)
    return _cache[s]

def _eval(s: str, xs: np.ndarray) -> np.ndarray:
    _, fn = _compile(s)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = fn(xs)
    if np.ndim(y) == 0:
        y = np.full_like(xs, float(y), dtype=float)
    return np.where(np.isfinite(y), y, np.nan)

def _fmt(v: float) -> str:
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else f"{v:.5g}"

def _find_roots(sa: str, sb: str, x0: float, x1: float) -> list[float]:
    ea, _ = _compile(sa)
    eb, _ = _compile(sb)
    diff  = ea - eb
    try:
        sols = sp.solve(diff, _X)
        out  = sorted({float(s) for s in sols if s.is_real and x0 <= float(s) <= x1})
        if out:
            return out
    except Exception:
        pass
    try:
        fn = sp.lambdify(_X, diff, modules=["numpy"])
        xs = np.linspace(x0, x1, 3000)
        with np.errstate(divide="ignore", invalid="ignore"):
            dv = fn(xs)
        if np.ndim(dv) == 0:
            return []
        dv = np.where(np.isfinite(dv), dv, np.nan)
        fin = np.isfinite(dv)
        idx = np.where(fin[:-1] & fin[1:] & (dv[:-1] * dv[1:] < 0))[0]
        roots = []
        for k in idx:
            try:
                roots.append(round(brentq(fn, xs[k], xs[k+1], xtol=1e-10), 10))
            except Exception:
                pass
        return sorted(set(roots))
    except Exception:
        return []

def _area_between(sa: str, sb: str, x0: float, x1: float) -> tuple[float, str]:
    ea, _ = _compile(sa)
    eb, _ = _compile(sb)
    try:
        val = float(sp.integrate(sp.Abs(ea - eb), (_X, x0, x1)))
        if np.isfinite(val):
            return val, "exact"
    except Exception:
        pass
    try:
        _, fa = _compile(sa)
        _, fb = _compile(sb)
        def ig(xv):
            with np.errstate(divide="ignore", invalid="ignore"):
                v = abs(float(fa(xv)) - float(fb(xv)))
            return v if np.isfinite(v) else 0.0
        val, _ = sci_int.quad(ig, x0, x1, limit=200)
        return val, "numerical"
    except Exception:
        return float("nan"), "failed"

# ── JS: double-click sub-region + draw mode ───────────────────────────────────
def _interactive_js(intersections_json: str, curves_json: str) -> None:
    """
    Injects two independent behaviours into the Streamlit page DOM:

    1. DOUBLE-CLICK SUB-REGION
       - On dblclick, finds the two nearest intersection x-values that bracket
         the click x-position.
       - Shades that sub-region on the plot via Plotly.relayout shapes.
       - Computes the approximate area using the trapezoidal rule on the
         pre-sampled curve data passed in curves_json, then shows a floating
         badge near the click position.

    2. DRAW MODE (toggle button injected below the chart)
       - A canvas overlay is placed over the Plotly div.
       - While draw mode is on, mousedown starts a path; mousemove extends it;
         mouseup closes it if the endpoint is within CLOSE_PX of the start.
       - On close, the shoelace formula gives the polygon area in pixel² which
         is converted to data-unit² using the current axis scale.
       - Result shown in a floating badge on the canvas.
    """
    script = f"""
<script>
(function() {{
  const IX_DATA    = {intersections_json};   // [{{x, pair}}]
  const CURVE_DATA = {curves_json};          // [{{xs:[], ys:[]}}]
  const CLOSE_PX   = 18;

  /* ── trapezoid area between two curves over [x0,x1] using sampled data ── */
  function approxAreaBetween(x0, x1) {{
    if (CURVE_DATA.length < 2) return null;
    // use first two curves for the sub-region area
    const c0 = CURVE_DATA[0], c1 = CURVE_DATA[1];
    const xs0 = c0.xs, ys0 = c0.ys;
    const xs1 = c1.xs, ys1 = c1.ys;
    // filter to [x0,x1]
    let area = 0, prev = null;
    for (let k = 0; k < xs0.length; k++) {{
      const xk = xs0[k];
      if (xk < x0 || xk > x1) continue;
      // interpolate c1 at xk
      let y1k = NaN;
      for (let m = 0; m < xs1.length - 1; m++) {{
        if (xs1[m] <= xk && xk <= xs1[m+1]) {{
          const t = (xk - xs1[m]) / (xs1[m+1] - xs1[m]);
          y1k = ys1[m] + t * (ys1[m+1] - ys1[m]);
          break;
        }}
      }}
      const diff = isFinite(ys0[k]) && isFinite(y1k) ? Math.abs(ys0[k] - y1k) : 0;
      if (prev !== null) {{
        area += (diff + prev.diff) * 0.5 * (xk - prev.x);
      }}
      prev = {{x: xk, diff}};
    }}
    return area;
  }}

  /* ── shoelace polygon area ── */
  function shoelace(pts) {{
    let s = 0;
    const n = pts.length;
    for (let i = 0; i < n; i++) {{
      const j = (i + 1) % n;
      s += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1];
    }}
    return Math.abs(s) / 2;
  }}

  /* ── pixel → data coords ── */
  function px2data(gd, px, py) {{
    try {{
      const xa = gd._fullLayout.xaxis;
      const ya = gd._fullLayout.yaxis;
      return [xa.p2l(px - xa._offset), ya.p2l(py - ya._offset)];
    }} catch(e) {{ return [NaN, NaN]; }}
  }}

  /* ── floating badge ── */
  function showBadge(container, cx, cy, html, color) {{
    let badge = container.querySelector('.__area_badge');
    if (!badge) {{
      badge = document.createElement('div');
      badge.className = '__area_badge';
      badge.style.cssText = `
        position:absolute;pointer-events:none;z-index:10000;
        background:rgba(13,13,13,0.93);border:1px solid rgba(255,255,255,0.18);
        border-radius:8px;padding:7px 12px;font:12px monospace;
        color:#e8e4dc;white-space:nowrap;transition:opacity 0.2s;
      `;
      container.appendChild(badge);
    }}
    badge.innerHTML = html;
    badge.style.left = (cx + 14) + 'px';
    badge.style.top  = (cy - 14) + 'px';
    badge.style.borderColor = color || 'rgba(255,255,255,0.18)';
    badge.style.opacity = '1';
    clearTimeout(badge.__timer);
    badge.__timer = setTimeout(() => {{ badge.style.opacity = '0'; }}, 5000);
  }}

  function init() {{
    const plots = document.querySelectorAll('.js-plotly-plot');
    if (!plots.length) {{ setTimeout(init, 400); return; }}
    const gd = plots[plots.length - 1];
    const wrapper = gd.parentElement;
    wrapper.style.position = 'relative';

    /* ════════════════════════════════════════════════
       1. DOUBLE-CLICK SUB-REGION
    ════════════════════════════════════════════════ */
    gd.on('plotly_doubleclick', function() {{
      // plotly_doubleclick doesn't carry coords; use last mousemove position
      const xClick = gd.__lastX;
      if (xClick === undefined) return;

      const ixXs = IX_DATA.map(p => p.x).sort((a,b) => a-b);
      if (ixXs.length < 2) return;

      // find bracketing pair
      let lo = null, hi = null;
      for (let k = 0; k < ixXs.length - 1; k++) {{
        if (ixXs[k] <= xClick && xClick <= ixXs[k+1]) {{
          lo = ixXs[k]; hi = ixXs[k+1]; break;
        }}
      }}
      if (lo === null) {{
        // outside all intersections — use nearest two
        lo = ixXs[0]; hi = ixXs[1];
      }}

      // shade sub-region
      const existingShapes = (gd.layout.shapes || [])
        .filter(s => !s.__subregion);
      const newShape = {{
        type:'rect', x0:lo, x1:hi, y0:0, y1:1, yref:'paper',
        fillcolor:'rgba(108,99,255,0.12)',
        line:{{color:'rgba(108,99,255,0.6)', width:1.5, dash:'dot'}},
        __subregion: true
      }};
      Plotly.relayout(gd, {{ shapes: [...existingShapes, newShape] }});

      // compute area
      const area = approxAreaBetween(lo, hi);
      const areaStr = area !== null ? area.toFixed(5) + ' sq.u' : '—';

      // find pixel position of click
      try {{
        const xa = gd._fullLayout.xaxis;
        const ya = gd._fullLayout.yaxis;
        const midX = (lo + hi) / 2;
        const px = xa.l2p(midX) + xa._offset;
        const py = ya.l2p(0)    + ya._offset;
        showBadge(wrapper, px, py,
          '<b>Sub-region</b> [' + lo.toFixed(4) + ' → ' + hi.toFixed(4) + ']<br>' +
          'Area ≈ ' + areaStr,
          'rgba(108,99,255,0.7)');
      }} catch(e) {{}}
    }});

    // track last mouse x in data coords
    gd.addEventListener('mousemove', function(e) {{
      try {{
        const r = gd.getBoundingClientRect();
        const xa = gd._fullLayout.xaxis;
        gd.__lastX = xa.p2l(e.clientX - r.left - xa._offset);
      }} catch(e) {{}}
    }});

    /* ════════════════════════════════════════════════
       2. DRAW MODE
    ════════════════════════════════════════════════ */
    // canvas
    const cv = document.createElement('canvas');
    cv.className = '__draw_cv';
    cv.style.cssText =
      'position:absolute;top:0;left:0;pointer-events:none;z-index:9998;';
    wrapper.appendChild(cv);
    const ctx = cv.getContext('2d');

    function resizeCv() {{
      const r = gd.getBoundingClientRect();
      cv.width  = r.width;
      cv.height = r.height;
    }}
    resizeCv();
    new ResizeObserver(resizeCv).observe(gd);

    // inject toggle button
    const btn = document.createElement('button');
    btn.textContent = '✏ Draw Region';
    btn.style.cssText = `
      margin-top:8px;padding:7px 18px;
      background:transparent;border:1px solid #252525;border-radius:8px;
      color:#888;font:11px Inter,sans-serif;letter-spacing:1px;
      text-transform:uppercase;cursor:pointer;transition:all .15s;
    `;
    wrapper.parentElement.insertBefore(btn, wrapper.nextSibling);

    let drawMode = false;
    let drawing  = false;
    let path     = [];   // [{{px,py}}] screen coords
    let rect     = gd.getBoundingClientRect();

    new ResizeObserver(() => {{ rect = gd.getBoundingClientRect(); }}).observe(gd);

    btn.addEventListener('click', () => {{
      drawMode = !drawMode;
      cv.style.pointerEvents = drawMode ? 'all' : 'none';
      btn.style.color         = drawMode ? '#6C63FF' : '#888';
      btn.style.borderColor   = drawMode ? '#6C63FF' : '#252525';
      btn.textContent         = drawMode ? '✕ Exit Draw' : '✏ Draw Region';
      if (!drawMode) {{
        ctx.clearRect(0, 0, cv.width, cv.height);
        path = []; drawing = false;
      }}
    }});

    function drawPath() {{
      if (path.length < 2) return;
      ctx.clearRect(0, 0, cv.width, cv.height);

      // filled polygon
      ctx.beginPath();
      ctx.moveTo(path[0].px, path[0].py);
      for (let i = 1; i < path.length; i++)
        ctx.lineTo(path[i].px, path[i].py);
      ctx.closePath();
      ctx.fillStyle   = 'rgba(108,99,255,0.15)';
      ctx.strokeStyle = '#6C63FF';
      ctx.lineWidth   = 1.8;
      ctx.fill();
      ctx.stroke();

      // start dot
      ctx.beginPath();
      ctx.arc(path[0].px, path[0].py, 5, 0, Math.PI*2);
      ctx.fillStyle = '#6C63FF';
      ctx.fill();
    }}

    cv.addEventListener('mousedown', e => {{
      if (!drawMode) return;
      rect = gd.getBoundingClientRect();
      drawing = true;
      path = [{{ px: e.clientX - rect.left, py: e.clientY - rect.top }}];
      ctx.clearRect(0, 0, cv.width, cv.height);
    }});

    cv.addEventListener('mousemove', e => {{
      if (!drawMode || !drawing) return;
      path.push({{ px: e.clientX - rect.left, py: e.clientY - rect.top }});
      drawPath();

      // show close-hint when near start
      if (path.length > 10) {{
        const dx = path[path.length-1].px - path[0].px;
        const dy = path[path.length-1].py - path[0].py;
        if (Math.sqrt(dx*dx + dy*dy) < CLOSE_PX) {{
          ctx.beginPath();
          ctx.arc(path[0].px, path[0].py, CLOSE_PX, 0, Math.PI*2);
          ctx.strokeStyle = 'rgba(108,99,255,0.4)';
          ctx.lineWidth   = 1;
          ctx.stroke();
        }}
      }}
    }});

    cv.addEventListener('mouseup', e => {{
      if (!drawMode || !drawing) return;
      drawing = false;

      if (path.length < 6) {{ ctx.clearRect(0,0,cv.width,cv.height); path=[]; return; }}

      const dx = path[path.length-1].px - path[0].px;
      const dy = path[path.length-1].py - path[0].py;
      const closed = Math.sqrt(dx*dx + dy*dy) < CLOSE_PX;

      if (!closed) {{
        // not closed — show hint
        ctx.font = '11px monospace';
        ctx.fillStyle = 'rgba(245,166,35,0.9)';
        ctx.fillText('Draw back to start ● to close', path[0].px + 8, path[0].py - 8);
        return;
      }}

      // close the path visually
      path.push(path[0]);
      drawPath();

      // shoelace in pixel coords
      const pxPts = path.map(p => [p.px, p.py]);
      const pxArea = shoelace(pxPts);

      // convert px² → data units²
      let dataArea = NaN;
      try {{
        const xa = gd._fullLayout.xaxis;
        const ya = gd._fullLayout.yaxis;
        // scale: how many data units per pixel
        const xScale = Math.abs(xa.p2l(1) - xa.p2l(0));
        const yScale = Math.abs(ya.p2l(1) - ya.p2l(0));
        dataArea = pxArea * xScale * yScale;
      }} catch(e) {{}}

      const areaStr = isFinite(dataArea)
        ? dataArea.toFixed(5) + ' sq.u'
        : pxArea.toFixed(1) + ' px²';

      // centroid for badge placement
      const cx = path.reduce((s,p) => s + p.px, 0) / path.length;
      const cy = path.reduce((s,p) => s + p.py, 0) / path.length;

      showBadge(wrapper, cx, cy,
        '<b>Drawn region</b><br>Area \u2248 ' + areaStr,
        'rgba(108,99,255,0.7)');

      // keep drawing active for another region
      path = [];
    }});

    // touch support
    cv.addEventListener('touchstart', e => {{
      e.preventDefault();
      const t = e.touches[0];
      cv.dispatchEvent(new MouseEvent('mousedown',
        {{clientX:t.clientX, clientY:t.clientY}}));
    }}, {{passive:false}});
    cv.addEventListener('touchmove', e => {{
      e.preventDefault();
      const t = e.touches[0];
      cv.dispatchEvent(new MouseEvent('mousemove',
        {{clientX:t.clientX, clientY:t.clientY}}));
    }}, {{passive:false}});
    cv.addEventListener('touchend', e => {{
      e.preventDefault();
      cv.dispatchEvent(new MouseEvent('mouseup', {{}}));
    }}, {{passive:false}});
  }}

  setTimeout(init, 900);
}})();
</script>
"""
    st.markdown(script, unsafe_allow_html=True)


# ── main module ───────────────────────────────────────────────────────────────
def area_module() -> None:
    st.title("⌗ Area Visualizer")
    st.markdown(
        "Plot up to **4 curves**, compare enclosed areas, and explore regions interactively.  \n"
        "**Double-click** between two intersections to see that sub-region's area.  \n"
        "Use **✏ Draw Region** to freehand-draw any closed region and get its area instantly."
    )
    st.info(
        "**Syntax:** `x**2`, `sin(x)`, `exp(x)`, `sqrt(x)`, `log(x)` …  "
        "Leave bounds at 0 to auto-detect from intersections."
    )

    # ── curve inputs ──────────────────────────────────────────
    num = int(st.number_input("Number of curves", min_value=2, max_value=4, value=2, step=1))
    defaults = ["x**2", "x + 2", "sin(x)*3", "sqrt(x)*2"]
    curves: list[str] = []
    for col, i in zip(st.columns(num), range(num)):
        with col:
            curves.append(st.text_input(f"f{i+1}(x)", value=defaults[i], key=f"af{i}").strip())

    # ── view window ───────────────────────────────────────────
    st.markdown("#### View Window")
    vc = st.columns(4)
    vx_min = vc[0].number_input("x min", value=-5.0,  format="%.2f", key="avxn")
    vx_max = vc[1].number_input("x max", value=5.0,   format="%.2f", key="avxx")
    vy_min = vc[2].number_input("y min", value=-5.0,  format="%.2f", key="avyn")
    vy_max = vc[3].number_input("y max", value=15.0,  format="%.2f", key="avyx")

    # ── region bounds ─────────────────────────────────────────
    st.markdown("#### Region Bounds *(leave both 0 → auto-detect from intersections)*")
    bc = st.columns([2, 2, 3])
    bound_a = bc[0].number_input("Left bound (a)",  value=0.0, format="%.4f", key="aba")
    bound_b = bc[1].number_input("Right bound (b)", value=0.0, format="%.4f", key="abb")
    auto_bounds = abs(bound_a - bound_b) < 1e-12
    with bc[2]:
        st.markdown("<br>", unsafe_allow_html=True)
        shade_all = st.checkbox("Shade all pairwise regions", value=True)

    method_sym = st.radio(
        "Integration method",
        ["Symbolic (exact)", "Numerical (SciPy)"],
        horizontal=True, key="ameth"
    )

    if not st.button("Plot & Compute", type="primary", key="aplot"):
        return

    valid = [c for c in curves if c]
    if len(valid) < 2:
        st.error("Enter at least 2 functions.")
        return
    if vx_min >= vx_max:
        st.error("x min must be less than x max.")
        return

    # ── compile ───────────────────────────────────────────────
    compiled: list[tuple[str, sp.Expr, object]] = []
    for s in valid:
        try:
            expr, fn = _compile(s)
            compiled.append((s, expr, fn))
        except Exception as e:
            st.error(f"Cannot parse `{s}`: {e}")
            return
    n = len(compiled)

    x_plot = np.linspace(vx_min, vx_max, 1200)

    # ── intersections ─────────────────────────────────────────
    all_roots: dict[tuple[int,int], list[float]] = {}
    for i, j in combinations(range(n), 2):
        all_roots[(i,j)] = _find_roots(compiled[i][0], compiled[j][0], vx_min, vx_max)

    # ── resolve bounds ────────────────────────────────────────
    if auto_bounds:
        flat = sorted({r for rs in all_roots.values() for r in rs})
        if len(flat) >= 2:
            a_eff, b_eff = flat[0], flat[-1]
            st.info(f"Auto bounds: a = {_fmt(a_eff)},  b = {_fmt(b_eff)}")
        elif len(flat) == 1:
            span = (vx_max - vx_min) * 0.25
            a_eff, b_eff = flat[0] - span, flat[0] + span
            st.info(f"One intersection — using ±{span:.2f} around it.")
        else:
            a_eff, b_eff = vx_min, vx_max
            st.info("No intersections found — using full view window.")
    else:
        if bound_a >= bound_b:
            st.error("Left bound must be less than right bound.")
            return
        a_eff, b_eff = bound_a, bound_b

    x_region = np.linspace(a_eff, b_eff, 1200)

    # ── figure ────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.10)", width=1))
    fig.add_vline(x=0, line=dict(color="rgba(255,255,255,0.10)", width=1))
    fig.add_vline(x=a_eff, line=dict(color="rgba(255,255,255,0.30)", width=1.2, dash="dot"))
    fig.add_vline(x=b_eff, line=dict(color="rgba(255,255,255,0.30)", width=1.2, dash="dot"))

    # ── pairwise shaded fills ─────────────────────────────────
    pair_areas: list[dict] = []
    for ridx, (i, j) in enumerate(combinations(range(n), 2)):
        si, _, _ = compiled[i]
        sj, _, _ = compiled[j]
        yi = _eval(si, x_region)
        yj = _eval(sj, x_region)
        valid_mask = np.isfinite(yi) & np.isfinite(yj)

        if shade_all and valid_mask.any():
            xv = x_region[valid_mask]
            fig.add_trace(go.Scatter(
                x=np.concatenate([xv, xv[::-1]]),
                y=np.concatenate([np.maximum(yi[valid_mask], yj[valid_mask]),
                                  np.minimum(yi[valid_mask], yj[valid_mask])[::-1]]),
                fill="toself",
                fillcolor=REGION_COLORS[ridx % len(REGION_COLORS)],
                line=dict(width=0),
                name=f"Region f{i+1}∩f{j+1}",
                showlegend=True,
                hoverinfo="skip",
            ))

        # area computation
        if "Symbolic" in method_sym:
            val, meth = _area_between(si, sj, a_eff, b_eff)
        else:
            try:
                _, fni = _compile(si)
                _, fnj = _compile(sj)
                def _ig(xv, _fni=fni, _fnj=fnj):
                    with np.errstate(divide="ignore", invalid="ignore"):
                        v = abs(float(_fni(xv)) - float(_fnj(xv)))
                    return v if np.isfinite(v) else 0.0
                val, _ = sci_int.quad(_ig, a_eff, b_eff, limit=200)
                meth = "numerical"
            except Exception:
                val, meth = float("nan"), "failed"

        pair_areas.append({"label": f"f{i+1} & f{j+1}", "area": val, "method": meth})

    # ── curves ────────────────────────────────────────────────
    for i, (s, expr, fn) in enumerate(compiled):
        fig.add_trace(go.Scatter(
            x=x_plot,
            y=_eval(s, x_plot),
            mode="lines",
            name=f"f{i+1}(x) = {s}",
            line=dict(color=CURVE_COLORS[i % len(CURVE_COLORS)], width=2.5),
            connectgaps=False,
            marker=dict(size=4),
            hovertemplate=f"<b>f{i+1}</b>: (%{{x:.3f}}, %{{y:.3f}})<extra></extra>",
        ))

    # ── intersection markers ──────────────────────────────────
    ix_x, ix_y, ix_txt = [], [], []
    for (i, j), roots in all_roots.items():
        _, _, fni = compiled[i]
        for xr in roots:
            try:
                yr = float(fni(xr))
                if np.isfinite(yr):
                    ix_x.append(xr); ix_y.append(yr)
                    ix_txt.append(f"f{i+1} ∩ f{j+1}<br>({_fmt(xr)}, {_fmt(yr)})")
            except Exception:
                pass
    if ix_x:
        fig.add_trace(go.Scatter(
            x=ix_x, y=ix_y, mode="markers", name="Intersections",
            marker=dict(size=8, color="#ffffff", line=dict(color="#6C63FF", width=2)),
            hovertemplate="%{text}<extra></extra>", text=ix_txt,
        ))

    # ── layout ────────────────────────────────────────────────
    ax = dict(showgrid=True, gridcolor="#1e1e1e", gridwidth=1,
              zeroline=False, fixedrange=False, color="#555",
              tickfont=dict(color="#555"))
    fig.update_layout(
        paper_bgcolor="#0d0d0d", plot_bgcolor="#111111",
        font=dict(family="Inter, sans-serif", color="#e8e4dc", size=12),
        xaxis=dict(**ax, range=[vx_min, vx_max],
                   title=dict(text="x", font=dict(color="#666"))),
        yaxis=dict(**ax, range=[vy_min, vy_max],
                   title=dict(text="y", font=dict(color="#666"))),
        legend=dict(bgcolor="rgba(17,17,17,0.85)", bordercolor="#252525",
                    borderwidth=1, font=dict(color="#e8e4dc")),
        hovermode="closest", hoverdistance=20,
        hoverlabel=dict(bgcolor="#1a1a1a", bordercolor="#333",
                        font=dict(family="Inter, monospace", size=11, color="#e8e4dc"),
                        namelength=0),
        margin=dict(l=48, r=24, t=36, b=48), height=520,
        dragmode="pan",
        modebar=dict(bgcolor="rgba(0,0,0,0)", color="#555", activecolor="#6C63FF"),
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        "modeBarButtonsToAdd": ["resetScale2d"],
        "toImageButtonOptions": {"format": "png", "scale": 2},
    })

    # ── inject interactive JS ─────────────────────────────────
    # build intersection list for JS
    ix_js = []
    for (i, j), roots in all_roots.items():
        for xr in roots:
            ix_js.append({"x": xr, "pair": f"f{i+1}∩f{j+1}"})

    # build sampled curve data for JS area approximation
    curves_js = []
    for s, _, _ in compiled:
        ys = _eval(s, x_plot)
        curves_js.append({
            "xs": [round(float(v), 6) for v in x_plot],
            "ys": [round(float(v), 6) if np.isfinite(v) else None for v in ys],
        })

    import json
    _interactive_js(json.dumps(ix_js), json.dumps(curves_js))

    st.caption(
        f"🖱 Scroll/zoom · Drag pan · **Double-click** between intersections for sub-region area · "
        f"**✏ Draw Region** to freehand any area  |  "
        f"Region: x ∈ [{_fmt(a_eff)}, {_fmt(b_eff)}]"
    )

    # ── results ───────────────────────────────────────────────
    st.markdown("#### Area Results")
    total = sum(p["area"] for p in pair_areas if np.isfinite(p["area"]))
    rows = []
    for p in pair_areas:
        av = p["area"]
        rows.append({
            "Pair": p["label"],
            "Area (sq. units)": f"{av:.6f}" if np.isfinite(av) else "—",
            "% of total": f"{av/total*100:.1f}%" if (np.isfinite(av) and total > 0) else "—",
            "Method": p["method"],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    valid_p = [p for p in pair_areas if np.isfinite(p["area"]) and p["area"] > 1e-12]
    if len(valid_p) >= 2:
        st.markdown("#### Area Ratios")
        base = valid_p[0]
        for col, p in zip(st.columns(len(valid_p)), valid_p):
            col.metric(f"{p['label']} / {base['label']}",
                       f"{p['area']/base['area']:.4f}")

    # intersection table
    ix_rows = []
    for (i, j), roots in all_roots.items():
        _, _, fni = compiled[i]
        for xr in roots:
            try:
                yr = float(fni(xr))
                ix_rows.append({"Curves": f"f{i+1} ∩ f{j+1}",
                                 "x": _fmt(xr),
                                 "y": _fmt(yr) if np.isfinite(yr) else "—"})
            except Exception:
                pass
    if ix_rows:
        st.markdown("#### Intersection Points")
        st.dataframe(ix_rows, use_container_width=True, hide_index=True)

    with st.expander("Symbolic expressions & antiderivatives"):
        for i, (s, expr, _) in enumerate(compiled):
            try:
                ad = sp.integrate(expr, _X)
                st.latex(rf"f_{{{i+1}}}(x)={sp.latex(expr)},\quad"
                         rf"\int f_{{{i+1}}}\,dx={sp.latex(ad)}+C")
            except Exception:
                st.latex(rf"f_{{{i+1}}}(x)={sp.latex(expr)}")
