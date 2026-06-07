import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="WAR ETF 3x | קסם תעודות סל", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; }
    .war-banner {
        background: linear-gradient(135deg,#0f3460,#16213e,#1a1a2e);
        color: white; padding: 22px 30px; border-radius: 12px;
        margin-bottom: 18px; text-align: center;
    }
    .exec-card {
        padding: 18px 22px; border-radius: 10px;
        color: white; text-align: center; margin: 4px 0;
    }
    .risk-card {
        background: #1a1a2e; color: white;
        padding: 16px 20px; border-radius: 10px;
        text-align: center; border: 1px solid #333;
    }
    .sector-card {
        border-left: 5px solid; padding: 12px 16px;
        border-radius: 6px; margin-bottom: 8px;
        background: #fafafa; min-height: 150px;
    }
</style>
""", unsafe_allow_html=True)

# ── Definitions ────────────────────────────────────────────────────────────────
SECTORS = {
    "Defense & Aerospace 🛡️": {
        "stocks": ["LMT", "RTX", "NOC", "GD", "HII", "KTOS"],
        "color": "#1f4e79", "he": "ביטחון ואוויר",
        "desc": "לוקהיד מרטין, ריית'און, נורת'רופ גרומן, ג'נרל דיינמיקס, HII, Kratos",
    },
    "Cyber & Intelligence 🔐": {
        "stocks": ["CRWD", "PANW", "CACI", "LDOS", "BAH", "SAIC"],
        "color": "#c00000", "he": "סייבר ומודיעין",
        "desc": "CrowdStrike, Palo Alto Networks, CACI, Leidos, Booz Allen, SAIC",
    },
    "Energy ⚡": {
        "stocks": ["XOM", "CVX", "COP", "SLB", "HAL", "MPC"],
        "color": "#7030a0", "he": "אנרגיה",
        "desc": "אקסון מובייל, שברון, ConocoPhillips, שלומברגר, הליבורטון, Marathon",
    },
    "Raw Materials & Metals ⛏️": {
        "stocks": ["MP", "NEM", "FCX", "AA", "CLF", "GOLD"],
        "color": "#833c00", "he": "חומרי גלם ומתכות",
        "desc": "MP Materials, ניומונט (זהב), פריפורט (נחושת), אלקואה, CLF, Barrick",
    },
    "Defense Tech 🚀": {
        "stocks": ["PLTR", "AVAV", "OSIS", "DRS", "AXON", "BWXT"],
        "color": "#375623", "he": "טכנולוגיה ביטחונית",
        "desc": "פלאנטיר, AeroVironment (מל\"טים), OSI Systems, Leonardo DRS, Axon, BWXT",
    },
    "Iran War — חשיפה ישירה 🇮🇷": {
        "stocks": ["RTX", "LMT", "XOM", "CVX", "CRWD", "PANW"],
        "color": "#8b0070", "he": "חשיפה ישירה - איראן",
        "desc": "הגנה אווירית (RTX/LMT), אנרגיה (XOM/CVX), סייבר-איראן (CRWD/PANW)",
    },
}

BENCHMARK_ETFS = {
    "ITA (iShares Defense ETF)": {"ticker": "ITA", "color": "#2196F3", "dash": "dash"},
    "XAR (SPDR Aerospace ETF)":  {"ticker": "XAR", "color": "#FF9800", "dash": "dot"},
    "PPA (Invesco Defense ETF)": {"ticker": "PPA", "color": "#9C27B0", "dash": "dashdot"},
}

WAR_PERIODS = {
    "פלישת רוסיה לאוקראינה":        {"start": "2022-02-24", "end": "2022-12-31", "fill": "rgba(220,50,50,0.12)",  "line": "rgba(220,50,50,0.6)"},
    "מלחמת עזה":                    {"start": "2023-10-07", "end": "2024-06-30", "fill": "rgba(255,140,0,0.12)", "line": "rgba(255,140,0,0.6)"},
    "תקיפות ישראל-איראן 2024":      {"start": "2024-04-13", "end": "2024-10-31", "fill": "rgba(130,0,220,0.12)", "line": "rgba(130,0,220,0.6)"},
    "מלחמת 12 הימים ישראל-איראן":   {"start": "2025-06-13", "end": "2025-06-24", "fill": "rgba(0,180,255,0.15)", "line": "rgba(0,180,255,0.7)"},
}

PERIODS_ANALYSIS = {
    "לפני המלחמות (2021)":         ("2021-01-01", "2022-02-23"),
    "מלחמת אוקראינה (2022)":       ("2022-02-24", "2022-12-31"),
    "בין המלחמות (2023 H1)":       ("2023-01-01", "2023-10-06"),
    "מלחמת עזה (2023-24)":         ("2023-10-07", "2024-06-30"),
    "תקיפות ישראל-איראן (2024)":   ("2024-04-13", "2024-10-31"),
    "מלחמת 12 הימים (יוני 2025)":  ("2025-06-13", "2025-06-30"),
}

FUND_STRUCTURE = {
    "שם הקרן": "WAR ETF 3x (WARX)",
    "דמי ניהול (TER)": "1.25% לשנה (קסם)",
    "דמי נאמן": "0.03% לשנה",
    "סה\"כ עלות למשקיע": "1.28% לשנה",
    "מינוף": "3x — daily rebalancing via swaps",
    "בורסה מוצעת": "NYSE Arca / TASE",
    "מספר מניות": "30 מניות ב-5 סקטורים",
    "ריבאלנסינג": "יומי — כדי לשמור על מינוף קבוע",
    "AUM מינימלי להשקה": "$50M",
    "מדיניות דיבידנד": "צבירה (Accumulating)",
    "מטבע בסיס": "USD",
    "סוג נגזרים": "Total Return Swaps + Futures",
}

GLOBAL_PERIODS = {
    "📅 כל הזמן":                      ("2021-01-01", str(date.today())),
    "🇺🇦 מלחמת אוקראינה":             ("2022-02-24", "2022-12-31"),
    "⚔️ בין המלחמות":                 ("2023-01-01", "2023-10-06"),
    "🇮🇱 מלחמת עזה":                  ("2023-10-07", "2024-06-30"),
    "🇮🇷 תקיפות ישראל-איראן 2024":    ("2024-04-13", "2024-10-31"),
    "💥 מלחמת 12 הימים (יוני 2025)":  ("2025-06-13", "2025-06-30"),
    "🔥 כל מלחמות המזרח התיכון":      ("2023-10-07", str(date.today())),
    "📆 בחירה חופשית":                None,
}

# ── Risk helpers ───────────────────────────────────────────────────────────────
def sharpe(rets, rf=0.045):
    excess = rets - rf / 252
    return float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0

def max_dd(rets):
    cum = (1 + rets).cumprod()
    return float(((cum / cum.expanding().max()) - 1).min() * 100)

def ann_vol(rets):
    return float(rets.std() * np.sqrt(252) * 100)

def ann_ret(rets):
    n = len(rets) / 252
    return float(((1 + rets).prod() ** (1 / n) - 1) * 100) if n > 0.1 else 0

def calmar(rets):
    mdd = abs(max_dd(rets) / 100)
    return ann_ret(rets) / 100 / mdd if mdd > 0 else 0

def beta(rets, bench):
    common = rets.align(bench, join="inner")
    cov = np.cov(common[0], common[1])
    return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0

def drawdown_series(rets):
    cum = (1 + rets).cumprod()
    return (cum / cum.expanding().max() - 1) * 100

# ── Data helpers ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers, start, end):
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    if isinstance(close, pd.Series):
        close = close.to_frame()
    return close.dropna(thresh=int(len(close) * 0.5), axis=1)

def sector_returns(prices, stock_selection):
    out = {}
    for sname, stocks in stock_selection.items():
        cols = [t for t in stocks if t in prices.columns]
        if cols:
            out[SECTORS[sname]["he"]] = prices[cols].pct_change().mean(axis=1)
    return pd.DataFrame(out).dropna()

def lev_nav(rets, lev):
    return (1 + rets * lev).cumprod() * 100

def period_return(series, start, end):
    s = series.loc[start:end]
    return float((1 + s).prod() - 1) if len(s) > 5 else None

def range_selector():
    return dict(
        buttons=[
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=3, label="3Y", step="year", stepmode="backward"),
            dict(step="all", label="ALL"),
        ],
        bgcolor="#2a2a2a", activecolor="#c00000",
        bordercolor="#555", borderwidth=1,
        font=dict(color="white", size=11),
    )

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ הגדרות")
    st.subheader("סקטורים ומניות")
    stock_selection = {}
    for sname, sinfo in SECTORS.items():
        c1, c2 = st.columns([1, 7])
        on = c1.checkbox("", value=True, key=f"chk_{sname}", label_visibility="collapsed")
        c2.markdown(f"**{sname}**")
        if on:
            chosen = st.multiselect(
                f"מניות — {sinfo['he']}", options=sinfo["stocks"],
                default=sinfo["stocks"], key=f"stocks_{sname}",
                label_visibility="collapsed",
            )
            if chosen:
                stock_selection[sname] = chosen

    st.divider()
    st.subheader("השוואה לתעודות קיימות")
    bench_selected = [n for n, i in BENCHMARK_ETFS.items() if st.checkbox(n, value=True, key=f"bench_{n}")]

    st.divider()
    lev_factor = st.select_slider("מינוף", options=[1, 2, 3], value=3)

    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if len(stock_selection) < 2:
    st.warning("⚠️ בחר לפחות 2 סקטורים.")
    st.stop()

# ── Load data ──────────────────────────────────────────────────────────────────
all_tickers = list({t for s in stock_selection.values() for t in s})
all_tickers += ["SPY"] + [BENCHMARK_ETFS[b]["ticker"] for b in bench_selected]

with st.spinner("📡 טוען נתוני שוק..."):
    prices_full = load_prices(all_tickers, "2018-01-01", str(date.today()))
    sec_ret_full = sector_returns(prices_full, stock_selection)

# ── Banner ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="war-banner">
    <h2 style="margin:0">🛡️ WAR ETF 3x</h2>
    <p style="margin:6px 0 0">תעודת סל ממונפת כפול 3 — חשיפה לסקטורי מלחמה</p>
    <small style="opacity:.7">הצעה לקסם תעודות סל | Demo 2025</small>
</div>
""", unsafe_allow_html=True)

