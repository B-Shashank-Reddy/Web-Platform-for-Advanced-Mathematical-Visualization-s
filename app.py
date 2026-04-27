import streamlit as st

st.set_page_config(
    page_title="MathViz",
    page_icon="∑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════
#  DESIGN SYSTEM  — one place, used everywhere
#  Colors:  bg=#0d0d0d  surface=#161616  border=#252525
#           accent=#6C63FF  text=#e8e4dc  muted=#666
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,700;1,700&display=swap');

/* ── reset & hide streamlit chrome ── */
#MainMenu,footer,header{visibility:hidden}
[data-testid="collapsedControl"],.stDeployButton,section[data-testid="stSidebar"]{display:none}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

/* ── base ── */
html,body,[data-testid="stAppViewContainer"]{
    background:#0d0d0d!important;
    font-family:'Inter',sans-serif;
    color:#e8e4dc;
}
[data-testid="stAppViewContainer"]>.main{padding:0!important}
.block-container{padding:0!important;max-width:100%!important}

/* ══════════════════════════════════
   HOME — HERO
══════════════════════════════════ */
.hero{
    min-height:100vh;
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    text-align:center;
    padding:60px 40px 80px;
    background:
        radial-gradient(ellipse 60% 50% at 20% 30%, rgba(108,99,255,0.07) 0%, transparent 70%),
        radial-gradient(ellipse 50% 40% at 80% 70%, rgba(108,99,255,0.05) 0%, transparent 70%),
        #0d0d0d;
}
.hero-pill{
    display:inline-block;
    font-size:11px;letter-spacing:3px;text-transform:uppercase;
    color:#6C63FF;font-weight:500;
    border:1px solid rgba(108,99,255,0.3);
    border-radius:100px;
    padding:6px 18px;
    margin-bottom:36px;
}
.hero-title{
    font-family:'Playfair Display',serif;
    font-size:clamp(52px,8vw,100px);
    line-height:1.0;
    color:#e8e4dc;
    margin-bottom:28px;
    letter-spacing:-1px;
}
.hero-title em{font-style:italic;color:#6C63FF;}
.hero-sub{
    max-width:460px;
    font-size:15px;line-height:1.85;
    color:#555;font-weight:300;
    margin-bottom:64px;
}
.bounce{
    font-size:18px;color:#333;
    animation:bounce 2.2s ease-in-out infinite;
    display:inline-block;
}
@keyframes bounce{
    0%,100%{transform:translateY(0);opacity:.3}
    50%{transform:translateY(8px);opacity:.8}
}

/* ══════════════════════════════════
   HOME — CARDS SECTION
══════════════════════════════════ */
.cards-wrap{
    background:#0d0d0d;
    padding:80px 48px 120px;
    border-top:1px solid #161616;
}
.section-eyebrow{
    font-size:10px;letter-spacing:4px;text-transform:uppercase;
    color:#444;text-align:center;margin-bottom:10px;
}
.section-title{
    font-family:'Playfair Display',serif;
    font-size:clamp(28px,3.5vw,44px);
    color:#e8e4dc;text-align:center;
    margin-bottom:56px;line-height:1.15;
}

/* card wrapper injected via st.markdown */
.card-shell{
    background:#111;
    border:1px solid #1e1e1e;
    border-radius:20px;
    padding:0;
    overflow:hidden;
    transition:border-color .25s,box-shadow .25s,transform .25s;
    cursor:pointer;
    height:100%;
}
.card-shell:hover{
    border-color:var(--ca);
    box-shadow:0 0 0 1px var(--ca), 0 20px 60px rgba(0,0,0,.5);
    transform:translateY(-5px);
}
.card-icon-box{
    width:100%;
    padding:36px 0 28px;
    display:flex;align-items:center;justify-content:center;
    font-size:48px;
    background:var(--cb);
    border-bottom:1px solid #1e1e1e;
}
.card-body{padding:28px 28px 32px;}
.card-num{
    font-size:10px;letter-spacing:3px;text-transform:uppercase;
    color:var(--ca);margin-bottom:10px;font-weight:500;
}
.card-title{
    font-family:'Playfair Display',serif;
    font-size:22px;color:#e8e4dc;
    margin-bottom:10px;line-height:1.2;
}
.card-desc{font-size:13px;color:#555;line-height:1.7;margin-bottom:24px;}
.card-cta{
    display:inline-flex;align-items:center;gap:8px;
    font-size:12px;letter-spacing:1px;text-transform:uppercase;
    color:var(--ca);font-weight:500;
}
.card-cta-arrow{
    display:inline-flex;align-items:center;justify-content:center;
    width:24px;height:24px;border-radius:50%;
    border:1px solid var(--ca);
    font-size:12px;
    transition:background .2s,transform .2s;
}
.card-shell:hover .card-cta-arrow{
    background:var(--ca);color:#000;transform:translateX(3px);
}

/* card-wrap: card visual + button below it as styled CTA */
div.card-wrap{
    display:block!important;
    border-radius:20px!important;
}
/* style the open button as a full-width coloured CTA */
div.card-wrap > div[data-testid="stButton"] > button{
    width:100%!important;
    background:var(--ca, #6C63FF)!important;
    color:#fff!important;
    border:none!important;
    border-radius:0 0 20px 20px!important;
    font-size:12px!important;
    font-weight:500!important;
    letter-spacing:1.5px!important;
    text-transform:uppercase!important;
    padding:14px 0!important;
    cursor:pointer!important;
    font-family:"Inter",sans-serif!important;
    min-height:unset!important;
    height:auto!important;
    margin-top:-4px!important;
    transition:opacity .2s!important;
}
div.card-wrap > div[data-testid="stButton"] > button:hover{
    opacity:0.85!important;
    transform:none!important;
    box-shadow:none!important;
}

/* ══════════════════════════════════
   MODULE PAGES — consistent topbar
══════════════════════════════════ */
.topbar{
    position:sticky;top:0;z-index:100;
    background:rgba(13,13,13,0.92);
    backdrop-filter:blur(12px);
    border-bottom:1px solid #1e1e1e;
    padding:0 48px;
    height:64px;
    display:flex;align-items:center;justify-content:space-between;
}
.topbar-left{display:flex;align-items:center;gap:16px;}
.topbar-dot{
    width:8px;height:8px;border-radius:50%;
    background:var(--ca,#6C63FF);
    flex-shrink:0;
}
.topbar-title{
    font-family:'Playfair Display',serif;
    font-size:20px;color:#e8e4dc;
}
.topbar-tag{
    font-size:10px;letter-spacing:2px;text-transform:uppercase;
    color:#333;font-weight:400;
}

/* back button */
div.backbtn > div[data-testid="stButton"] > button{
    background:transparent!important;
    border:1px solid #252525!important;
    border-radius:8px!important;
    color:#555!important;
    font-size:11px!important;letter-spacing:1px!important;
    text-transform:uppercase!important;
    padding:7px 16px!important;
    min-height:unset!important;height:auto!important;
    font-family:'Inter',sans-serif!important;
    transition:all .15s!important;
}
div.backbtn > div[data-testid="stButton"] > button:hover{
    border-color:#e8e4dc!important;color:#e8e4dc!important;
    background:transparent!important;
    transform:none!important;box-shadow:none!important;
}

/* module content area */
.mod-content{
    padding:44px 56px;
    max-width:1000px;
}

/* ══════════════════════════════════
   FORM ELEMENTS — unified dark theme
══════════════════════════════════ */
.stTextInput input,.stNumberInput input,.stTextArea textarea{
    background:#111!important;
    border:1px solid #252525!important;
    border-radius:10px!important;
    color:#e8e4dc!important;
    font-family:'Inter',sans-serif!important;
    font-size:14px!important;
    padding:10px 14px!important;
}
.stTextInput input:focus,.stNumberInput input:focus{
    border-color:#6C63FF!important;
    box-shadow:0 0 0 3px rgba(108,99,255,.1)!important;
}
.stSelectbox>div>div,.stMultiSelect>div>div{
    background:#111!important;border-color:#252525!important;
    border-radius:10px!important;color:#e8e4dc!important;
}
label,.stRadio label,.stCheckbox label{
    color:#888!important;font-family:'Inter',sans-serif!important;font-size:13px!important;
}
.stRadio>div{gap:8px!important;}

/* primary action buttons in modules */
.mod-content div[data-testid="stButton"] > button{
    background:#6C63FF!important;
    color:#fff!important;border:none!important;
    border-radius:10px!important;
    font-size:13px!important;font-weight:500!important;
    letter-spacing:.3px!important;
    padding:11px 28px!important;
    font-family:'Inter',sans-serif!important;
    min-height:unset!important;height:auto!important;
    transition:opacity .15s,transform .15s!important;
}
.mod-content div[data-testid="stButton"] > button:hover{
    opacity:.85!important;transform:translateY(-1px)!important;
    box-shadow:0 6px 20px rgba(108,99,255,.3)!important;
}

/* result cards */
.result-box{
    background:#111;border:1px solid #1e1e1e;
    border-radius:14px;padding:24px 28px;margin-top:8px;
}
.result-label{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#444;margin-bottom:6px;}
.result-value{font-size:28px;font-weight:600;color:#e8e4dc;}

/* expanders */
.stExpander{
    background:#111!important;border:1px solid #1e1e1e!important;
    border-radius:12px!important;overflow:hidden!important;
}
.stExpander summary{color:#e8e4dc!important;font-family:'Inter',sans-serif!important;}

/* dataframe */
[data-testid="stDataFrame"]{
    border:1px solid #1e1e1e!important;border-radius:12px!important;overflow:hidden!important;
}

/* alerts */
.stAlert{border-radius:10px!important;font-family:'Inter',sans-serif!important;font-size:13px!important;}

/* sliders */
.stSlider>div>div>div{background:#6C63FF!important;}

/* headings inside modules */
h1,h2,h3,h4{font-family:'Playfair Display',serif!important;color:#e8e4dc!important;}
p,span{color:#aaa;}
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"
page = st.session_state.page

# ══════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════
if page == "home":

    # HERO
    st.markdown("""
<div class="hero">
    <div class="hero-pill">Mathematics · Visualization · Computation</div>
    <h1 class="hero-title">Math,<br>made <em>visible.</em></h1>
    <p class="hero-sub">
        A hands-on toolkit for students — from school to early engineering —
        built to make matrices, calculus, graphs and areas feel intuitive.
    </p>
    <span class="bounce">↓</span>
</div>
""", unsafe_allow_html=True)

    # SECTION HEADING
    st.markdown("""
<div class="cards-wrap">
    <p class="section-eyebrow">Choose a module to begin</p>
    <h2 class="section-title">What do you want<br>to explore?</h2>
</div>
""", unsafe_allow_html=True)

    # CARDS — 4 columns
    c1, c2, c3, c4 = st.columns(4, gap="small")

    cards = [
        (c1, "matrix",   "#6C63FF", "rgba(108,99,255,0.06)", "01", "∑",  "Matrix Operations",  "Determinants, inverses, rank, eigenvalues and full matrix arithmetic."),
        (c2, "calculus", "#3ECFCF", "rgba(62,207,207,0.06)",  "02", "∫",  "Calculus",            "Limits, nth-order derivatives and symbolic integrals — all exact."),
        (c3, "graphing", "#FF6B6B", "rgba(255,107,107,0.06)", "03", "∿",  "Graphing & Conics",   "Plot up to 5 functions with auto-scaled axes and derivative display."),
        (c4, "area",     "#F5A623", "rgba(245,166,35,0.06)",  "04", "⌗",  "Area Visualizer",     "Exact or approximate area between two curves with a shaded plot."),
    ]

    for col, key, ca, cb, num, icon, title, desc in cards:
        with col:
            st.markdown(f"""
<div class="card-wrap" style="--ca:{ca};">
<div class="card-shell" style="--ca:{ca};--cb:{cb};">
    <div class="card-icon-box" style="background:{cb};">
        <span style="font-size:48px;line-height:1;">{icon}</span>
    </div>
    <div class="card-body">
        <div class="card-num" style="color:{ca};">{num}</div>
        <div class="card-title">{title}</div>
        <div class="card-desc">{desc}</div>
    </div>
</div>
""", unsafe_allow_html=True)
            if st.button(f"Open {title} →", key=f"go_{key}"):
                st.session_state.page = key
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  MODULE PAGES
# ══════════════════════════════════════════════════════════════
else:
    meta = {
        "matrix":   ("Matrix Operations",  "#6C63FF"),
        "calculus": ("Calculus",            "#3ECFCF"),
        "graphing": ("Graphing & Conics",   "#FF6B6B"),
        "area":     ("Area Visualizer",     "#F5A623"),
    }
    mod_title, mod_color = meta.get(page, ("Module", "#6C63FF"))

    # TOPBAR
    st.markdown(f"""
<div class="topbar" style="--ca:{mod_color};">
    <div class="topbar-left">
        <div class="topbar-dot" style="background:{mod_color};"></div>
        <div class="topbar-title">{mod_title}</div>
    </div>
    <div class="topbar-tag">MathViz</div>
</div>
""", unsafe_allow_html=True)

    # BACK BUTTON
    st.markdown('<div class="backbtn" style="padding:16px 56px 0;">', unsafe_allow_html=True)
    if st.button("← Home", key="back"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # MODULE CONTENT
    st.markdown('<div class="mod-content">', unsafe_allow_html=True)

    if page == "matrix":
        from modules.matrix import matrix_module
        matrix_module()
    elif page == "calculus":
        from modules.calculus import calculus_module
        calculus_module()
    elif page == "graphing":
        from modules.graphing import graphing_module
        graphing_module()
    elif page == "area":
        from modules.area import area_module
        area_module()

    st.markdown('</div>', unsafe_allow_html=True)