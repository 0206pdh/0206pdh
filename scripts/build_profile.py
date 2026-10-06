"""Render the profile SVGs (contribution heatmap + stats card) from real data.

Usage: GITHUB_TOKEN=... python scripts/build_profile.py [login]
Standard library only. Writes assets/{heatmap,stats}-{dark,light}.svg so the
README can pick the one matching the viewer's theme with <picture>.
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "0206pdh"
OUT = Path(__file__).resolve().parent.parent / "assets"

# colours follow GitHub's own dark / light canvas so the cards blend into the page
THEMES = {
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3",
                 muted="#8b949e", accent="#39d353",
                 greens=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]),
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d0d7de", text="#1f2328",
                  muted="#656d76", accent="#1a7f37",
                  greens=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN (or GH_TOKEN) is required")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": LOGIN},
    )
    with urllib.request.urlopen(req) as res:
        body = json.load(res)
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(count, peak):
    if count == 0:
        return 0
    return min(4, 1 + int(3 * count / peak)) if peak else 1


def render_heatmap(cal, t):
    weeks = cal["weeks"]
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    # cap the scale at the 95th percentile so one huge day doesn't flatten the rest
    active = sorted(c for c in counts if c)
    peak = active[int(len(active) * 0.95) - 1] if active else 0

    cell, gap, left, top = 12, 3, 44, 58
    step = cell + gap
    width = left + len(weeks) * step + 20
    height = top + 7 * step + 44

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        "<style>"
        ".c{animation:pop 12s ease-in-out infinite backwards}"
        "@keyframes pop{0%,97%,100%{opacity:0;transform:scale(.3)}"
        "3%,90%{opacity:1;transform:scale(1)}}"
        ".c{transform-box:fill-box;transform-origin:center}"
        "</style>",
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text x="{left}" y="28" fill="{t["text"]}" font-size="14">'
        f'<tspan fill="{t["accent"]}">{cal["totalContributions"]:,}</tspan>'
        " contributions in the last year</text>",
    ]

    last_month = None
    for x, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and x < len(weeks) - 2:
            parts.append(
                f'<text x="{left + x * step}" y="{top - 8}" fill="{t["muted"]}" '
                f'font-size="10">{MONTHS[first.month - 1]}</text>'
            )
            last_month = first.month
        for day in week["contributionDays"]:
            y = day["weekday"]
            lv = level(day["contributionCount"], peak)
            delay = x * 0.04 + y * 0.015
            parts.append(
                f'<rect class="c" style="animation-delay:{delay:.3f}s" '
                f'x="{left + x * step}" y="{top + y * step}" width="{cell}" '
                f'height="{cell}" rx="2.5" fill="{t["greens"][lv]}">'
                f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>'
            )

    for y, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(
            f'<text x="12" y="{top + y * step + 10}" fill="{t["muted"]}" '
            f'font-size="10">{label}</text>'
        )

    legend_y = top + 7 * step + 14
    legend_x = width - 20 - 5 * step - 70
    parts.append(f'<text x="{legend_x}" y="{legend_y + 10}" fill="{t["muted"]}" font-size="10">Less</text>')
    for i, color in enumerate(t["greens"]):
        parts.append(
            f'<rect x="{legend_x + 32 + i * step}" y="{legend_y}" width="{cell}" '
            f'height="{cell}" rx="2.5" fill="{color}"/>'
        )
    parts.append(
        f'<text x="{legend_x + 36 + 5 * step}" y="{legend_y + 10}" fill="{t["muted"]}" '
        'font-size="10">More</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def streaks(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    # today may still be empty; don't let that break the running streak
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return current, longest


def render_stats(cal, t):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    active = sum(1 for d in days if d["contributionCount"])
    best = max(days, key=lambda d: d["contributionCount"])
    tiles = [
        (f'{cal["totalContributions"]:,}', "contributions", "last 12 months"),
        (str(current), "current streak", "days in a row"),
        (str(longest), "longest streak", "days in a row"),
        (str(active), "active days", f"of {len(days)}"),
        (str(best["contributionCount"]), "best day", best["date"]),
        (f'{cal["totalContributions"] / max(active, 1):.1f}', "avg / active day", "contributions"),
    ]

    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["contributionCount"]
    months = sorted(monthly)[-12:]

    width, height, pad = 840, 720, 32
    tile_w, tile_h, tile_gap = (width - 2 * pad - 24) / 2, 124, 24
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        "<style>"
        ".b{transform-box:fill-box;transform-origin:bottom;"
        "animation:grow 12s ease-in-out infinite backwards}"
        "@keyframes grow{0%,98%,100%{transform:scaleY(0)}8%,90%{transform:scaleY(1)}}"
        "</style>",
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]
    for i, (value, label, sub) in enumerate(tiles):
        x = pad + (i % 2) * (tile_w + tile_gap)
        y = pad + (i // 2) * (tile_h + tile_gap)
        parts += [
            f'<rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" rx="8" '
            f'fill="{t["panel"]}" stroke="{t["border"]}"/>',
            f'<text x="{x + 24}" y="{y + 60}" fill="{t["accent"]}" font-size="44" '
            f'font-weight="700">{value}</text>',
            f'<text x="{x + 24}" y="{y + 90}" fill="{t["text"]}" font-size="18">{label}</text>',
            f'<text x="{x + 24}" y="{y + 110}" fill="{t["muted"]}" font-size="14">{sub}</text>',
        ]

    chart_top = pad + 3 * (tile_h + tile_gap) + 36
    chart_bottom = height - pad - 28
    chart_h = chart_bottom - chart_top
    parts.append(
        f'<text x="{pad}" y="{chart_top - 14}" fill="{t["muted"]}" font-size="16">'
        "contributions per month</text>"
    )
    slot = (width - 2 * pad) / len(months)
    bar_w = slot * 0.62
    top_value = max(monthly[m] for m in months) or 1
    for i, m in enumerate(months):
        h = max(2, chart_h * monthly[m] / top_value)
        x = pad + i * slot + (slot - bar_w) / 2
        parts += [
            f'<rect class="b" style="animation-delay:{i * 0.06:.2f}s" x="{x:.1f}" '
            f'y="{chart_bottom - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" '
            f'fill="{t["greens"][2 + (monthly[m] * 2 >= top_value)]}">'
            f"<title>{m}: {monthly[m]}</title></rect>",
            f'<text x="{x + bar_w / 2:.1f}" y="{chart_bottom + 20}" fill="{t["muted"]}" '
            f'font-size="13" text-anchor="middle">{MONTHS[int(m[5:]) - 1]}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    cal = fetch_calendar()
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"heatmap-{name}.svg").write_text(render_heatmap(cal, theme), encoding="utf-8")
        (OUT / f"stats-{name}.svg").write_text(render_stats(cal, theme), encoding="utf-8")
    print(f"rendered heatmap + stats SVGs for {LOGIN} "
          f"({cal['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
