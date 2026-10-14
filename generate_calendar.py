"""ECJTU CalendarServlet -> iCalendar. Fail closed on unknown responses."""
import os
import re
import json
import html
import hashlib
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
URL = "https://jwxt.ecjtu.edu.cn/weixin/CalendarServlet"

def escape(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

def get_page(date):
    token = os.environ.get("ECJTU_WEIXIN_ID", "").strip()
    if not token:
        raise RuntimeError("Missing ECJTU_WEIXIN_ID secret")
    query = urllib.parse.urlencode({"weiXinID": token, "date": date})
    req = urllib.request.Request(URL + "?" + query, headers={"User-Agent": "Mozilla/5.0 (compatible; CalendarSync/1.0)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def parse(raw):
    """Accept structured JSON only; HTML requires inspection before parser is implemented."""
    try:
        data = json.loads(raw)
    except ValueError:
        safe = re.sub(r"orOcuwWo[A-Za-z0-9_-]+", "[REDACTED]", raw[:400])
        print("Interface returned non-JSON content; parser needs adapting.")
        print("Response starts with:", re.sub(r"<[^>]*>", " ", html.unescape(safe))[:160])
        raise RuntimeError("Unsupported response format: expected JSON")
    if isinstance(data, dict):
        data = data.get("courses", data.get("events", data.get("data")))
    if not isinstance(data, list):
        raise RuntimeError("Unsupported JSON structure")
    result = []
    for item in data:
        if not isinstance(item, dict):
            raise RuntimeError("Unexpected course item")
        title = item.get("title") or item.get("courseName") or item.get("name")
        start = item.get("start") or item.get("startTime")
        end = item.get("end") or item.get("endTime")
        if not all((title, start, end)):
            raise RuntimeError("Course missing title/start/end; refusing partial calendar")
        def convert(v):
            return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=TZ) if datetime.fromisoformat(str(v).replace("Z", "+00:00")).tzinfo is None else datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(TZ)
        result.append((str(title), convert(start), convert(end), str(item.get("location") or item.get("classroom") or "")))
    return result

def main():
    today = datetime.now(TZ).date()
    # Fetch a week at a time; interface behavior still needs verification.
    events = []
    for week in range(20):
        date = (today + timedelta(days=week * 7)).isoformat()
        events.extend(parse(get_page(date)))
    if not events:
        raise RuntimeError("No classes returned: preserving previous calendar")
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ECJTU Watch Calendar//CN", "CALSCALE:GREGORIAN", "X-WR-CALNAME:华东交大课表", "X-WR-TIMEZONE:Asia/Shanghai"]
    unique = {}
    for title, start, end, location in events:
        if end <= start:
            raise RuntimeError("Invalid event time")
        uid = hashlib.sha256(f"{title}|{start.isoformat()}|{location}".encode()).hexdigest()[:24] + "@ecjtu-watch"
        unique[uid] = (title, start, end, location)
    for uid, (title, start, end, location) in sorted(unique.items(), key=lambda x: x[1][1]):
        lines += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp, "DTSTART;TZID=Asia/Shanghai:" + start.strftime("%Y%m%dT%H%M%S"), "DTEND;TZID=Asia/Shanghai:" + end.strftime("%Y%m%dT%H%M%S"), "SUMMARY:" + escape(title), "LOCATION:" + escape(location), "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY", "DESCRIPTION:即将上课", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    with open("calendar.ics", "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    print(f"Generated {len(unique)} events")

if __name__ == "__main__":
    main()
