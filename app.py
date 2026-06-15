import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Kesem WAR Leverage x3 (WAR3) | קסם תעודות סל", page_icon="🛡️", layout="wide")

# ── Design system (minimal-luxury dark) ─────────────────────────────────────────
ACCENT   = "#b21e35"   # בורדו — צבע ההדגשה היחיד
POS      = "#29c46b"   # ירוק לתשואה חיובית
NEG      = "#ef4444"   # אדום לשלילי
MUTED    = "#8b93a3"
SURFACE  = "#141922"
BORDER   = "#232a36"

st.markdown(f"""
<style>
    .block-container {{ padding-top: 1.4rem; max-width: 1280px; }}
    /* עברית — RTL על התוכן הראשי בלבד (הסיידבר נשאר משמאל כדי שהקיפול יעבוד) */
    .block-container {{ direction: rtl; }}
    .block-container p, .block-container li,
    .block-container h1, .block-container h2, .block-container h3,
    .block-container h4 {{ text-align: right; }}
    [data-testid="stSidebar"] {{ direction: rtl; text-align: right; }}
    /* טבלאות ומספרים נשארים LTR לקריאות נכונה */
    [data-testid="stDataFrame"], .js-plotly-plot {{ direction: ltr; }}
    h1, h2, h3 {{ letter-spacing: .2px; }}
    .hero {{
        background: linear-gradient(135deg,#161b24,#0c0f14);
        border: 1px solid {BORDER}; border-bottom: 3px solid {ACCENT};
        border-radius: 16px; padding: 26px 30px; text-align: center; margin-bottom: 20px;
    }}
    .hero-title {{ font-size: 34px; font-weight: 900; letter-spacing: 1px; color: #fff; margin: 0; }}
    .hero-sub   {{ color: #b9c0cc; margin-top: 6px; font-size: 15px; }}
    .hero-tag   {{ color: {MUTED}; font-size: 11px; margin-top: 10px;
                   text-transform: uppercase; letter-spacing: 3px; }}
    .kpi {{
        background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px;
        padding: 16px 14px; text-align: center; height: 100%;
    }}
    .kpi-label {{ font-size: 12px; color: {MUTED}; }}
    .kpi-value {{ font-size: 29px; font-weight: 800; margin: 7px 0 4px; line-height: 1; }}
    .kpi-sub   {{ font-size: 11px; color: #6b7280; }}
    .sector-card {{
        background: {SURFACE}; border: 1px solid {BORDER}; border-right: 4px solid;
        border-radius: 12px; padding: 14px 16px; height: 100%;
    }}
    .sector-name {{ font-size: 15px; font-weight: 800; }}
    .sector-tk   {{ font-size: 12px; color: {MUTED}; }}
</style>
""", unsafe_allow_html=True)