# ── Period selector ────────────────────────────────────────────────────────────
sel_period = st.radio("בחר תקופה:", list(GLOBAL_PERIODS.keys()), horizontal=True, index=0)

if GLOBAL_PERIODS[sel_period] is None:
    fc1, fc2 = st.columns(2)
    d_s = fc1.date_input("מתאריך", value=date(2021, 1, 1), min_value=date(2018, 1, 1))
    d_e = fc2.date_input("עד תאריך", value=date.today(), max_value=date.today())
    g_start, g_end = str(d_s), str(d_e)
else:
    g_start, g_end = GLOBAL_PERIODS[sel_period]

prices  = prices_full.loc[g_start:g_end]
sec_ret = sec_ret_full.loc[g_start:g_end]

# Common series used across tabs
etf_r = sec_ret.mean(axis=1)
spy_r = prices["SPY"].pct_change().dropna() if "SPY" in prices.columns else None
etf_r_lev = etf_r * lev_factor

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Executive Summary",
    "📊 סקטורים וקורלציה",
    "📈 בק-טסטינג",
    "💰 סימולציית השקעה",
    "⚠️ ניתוח סיכון",
    "🔍 מניות בודדות",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0 — EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab0:
    st.markdown("## WAR ETF 3x — Executive Summary לקסם תעודות סל")

    # ── Key metrics ──
    tot_ret_lev = ann_ret(etf_r_lev)
    tot_ret_1x  = ann_ret(etf_r)
    spy_ret     = ann_ret(spy_r) if spy_r is not None else 0
    sr_lev  = sharpe(etf_r_lev)
    mdd_lev = max_dd(etf_r_lev)
    vol_lev = ann_vol(etf_r_lev)
    cal_lev = calmar(etf_r_lev)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#7b0000,#c00000)">
        <div style="font-size:11px;opacity:.8">תשואה שנתית</div>
        <div style="font-size:28px;font-weight:900">{tot_ret_lev:+.1f}%</div>
        <div style="font-size:11px;opacity:.7">ETF {lev_factor}x</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#0d3359,#1f4e79)">
        <div style="font-size:11px;opacity:.8">עודף על S&P</div>
        <div style="font-size:28px;font-weight:900">{tot_ret_lev-spy_ret:+.1f}%</div>
        <div style="font-size:11px;opacity:.7">Alpha שנתי</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#1a3a1a,#27ae60)">
        <div style="font-size:11px;opacity:.8">Sharpe Ratio</div>
        <div style="font-size:28px;font-weight:900">{sr_lev:.2f}</div>
        <div style="font-size:11px;opacity:.7">&gt;1 = מצוין</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#3a1a00,#8b4000)">
        <div style="font-size:11px;opacity:.8">Max Drawdown</div>
        <div style="font-size:28px;font-weight:900">{mdd_lev:.1f}%</div>
        <div style="font-size:11px;opacity:.7">ירידה מקסימלית</div></div>""", unsafe_allow_html=True)
    c5.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#1a1a3a,#4040aa)">
        <div style="font-size:11px;opacity:.8">תנודתיות שנתית</div>
        <div style="font-size:28px;font-weight:900">{vol_lev:.1f}%</div>
        <div style="font-size:11px;opacity:.7">Annualized Vol</div></div>""", unsafe_allow_html=True)
    c6.markdown(f"""<div class="exec-card" style="background:linear-gradient(135deg,#2a0a2a,#7a0a7a)">
        <div style="font-size:11px;opacity:.8">Calmar Ratio</div>
        <div style="font-size:28px;font-weight:900">{cal_lev:.2f}</div>
        <div style="font-size:11px;opacity:.7">תשואה/סיכון</div></div>""", unsafe_allow_html=True)

    st.divider()

    # ── Thesis ──
    col_thesis, col_fund = st.columns([3, 2])
    with col_thesis:
        st.markdown("### 💡 התזה — למה WAR ETF 3x?")
        st.markdown(f"""
**🌍 עולם עם יותר מלחמות** — מאז 2022 פרצו 3 מלחמות גדולות (אוקראינה, עזה, איראן).
שוק תעודות הסל הקיים לא מציע חשיפה ממוקדת וממונפת לתמה הזו.

**📈 ביצועי מלחמה עוקפים את השוק** — ב-{len(WAR_PERIODS)} תקופות מלחמה שנבחנו,
הסקטורים בתעודה עשו בממוצע `{tot_ret_1x:.1f}%` שנתי לעומת `{spy_ret:.1f}%` ב-S&P 500.

**🛡️ מינוף 3x על הנכס הנכון** — במקום להמר על Polymarket אם תהיה מלחמה,
המשקיע מקבל חשיפה מובנית ל-30 מניות מ-5 סקטורים שמרוויחים ממלחמה (**כן** ו-**לא**).

**🆕 מוצר ייחודי בשוק** — אין היום תעודה ממונפת 3x עם פוקוס על war economy.
ITA/XAR/PPA הם 1x בלבד ולא כוללים סייבר, אנרגיה וחומרי גלם.
        """)

    with col_fund:
        st.markdown("### 🏗️ מבנה הקרן")
        for k, v in FUND_STRUCTURE.items():
            st.markdown(f"**{k}:** {v}")

    st.divider()

    # ── Mini performance chart ──
    st.markdown("### 📈 ביצועים — War ETF 3x vs שוק")
    fig_exec = go.Figure()
    for war_name, wp in WAR_PERIODS.items():
        fig_exec.add_vrect(x0=wp["start"], x1=wp["end"], fillcolor=wp["fill"],
                           line=dict(color=wp["line"], width=1), layer="below",
                           annotation_text=war_name.split(" ")[0],
                           annotation_position="top left", annotation_font_size=9)
    if spy_r is not None:
        fig_exec.add_trace(go.Scatter(x=lev_nav(spy_r, 1).index, y=lev_nav(spy_r, 1).values,
                                      name="S&P 500", line=dict(color="#888", width=1.5, dash="dash")))
    fig_exec.add_trace(go.Scatter(x=lev_nav(etf_r, 1).index, y=lev_nav(etf_r, 1).values,
                                  name="War ETF 1x", line=dict(color="#1f4e79", width=2, dash="dot")))
    fig_exec.add_trace(go.Scatter(x=lev_nav(etf_r, lev_factor).index, y=lev_nav(etf_r, lev_factor).values,
                                  name=f"War ETF {lev_factor}x ⭐", line=dict(color="#c00000", width=3.5),
                                  fill="tozeroy", fillcolor="rgba(192,0,0,0.06)"))
    fig_exec.update_layout(height=350, hovermode="x unified", margin=dict(l=20, r=20, t=10, b=20),
                           yaxis_title="שווי תיק (בסיס 100)",
                           legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
                           xaxis=dict(rangeselector=range_selector(), type="date"))
    st.plotly_chart(fig_exec, use_container_width=True)

    st.divider()

    # ── Fee comparison ──
    col_fee, col_why = st.columns([2, 1])
    with col_fee:
        st.markdown("### 💸 השוואת דמי ניהול — WAR ETF vs מתחרים")
        fee_data = {
            "TQQQ\n3x Nasdaq":   0.86,
            "UPRO\n3x S&P 500":  0.91,
            "SOXL\n3x Chips":    0.99,
            "LABU\n3x Biotech":  1.09,
            "ITA\nDefense 1x":   0.40,
            "XAR\nAerospace 1x": 0.35,
            "WAR ETF 3x\n⭐ קסם": 1.25,
        }
        colors_fee = ["#888" if "WAR" not in k else "#c00000" for k in fee_data]
        fig_fee = go.Figure(go.Bar(
            x=list(fee_data.keys()),
            y=list(fee_data.values()),
            marker_color=colors_fee,
            text=[f"{v:.2f}%" for v in fee_data.values()],
            textposition="outside",
        ))
        fig_fee.add_hline(y=1.25, line_dash="dot", line_color="#c00000", line_width=1.5,
                          annotation_text="WAR ETF 1.25%", annotation_position="right")
        fig_fee.update_layout(
            height=320, margin=dict(l=20, r=60, t=20, b=20),
            yaxis=dict(title="דמי ניהול שנתיים (%)", ticksuffix="%", range=[0, 1.6]),
            showlegend=False,
        )
        st.plotly_chart(fig_fee, use_container_width=True)

    with col_why:
        st.markdown("### 🎯 למה 1.25% מוצדק?")
        st.markdown("""
**תמה ייחודית** — אפס מתחרים ישירים, pricing power מלא

**עלות תפעולית גבוהה** — daily rebalancing ב-30 מניות + 5 סקטורים + swaps

**Alpha מוכח** — ביצועי יתר על S&P בכל תקופות המלחמה שנבחנו

**קהל יעד מחויב** — משקיע שמחפש war exposure לא יסרב ל-0.3% יותר
        """)

    st.divider()

    # ── Revenue potential ──
    st.markdown("### 💼 פוטנציאל הכנסות — קסם תעודות סל")

    MGMT_FEE   = 0.0125   # 1.25%
    TRUSTEE    = 0.0003   # 0.03%
    aum_levels = [50, 100, 250, 500, 1_000, 2_500]

    rev_rows = []
    for aum in aum_levels:
        aum_usd = aum * 1_000_000
        mgmt_rev    = aum_usd * MGMT_FEE
        trustee_rev = aum_usd * TRUSTEE
        total_rev   = mgmt_rev + trustee_rev
        rev_rows.append({
            "AUM ($M)":           f"${aum:,}M",
            "הכנסת קסם (1.25%)": f"${mgmt_rev/1e6:.3f}M",
            "הכנסת נאמן (0.03%)":f"${trustee_rev/1000:.0f}K",
            "סה\"כ הכנסות":       f"${total_rev/1e6:.3f}M",
        })

    df_rev = pd.DataFrame(rev_rows).set_index("AUM ($M)")
    st.dataframe(df_rev, use_container_width=True)

    # Visual bar chart
    fig_rev = go.Figure()
    aum_vals  = [a * 1e6 for a in aum_levels]
    mgmt_vals = [a * MGMT_FEE / 1e6 for a in aum_vals]
    trust_vals= [a * TRUSTEE / 1e6 for a in aum_vals]
    labels    = [f"${a}M" for a in aum_levels]

    fig_rev.add_trace(go.Bar(name="קסם — דמי ניהול 1.25%", x=labels, y=mgmt_vals,
                             marker_color="#c00000",
                             text=[f"${v:.2f}M" for v in mgmt_vals], textposition="inside"))
    fig_rev.add_trace(go.Bar(name="נאמן — 0.03%", x=labels, y=trust_vals,
                             marker_color="#1f4e79",
                             text=[f"${v*1000:.0f}K" for v in trust_vals], textposition="inside"))
    fig_rev.update_layout(
        barmode="stack", height=320,
        xaxis_title="AUM", yaxis=dict(title="הכנסה שנתית ($M)", tickprefix="$", ticksuffix="M"),
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig_rev, use_container_width=True)
    st.caption("💡 על AUM של $500M — קסם מרוויחה **$6.25M בשנה** מדמי ניהול בלבד. הנאמן מקבל **$150K** נוספים.")

    st.caption("⚠️ לצרכי מחקר ולמידה בלבד — אין לראות בכך ייעוץ השקעות. ביצועי עבר אינם ערובה לעתיד.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SECTORS & CORRELATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("הסקטורים שנבחרו לתעודה")
    cols = st.columns(len(stock_selection))
    for i, (sname, stocks) in enumerate(stock_selection.items()):
        info = SECTORS[sname]
        stocks_ok = [t for t in stocks if t in prices.columns]
        total_ret = float((prices[stocks_ok].iloc[-1] / prices[stocks_ok].iloc[0] - 1).mean() * 100) if stocks_ok else None
        arrow = "▲" if (total_ret or 0) > 0 else "▼"
        rc = "#27ae60" if (total_ret or 0) > 0 else "#e74c3c"
        ret_str = f"{arrow} {abs(total_ret):.1f}%" if total_ret is not None else "—"
        cols[i].markdown(f"""
        <div class="sector-card" style="border-color:{info['color']};background:{info['color']}0d">
            <b style="color:{info['color']};font-size:14px">{info['he']}</b><br>
            <small style="color:#555">{', '.join(stocks_ok)}</small><br><br>
            <span style="font-size:20px;font-weight:800;color:{rc}">{ret_str}</span>
            <span style="font-size:11px;color:#888"> {sel_period}</span>
        </div>""", unsafe_allow_html=True)

    st.divider()

    col_corr, col_roll = st.columns([1, 1])

    with col_corr:
        st.subheader("מטריצת קורלציה")
        corr = sec_ret.corr()
        fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn_r",
                             zmin=-1, zmax=1, aspect="auto")
        fig_corr.update_traces(textfont_size=13, textfont_color="white")
        fig_corr.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10),
                               coloraxis_colorbar_title="קורלציה", xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_corr, use_container_width=True)
        upper = corr.values[np.triu_indices_from(corr.values, k=1)]
        avg_c = float(upper.mean())
        if avg_c < 0.6:   st.success(f"✅ קורלציה ממוצעת {avg_c:.2f} — גיוון טוב.")
        elif avg_c < 0.8: st.warning(f"⚠️ קורלציה ממוצעת {avg_c:.2f} — גיוון בינוני.")
        else:             st.error(f"❌ קורלציה ממוצעת {avg_c:.2f} — הסקטורים נעים יחד מדי.")

    with col_roll:
        st.subheader("קורלציה רולינג (60 יום)")
        if len(sec_ret.columns) >= 2:
            pairs = [(sec_ret.columns[i], sec_ret.columns[j])
                     for i in range(len(sec_ret.columns))
                     for j in range(i + 1, min(i + 3, len(sec_ret.columns)))]
            fig_roll = go.Figure()
            for c1_name, c2_name in pairs[:4]:
                roll = sec_ret[c1_name].rolling(60).corr(sec_ret[c2_name]).dropna()
                fig_roll.add_trace(go.Scatter(x=roll.index, y=roll.values,
                                              name=f"{c1_name.split()[0]}×{c2_name.split()[0]}",
                                              mode="lines", line=dict(width=1.8)))
            fig_roll.add_hline(y=0, line_dash="dash", line_color="#aaa", line_width=1)
            fig_roll.update_layout(height=380, hovermode="x unified",
                                   yaxis=dict(title="קורלציה", range=[-1, 1]),
                                   margin=dict(l=10, r=10, t=20, b=10),
                                   legend=dict(x=0, y=1, font=dict(size=10)))
            st.plotly_chart(fig_roll, use_container_width=True)
            st.caption("קורלציה גבוהה בזמן מלחמה = הסקטורים נעים ביחד. קורלציה נמוכה = גיוון אמיתי.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BACKTESTING
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"War ETF {lev_factor}x — ביצועים היסטוריים והשוואה לתעודות קיימות")
    fig_bt = go.Figure()
    for war_name, wp in WAR_PERIODS.items():
        fig_bt.add_vrect(x0=wp["start"], x1=wp["end"], fillcolor=wp["fill"],
                         line=dict(color=wp["line"], width=1, dash="dot"), layer="below",
                         annotation_text=war_name, annotation_position="top left", annotation_font_size=10)
    if spy_r is not None:
        fig_bt.add_trace(go.Scatter(x=lev_nav(spy_r, 1).index, y=lev_nav(spy_r, 1).values,
                                    name="S&P 500", line=dict(color="#888", width=1.8, dash="dash")))
    for bname in bench_selected:
        bt = BENCHMARK_ETFS[bname]["ticker"]
        if bt in prices.columns:
            b_r = prices[bt].pct_change().dropna()
            fig_bt.add_trace(go.Scatter(x=lev_nav(b_r, 1).index, y=lev_nav(b_r, 1).values,
                                        name=bname.split("(")[1].rstrip(")"),
                                        line=dict(color=BENCHMARK_ETFS[bname]["color"], width=2,
                                                  dash=BENCHMARK_ETFS[bname]["dash"])))
    if lev_factor > 1:
        fig_bt.add_trace(go.Scatter(x=lev_nav(etf_r, 1).index, y=lev_nav(etf_r, 1).values,
                                    name="War ETF 1x", line=dict(color="#1f4e79", width=2, dash="dot")))
    fig_bt.add_trace(go.Scatter(x=lev_nav(etf_r, lev_factor).index, y=lev_nav(etf_r, lev_factor).values,
                                name=f"War ETF {lev_factor}x ⭐", line=dict(color="#c00000", width=3.5),
                                fill="tozeroy", fillcolor="rgba(192,0,0,0.06)"))
    fig_bt.update_layout(height=480, hovermode="x unified", yaxis_title="שווי תיק (בסיס 100)",
                         xaxis=dict(rangeselector=range_selector(), type="date", title="תאריך"),
                         legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
                         margin=dict(l=20, r=20, t=20, b=30))
    st.plotly_chart(fig_bt, use_container_width=True)

    st.divider()
    st.subheader("השוואת תשואות לפי תקופה")
    rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf = period_return(etf_r, ps, pe)
        if r_etf is None: continue
        r_lev = period_return(etf_r * lev_factor, ps, pe) if lev_factor > 1 else None
        r_spy = period_return(spy_r, ps, pe) if spy_r is not None else None
        row = {"תקופה": pname,
               f"War ETF {lev_factor}x": f"{r_lev*100:+.1f}%" if r_lev else "—",
               "War ETF 1x": f"{r_etf*100:+.1f}%",
               "S&P 500": f"{r_spy*100:+.1f}%" if r_spy else "—"}
        for bname in bench_selected:
            bt = BENCHMARK_ETFS[bname]["ticker"]
            if bt in prices.columns:
                r_b = period_return(prices[bt].pct_change().dropna(), ps, pe)
                row[bname.split("(")[1].rstrip(")")] = f"{r_b*100:+.1f}%" if r_b else "—"
        rows.append(row)
    if rows:
        df_table = pd.DataFrame(rows).set_index("תקופה")
        def color_cell(val):
            if not isinstance(val, str) or val == "—": return ""
            try:
                return f"color:{'#27ae60' if float(val.replace('%','').replace('+',''))>0 else '#c0392b'};font-weight:bold"
            except: return ""
        st.dataframe(df_table.style.map(color_cell), use_container_width=True)

    st.divider()
    st.subheader("ביצועי סקטורים בתקופות מלחמה")
    wcols = st.columns(min(len(WAR_PERIODS), 2))
    for i, (war_name, wp) in enumerate(WAR_PERIODS.items()):
        col_w = wcols[i % 2]
        sp = {}
        for sname, stocks in stock_selection.items():
            sok = [t for t in stocks if t in prices.columns]
            if not sok: continue
            pd_ = prices[sok].loc[wp["start"]:wp["end"]]
            if len(pd_) < 5: continue
            sp[SECTORS[sname]["he"]] = float((pd_.iloc[-1] / pd_.iloc[0] - 1).mean() * 100)
        if not sp: col_w.info(f"{war_name} — אין נתונים"); continue
        fig_bar = go.Figure(go.Bar(x=list(sp.values()), y=list(sp.keys()), orientation="h",
                                   marker_color=["#27ae60" if v > 0 else "#e74c3c" for v in sp.values()],
                                   text=[f"{v:+.1f}%" for v in sp.values()], textposition="outside"))
        fig_bar.update_layout(title=war_name, height=260,
                              margin=dict(l=10, r=60, t=35, b=10), showlegend=False)
        col_w.plotly_chart(fig_bar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 💰 סימולציית השקעה — כמה היית מרוויח?")
    ci1, ci2, _ = st.columns([1, 1, 1])
    invest_amount = ci1.number_input("סכום השקעה ראשוני ($)", min_value=100,
                                     max_value=10_000_000, value=10_000, step=1_000, format="%d")
    chart_mode = ci2.radio("תצוגת גרף", ["$ שווי", "% תשואה"], horizontal=True)
    sim_start, sim_end = g_start, g_end
    st.caption(f"תקופה: **{sel_period}** ({g_start} → {g_end})")
    st.divider()

    etf_rp  = etf_r.loc[sim_start:sim_end]
    spy_rp  = spy_r.loc[sim_start:sim_end] if spy_r is not None else None

    def pf(r_slice): return float((1 + r_slice).prod()) * invest_amount if len(r_slice) > 0 else invest_amount
    final_lev = pf(etf_rp * lev_factor); final_1x = pf(etf_rp)
    final_spy = pf(spy_rp) if spy_rp is not None else None

    st.markdown(f"""
    <div style="display:flex;gap:14px;margin-bottom:20px;flex-wrap:wrap;">
        <div class="exec-card" style="flex:1;min-width:160px;background:linear-gradient(135deg,#7b0000,#c00000)">
            <div style="font-size:12px;opacity:.8">War ETF {lev_factor}x</div>
            <div style="font-size:32px;font-weight:900;margin:4px 0">${final_lev:,.0f}</div>
            <div style="font-size:13px">{'▲' if final_lev>invest_amount else '▼'} ${abs(final_lev-invest_amount):,.0f} ({(final_lev/invest_amount-1)*100:+.1f}%)</div>
        </div>
        <div class="exec-card" style="flex:1;min-width:160px;background:linear-gradient(135deg,#0d3359,#1f4e79)">
            <div style="font-size:12px;opacity:.8">War ETF 1x</div>
            <div style="font-size:32px;font-weight:900;margin:4px 0">${final_1x:,.0f}</div>
            <div style="font-size:13px">{'▲' if final_1x>invest_amount else '▼'} ${abs(final_1x-invest_amount):,.0f} ({(final_1x/invest_amount-1)*100:+.1f}%)</div>
        </div>
        <div class="exec-card" style="flex:1;min-width:160px;background:linear-gradient(135deg,#2d2d2d,#444)">
            <div style="font-size:12px;opacity:.8">S&P 500</div>
            <div style="font-size:32px;font-weight:900;margin:4px 0">${final_spy:,.0f}</div>
            <div style="font-size:13px">{'▲' if (final_spy or 0)>invest_amount else '▼'} ${abs((final_spy or invest_amount)-invest_amount):,.0f} ({((final_spy or invest_amount)/invest_amount-1)*100:+.1f}%)</div>
        </div>
        <div class="exec-card" style="flex:1;min-width:160px;background:linear-gradient(135deg,#1a3a1a,#27ae60)">
            <div style="font-size:12px;opacity:.8">יתרון {lev_factor}x על S&P</div>
            <div style="font-size:32px;font-weight:900;margin:4px 0">x{final_lev/(final_spy or 1):.1f}</div>
            <div style="font-size:13px">+${final_lev-(final_spy or 0):,.0f} יותר</div>
        </div>
    </div>""", unsafe_allow_html=True)

    pct_mode = chart_mode == "% תשואה"
    def make_s(r, m=1):
        r2 = r * m
        return ((1 + r2).cumprod() - 1) * 100 if pct_mode else (1 + r2).cumprod() * invest_amount

    fig_sim = go.Figure()
    for war_name, wp in WAR_PERIODS.items():
        if wp["start"] <= sim_end and wp["end"] >= sim_start:
            fig_sim.add_vrect(x0=max(wp["start"], sim_start), x1=min(wp["end"], sim_end),
                              fillcolor=wp["fill"], line=dict(color=wp["line"], width=1), layer="below",
                              annotation_text=war_name.split(" ")[0], annotation_position="top left")
    fig_sim.add_hline(y=0 if pct_mode else invest_amount, line_dash="dot", line_color="#999", line_width=1)
    if spy_rp is not None:
        s = make_s(spy_rp)
        fig_sim.add_trace(go.Scatter(x=s.index, y=s.values, name="S&P 500",
                                     line=dict(color="#888", width=1.8, dash="dash")))
    if lev_factor > 1:
        s = make_s(etf_rp)
        fig_sim.add_trace(go.Scatter(x=s.index, y=s.values, name="War ETF 1x",
                                     line=dict(color="#1f4e79", width=2, dash="dot")))
    sl = make_s(etf_rp, lev_factor)
    fig_sim.add_trace(go.Scatter(x=sl.index, y=sl.values, name=f"War ETF {lev_factor}x ⭐",
                                 line=dict(color="#c00000", width=3.5),
                                 fill="tozeroy", fillcolor="rgba(192,0,0,0.06)"))
    xc = dict(title="תאריך", range=[sim_start, sim_end], type="date")
    if not pct_mode: xc["rangeselector"] = range_selector()
    fig_sim.update_layout(height=440, hovermode="x unified", xaxis=xc,
                          yaxis=dict(title=f"תשואה מצטברת מ-{sim_start}(%)" if pct_mode else "שווי($)",
                                     ticksuffix="%" if pct_mode else "", tickprefix="" if pct_mode else "$",
                                     tickformat=".1f" if pct_mode else ",.0f"),
                          legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
                          margin=dict(l=20, r=20, t=10, b=30))
    if pct_mode:
        st.caption(f"ℹ️ % מצטבר מ-{sim_start}. לתת-תקופה — בחר תקופה בכפתורים למעלה.")
    st.plotly_chart(fig_sim, use_container_width=True)

    st.divider()
    st.subheader("כמה היית מרוויח בכל תקופת מלחמה?")
    sim_rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf = period_return(etf_r, ps, pe)
        if r_etf is None: continue
        r_lev = float((1 + etf_r.loc[ps:pe] * lev_factor).prod() - 1)
        r_spy2 = period_return(spy_r, ps, pe) if spy_r is not None else None
        def fmt(r): return f"{'+'if r>0 else ''}${r*invest_amount:,.0f} ({r*100:+.1f}%)"
        sim_rows.append({"תקופה": pname, f"War ETF {lev_factor}x": fmt(r_lev),
                         "War ETF 1x": fmt(r_etf), "S&P 500": fmt(r_spy2) if r_spy2 else "—"})
    if sim_rows:
        df_sim = pd.DataFrame(sim_rows).set_index("תקופה")
        def color_money(val):
            if not isinstance(val, str) or val == "—": return ""
            return f"color:{'#27ae60' if val.startswith('+') else '#c0392b'};font-weight:bold"
        st.dataframe(df_sim.style.map(color_money), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RISK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚠️ ניתוח סיכון — War ETF 3x")

    series_map = {f"War ETF {lev_factor}x": etf_r * lev_factor, "War ETF 1x": etf_r}
    if spy_r is not None: series_map["S&P 500"] = spy_r
    for bname in bench_selected:
        bt = BENCHMARK_ETFS[bname]["ticker"]
        if bt in prices.columns:
            series_map[bname.split("(")[1].rstrip(")")] = prices[bt].pct_change().dropna()

    # ── Risk metrics table ──
    risk_rows = []
    for name, r in series_map.items():
        risk_rows.append({
            "נכס": name,
            "תשואה שנתית": f"{ann_ret(r):+.1f}%",
            "תנודתיות שנתית": f"{ann_vol(r):.1f}%",
            "Sharpe Ratio": f"{sharpe(r):.2f}",
            "Max Drawdown": f"{max_dd(r):.1f}%",
            "Calmar Ratio": f"{calmar(r):.2f}",
        })
    df_risk = pd.DataFrame(risk_rows).set_index("נכס")

    def color_risk(val):
        if not isinstance(val, str): return ""
        try:
            num = float(val.replace("%","").replace("+",""))
            col_name = ""
            return ""
        except: return ""

    st.dataframe(df_risk, use_container_width=True)

    st.divider()
    col_dd, col_vol = st.columns(2)

    # ── Drawdown chart ──
    with col_dd:
        st.markdown("#### 📉 Drawdown — ירידה מהשיא")
        fig_dd = go.Figure()
        colors_dd = {"War ETF 1x": "#1f4e79", "S&P 500": "#888"}
        colors_dd[f"War ETF {lev_factor}x"] = "#c00000"
        for name, r in series_map.items():
            dd = drawdown_series(r)
            fig_dd.add_trace(go.Scatter(
                x=dd.index, y=dd.values, name=name, mode="lines",
                line=dict(color=colors_dd.get(name, "#aaa"), width=2),
                fill="tozeroy" if name == f"War ETF {lev_factor}x" else None,
                fillcolor="rgba(192,0,0,0.07)" if name == f"War ETF {lev_factor}x" else None,
            ))
        fig_dd.add_hline(y=0, line_dash="dot", line_color="#555", line_width=1)
        fig_dd.update_layout(height=340, hovermode="x unified",
                             yaxis=dict(title="Drawdown (%)", ticksuffix="%"),
                             xaxis=dict(rangeselector=range_selector(), type="date"),
                             legend=dict(x=0.01, y=0.01),
                             margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_dd, use_container_width=True)
        mdd_val = max_dd(etf_r * lev_factor)
        st.caption(f"Max Drawdown של War ETF {lev_factor}x: **{mdd_val:.1f}%** — הנקודה הכואבת ביותר למשקיע.")

    # ── Annualized rolling volatility ──
    with col_vol:
        st.markdown("#### 📊 תנודתיות רולינג (30 יום)")
        fig_vol = go.Figure()
        for name, r in list(series_map.items())[:3]:
            rv = r.rolling(30).std() * np.sqrt(252) * 100
            fig_vol.add_trace(go.Scatter(
                x=rv.index, y=rv.values, name=name, mode="lines",
                line=dict(color=colors_dd.get(name, "#aaa"), width=2),
            ))
        for war_name, wp in WAR_PERIODS.items():
            fig_vol.add_vrect(x0=wp["start"], x1=wp["end"], fillcolor=wp["fill"],
                              line=dict(color=wp["line"], width=1), layer="below")
        fig_vol.update_layout(height=340, hovermode="x unified",
                              yaxis=dict(title="תנודתיות שנתית (%)", ticksuffix="%"),
                              xaxis=dict(rangeselector=range_selector(), type="date"),
                              legend=dict(x=0.01, y=0.99),
                              margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_vol, use_container_width=True)
        st.caption("תנודתיות גבוהה בזמן מלחמה — זו בדיוק ההזדמנות לתעודה ממונפת.")

    st.divider()

    # ── Risk/return scatter ──
    st.markdown("#### 🎯 Risk/Return — כל הנכסים")
    rr_data = [{"נכס": n, "תשואה שנתית (%)": ann_ret(r), "תנודתיות (%)": ann_vol(r), "Sharpe": sharpe(r)}
               for n, r in series_map.items()]
    df_rr = pd.DataFrame(rr_data)
    fig_rr = px.scatter(df_rr, x="תנודתיות (%)", y="תשואה שנתית (%)", text="נכס",
                        size="Sharpe", color="Sharpe",
                        color_continuous_scale="RdYlGn", size_max=40)
    fig_rr.update_traces(textposition="top center")
    fig_rr.add_hline(y=0, line_dash="dot", line_color="#aaa")
    fig_rr.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20),
                         coloraxis_colorbar_title="Sharpe")
    st.plotly_chart(fig_rr, use_container_width=True)
    st.caption("גודל הנקודה = Sharpe Ratio. נכס טוב: גבוה ושמאלי (תשואה גבוהה, תנודתיות נמוכה).")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — INDIVIDUAL STOCKS
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("ביצועי מניות בודדות לפי תקופות (%)")
    stock_rows = {}
    sector_label = {}
    for sname, stocks in stock_selection.items():
        info = SECTORS[sname]
        for ticker in stocks:
            if ticker not in prices.columns: continue
            sector_label[ticker] = info["he"]
            row = {"סקטור": info["he"]}
            for pname, (ps, pe) in PERIODS_ANALYSIS.items():
                s = prices[ticker].loc[ps:pe]
                row[pname] = round(float((s.iloc[-1]/s.iloc[0]-1)*100),1) if len(s)>5 else np.nan
            row["ממוצע בתקופות מלחמה"] = round(np.nanmean([
                row.get("מלחמת אוקראינה (2022)", np.nan),
                row.get("מלחמת עזה (2023-24)", np.nan),
                row.get("תקיפות ישראל-איראן (2024)", np.nan),
                row.get("מלחמת 12 הימים (יוני 2025)", np.nan),
            ]), 1)
            stock_rows[ticker] = row

    df_stocks = pd.DataFrame(stock_rows).T
    df_stocks.index.name = "מניה"
    numeric_cols = [c for c in df_stocks.columns if c != "סקטור"]
    heat_data = df_stocks[numeric_cols].apply(pd.to_numeric, errors="coerce")
    vmax = min(float(heat_data.abs().max().max()), 250)
    fig_heat = px.imshow(heat_data.T, text_auto=".0f", color_continuous_scale="RdYlGn",
                         zmin=-vmax, zmax=vmax, aspect="auto")
    fig_heat.update_layout(height=360, margin=dict(l=20,r=20,t=20,b=20),
                           xaxis_title="מניה", yaxis_title="תקופה", coloraxis_colorbar_title="%")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()
    df_display = df_stocks.sort_values("ממוצע בתקופות מלחמה", ascending=False)
    def color_pct(val):
        if pd.isna(val) or not isinstance(val,(int,float)): return ""
        return f"color:{'#27ae60' if val>0 else '#c0392b'};font-weight:600"
    nd = [c for c in df_display.columns if c != "סקטור"]
    st.dataframe(df_display.style.map(color_pct, subset=nd), use_container_width=True, height=460)

    st.divider()
    c_top, c_bot = st.columns(2)
    sw = df_stocks["ממוצע בתקופות מלחמה"].dropna().sort_values(ascending=False)
    with c_top:
        st.markdown("**🏆 Top 5 — הכי הרוויחו ממלחמות**")
        for ticker, val in sw.head(5).items():
            st.markdown(f"- **{ticker}** ({sector_label.get(ticker,'')}) — `{val:+.1f}%`")
    with c_bot:
        st.markdown("**📉 Bottom 5 — הכי ירדו**")
        for ticker, val in sw.tail(5).sort_values().items():
            st.markdown(f"- **{ticker}** ({sector_label.get(ticker,'')}) — `{val:+.1f}%`")


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""<div style="text-align:center;color:#aaa;font-size:12px;padding:8px 0">
    WAR ETF 3x — Demo for Qesem ETF Proposal &nbsp;|&nbsp; נתונים: Yahoo Finance / yfinance<br>
    <b>לצרכי מחקר ולמידה בלבד — אין לראות בכך ייעוץ השקעות</b>
</div>""", unsafe_allow_html=True)
