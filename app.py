import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import warnings
warnings.filterwarnings("ignore")

# ── Page config ──────────────────────────────────────────────────────────────
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
        height: 175px;
    }
    .war-banner {
        background: linear-gradient(135deg,#0f3460,#16213e,#1a1a2e);
        color: white;
        padding: 22px 30px;
        border-radius: 12px;
        margin-bottom: 24px;
        text-align: center;
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

WAR_PERIODS = {
    "פלישת רוסיה לאוקראינה": {
        "start": "2022-02-24",
        "end": "2022-12-31",
        "fill": "rgba(220,50,50,0.12)",
        "line": "rgba(220,50,50,0.6)",
    },
    "מלחמת עזה": {
        "start": "2023-10-07",
        "end": "2024-06-30",
        "fill": "rgba(255,140,0,0.12)",
        "line": "rgba(255,140,0,0.6)",
    },
}

PERIODS_ANALYSIS = {
    "לפני המלחמות (2021)": ("2021-01-01", "2022-02-23"),
    "מלחמת אוקראינה (2022)": ("2022-02-24", "2022-12-31"),
    "בין המלחמות (2023 H1)": ("2023-01-01", "2023-10-06"),
    "מלחמת עזה (2023-24)": ("2023-10-07", "2024-06-30"),
}

# ── Data helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    return close.dropna(thresh=int(len(close) * 0.5), axis=1)


def sector_returns(prices: pd.DataFrame, sectors: list[str]) -> pd.DataFrame:
    out = {}
    for s in sectors:
        cols = [t for t in SECTORS[s]["stocks"] if t in prices.columns]
        if cols:
            out[SECTORS[s]["he"]] = prices[cols].pct_change().mean(axis=1)
    return pd.DataFrame(out).dropna()


def lev_nav(rets: pd.Series, lev: int) -> pd.Series:
    return (1 + rets * lev).cumprod() * 100


def period_return(series: pd.Series, start: str, end: str) -> float | None:
    s = series.loc[start:end]
    return float((1 + s).prod() - 1) if len(s) > 5 else None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ הגדרות")
    st.subheader("סקטורים לתעודה")
    selected = [s for s in SECTORS if st.checkbox(s, value=True, key=s)]

    st.divider()
    st.subheader("תקופת בק-טסטינג")
    d_start = st.date_input("מתאריך", value=date(2021, 1, 1), min_value=date(2018, 1, 1))
    d_end   = st.date_input("עד תאריך", value=date(2024, 12, 31))

    st.divider()
    lev_factor = st.select_slider("מינוף", options=[1, 2, 3], value=3)

    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if len(selected) < 2:
    st.warning("⚠️ בחר לפחות 2 סקטורים כדי לחשב קורלציה.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
all_tickers = list({t for s in selected for t in SECTORS[s]["stocks"]}) + ["SPY"]

with st.spinner("📡 טוען נתוני שוק..."):
    prices = load_prices(all_tickers, str(d_start), str(d_end))
    sec_ret = sector_returns(prices, selected)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="war-banner">
    <h2 style="margin:0">🛡️ WAR ETF 3x</h2>
    <p style="margin:6px 0 0">תעודת סל ממונפת כפול 3 — חשיפה לסקטורי מלחמה</p>
    <small style="opacity:.7">הצעה לקסם תעודות סל | Demo 2025</small>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 סקטורים וקורלציה", "📈 בק-טסטינג", "🔍 מניות בודדות"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1  —  SECTORS & CORRELATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("הסקטורים שנבחרו לתעודה")

    cols = st.columns(len(selected))
    for i, sname in enumerate(selected):
        info = SECTORS[sname]
        stocks_ok = [t for t in info["stocks"] if t in prices.columns]
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
            <span style="font-size:12px;color:#444">{info['desc']}</span><br><br>
            <span style="font-size:18px;font-weight:700;color:{ret_color}">{ret_str}</span>
            <span style="font-size:11px;color:#888"> מתחילת התקופה</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Correlation heatmap
    st.subheader("מטריצת קורלציה בין הסקטורים")

    corr = sec_ret.corr()
    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdYlGn_r",
        zmin=-1, zmax=1,
        aspect="auto",
    )
    fig_corr.update_traces(textfont_size=15, textfont_color="white")
    fig_corr.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        coloraxis_colorbar_title="קורלציה",
        xaxis_title="",
        yaxis_title="",
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    # Summary metrics below the matrix
    upper = corr.values[np.triu_indices_from(corr.values, k=1)]
    avg_c = float(upper.mean())
    min_idx = np.unravel_index(np.argmin(corr.values + np.eye(len(corr)) * 99), corr.shape)
    max_idx = np.unravel_index(np.argmax(corr.values - np.eye(len(corr)) * 99), corr.shape)

    m1, m2, m3 = st.columns(3)
    m1.metric("קורלציה ממוצעת", f"{avg_c:.2f}",
              help="ערך נמוך = גיוון טוב יותר בתעודה")
    m2.metric("הצמד הכי פחות מתואם",
              f"{corr.index[min_idx[0]].split()[0]} × {corr.columns[min_idx[1]].split()[0]}",
              f"{corr.values[min_idx]:.2f}")
    m3.metric("הצמד הכי מתואם",
              f"{corr.index[max_idx[0]].split()[0]} × {corr.columns[max_idx[1]].split()[0]}",
              f"{corr.values[max_idx]:.2f}")

    # Explanation box
    if avg_c < 0.6:
        st.success(f"✅ קורלציה ממוצעת של {avg_c:.2f} — הסקטורים מגוונים מספיק. זה טוב לתעודת הסל.")
    elif avg_c < 0.8:
        st.warning(f"⚠️ קורלציה ממוצעת של {avg_c:.2f} — גיוון בינוני. שקול להחליף סקטור.")
    else:
        st.error(f"❌ קורלציה ממוצעת של {avg_c:.2f} — הסקטורים נעים יחד מדי. שנה את הבחירה.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2  —  BACKTESTING
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"War ETF {lev_factor}x vs S&P 500 — ביצועים היסטוריים")

    etf_r = sec_ret.mean(axis=1)
    spy_r = prices["SPY"].pct_change().dropna() if "SPY" in prices.columns else None

    # Build performance chart
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
            x=lev_nav(spy_r, 1).index,
            y=lev_nav(spy_r, 1).values,
            name="S&P 500",
            line=dict(color="#888", width=1.8, dash="dash"),
        ))

    if lev_factor > 1:
        fig_bt.add_trace(go.Scatter(
            x=lev_nav(etf_r, 1).index,
            y=lev_nav(etf_r, 1).values,
            name="War ETF 1x",
            line=dict(color="#1f4e79", width=2, dash="dot"),
        ))

    fig_bt.add_trace(go.Scatter(
        x=lev_nav(etf_r, lev_factor).index,
        y=lev_nav(etf_r, lev_factor).values,
        name=f"War ETF {lev_factor}x ⭐",
        line=dict(color="#c00000", width=3.5),
        fill="tozeroy",
        fillcolor="rgba(192,0,0,0.06)",
    ))

    fig_bt.update_layout(
        height=480,
        hovermode="x unified",
        xaxis_title="תאריך",
        yaxis_title="שווי תיק (בסיס 100)",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
        margin=dict(l=20, r=20, t=20, b=30),
    )
    st.plotly_chart(fig_bt, use_container_width=True)

    st.divider()

    # Period comparison table
    st.subheader("השוואת תשואות לפי תקופה")

    rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf   = period_return(etf_r, ps, pe)
        r_lev   = period_return(etf_r * lev_factor, ps, pe) if lev_factor > 1 else None
        r_spy   = period_return(spy_r, ps, pe) if spy_r is not None else None
        if r_etf is None:
            continue
        rows.append({
            "תקופה": pname,
            f"War ETF {lev_factor}x": f"{r_lev*100:+.1f}%" if r_lev else "—",
            "War ETF 1x": f"{r_etf*100:+.1f}%",
            "S&P 500": f"{r_spy*100:+.1f}%" if r_spy is not None else "—",
            "עודף vs S&P (ETF 1x)": f"{(r_etf-(r_spy or 0))*100:+.1f}%" if r_spy is not None else "—",
        })

    if rows:
        df_table = pd.DataFrame(rows).set_index("תקופה")

        def color_cell(val):
            if not isinstance(val, str) or val == "—":
                return ""
            try:
                num = float(val.replace("%", "").replace("+", ""))
                return f"color: {'#27ae60' if num > 0 else '#c0392b'}; font-weight: bold"
            except Exception:
                return ""

        st.dataframe(df_table.style.map(color_cell), use_container_width=True)

    # War performance bars
    st.divider()
    st.subheader("ביצועי סקטורים בתקופות מלחמה")

    war_col1, war_col2 = st.columns(2)
    for col_w, (war_name, wp) in zip([war_col1, war_col2], WAR_PERIODS.items()):
        sector_perfs = {}
        for sname in selected:
            info = SECTORS[sname]
            stocks_ok = [t for t in info["stocks"] if t in prices.columns]
            if not stocks_ok:
                continue
            period_p = prices[stocks_ok].loc[wp["start"]:wp["end"]]
            if len(period_p) < 5:
                continue
            perf = float((period_p.iloc[-1] / period_p.iloc[0] - 1).mean() * 100)
            sector_perfs[info["he"]] = perf

        if not sector_perfs:
            col_w.info(f"{war_name} — אין נתונים מספיקים")
            continue

        fig_bar = go.Figure(go.Bar(
            x=list(sector_perfs.values()),
            y=list(sector_perfs.keys()),
            orientation="h",
            marker_color=["#27ae60" if v > 0 else "#e74c3c" for v in sector_perfs.values()],
            text=[f"{v:+.1f}%" for v in sector_perfs.values()],
            textposition="outside",
        ))
        fig_bar.update_layout(
            title=war_name,
            height=280,
            margin=dict(l=10, r=60, t=40, b=20),
            xaxis_title="תשואה (%)",
            xaxis_zeroline=True,
            xaxis_zerolinecolor="#333",
            showlegend=False,
        )
        col_w.plotly_chart(fig_bar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3  —  INDIVIDUAL STOCKS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("ביצועי מניות בודדות לפי תקופות (%)")

    stock_rows: dict[str, dict] = {}
    sector_label: dict[str, str] = {}

    for sname in selected:
        info = SECTORS[sname]
        for ticker in info["stocks"]:
            if ticker not in prices.columns:
                continue
            sector_label[ticker] = info["he"]
            row = {"סקטור": info["he"]}
            for pname, (ps, pe) in PERIODS_ANALYSIS.items():
                s = prices[ticker].loc[ps:pe]
                row[pname] = round(float((s.iloc[-1] / s.iloc[0] - 1) * 100), 1) if len(s) > 5 else np.nan
            row["ממוצע בתקופות מלחמה"] = round(
                np.nanmean([row.get("מלחמת אוקראינה (2022)", np.nan),
                            row.get("מלחמת עזה (2023-24)", np.nan)]), 1)
            stock_rows[ticker] = row

    df_stocks = pd.DataFrame(stock_rows).T
    df_stocks.index.name = "מניה"

    # Heatmap of numeric columns
    numeric_cols = [c for c in df_stocks.columns if c != "סקטור"]
    heat_data = df_stocks[numeric_cols].apply(pd.to_numeric, errors="coerce")

    vmax = min(float(heat_data.abs().max().max()), 200)

    fig_heat = px.imshow(
        heat_data.T,
        text_auto=".0f",
        color_continuous_scale="RdYlGn",
        zmin=-vmax, zmax=vmax,
        aspect="auto",
    )
    fig_heat.update_layout(
        height=340,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="מניה",
        yaxis_title="תקופה",
        coloraxis_colorbar_title="%",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # Sortable table
    st.subheader("טבלת מניות מלאה")
    df_display = df_stocks.sort_values("ממוצע בתקופות מלחמה", ascending=False)

    def color_pct(val):
        if pd.isna(val) or not isinstance(val, (int, float)):
            return ""
        return f"color: {'#27ae60' if val > 0 else '#c0392b'}; font-weight:600"

    numeric_display = [c for c in df_display.columns if c != "סקטור"]
    st.dataframe(
        df_display.style.map(color_pct, subset=numeric_display),
        use_container_width=True,
        height=460,
    )

    st.divider()

    # Top/Bottom in war periods
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
