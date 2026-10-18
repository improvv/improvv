"""Render up to 1,000 recent public commits in KST using GitHub CLI."""

import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone


def main():
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "improvv")
    counts = [0, 0, 0, 0]
    weekdays = [0] * 7
    seen = set()
    for page in range(1, 11):
        result = subprocess.run(
            ["gh", "api", "--method", "GET", "search/commits",
             "-f", f"q=author:{owner} is:public", "-f", "sort=committer-date",
             "-f", "order=desc", "-f", "per_page=100", "-f", f"page={page}"],
            check=True, capture_output=True, text=True,
        )
        data = json.loads(result.stdout)
        if data.get("incomplete_results"):
            raise RuntimeError("GitHub returned incomplete results; keeping existing stats")
        for item in data["items"]:
            if item["sha"] in seen:
                continue
            seen.add(item["sha"])
            date = item["commit"]["author"]["date"]
            local_date = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(
                timezone(timedelta(hours=9))
            )
            counts[((local_date.hour - 6) % 24) // 6] += 1
            weekdays[local_date.weekday()] += 1
        if len(data["items"]) < 100 or page * 100 >= data["total_count"]:
            break

    total = sum(counts)
    if not total:
        raise RuntimeError("No public commits found; keeping existing stats")
    labels = ["🌞 Morning", "🌆 Daytime", "🌃 Evening", "🌙 Night"]
    def rows(labels, values, width):
        lines = []
        for label, count in zip(labels, values):
            percent = count / total * 100
            filled = round(percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            lines.append(f"{label:<{width}} {count:>4}  {bar} {percent:5.1f}%")
        return "\n".join(lines)

    times = rows(labels, counts, 10)
    days = rows(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], weekdays, 3)
    block = (
        '<table width="100%">\n<tr>\n'
        '<td width="50%" valign="top">\n\n'
        '<b>🌞 By Time of Day</b>\n<pre>' + times + '</pre>\n\n</td>\n'
        '<td width="50%" valign="top">\n\n'
        '<b>📅 By Day of Week</b>\n<pre>' + days + '</pre>\n\n</td>\n'
        '</tr>\n</table>'
    )
    readme = Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text()
    start, end = "<!--START_SECTION:commit-times-->", "<!--END_SECTION:commit-times-->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError("Expected exactly one commit-times section")
    before, rest = text.split(start)
    _, after = rest.split(end)
    readme.write_text(before + start + "\n" + block + "\n" + end + after)
    print(f"Updated commit times from {total} unique public commits (KST)")


if __name__ == "__main__":
    main()
