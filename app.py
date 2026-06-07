import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="WAR ETF 3x | קסם תעודות סל",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .sector-card {
        border-left: 5px solid;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 8px;
        background: #fafafa;
        min-height: 160px;
    }
    .war-banner {
        background: linear-gradient(135deg,#0f3460,#16213e,#1a1a2e);
        color: white;
        padding: 22px 30px;
        border-radius: 12px;
        margin-bottom: 24px;
        text-align: center;
    }
    .sim-box {
        background: linear-gradient(135deg,#1a3a1a,#0d260d);
        color: white;
        padding: 20px 28px;
        border-radius: 10px;
        margin: 12px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Definitions ───────────────────────────────────────────────────────────────
SECTORS = {
    "Defense & Aerospace 🛡️": {
        "stocks": ["LMT", "RTX", "NOC", "GD", "HII", "KTOS"],
        "color": "#1f4e79",
        "he": "ביטחון ואוויר",
        "desc": "לוקהיד מרטין, ריית'און, נורת'רופ גרומן, ג'נרל דיינמיקס, HII, Kratos",
    },
    "Cyber & Intelligence 🔐": {
        "stocks": ["CRWD", "PANW", "CACI", "LDOS", "BAH", "SAIC"],
        "color": "#c00000",
        "he": "סייבר ומודיעין",
        "desc": "CrowdStrike, Palo Alto Networks, CACI, Leidos, Booz Allen, SAIC",
    },
    "Energy ⚡": {
        "stocks": ["XOM", "CVX", "COP", "SLB", "HAL", "MPC"],
        "color": "#7030a0",
        "he": "אנרגיה",
        "desc": "אקסון מובייל, שברון, ConocoPhillips, שלומברגר, הליבורטון, Marathon",
    },
    "Raw Materials & Metals ⛏️": {
        "stocks": ["MP", "NEM", "FCX", "AA", "CLF", "GOLD"],
        "color": "#833c00",
        "he": "חומרי גלם ומתכות",
        "desc": "MP Materials, ניומונט (זהב), פריפורט (נחושת), אלקואה, CLF, Barrick",
    },
    "Defense Tech 🚀": {
        "stocks": ["PLTR", "AVAV", "OSIS", "DRS", "AXON", "BWXT"],
        "color": "#375623",
        "he": "טכנולוגיה ביטחונית",
        "desc": "פלאנטיר, AeroVironment (מל\"טים), OSI Systems, Leonardo DRS, Axon, BWXT",
    },
}

BENCHMARK_ETFS = {
    "ITA (iShares Defense ETF)": {"ticker": "ITA", "color": "#2196F3", "dash": "dash"},
    "XAR (SPDR Aerospace ETF)":  {"ticker": "XAR", "color": "#FF9800", "dash": "dot"},
    "PPA (Invesco Defense ETF)": {"ticker": "PPA", "color": "#9C27B0", "dash": "dashdot"},
}

WAR_PERIODS = {
    "פלישת רוסיה לאוקראינה": {
        "start": "2022-02-24", "end": "2022-12-31",
        "fill": "rgba(220,50,50,0.12)", "line": "rgba(220,50,50,0.6)",
    },
    "מלחמת עזה": {
        "start": "2023-10-07", "end": "2024-06-30",
        "fill": "rgba(255,140,0,0.12)", "line": "rgba(255,140,0,0.6)",
    },
}

PERIODS_ANALYSIS = {
    "לפני המלחמות (2021)":      ("2021-01-01", "2022-02-23"),
    "מלחמת אוקראינה (2022)":    ("2022-02-24", "2022-12-31"),
    "בין המלחמות (2023 H1)":    ("2023-01-01", "2023-10-06"),
    "מלחמת עזה (2023-24)":      ("2023-10-07", "2024-06-30"),
}

# ── Data helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    if isinstance(close, pd.Series):
        close = close.to_frame()
    return close.dropna(thresh=int(len(close) * 0.5), axis=1)


def sector_returns(prices: pd.DataFrame, stock_selection: dict[str, list[str]]) -> pd.DataFrame:
    out = {}
    for sname, stocks in stock_selection.items():
        cols = [t for t in stocks if t in prices.columns]
        if cols:
            out[SECTORS[sname]["he"]] = prices[cols].pct_change().mean(axis=1)
    return pd.DataFrame(out).dropna()


def lev_nav(rets: pd.Series, lev: int) -> pd.Series:
    return (1 + rets * lev).cumprod() * 100


def period_return(series: pd.Series, start: str, end: str):
    s = series.loc[start:end]
    return float((1 + s).prod() - 1) if len(s) > 5 else None

# ── Sidebar — stock selection only ───────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ הגדרות")

    st.subheader("סקטורים ומניות")
    stock_selection: dict[str, list[str]] = {}
    for sname, sinfo in SECTORS.items():
        col_check, col_label = st.columns([1, 7])
        sector_on = col_check.checkbox("", value=True, key=f"chk_{sname}", label_visibility="collapsed")
        col_label.markdown(f"**{sname}**")
        if sector_on:
            chosen = st.multiselect(
                f"מניות — {sinfo['he']}",
                options=sinfo["stocks"],
                default=sinfo["stocks"],
                key=f"stocks_{sname}",
                label_visibility="collapsed",
            )
            if chosen:
                stock_selection[sname] = chosen

    st.divider()
    st.subheader("השוואה לתעודות קיימות")
    bench_selected = [
        name for name, info in BENCHMARK_ETFS.items()
        if st.checkbox(name, value=True, key=f"bench_{name}")
    ]

    st.divider()
    lev_factor = st.select_slider("מינוף", options=[1, 2, 3], value=3)

    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if len(stock_selection) < 2:
    st.warning("⚠️ בחר לפחות 2 סקטורים עם מניות כדי לחשב קורלציה.")
    st.stop()

# ── Load full data (fixed wide range) ────────────────────────────────────────
D_START, D_END = "2018-01-01", "2024-12-31"
all_tickers = list({t for stocks in stock_selection.values() for t in stocks})
all_tickers += ["SPY"] + [BENCHMARK_ETFS[b]["ticker"] for b in bench_selected]

with st.spinner("📡 טוען נתוני שוק..."):
    prices = load_prices(all_tickers, D_START, D_END)
    sec_ret_full = sector_returns(prices, stock_selection)

# ── Banner + global period selector ──────────────────────────────────────────
st.markdown("""
<div class="war-banner">
    <h2 style="margin:0">🛡️ WAR ETF 3x</h2>
    <p style="margin:6px 0 0">תעודת סל ממונפת כפול 3 — חשיפה לסקטורי מלחמה</p>
    <small style="opacity:.7">הצעה לקסם תעודות סל | Demo 2025</small>
</div>
""", unsafe_allow_html=True)

# Period selector — shown in page, above tabs
GLOBAL_PERIODS = {
    "📅 כל הזמן":                  ("2021-01-01", "2024-12-31"),
    "🇺🇦 מלחמת אוקראינה":          ("2022-02-24", "2022-12-31"),
    "⚔️ בין המלחמות":              ("2023-01-01", "2023-10-06"),
    "🇮🇱 מלחמת עזה":               ("2023-10-07", "2024-06-30"),
    "🔥 שתי המלחמות יחד":          ("2022-02-24", "2024-06-30"),
    "📆 בחירה חופשית":             None,
}

sel_period = st.radio(
    "בחר תקופה להצגה:",
    list(GLOBAL_PERIODS.keys()),
    horizontal=True,
    index=0,
    label_visibility="visible",
)

if GLOBAL_PERIODS[sel_period] is None:
    fc1, fc2 = st.columns(2)
    d_start = fc1.date_input("מתאריך", value=date(2021, 1, 1), min_value=date(2018, 1, 1))
    d_end   = fc2.date_input("עד תאריך", value=date(2024, 12, 31))
    g_start, g_end = str(d_start), str(d_end)
else:
    g_start, g_end = GLOBAL_PERIODS[sel_period]

# Slice data to the selected period
prices   = prices.loc[g_start:g_end]
sec_ret  = sec_ret_full.loc[g_start:g_end]

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 סקטורים וקורלציה",
    "📈 בק-טסטינג",
    "💰 סימולציית השקעה",
    "🔍 מניות בודדות",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1  —  SECTORS & CORRELATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("הסקטורים שנבחרו לתעודה")

    cols = st.columns(len(stock_selection))
    for i, (sname, stocks) in enumerate(stock_selection.items()):
        info = SECTORS[sname]
        stocks_ok = [t for t in stocks if t in prices.columns]
        total_ret = None
        if stocks_ok:
            r = prices[stocks_ok]
            total_ret = float((r.iloc[-1] / r.iloc[0] - 1).mean() * 100)
        arrow = "▲" if (total_ret or 0) > 0 else "▼"
        ret_color = "#27ae60" if (total_ret or 0) > 0 else "#e74c3c"
        ret_str = f"{arrow} {abs(total_ret):.1f}%" if total_ret is not None else "—"

        cols[i].markdown(f"""
        <div class="sector-card" style="border-color:{info['color']}; background:{info['color']}0d">
            <b style="color:{info['color']};font-size:15px">{info['he']}</b><br>
            <small style="color:#555">{', '.join(stocks_ok)}</small><br><br>
            <span style="font-size:18px;font-weight:700;color:{ret_color}">{ret_str}</span>
            <span style="font-size:11px;color:#888"> {sel_period}</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("מטריצת קורלציה בין הסקטורים")

    corr = sec_ret.corr()
    fig_corr = px.imshow(
        corr, text_auto=".2f",
        color_continuous_scale="RdYlGn_r",
        zmin=-1, zmax=1, aspect="auto",
    )
    fig_corr.update_traces(textfont_size=15, textfont_color="white")
    fig_corr.update_layout(
        height=420, margin=dict(l=20, r=20, t=30, b=20),
        coloraxis_colorbar_title="קורלציה",
        xaxis_title="", yaxis_title="",
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    upper = corr.values[np.triu_indices_from(corr.values, k=1)]
    avg_c = float(upper.mean())
    min_idx = np.unravel_index(np.argmin(corr.values + np.eye(len(corr)) * 99), corr.shape)
    max_idx = np.unravel_index(np.argmax(corr.values - np.eye(len(corr)) * 99), corr.shape)

    m1, m2, m3 = st.columns(3)
    m1.metric("קורלציה ממוצעת", f"{avg_c:.2f}", help="ערך נמוך = גיוון טוב יותר")
    m2.metric("הצמד הכי פחות מתואם",
              f"{corr.index[min_idx[0]].split()[0]} × {corr.columns[min_idx[1]].split()[0]}",
              f"{corr.values[min_idx]:.2f}")
    m3.metric("הצמד הכי מתואם",
              f"{corr.index[max_idx[0]].split()[0]} × {corr.columns[max_idx[1]].split()[0]}",
              f"{corr.values[max_idx]:.2f}")

    if avg_c < 0.6:
        st.success(f"✅ קורלציה ממוצעת {avg_c:.2f} — הסקטורים מגוונים מספיק.")
    elif avg_c < 0.8:
        st.warning(f"⚠️ קורלציה ממוצעת {avg_c:.2f} — גיוון בינוני. שקול להחליף סקטור.")
    else:
        st.error(f"❌ קורלציה ממוצעת {avg_c:.2f} — הסקטורים נעים יחד מדי.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2  —  BACKTESTING
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"War ETF {lev_factor}x — ביצועים היסטוריים והשוואה לתעודות קיימות")

    etf_r = sec_ret.mean(axis=1)
    spy_r = prices["SPY"].pct_change().dropna() if "SPY" in prices.columns else None

    fig_bt = go.Figure()

    for war_name, wp in WAR_PERIODS.items():
        fig_bt.add_vrect(
            x0=wp["start"], x1=wp["end"],
            fillcolor=wp["fill"],
            line=dict(color=wp["line"], width=1, dash="dot"),
            layer="below",
            annotation_text=war_name,
            annotation_position="top left",
            annotation_font_size=11,
        )

    if spy_r is not None:
        fig_bt.add_trace(go.Scatter(
            x=lev_nav(spy_r, 1).index, y=lev_nav(spy_r, 1).values,
            name="S&P 500", line=dict(color="#888", width=1.8, dash="dash"),
        ))

    # Benchmark ETFs
    for bname in bench_selected:
        bticker = BENCHMARK_ETFS[bname]["ticker"]
        if bticker in prices.columns:
            b_r = prices[bticker].pct_change().dropna()
            fig_bt.add_trace(go.Scatter(
                x=lev_nav(b_r, 1).index, y=lev_nav(b_r, 1).values,
                name=bname.split("(")[1].rstrip(")"),
                line=dict(
                    color=BENCHMARK_ETFS[bname]["color"],
                    width=2,
                    dash=BENCHMARK_ETFS[bname]["dash"],
                ),
            ))

    if lev_factor > 1:
        fig_bt.add_trace(go.Scatter(
            x=lev_nav(etf_r, 1).index, y=lev_nav(etf_r, 1).values,
            name="War ETF 1x",
            line=dict(color="#1f4e79", width=2, dash="dot"),
        ))

    fig_bt.add_trace(go.Scatter(
        x=lev_nav(etf_r, lev_factor).index, y=lev_nav(etf_r, lev_factor).values,
        name=f"War ETF {lev_factor}x ⭐",
        line=dict(color="#c00000", width=3.5),
        fill="tozeroy", fillcolor="rgba(192,0,0,0.06)",
    ))

    fig_bt.update_layout(
        height=500, hovermode="x unified",
        xaxis=dict(
            title="תאריך",
            rangeselector=dict(
                buttons=[
                    dict(count=1,  label="1M",  step="month", stepmode="backward"),
                    dict(count=6,  label="6M",  step="month", stepmode="backward"),
                    dict(count=1,  label="YTD", step="year",  stepmode="todate"),
                    dict(count=1,  label="1Y",  step="year",  stepmode="backward"),
                    dict(count=3,  label="3Y",  step="year",  stepmode="backward"),
                    dict(step="all", label="ALL"),
                ],
                bgcolor="#2a2a2a", activecolor="#c00000",
                bordercolor="#555", borderwidth=1,
                font=dict(color="white", size=11),
            ),
            type="date",
        ),
        yaxis_title="שווי תיק (בסיס 100)",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
        margin=dict(l=20, r=20, t=20, b=30),
    )
    st.plotly_chart(fig_bt, use_container_width=True)

    st.divider()

    # Period table — now includes benchmark ETFs
    st.subheader("השוואת תשואות לפי תקופה")

    rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf = period_return(etf_r, ps, pe)
        if r_etf is None:
            continue
        r_lev = period_return(etf_r * lev_factor, ps, pe) if lev_factor > 1 else None
        r_spy = period_return(spy_r, ps, pe) if spy_r is not None else None
        row = {
            "תקופה": pname,
            f"War ETF {lev_factor}x": f"{r_lev*100:+.1f}%" if r_lev else "—",
            "War ETF 1x": f"{r_etf*100:+.1f}%",
            "S&P 500": f"{r_spy*100:+.1f}%" if r_spy else "—",
        }
        for bname in bench_selected:
            bticker = BENCHMARK_ETFS[bname]["ticker"]
            if bticker in prices.columns:
                b_r2 = prices[bticker].pct_change().dropna()
                r_b = period_return(b_r2, ps, pe)
                short = bname.split("(")[1].rstrip(")")
                row[short] = f"{r_b*100:+.1f}%" if r_b else "—"
        rows.append(row)

    if rows:
        df_table = pd.DataFrame(rows).set_index("תקופה")

        def color_cell(val):
            if not isinstance(val, str) or val == "—":
                return ""
            try:
                num = float(val.replace("%", "").replace("+", ""))
                return f"color: {'#27ae60' if num > 0 else '#c0392b'}; font-weight:bold"
            except Exception:
                return ""

        st.dataframe(df_table.style.map(color_cell), use_container_width=True)

    # War bars
    st.divider()
    st.subheader("ביצועי סקטורים בתקופות מלחמה")
    war_col1, war_col2 = st.columns(2)
    for col_w, (war_name, wp) in zip([war_col1, war_col2], WAR_PERIODS.items()):
        sector_perfs = {}
        for sname, stocks in stock_selection.items():
            stocks_ok = [t for t in stocks if t in prices.columns]
            if not stocks_ok:
                continue
            period_p = prices[stocks_ok].loc[wp["start"]:wp["end"]]
            if len(period_p) < 5:
                continue
            perf = float((period_p.iloc[-1] / period_p.iloc[0] - 1).mean() * 100)
            sector_perfs[SECTORS[sname]["he"]] = perf

        if not sector_perfs:
            col_w.info(f"{war_name} — אין נתונים")
            continue

        fig_bar = go.Figure(go.Bar(
            x=list(sector_perfs.values()), y=list(sector_perfs.keys()),
            orientation="h",
            marker_color=["#27ae60" if v > 0 else "#e74c3c" for v in sector_perfs.values()],
            text=[f"{v:+.1f}%" for v in sector_perfs.values()],
            textposition="outside",
        ))
        fig_bar.update_layout(
            title=war_name, height=280,
            margin=dict(l=10, r=60, t=40, b=20),
            xaxis_title="תשואה (%)", showlegend=False,
        )
        col_w.plotly_chart(fig_bar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3  —  INVESTMENT SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    # ── Inputs ──
    st.markdown("### 💰 סימולציית השקעה — כמה היית מרוויח?")
    col_inp, col_view, col_spacer = st.columns([1, 1, 1])
    invest_amount = col_inp.number_input(
        "סכום השקעה ראשוני ($)",
        min_value=100, max_value=10_000_000,
        value=10_000, step=1_000, format="%d",
    )
    chart_mode = col_view.radio("תצוגת גרף", ["$ שווי", "% תשואה"], horizontal=True)
    sim_start, sim_end = g_start, g_end
    st.caption(f"מציג תקופה: **{sel_period}** ({g_start} → {g_end})")
    st.divider()

    etf_r   = sec_ret.mean(axis=1)
    spy_r   = prices["SPY"].pct_change().dropna() if "SPY" in prices.columns else None

    # Slice to the chosen period for the cards
    etf_r_period = etf_r.loc[sim_start:sim_end]
    spy_r_period = spy_r.loc[sim_start:sim_end] if spy_r is not None else None

    etf_1x_val  = (1 + etf_r).cumprod() * invest_amount
    etf_lev_val = (1 + etf_r * lev_factor).cumprod() * invest_amount
    spy_val     = (1 + spy_r).cumprod() * invest_amount if spy_r is not None else None

    def period_final(r_slice):
        return float((1 + r_slice).prod()) * invest_amount if len(r_slice) > 0 else invest_amount

    final_lev = period_final(etf_r_period * lev_factor)
    final_1x  = period_final(etf_r_period)
    final_spy = period_final(spy_r_period) if spy_r_period is not None else None

    profit_lev = final_lev - invest_amount
    profit_1x  = final_1x  - invest_amount
    profit_spy = (final_spy - invest_amount) if final_spy else None

    # ── Hero cards ──
    st.markdown(f"""
    <div style="display:flex; gap:16px; margin-bottom:20px; flex-wrap:wrap;">
        <div style="flex:1; min-width:180px; background:linear-gradient(135deg,#7b0000,#c00000);
                    color:white; padding:20px 24px; border-radius:12px; text-align:center;">
            <div style="font-size:13px; opacity:.8;">War ETF {lev_factor}x</div>
            <div style="font-size:36px; font-weight:900; margin:6px 0;">${final_lev:,.0f}</div>
            <div style="font-size:15px; opacity:.9;">
                {'▲' if profit_lev > 0 else '▼'} ${abs(profit_lev):,.0f}
                &nbsp;({(final_lev/invest_amount-1)*100:+.1f}%)
            </div>
        </div>
        <div style="flex:1; min-width:180px; background:linear-gradient(135deg,#0d3359,#1f4e79);
                    color:white; padding:20px 24px; border-radius:12px; text-align:center;">
            <div style="font-size:13px; opacity:.8;">War ETF 1x</div>
            <div style="font-size:36px; font-weight:900; margin:6px 0;">${final_1x:,.0f}</div>
            <div style="font-size:15px; opacity:.9;">
                {'▲' if profit_1x > 0 else '▼'} ${abs(profit_1x):,.0f}
                &nbsp;({(final_1x/invest_amount-1)*100:+.1f}%)
            </div>
        </div>
        <div style="flex:1; min-width:180px; background:linear-gradient(135deg,#2d2d2d,#444);
                    color:white; padding:20px 24px; border-radius:12px; text-align:center;">
            <div style="font-size:13px; opacity:.8;">S&P 500</div>
            <div style="font-size:36px; font-weight:900; margin:6px 0;">${final_spy:,.0f}</div>
            <div style="font-size:15px; opacity:.9;">
                {'▲' if (profit_spy or 0) > 0 else '▼'} ${abs(profit_spy or 0):,.0f}
                &nbsp;({(final_spy/invest_amount-1)*100:+.1f}%)
            </div>
        </div>
        <div style="flex:1; min-width:180px; background:linear-gradient(135deg,#1a3a1a,#27ae60);
                    color:white; padding:20px 24px; border-radius:12px; text-align:center;">
            <div style="font-size:13px; opacity:.8;">יתרון {lev_factor}x על S&P</div>
            <div style="font-size:36px; font-weight:900; margin:6px 0;">
                x{final_lev/final_spy:.1f}
            </div>
            <div style="font-size:15px; opacity:.9;">
                +${final_lev - final_spy:,.0f} יותר
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Chart ──
    pct_mode = chart_mode == "% תשואה"

    # Slice all series to the chosen period
    etf_r_slice = etf_r.loc[sim_start:sim_end]
    spy_r_slice = spy_r.loc[sim_start:sim_end] if spy_r is not None else None

    def make_series(r_slice, multiplier=1):
        r = r_slice * multiplier
        if pct_mode:
            return ((1 + r).cumprod() - 1) * 100
        else:
            return (1 + r).cumprod() * invest_amount

    fig_sim = go.Figure()

    # War period shading (only if inside the chosen range)
    for war_name, wp in WAR_PERIODS.items():
        if wp["start"] <= sim_end and wp["end"] >= sim_start:
            fig_sim.add_vrect(
                x0=max(wp["start"], sim_start), x1=min(wp["end"], sim_end),
                fillcolor=wp["fill"],
                line=dict(color=wp["line"], width=1, dash="dot"),
                layer="below",
                annotation_text=war_name,
                annotation_position="top left",
                annotation_font_size=11,
            )

    # Zero / baseline line
    fig_sim.add_hline(
        y=0 if pct_mode else invest_amount,
        line_dash="dot", line_color="#999", line_width=1.2,
        annotation_text="  0%" if pct_mode else f"  ${invest_amount:,.0f}",
        annotation_position="right", annotation_font_size=10,
    )

    if spy_r_slice is not None:
        s = make_series(spy_r_slice)
        fig_sim.add_trace(go.Scatter(
            x=s.index, y=s.values,
            name="S&P 500", line=dict(color="#888", width=1.8, dash="dash"),
            hovertemplate="%{y:.1f}%" if pct_mode else "$%{y:,.0f}",
        ))

    for bname in bench_selected:
        bticker = BENCHMARK_ETFS[bname]["ticker"]
        if bticker in prices.columns:
            b_slice = prices[bticker].pct_change().dropna().loc[sim_start:sim_end]
            s = make_series(b_slice)
            fig_sim.add_trace(go.Scatter(
                x=s.index, y=s.values,
                name=bname.split("(")[1].rstrip(")"),
                line=dict(color=BENCHMARK_ETFS[bname]["color"], width=2,
                          dash=BENCHMARK_ETFS[bname]["dash"]),
                hovertemplate="%{y:.1f}%" if pct_mode else "$%{y:,.0f}",
            ))

    if lev_factor > 1:
        s = make_series(etf_r_slice)
        fig_sim.add_trace(go.Scatter(
            x=s.index, y=s.values,
            name="War ETF 1x",
            line=dict(color="#1f4e79", width=2, dash="dot"),
            hovertemplate="%{y:.1f}%" if pct_mode else "$%{y:,.0f}",
        ))

    s_lev = make_series(etf_r_slice, lev_factor)
    fig_sim.add_trace(go.Scatter(
        x=s_lev.index, y=s_lev.values,
        name=f"War ETF {lev_factor}x ⭐",
        line=dict(color="#c00000", width=3.5),
        fill="tozeroy", fillcolor="rgba(192,0,0,0.06)",
        hovertemplate="%{y:.1f}%" if pct_mode else "$%{y:,.0f}",
    ))

    range_buttons = [
        dict(count=1,  label="1M",  step="month", stepmode="backward"),
        dict(count=6,  label="6M",  step="month", stepmode="backward"),
        dict(count=1,  label="YTD", step="year",  stepmode="todate"),
        dict(count=1,  label="1Y",  step="year",  stepmode="backward"),
        dict(count=3,  label="3Y",  step="year",  stepmode="backward"),
        dict(step="all", label="ALL"),
    ]

    fig_sim.update_layout(
        height=460, hovermode="x unified",
        xaxis=dict(
            title="תאריך",
            range=[sim_start, sim_end],
            rangeselector=dict(
                buttons=range_buttons,
                bgcolor="#2a2a2a", activecolor="#c00000",
                bordercolor="#555", borderwidth=1,
                font=dict(color="white", size=11),
            ),
            type="date",
        ),
        yaxis=dict(
            title="תשואה (%)" if pct_mode else "שווי תיק ($)",
            ticksuffix="%" if pct_mode else "",
            tickprefix="" if pct_mode else "$",
            tickformat=".1f" if pct_mode else ",.0f",
        ),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
        margin=dict(l=20, r=20, t=10, b=30),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

    # ── War period breakdown ──
    st.divider()
    st.subheader("כמה היית מרוויח בכל תקופת מלחמה?")

    sim_rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf = period_return(etf_r, ps, pe)
        if r_etf is None:
            continue
        r_lev  = float((1 + etf_r.loc[ps:pe] * lev_factor).prod() - 1)
        r_spy2 = period_return(spy_r, ps, pe) if spy_r is not None else None
        def fmt(r): return f"{'+'if r>0 else ''}${r*invest_amount:,.0f} ({r*100:+.1f}%)"
        sim_rows.append({
            "תקופה": pname,
            f"War ETF {lev_factor}x": fmt(r_lev),
            "War ETF 1x": fmt(r_etf),
            "S&P 500": fmt(r_spy2) if r_spy2 else "—",
        })

    if sim_rows:
        df_sim = pd.DataFrame(sim_rows).set_index("תקופה")

        def color_money(val):
            if not isinstance(val, str) or val == "—":
                return ""
            try:
                sign = 1 if val.startswith("+") else -1
                return f"color: {'#27ae60' if sign > 0 else '#c0392b'}; font-weight:bold"
            except Exception:
                return ""

        st.dataframe(df_sim.style.map(color_money), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4  —  INDIVIDUAL STOCKS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("ביצועי מניות בודדות לפי תקופות (%)")

    stock_rows: dict[str, dict] = {}
    sector_label: dict[str, str] = {}

    for sname, stocks in stock_selection.items():
        info = SECTORS[sname]
        for ticker in stocks:
            if ticker not in prices.columns:
                continue
            sector_label[ticker] = info["he"]
            row = {"סקטור": info["he"]}
            for pname, (ps, pe) in PERIODS_ANALYSIS.items():
                s = prices[ticker].loc[ps:pe]
                row[pname] = round(float((s.iloc[-1] / s.iloc[0] - 1) * 100), 1) if len(s) > 5 else np.nan
            row["ממוצע בתקופות מלחמה"] = round(
                np.nanmean([
                    row.get("מלחמת אוקראינה (2022)", np.nan),
                    row.get("מלחמת עזה (2023-24)", np.nan),
                ]), 1)
            stock_rows[ticker] = row

    df_stocks = pd.DataFrame(stock_rows).T
    df_stocks.index.name = "מניה"

    numeric_cols = [c for c in df_stocks.columns if c != "סקטור"]
    heat_data = df_stocks[numeric_cols].apply(pd.to_numeric, errors="coerce")
    vmax = min(float(heat_data.abs().max().max()), 200)

    fig_heat = px.imshow(
        heat_data.T, text_auto=".0f",
        color_continuous_scale="RdYlGn",
        zmin=-vmax, zmax=vmax, aspect="auto",
    )
    fig_heat.update_layout(
        height=340, margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="מניה", yaxis_title="תקופה",
        coloraxis_colorbar_title="%",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()
    st.subheader("טבלת מניות מלאה")
    df_display = df_stocks.sort_values("ממוצע בתקופות מלחמה", ascending=False)

    def color_pct(val):
        if pd.isna(val) or not isinstance(val, (int, float)):
            return ""
        return f"color: {'#27ae60' if val > 0 else '#c0392b'}; font-weight:600"

    numeric_display = [c for c in df_display.columns if c != "סקטור"]
    st.dataframe(
        df_display.style.map(color_pct, subset=numeric_display),
        use_container_width=True, height=460,
    )

    st.divider()
    col_top, col_bot = st.columns(2)
    war_col = "ממוצע בתקופות מלחמה"
    sorted_war = df_stocks[war_col].dropna().sort_values(ascending=False)

    with col_top:
        st.markdown("**🏆 Top 5 — הכי הרוויחו ממלחמות**")
        for ticker, val in sorted_war.head(5).items():
            st.markdown(f"- **{ticker}** ({sector_label.get(ticker,'')}) — `{val:+.1f}%`")

    with col_bot:
        st.markdown("**📉 Bottom 5 — הכי ירדו בתקופות מלחמה**")
        for ticker, val in sorted_war.tail(5).sort_values().items():
            st.markdown(f"- **{ticker}** ({sector_label.get(ticker,'')}) — `{val:+.1f}%`")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;color:#aaa;font-size:12px;padding:8px 0">
    WAR ETF 3x — Demo for Qesem ETF Proposal &nbsp;|&nbsp; נתונים: Yahoo Finance / yfinance<br>
    <b>לצרכי מחקר ולמידה בלבד — אין לראות בכך ייעוץ השקעות</b>
</div>
""", unsafe_allow_html=True)