def kpi(label, value, sub, color="#e6e8ec"):
    return (f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')

def pos_neg(v):
    return POS if v >= 0 else NEG

# ── Definitions ─────────────────────────────────────────────────────────────────
SECTORS = {
    "סקטור 1: תעשיות ביטחוניות 🛡️": {
        "stocks": ["LMT", "RTX", "NOC", "GD", "HII", "LHX"],
        "color": "#3b82f6", "he": "תעשיות ביטחוניות",
        "desc": "חברות תעשייה כבדה בעלות חוזים ממשלתיים קשיחים הנהנות מזינוק מיידי ב\"צבר ההזמנות\" בעת הסלמה.",
    },
    "סקטור 2: סייבר הגנתי 🔐": {
        "stocks": ["CRWD", "PANW", "ZS", "FTNT", "NET", "S"],
        "color": "#10b981", "he": "סייבר הגנתי",
        "desc": "חברות טכנולוגיית אבטחה לענן. מלחמות מודרניות כוללות חזית דיגיטלית המאלצת הקפצת תקציבי הגנה.",
    },
    "סקטור 3: אנרגיה מסורתית ⛽": {
        "stocks": ["XOM", "CVX", "COP", "SLB", "HAL", "MPC"],
        "color": "#f59e0b", "he": "אנרגיה מסורתית",
        "desc": "חברות הפקה וזיקוק נפט וגז. סכסוכים משבשים אספקה ומזניקים את מחירי החביות ושולי הרווח.",
    },
    "סקטור 4: ספנות ותובלה 🚢": {
        "stocks": ["ZIM", "FRO", "STNG", "GSL", "MATX", "KEX"],
        "color": "#8b5cf6", "he": "ספנות ותובלה",
        "desc": "חברות צי מיכליות. חסימת נתיבי שיט מאלצת הארכת מסלולים המקפיצה את מחירי השילוח העולמיים.",
    },
    "סקטור 5: תקשורת לוויינית ומודיעין 🛰️": {
        "stocks": ["PLTR", "IRDM", "VSAT", "GSAT", "LDOS", "CACI"],
        "color": "#06b6d4", "he": "תקשורת לוויינית ומודיעין",
        "desc": "חברות המפעילות לוויינים ומערכות AI בזמן אמת. ביקוש קריטי למידע וניווט במקומות בהם נפגעו תשתיות.",
    },
}

BENCHMARK_ETFS = {
    "ITA (iShares Defense ETF)": {"ticker": "ITA", "color": "#2196F3", "dash": "dash"},
    "XAR (SPDR Aerospace ETF)":  {"ticker": "XAR", "color": "#FF9800", "dash": "dot"},
    "PPA (Invesco Defense ETF)": {"ticker": "PPA", "color": "#9C27B0", "dash": "dashdot"},
    "הראל ת\"א בטחוניות 🇮🇱": {"ticker": "HRL_DEF", "color": "#2e7d32", "dash": "longdash",
                              "custom": "harel_ta_defense.csv"},
}

WAR_PERIODS = {
    "פלישת רוסיה לאוקראינה":        {"start": "2022-02-24", "end": "2022-12-31", "fill": "rgba(220,50,50,0.10)",  "line": "rgba(220,50,50,0.5)"},
    "מלחמת עזה":                    {"start": "2023-10-07", "end": "2024-06-30", "fill": "rgba(255,140,0,0.10)", "line": "rgba(255,140,0,0.5)"},
    "תקיפות ישראל-איראן 2024":      {"start": "2024-04-13", "end": "2024-10-31", "fill": "rgba(130,80,220,0.10)", "line": "rgba(130,80,220,0.5)"},
    "מלחמת 12 הימים ישראל-איראן":   {"start": "2025-06-13", "end": "2025-06-24", "fill": "rgba(0,180,255,0.12)", "line": "rgba(0,180,255,0.6)"},
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
    "שם הקרן": "Kesem WAR Leverage x3 (WAR3)",
    "מנהל הקרן": "קסם תעודות סל (קבוצת הפניקס)",
    "נאמן": "מזרחי טפחות חברה לנאמנויות בע\"מ",
    "סוג קרן": "קרן פטורה",
    "דמי ניהול (TER)": "2% לשנה",
    "דמי נאמן": "0.03% לשנה",
    "סה\"כ עלות למשקיע": "2.03% לשנה",
    "מינוף": "3x — daily rebalancing via swaps",
    "בורסה": "הבורסה לני\"ע בתל אביב (TASE)",
    "מספר מניות": "30 מניות ב-5 סקטורים",
    "ריבאלנסינג": "יומי — כדי לשמור על מינוף קבוע",
    "AUM מינימלי להשקה": "₪200M",
    "מדיניות דיבידנד": "צבירה (Accumulating)",
    "מטבע מסחר": "שקל (₪) — נכסי בסיס דולריים",
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

# תחילת הנתונים האחידה — כל הסל (30 המניות) קיים מ-2021. כל סרגלי הזמן חסומים לכאן.
DATA_START = "2021-01-01"
DATA_START_DATE = date(2021, 1, 1)

# ── Risk helpers ────────────────────────────────────────────────────────────────
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

def drawdown_series(rets):
    cum = (1 + rets).cumprod()
    return (cum / cum.expanding().max() - 1) * 100

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers, start, end):
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    if isinstance(close, pd.Series):
        close = close.to_frame()
    return close.dropna(thresh=int(len(close) * 0.5), axis=1)

@st.cache_data(ttl=3600, show_spinner=False)
def load_custom_series(csv_name):
    """קורא קרן מקובץ CSV מקומי (snapshot מגלובס) ומחזיר סדרת מחירי סגירה לפי תאריך."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), csv_name)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df["close"]

def bench_label(name):
    """תווית קצרה לגרף: החלק בסוגריים אם קיים, אחרת השם המלא."""
    return name.split("(")[1].rstrip(")") if "(" in name else name

def sector_returns(prices, stock_selection):
    out = {}
    for sname, stocks in stock_selection.items():
        cols = [t for t in stocks if t in prices.columns]
        if cols:
            out[SECTORS[sname]["he"]] = prices[cols].pct_change().mean(axis=1)
    return pd.DataFrame(out).dropna()

def fund_weights(stock_selection, cap=0.20):
    """מנוע משקולות שיטתי: משקל שווה לסקטור (20%) ולמניה בתוכו, ואז אכיפת תקרת
    משקל קשיחה של `cap` למניה בודדת מתוך כלל הקרן, עם דילול ופיזור-מחדש אוטומטי."""
    n_sec = len(stock_selection)
    rows = []
    for sname, stocks in stock_selection.items():
        if not stocks:
            continue
        per = (1.0 / n_sec) / len(stocks)
        for t in stocks:
            rows.append({"מניה": t, "סקטור": SECTORS[sname]["he"], "color": SECTORS[sname]["color"], "w": per})
    df = pd.DataFrame(rows)
    # אכיפת תקרה עם פיזור-מחדש (איטרטיבי, עד התכנסות)
    for _ in range(20):
        over = df["w"] > cap + 1e-12
        if not over.any():
            break
        excess = float((df.loc[over, "w"] - cap).sum())
        df.loc[over, "w"] = cap
        room = ~over
        base = float(df.loc[room, "w"].sum())
        if base <= 0:
            break
        df.loc[room, "w"] += excess * df.loc[room, "w"] / base
    return df

# עלויות המוצר הממונף — מנוכות מהתשואה כדי שהמספרים יהיו נטו (ולא ברוטו אופטימי)
TER_ANNUAL   = 0.02    # דמי ניהול קסם (2%)
FINANCE_RATE = 0.045   # עלות מימון המינוף ≈ ריבית חסרת-סיכון, על החלק המושאל
TRADING_DAYS = 252

def lev_net(rets, lev):
    """תשואה יומית ממונפת נטו: מינוף×תשואת הסל פחות עלות יומית (TER + מימון על החלק הממונף).
    ב-lev=1 מחזיר ברוטו — מתאים לקווי ייחוס (S&P / תעודות אמיתיות שכבר כוללות עלויות)."""
    daily = rets * lev
    if lev > 1:
        daily = daily - (TER_ANNUAL + (lev - 1) * FINANCE_RATE) / TRADING_DAYS
    return daily

def lev_nav(rets, lev):
    return (1 + lev_net(rets, lev)).cumprod() * 100

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
        bgcolor="#1c2230", activecolor=ACCENT,
        bordercolor=BORDER, borderwidth=1,
        font=dict(color="white", size=11),
    )

def style_fig(fig):
    """אחידות עיצובית לכל הגרפים — מקרא שקוף, מרווחים נקיים."""
    fig.update_layout(
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig

# ── Sidebar (פשוט — מתקדם מוסתר) ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ הגדרות")
    lev_factor = st.select_slider("מינוף", options=[1, 2, 3], value=3,
                                  help="רמת המינוף של התעודה")

    with st.expander("הגדרות מתקדמות", expanded=False):
        st.caption("סקטורים ומניות")
        stock_selection = {}
        for sname, sinfo in SECTORS.items():
            on = st.checkbox(sname, value=True, key=f"chk_{sname}")
            if on:
                chosen = st.multiselect(
                    f"מניות — {sinfo['he']}", options=sinfo["stocks"],
                    default=sinfo["stocks"], key=f"stocks_{sname}",
                    label_visibility="collapsed",
                )
                if chosen:
                    stock_selection[sname] = chosen

        st.caption("השוואה לתעודות קיימות")
        bench_selected = [n for n in BENCHMARK_ETFS
                          if st.checkbox(n, value=True, key=f"bench_{n}")]

    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("נתונים: Yahoo Finance · TASE/גלובס")

if len(stock_selection) < 2:
    st.warning("⚠️ בחר לפחות 2 סקטורים ב'הגדרות מתקדמות'.")
    st.stop()

# ── Load data ───────────────────────────────────────────────────────────────────
all_tickers = list({t for s in stock_selection.values() for t in s})
all_tickers += ["SPY"] + [BENCHMARK_ETFS[b]["ticker"] for b in bench_selected
                          if "custom" not in BENCHMARK_ETFS[b]]

with st.spinner("📡 טוען נתוני שוק..."):
    prices_full = load_prices(all_tickers, DATA_START, str(date.today()))
    # קרנות מ-CSV מקומי (כמו הראל ת"א בטחוניות) — מיישרים לימי המסחר עם ffill
    for b in bench_selected:
        cfg = BENCHMARK_ETFS[b]
        if "custom" in cfg:
            s = load_custom_series(cfg["custom"])
            if s is not None and not s.empty:
                prices_full[cfg["ticker"]] = s.reindex(prices_full.index, method="ffill")
    sec_ret_full = sector_returns(prices_full, stock_selection)

# ── Brand / logo ────────────────────────────────────────────────────────────────
# אם קיים qesem_logo.png בתיקייה — מוצג אוטומטית. אחרת מוצג wordmark טקסטואלי.
import os as _os
_LOGO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "qesem_logo.png")
if _os.path.exists(_LOGO):
    _lc = st.columns([2, 1, 2])
    _lc[1].image(_LOGO, use_container_width=True)

# ── Hero ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="hero-tag" style="margin:0 0 8px;color:{ACCENT}">◆ קסם תעודות סל · קבוצת הפניקס</div>
    <div class="hero-title">🛡️ Kesem WAR Leverage ×3</div>
    <div class="hero-sub">תעודת סל ממונפת ×3 — חשיפה ממוקדת לכלכלת מלחמה</div>
    <div class="hero-tag">WAR3 · הצעה למחלקת המוצרים · קסם תעודות סל</div>
</div>
""", unsafe_allow_html=True)

