"""
מושך את היסטוריית המחירים של 'הראל סל ת"א בטחוניות' (קרן סל 1233170, instrumentId 620912)
ממקור הנתונים של גלובס, ושומר ל-harel_ta_defense.csv.

הרצה לרענון הנתונים:  python3 fetch_harel.py
"""
import csv
import json
import datetime as dt
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

INSTRUMENT_ID = 620912
PAGE = f"https://www.globes.co.il/portal/instrument.aspx?instrumentid={INSTRUMENT_ID}"
DATA = f"https://www.globes.co.il/portal/Graphs/data/instrumentInfo5.ashx?symbol={INSTRUMENT_ID}%7C0&source=2&type=all"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OUT = Path(__file__).parent / "harel_ta_defense.csv"


def fetch():
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    # 1) חימום: לקבל cookies מהדף הראשי
    opener.open(Request(PAGE, headers={"User-Agent": UA}), timeout=25).read()
    # 2) למשוך את נתוני הגרף עם אותו session
    req = Request(DATA, headers={
        "User-Agent": UA, "Referer": PAGE, "X-Requested-With": "XMLHttpRequest",
    })
    raw = opener.open(req, timeout=25).read().decode("utf-8").strip()
    if raw.startswith("("):           # JSONP-style: ( {...} );
        raw = raw[1:raw.rfind(")")]
    payload = json.loads(raw)
    if not payload.get("data"):
        raise SystemExit("⚠️ לא התקבלו נתונים — ייתכן שגלובס שינו הגנה/endpoint.")
    return payload


def main():
    payload = fetch()
    rows = payload["data"]            # [ts_ms, open, high, low, close, volume]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for ts, o, h, l, c, v in rows:
            d = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).date()
            w.writerow([d.isoformat(), o, h, l, c, v])
    print(f"✅ נשמרו {len(rows)} ימי מסחר → {OUT.name}")
    print(f"   טווח: {dt.datetime.fromtimestamp(rows[0][0]/1000, dt.timezone.utc).date()} "
          f"→ {dt.datetime.fromtimestamp(rows[-1][0]/1000, dt.timezone.utc).date()} "
          f"| שער אחרון: {rows[-1][4]}")


if __name__ == "__main__":
    main()
