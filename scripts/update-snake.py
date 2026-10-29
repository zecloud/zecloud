#!/usr/bin/env python3
"""Generate a public-only calendar snapshot. No GitHub token is used or needed."""

import datetime as dt
import argparse
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/users/zecloud/contributions"


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-date" not in attrs or "data-level" not in attrs:
            return
        date = dt.date.fromisoformat(attrs["data-date"])
        level = int(attrs["data-level"])
        if not 0 <= level <= 4 or date.isoformat() in self.days:
            raise ValueError("Invalid or duplicate contribution day")
        self.days[date.isoformat()] = level


def build_snapshot(html, now=None):
    parser = CalendarParser()
    parser.feed(html)
    days = [{"date": date, "level": level} for date, level in sorted(parser.days.items())]
    if not 364 <= len(days) <= 371:
        raise ValueError(f"Expected a full contribution year, got {len(days)} days")
    for previous, current in zip(days, days[1:]):
        if dt.date.fromisoformat(current["date"]) - dt.date.fromisoformat(previous["date"]) != dt.timedelta(days=1):
            raise ValueError("Contribution dates are not consecutive")
    now = now or dt.datetime.now(dt.timezone.utc)
    last = dt.date.fromisoformat(days[-1]["date"])
    if not 0 <= (now.date() - last).days <= 2:
        raise ValueError("GitHub returned an outdated or future contribution calendar")
    return {
        "username": "zecloud",
        "source": URL,
        "generatedAt": now.isoformat(),
        "days": days,
    }


def validate_snapshot(snapshot):
    if snapshot.get("username") != "zecloud":
        raise ValueError("Unexpected calendar owner")
    generated = dt.datetime.fromisoformat(snapshot["generatedAt"])
    html = "".join(
        f'<td data-date="{escape(day["date"], quote=True)}" data-level="{int(day["level"])}"></td>'
        for day in snapshot["days"]
    )
    validated = build_snapshot(html, generated)
    if validated["days"] != snapshot["days"]:
        raise ValueError("Snapshot must contain sorted dates and integer levels")
    return snapshot


def render_svg(snapshot, animated=True):
    validate_snapshot(snapshot)
    days = snapshot["days"][-364:]
    first = dt.date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7
    columns = (len(days) + offset + 6) // 7
    width = columns * 14 + 24
    # A serpentine scan is a collision-free route across every contribution.
    route = [(x, y) for x in range(columns) for y in (range(7) if x % 2 == 0 else range(6, -1, -1))]
    visit = {point: index for index, point in enumerate(route)}
    frames = len(route) + 10
    duration = frames * 0.1
    colors = ["#18292e", "#1d503e", "#307653", "#53a669", "#87cc73"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="144" viewBox="0 0 {width} 144" role="img" aria-labelledby="title description">',
        "<title id=\"title\">ZeCloud — Snake des contributions GitHub</title>",
        f'<desc id="description">Calendrier public du {days[0]["date"]} au {days[-1]["date"]}. '
        f'Instantané du {snapshot["generatedAt"][:10]}. Un serpent parcourt les cases de haut en bas, puis de bas en haut. '
        'Les couleurs représentent les niveaux de contribution GitHub, pas un nombre exact. Aperçu décoratif ; jeu interactif distinct.</desc>',
        f'<rect width="{width}" height="144" rx="8" fill="#0b1216"/>',
    ]
    styles = []
    for index, day in enumerate(days):
        x, y = divmod(index + offset, 7)
        name = f"day-{index}"
        if animated and day["level"]:
            eaten = (visit[(x, y)] + 1) / frames * 100
            styles.append(f"@keyframes {name}{{0%,{max(0, eaten - .01):.4f}%{{opacity:1}}{eaten:.4f}%,100%{{opacity:.15}}}}")
            styles.append(f"#{name}{{animation:{name} {duration:.1f}s steps(1,end) infinite}}")
        parts.append(f'<rect id="{name}" x="{12 + x * 14}" y="{12 + y * 14}" width="10" height="10" rx="2" fill="{colors[day["level"]]}"><title>{day["date"]} · niveau {day["level"]}/4</title></rect>')
    if animated:
        for segment in range(5, -1, -1):
            name = f"snake-{segment}"
            points = []
            for frame in range(frames):
                position = frame - segment
                visible = 0 <= position < len(route)
                x, y = route[max(0, min(len(route) - 1, position))]
                points.append(f"{frame / (frames - 1) * 100:.4f}%{{transform:translate({12 + x * 14}px,{12 + y * 14}px);opacity:{int(visible)}}}")
            styles.append(f"@keyframes {name}{{{''.join(points)}}}")
            styles.append(f"#{name}{{animation:{name} {duration:.1f}s steps(1,end) infinite}}")
            parts.append(f'<rect id="{name}" width="10" height="10" rx="2" fill="{"#e6f4ff" if segment == 0 else "#85bce2"}" opacity="0"/>')
        styles.append("@media(prefers-reduced-motion:reduce){rect{animation:none!important}}")
        parts.insert(4, f"<style>{''.join(styles)}</style>")
    parts.append(f'<text x="12" y="129" fill="#9fafb3" font-family="monospace" font-size="10">@zecloud · {days[0]["date"]} / {days[-1]["date"]} · public contributions</text>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", action="store_true", help="Render the checked-in snapshot without network access")
    args = parser.parse_args()
    destination = ROOT / "assets" / "contributions.json"
    if args.from_snapshot:
        snapshot = validate_snapshot(json.loads(destination.read_text(encoding="utf-8")))
    else:
        request = urllib.request.Request(URL, headers={"User-Agent": "ZeCloud-contribution-snapshot", "Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=30) as response:
            snapshot = build_snapshot(response.read().decode("utf-8"))
    outputs = {
        destination: json.dumps(snapshot, ensure_ascii=True, indent=2) + "\n",
        ROOT / "assets" / "github-contribution-snake.svg": render_svg(snapshot),
        ROOT / "assets" / "contributions-static.svg": render_svg(snapshot, animated=False),
    }
    for path, content in outputs.items():
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    print(f"Saved {len(snapshot['days'])} public days and animated/static SVG previews.")


if __name__ == "__main__":
    main()