# ── Period selector ─────────────────────────────────────────────────────────────
sel_period = st.radio("תקופת ניתוח", list(GLOBAL_PERIODS.keys()), horizontal=True, index=0)
if GLOBAL_PERIODS[sel_period] is None:
    fc1, fc2 = st.columns(2)
    d_s = fc1.date_input("מתאריך", value=DATA_START_DATE, min_value=DATA_START_DATE, max_value=date.today())
    d_e = fc2.date_input("עד תאריך", value=date.today(), min_value=DATA_START_DATE, max_value=date.today())
    g_start, g_end = str(d_s), str(d_e)
else:
    g_start, g_end = GLOBAL_PERIODS[sel_period]

prices  = prices_full.loc[g_start:g_end]
sec_ret = sec_ret_full.loc[g_start:g_end]

# Common series
etf_r     = sec_ret.mean(axis=1)
spy_r     = prices["SPY"].pct_change().dropna() if "SPY" in prices.columns else None
etf_r_lev = lev_net(etf_r, lev_factor)   # נטו: בניכוי דמי ניהול + מימון מינוף

tab_story, tab_perf, tab_sim, tab_biz = st.tabs([
    "🎯 ההזדמנות",
    "📈 ביצועים וסיכון",
    "💰 סימולציית השקעה",
    "💼 מודל עסקי ומבנה",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ההזדמנות (story + thesis + sectors)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_story:
    # KPIs
    tot_ret_lev = ann_ret(etf_r_lev)
    tot_ret_1x  = ann_ret(etf_r)
    spy_ret     = ann_ret(spy_r) if spy_r is not None else 0
    sr_lev, mdd_lev, vol_lev, cal_lev = sharpe(etf_r_lev), max_dd(etf_r_lev), ann_vol(etf_r_lev), calmar(etf_r_lev)

    cards = st.columns(6)
    cards[0].markdown(kpi("תשואה שנתית", f"{tot_ret_lev:+.1f}%", f"ETF {lev_factor}x · נטו", pos_neg(tot_ret_lev)), unsafe_allow_html=True)
    cards[1].markdown(kpi("עודף על S&P", f"{tot_ret_lev-spy_ret:+.1f}%", "תשואה עודפת", pos_neg(tot_ret_lev-spy_ret)), unsafe_allow_html=True)
    cards[2].markdown(kpi("Sharpe", f"{sr_lev:.2f}", "תשואה מותאמת-סיכון", ACCENT), unsafe_allow_html=True)
    cards[3].markdown(kpi("Max Drawdown", f"{mdd_lev:.1f}%", "ירידה מקסימלית", NEG), unsafe_allow_html=True)
    cards[4].markdown(kpi("תנודתיות", f"{vol_lev:.1f}%", "שנתית", "#e6e8ec"), unsafe_allow_html=True)
    cards[5].markdown(kpi("Calmar", f"{cal_lev:.2f}", "תשואה / סיכון", ACCENT), unsafe_allow_html=True)

    st.caption(f"📌 כל המספרים הממונפים מוצגים **נטו** — בניכוי דמי ניהול {TER_ANNUAL*100:.0f}% "
               f"ועלות מימון המינוף (~{FINANCE_RATE*100:.1f}% שנתי על החלק המושאל).")

    st.divider()
    st.markdown("### 💡 התזה")
    st.markdown(f"""
**🌍 עולם עם יותר מלחמות** — מאז 2022 פרצו 3 מלחמות גדולות (אוקראינה, עזה, איראן).
שוק תעודות הסל הקיים לא מציע חשיפה ממוקדת וממונפת לתמה הזו.

**📈 ביצועי מלחמה עוקפים את השוק** — ב-{len(WAR_PERIODS)} תקופות מלחמה שנבחנו,
הסקטורים בתעודה עשו בממוצע `{tot_ret_1x:.1f}%` שנתי לעומת `{spy_ret:.1f}%` ב-S&P 500.

**🛡️ מינוף ×{lev_factor} על הנכס הנכון** — חשיפה מובנית ל-30 מניות מ-5 סקטורים שמרוויחים בזמן הסלמה.

**🆕 מוצר ייחודי בשוק** — אין היום תעודה ממונפת ×3 עם פוקוס על כלכלת מלחמה.
ITA/XAR/PPA הן ×1 בלבד ולא כוללות סייבר, אנרגיה וספנות.
    """)

    st.divider()
    st.markdown("### 🧩 הסקטורים בתעודה")
    scols = st.columns(len(stock_selection))
    for i, (sname, stocks) in enumerate(stock_selection.items()):
        info = SECTORS[sname]
        ok = [t for t in stocks if t in prices.columns]
        tr = float((prices[ok].iloc[-1] / prices[ok].iloc[0] - 1).mean() * 100) if ok else None
        ret_html = (f'<span style="color:{pos_neg(tr)};font-weight:800;font-size:18px">'
                    f'{"▲" if (tr or 0)>=0 else "▼"} {abs(tr):.1f}%</span>') if tr is not None else "—"
        scols[i].markdown(f"""
        <div class="sector-card" style="border-right-color:{info['color']}">
            <div class="sector-name" style="color:{info['color']}">{info['he']}</div>
            <div class="sector-tk">{', '.join(ok)}</div>
            <div style="margin-top:10px">{ret_html}
            <span style="font-size:11px;color:{MUTED}"> · {sel_period}</span></div>
        </div>""", unsafe_allow_html=True)

    with st.expander("⚙️ מנוע ניהול המשקולות — אכיפת תקרת 20% למניה"):
        wdf = fund_weights(stock_selection, cap=0.20).sort_values("w", ascending=True)
        fig_w = go.Figure(go.Bar(
            x=(wdf["w"] * 100).values, y=wdf["מניה"].values, orientation="h",
            marker_color=wdf["color"].values,
            text=[f"{v*100:.1f}%" for v in wdf["w"]], textposition="outside",
            customdata=wdf["סקטור"].values,
            hovertemplate="%{y} · %{customdata}<br>משקל: %{x:.2f}%<extra></extra>",
        ))
        fig_w.add_vline(x=20, line_dash="dot", line_color=ACCENT, line_width=1.5,
                        annotation_text="תקרה 20%", annotation_position="top")
        fig_w.update_layout(height=520, xaxis=dict(title="משקל בקרן (%)", ticksuffix="%", range=[0, 22]),
                            yaxis=dict(title=""))
        st.plotly_chart(style_fig(fig_w), use_container_width=True)
        mx = float(wdf["w"].max()) * 100
        st.caption(f"האלגוריתם מקצה משקל שווה ואוכף תקרה קשיחה של 20% למניה. "
                   f"המשקל הגבוה ביותר כרגע: **{mx:.1f}%** — ✅ כל המניות מתחת לתקרה "
                   f"(אם מניה הייתה חורגת, היה מתבצע דילול ופיזור-מחדש אוטומטי).")

    with st.expander("📋 מתודולוגיה וגילוי נאות — חשוב לקרוא"):
        st.markdown(f"""
**מנוע שיטתי מבוסס-כללים:** לכל סקטור מוגדר יוניברס של 6 החברות המובילות בנזילות ובשווי-שוק. האלגוריתם
מקצה משקל שווה (20% לסקטור, ≈16.7% למניה) ו**אוכף תקרת משקל קשיחה של 20% למניה בודדת** עם דילול
ופיזור-מחדש אוטומטי בכל ריבאלנס. הכללים שקופים ומוגדרים מראש — לא "קופסה שחורה".

**⚠️ אימות היסטורי (Backtesting):** הבק-טסט משמש לאימות התנהגות הסל בתקופות הסלמה — **לא** לבחירת מניות
בדיעבד. ביצועי העבר **אילוסטרטיביים ואינם תחזית לעתיד**; מדד מסחרי ייבחן גם out-of-sample.

**⏱️ אופק החזקה — מוצר טקטי:** בשל המינוף היומי, דשדוש תנודתי שוחק את ערך הקרן (vol decay). התעודה מיועדת
להחזקה **טקטית סביב אירועי הסלמה**, ולא להחזקה ארוכת-טווח. התשואות הרב-שנתיות מוצגות להמחשת התזה בלבד.

**עלויות:** התשואות הממונפות מוצגות **נטו** — בניכוי דמי ניהול {TER_ANNUAL*100:.0f}% לשנה ועלות מימון
המינוף (~{FINANCE_RATE*100:.1f}% שנתי על החלק המושאל, ≈{(TER_ANNUAL+(lev_factor-1)*FINANCE_RATE)*100:.1f}%
דראג שנתי כולל ב-{lev_factor}x). תעודות ההשוואה (ITA/XAR/PPA/הראל/S&P) משקפות את עלויותיהן בפועל דרך מחירן.
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ביצועים וסיכון
# ═══════════════════════════════════════════════════════════════════════════════
with tab_perf:
    st.markdown(f"### 📈 ביצועים היסטוריים — War ETF {lev_factor}x מול השוק")
    fig_bt = go.Figure()
    for war_name, wp in WAR_PERIODS.items():
        fig_bt.add_vrect(x0=wp["start"], x1=wp["end"], fillcolor=wp["fill"],
                         line=dict(color=wp["line"], width=1, dash="dot"), layer="below",
                         annotation_text=war_name, annotation_position="top left", annotation_font_size=10)
    if spy_r is not None:
        nav_spy = lev_nav(spy_r, 1)
        fig_bt.add_trace(go.Scatter(x=nav_spy.index, y=nav_spy.values,
                                    name="S&P 500", line=dict(color="#888", width=1.8, dash="dash")))
    for bname in bench_selected:
        bt = BENCHMARK_ETFS[bname]["ticker"]
        if bt in prices.columns:
            nav_b = lev_nav(prices[bt].pct_change().dropna(), 1)
            fig_bt.add_trace(go.Scatter(x=nav_b.index, y=nav_b.values, name=bench_label(bname),
                                        line=dict(color=BENCHMARK_ETFS[bname]["color"], width=2,
                                                  dash=BENCHMARK_ETFS[bname]["dash"])))
    if lev_factor > 1:
        nav_1x = lev_nav(etf_r, 1)
        fig_bt.add_trace(go.Scatter(x=nav_1x.index, y=nav_1x.values,
                                    name="War ETF 1x", line=dict(color="#5b7fb0", width=1.6, dash="dot")))
    nav_lev = lev_nav(etf_r, lev_factor)
    fig_bt.add_trace(go.Scatter(x=nav_lev.index, y=nav_lev.values,
                                name=f"War ETF {lev_factor}x ⭐", line=dict(color=ACCENT, width=3.5),
                                fill="tozeroy", fillcolor="rgba(178,30,53,0.06)"))
    fig_bt.update_layout(height=470, hovermode="x unified", yaxis_title="שווי תיק (בסיס 100)",
                         xaxis=dict(rangeselector=range_selector(), type="date", title="תאריך"),
                         legend=dict(x=0.01, y=0.99))
    st.plotly_chart(style_fig(fig_bt), use_container_width=True)

    st.divider()
    st.markdown("#### 📊 תשואה לפי תקופה — מול תעודות ההשוואה")
    rows = []
    for pname, (ps, pe) in PERIODS_ANALYSIS.items():
        r_etf = period_return(etf_r, ps, pe)
        if r_etf is None: continue
        r_lev = float((1 + lev_net(etf_r.loc[ps:pe], lev_factor)).prod() - 1)
        r_spy = period_return(spy_r, ps, pe) if spy_r is not None else None
        row = {"תקופה": pname, f"War ETF {lev_factor}x": f"{r_lev*100:+.1f}%",
               "War ETF 1x": f"{r_etf*100:+.1f}%",
               "S&P 500": f"{r_spy*100:+.1f}%" if r_spy else "—"}
        for bname in bench_selected:
            bt = BENCHMARK_ETFS[bname]["ticker"]
            if bt in prices.columns:
                r_b = period_return(prices[bt].pct_change().dropna(), ps, pe)
                row[bench_label(bname)] = f"{r_b*100:+.1f}%" if r_b else "—"
        rows.append(row)
    if rows:
        def color_cell(val):
            if not isinstance(val, str) or val == "—": return ""
            try:
                return f"color:{POS if float(val.replace('%','').replace('+',''))>0 else NEG};font-weight:bold"
            except: return ""
        st.dataframe(pd.DataFrame(rows).set_index("תקופה").style.map(color_cell), use_container_width=True)

    st.divider()
    st.markdown("#### ⚠️ מדדי סיכון — כל הנכסים")
    series_map = {f"War ETF {lev_factor}x": lev_net(etf_r, lev_factor), "War ETF 1x": etf_r}
    if spy_r is not None: series_map["S&P 500"] = spy_r
    for bname in bench_selected:
        bt = BENCHMARK_ETFS[bname]["ticker"]
        if bt in prices.columns:
            series_map[bench_label(bname)] = prices[bt].pct_change().dropna()

    risk_rows = [{
        "נכס": name, "תשואה שנתית": f"{ann_ret(r):+.1f}%", "תנודתיות": f"{ann_vol(r):.1f}%",
        "Sharpe": f"{sharpe(r):.2f}", "Max DD": f"{max_dd(r):.1f}%", "Calmar": f"{calmar(r):.2f}",
    } for name, r in series_map.items()]
    st.dataframe(pd.DataFrame(risk_rows).set_index("נכס"), use_container_width=True)

    colors_line = {"War ETF 1x": "#5b7fb0", "S&P 500": "#888", f"War ETF {lev_factor}x": ACCENT}

    col_dd, col_vol = st.columns(2)
    with col_dd:
        st.markdown("#### 📉 Drawdown — ירידה מהשיא")
        fig_dd = go.Figure()
        for name, r in series_map.items():
            dd = drawdown_series(r)
            is_lev = name == f"War ETF {lev_factor}x"
            fig_dd.add_trace(go.Scatter(x=dd.index, y=dd.values, name=name, mode="lines",
                line=dict(color=colors_line.get(name, "#6b7280"), width=2),
                fill="tozeroy" if is_lev else None,
                fillcolor="rgba(178,30,53,0.07)" if is_lev else None))
        fig_dd.add_hline(y=0, line_dash="dot", line_color="#555", line_width=1)
        fig_dd.update_layout(height=330, hovermode="x unified", yaxis=dict(title="Drawdown (%)", ticksuffix="%"),
                             xaxis=dict(rangeselector=range_selector(), type="date"), legend=dict(x=0.01, y=0.01))
        st.plotly_chart(style_fig(fig_dd), use_container_width=True)
        st.caption("📉 **Drawdown** = כמה אחוז ירדת מהשיא. הנקודה הכי עמוקה היא ההפסד הגדול ביותר "
                   "שהיית חווה — וב-×3 היא חדה במיוחד.")

    with col_vol:
        st.markdown("#### 📊 תנודתיות רולינג (30 יום)")
        fig_vol = go.Figure()
        for name, r in list(series_map.items())[:3]:
            rv = r.rolling(30).std() * np.sqrt(252) * 100
            fig_vol.add_trace(go.Scatter(x=rv.index, y=rv.values, name=name, mode="lines",
                                         line=dict(color=colors_line.get(name, "#6b7280"), width=2)))
        for war_name, wp in WAR_PERIODS.items():
            fig_vol.add_vrect(x0=wp["start"], x1=wp["end"], fillcolor=wp["fill"],
                              line=dict(color=wp["line"], width=1), layer="below")
        fig_vol.update_layout(height=330, hovermode="x unified", yaxis=dict(title="תנודתיות שנתית (%)", ticksuffix="%"),
                              xaxis=dict(rangeselector=range_selector(), type="date"), legend=dict(x=0.01, y=0.99))
        st.plotly_chart(style_fig(fig_vol), use_container_width=True)
        st.caption("📊 **תנודתיות** = עוצמת התנודות במחיר. קו גבוה יותר = השקעה פראית ומסוכנת יותר. "
                   "שים לב שה-×3 (אדום) תנודתי בהרבה מה-S&P.")

    st.markdown("#### 🎯 Risk / Return — כל הנכסים")
    rr = pd.DataFrame([{"נכס": n, "תנודתיות (%)": ann_vol(r), "תשואה שנתית (%)": ann_ret(r),
                        "Sharpe": sharpe(r)} for n, r in series_map.items()])
    rr["גודל"] = rr["Sharpe"].clip(lower=0.1)
    fig_rr = px.scatter(rr, x="תנודתיות (%)", y="תשואה שנתית (%)", text="נכס",
                        size="גודל", color="Sharpe", hover_data={"גודל": False},
                        color_continuous_scale="RdYlGn", size_max=38)
    fig_rr.update_traces(textposition="top center")
    fig_rr.add_hline(y=0, line_dash="dot", line_color="#aaa")
    fig_rr.update_layout(height=380, coloraxis_colorbar_title="Sharpe")
    st.plotly_chart(style_fig(fig_rr), use_container_width=True)
    st.caption("🎯 כל בועה = נכס: גובה = תשואה, ימין = סיכון. הכי טוב **שמאל-למעלה** (הרבה תשואה, מעט סיכון). "
               "צבע/גודל = **Sharpe** — תשואה ביחס לסיכון (ירוק = משתלם).")

    # ── קורלציה (משני — באקורדיון) ──
    with st.expander("🔗 קורלציה וגיוון בין הסקטורים"):
        col_corr, col_roll = st.columns(2)
        with col_corr:
            corr = sec_ret.corr()
            fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn_r",
                                 zmin=-1, zmax=1, aspect="auto")
            fig_corr.update_traces(textfont_size=12)
            fig_corr.update_layout(height=360, coloraxis_colorbar_title="קורלציה", xaxis_title="", yaxis_title="")
            st.plotly_chart(style_fig(fig_corr), use_container_width=True)
            upper = corr.values[np.triu_indices_from(corr.values, k=1)]
            avg_c = float(upper.mean())
            if avg_c < 0.6:   st.success(f"✅ קורלציה ממוצעת {avg_c:.2f} — גיוון טוב.")
            elif avg_c < 0.8: st.warning(f"⚠️ קורלציה ממוצעת {avg_c:.2f} — גיוון בינוני.")
            else:             st.error(f"❌ קורלציה ממוצעת {avg_c:.2f} — הסקטורים נעים יחד מדי.")
        with col_roll:
            if len(sec_ret.columns) >= 2:
                pairs = [(sec_ret.columns[i], sec_ret.columns[j])
                         for i in range(len(sec_ret.columns))
                         for j in range(i + 1, min(i + 3, len(sec_ret.columns)))]
                fig_roll = go.Figure()
                for a, b in pairs[:4]:
                    roll = sec_ret[a].rolling(60).corr(sec_ret[b]).dropna()
                    fig_roll.add_trace(go.Scatter(x=roll.index, y=roll.values,
                                                  name=f"{a.split()[0]}×{b.split()[0]}",
                                                  mode="lines", line=dict(width=1.8)))
                fig_roll.add_hline(y=0, line_dash="dash", line_color="#aaa", line_width=1)
                fig_roll.update_layout(height=360, hovermode="x unified",
                                       yaxis=dict(title="קורלציה רולינג (60י')", range=[-1, 1]),
                                       legend=dict(x=0, y=1, font=dict(size=10)))
                st.plotly_chart(style_fig(fig_roll), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — סימולציית השקעה (עצמאי, עם טווחי זמן משלו)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sim:
    st.markdown("### 💰 סימולציית השקעה — כמה היית מרוויח?")
    st.caption("בחר סכום וטווח זמן, וראה איך ההשקעה הייתה מתפתחת (נטו — בניכוי דמי ניהול ומימון מינוף).")

    data_start, data_end = prices_full.index.min(), prices_full.index.max()
    cc = st.columns([1.2, 2])
    invest_amount = cc[0].number_input("💵 סכום השקעה (₪)", min_value=100, max_value=10_000_000,
                                       value=10_000, step=1_000, format="%d")
    RANGES = {"שנה": 1, "3 שנים": 3, "5 שנים": 5}
    choice = cc[1].radio("📅 טווח זמן", list(RANGES) + ["כל התקופה", "מותאם אישית"],
                         horizontal=True, index=1)
    if choice == "מותאם אישית":
        dca, dcb = st.columns(2)
        s_in = dca.date_input("מתאריך", value=(data_end - pd.DateOffset(years=3)).date(),
                              min_value=data_start.date(), max_value=data_end.date())
        e_in = dcb.date_input("עד תאריך", value=data_end.date(),
                              min_value=data_start.date(), max_value=data_end.date())
        sim_s, sim_e = pd.Timestamp(s_in), pd.Timestamp(e_in)
    elif choice == "כל התקופה":
        sim_s, sim_e = data_start, data_end
    else:
        sim_s, sim_e = data_end - pd.DateOffset(years=RANGES[choice]), data_end
    # לא חורגים מהדטא שיש לנו (2021 → היום)
    sim_s, sim_e = max(sim_s, data_start), min(sim_e, data_end)

    etf_full = sec_ret_full.mean(axis=1)
    spy_full = prices_full["SPY"].pct_change().dropna() if "SPY" in prices_full.columns else None
    etf_s = etf_full.loc[sim_s:sim_e]
    spy_s = spy_full.loc[sim_s:sim_e] if spy_full is not None else None

    if len(etf_s) < 5:
        st.warning("טווח קצר מדי. בחר טווח זמן ארוך יותר.")
    else:
        def pf(r): return float((1 + r).prod()) * invest_amount
        final_lev = pf(lev_net(etf_s, lev_factor))
        final_spy = pf(spy_s) if spy_s is not None and len(spy_s) else None
        profit = final_lev - invest_amount
        yrs = max((sim_e - sim_s).days / 365.25, 0.01)

        st.markdown(f"""
        <div class="hero" style="margin-top:10px">
            <div class="hero-tag">השקעה של ₪{invest_amount:,.0f} הייתה הופכת ל־</div>
            <div class="hero-title" style="color:{pos_neg(profit)}">₪{final_lev:,.0f}</div>
            <div class="hero-sub">רווח של ₪{profit:,.0f} ({(final_lev/invest_amount-1)*100:+.0f}%) ·
            על פני {yrs:.1f} שנים · War ETF {lev_factor}x</div>
        </div>""", unsafe_allow_html=True)

        st.warning("⚠️ **מוצר טקטי — לא להחזקה ארוכת טווח.** התעודה מיועדת להחזקה סביב אירועי הסלמה. "
                   "המינוף היומי גורם לשחיקה מתמטית (vol decay) בתקופות דשדוש — התשואה הרב-שנתית מוצגת "
                   "להמחשת התזה, לא כהמלצת החזקה ממושכת.")

        k = st.columns(3)
        k[0].markdown(kpi(f"War ETF {lev_factor}x", f"₪{final_lev:,.0f}",
                          f"{(final_lev/invest_amount-1)*100:+.1f}%", pos_neg(profit)), unsafe_allow_html=True)
        k[1].markdown(kpi("S&P 500", f"₪{final_spy:,.0f}" if final_spy else "—",
                          f"{((final_spy or invest_amount)/invest_amount-1)*100:+.1f}%" if final_spy else "—",
                          pos_neg((final_spy or invest_amount)-invest_amount)), unsafe_allow_html=True)
        k[2].markdown(kpi("יתרון על S&P", f"×{final_lev/final_spy:.1f}" if final_spy else "—",
                          f"+₪{final_lev-(final_spy or 0):,.0f}" if final_spy else "—", ACCENT), unsafe_allow_html=True)

        nav_l = (1 + lev_net(etf_s, lev_factor)).cumprod() * invest_amount
        fig_sim = go.Figure()
        for war_name, wp in WAR_PERIODS.items():
            ws, we = pd.Timestamp(wp["start"]), pd.Timestamp(wp["end"])
            if ws <= sim_e and we >= sim_s:
                fig_sim.add_vrect(x0=max(ws, sim_s), x1=min(we, sim_e), fillcolor=wp["fill"],
                                  line=dict(color=wp["line"], width=1), layer="below",
                                  annotation_text=war_name.split(" ")[0],
                                  annotation_position="top left", annotation_font_size=9)
        if spy_s is not None and len(spy_s):
            nav_s = (1 + spy_s).cumprod() * invest_amount
            fig_sim.add_trace(go.Scatter(x=nav_s.index, y=nav_s.values, name="S&P 500",
                                         line=dict(color="#888", width=1.8, dash="dash")))
        fig_sim.add_trace(go.Scatter(x=nav_l.index, y=nav_l.values, name=f"War ETF {lev_factor}x ⭐",
                                     line=dict(color=ACCENT, width=3.2), fill="tozeroy",
                                     fillcolor="rgba(178,30,53,0.08)"))
        fig_sim.add_hline(y=invest_amount, line_dash="dot", line_color="#999", line_width=1,
                          annotation_text="קרן", annotation_position="right")
        fig_sim.update_layout(height=420, hovermode="x unified", xaxis=dict(type="date", title="תאריך"),
                              yaxis=dict(title="שווי התיק (₪)", tickprefix="₪", tickformat=",.0f"),
                              legend=dict(x=0.01, y=0.99))
        st.plotly_chart(style_fig(fig_sim), use_container_width=True)

        st.divider()
        st.markdown("#### ⚔️ כמה היית מרוויח בכל תקופת מלחמה?")
        sim_rows = []
        for pname, (ps, pe) in PERIODS_ANALYSIS.items():
            r_etf = period_return(etf_full, ps, pe)
            if r_etf is None: continue
            r_lev = float((1 + lev_net(etf_full.loc[ps:pe], lev_factor)).prod() - 1)
            r_spy = period_return(spy_full, ps, pe) if spy_full is not None else None
            def fmt(r): return f"₪{r*invest_amount:,.0f} ({r*100:+.1f}%)"
            sim_rows.append({"תקופה": pname, f"War ETF {lev_factor}x": fmt(r_lev),
                             "S&P 500": fmt(r_spy) if r_spy is not None else "—"})
        if sim_rows:
            def color_cell(val):
                if not isinstance(val, str) or val == "—": return ""
                return f"color:{POS if '+' in val else NEG};font-weight:bold"
            st.dataframe(pd.DataFrame(sim_rows).set_index("תקופה").style.map(color_cell),
                         use_container_width=True)
        st.caption("💡 הסימולציה ב-₪, נטו, מבוססת תשואת נכסי הבסיס — מניחה השקעה חד-פעמית בתחילת התקופה "
                   "(ללא הפקדות נוספות) ולפני השפעת שער חליפין ₪/$.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — מודל עסקי ומבנה
# ═══════════════════════════════════════════════════════════════════════════════
with tab_biz:
    col_fee, col_why = st.columns([2, 1])
    with col_fee:
        st.markdown("### 💸 דמי ניהול — מול מתחרים")
        fee_data = {
            "TQQQ\n3x Nasdaq": 0.86, "UPRO\n3x S&P 500": 0.91, "SOXL\n3x Chips": 0.99,
            "LABU\n3x Biotech": 1.09, "ITA\nDefense 1x": 0.40, "XAR\nAerospace 1x": 0.35,
            "WAR ETF 3x\n⭐ קסם": 2.0,
        }
        colors_fee = [ACCENT if "WAR" in k else "#3a4252" for k in fee_data]
        fig_fee = go.Figure(go.Bar(x=list(fee_data.keys()), y=list(fee_data.values()),
                                   marker_color=colors_fee, text=[f"{v:.2f}%" for v in fee_data.values()],
                                   textposition="outside"))
        fig_fee.add_hline(y=2.0, line_dash="dot", line_color=ACCENT, line_width=1.5,
                          annotation_text="WAR ETF 2%", annotation_position="right")
        fig_fee.update_layout(height=330, showlegend=False,
                              yaxis=dict(title="דמי ניהול שנתיים (%)", ticksuffix="%", range=[0, 2.4]))
        st.plotly_chart(style_fig(fig_fee), use_container_width=True)
    with col_why:
        st.markdown("### 🎯 למה 2% מוצדק?")
        st.markdown("""
**תמה ייחודית** — אפס מתחרים ישירים, pricing power מלא.

**עלות תפעולית גבוהה** — ריבאלנס יומי של 30 מניות ב-5 סקטורים + swaps.

**מינוף ×3 בנוי** — מורכבות תפעולית גבוהה מתעודה רגילה.

**קהל יעד מחויב** — משקיע שמחפש war exposure לא יסרב לפרמיה על מוצר ייחודי.
        """)

    st.divider()
    st.markdown("### 🏗️ מבנה הקרן")
    fs_items = list(FUND_STRUCTURE.items())
    fc = st.columns(2)
    for i, (k, v) in enumerate(fs_items):
        fc[i % 2].markdown(f"**{k}:** {v}")

    st.caption("⚠️ לצרכי מחקר ולמידה בלבד — אין לראות בכך ייעוץ השקעות. ביצועי עבר אינם ערובה לעתיד.")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"""<div style="text-align:center;color:{MUTED};font-size:12px;padding:8px 0">
    Kesem WAR Leverage x3 (WAR3) — הצעה לקסם תעודות סל &nbsp;|&nbsp; נתונים: Yahoo Finance · TASE/גלובס<br>
    <b>לצרכי מחקר ולמידה בלבד — אין לראות בכך ייעוץ השקעות</b>
</div>""", unsafe_allow_html=True)
