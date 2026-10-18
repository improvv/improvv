"""Render up to 1,000 recent public commits in KST using GitHub CLI."""

import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone


def main():
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "improvv")
    counts = [0, 0, 0, 0]
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
            hour = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(
                timezone(timedelta(hours=9))
            ).hour
            counts[((hour - 6) % 24) // 6] += 1
        if len(data["items"]) < 100 or page * 100 >= data["total_count"]:
            break

    total = sum(counts)
    if not total:
        raise RuntimeError("No public commits found; keeping existing stats")
    labels = ["🌞 Morning", "🌆 Daytime", "🌃 Evening", "🌙 Night"]
    lines = []
    for label, count in zip(labels, counts):
        percent = count / total * 100
        filled = round(percent / 4)
        bar = "█" * filled + "░" * (25 - filled)
        lines.append(f"{label:<10} {count:>4} commits  {bar}  {percent:5.2f}%")
    block = "```text\n" + "\n".join(lines) + "\n```"
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
