#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.1.0
"""
Generate digest tree index in org-mode format.

Replaces llms-gen.py with a hierarchical tree structure.

examples:
  %(prog)s                    # generate digests.org
  %(prog)s -o index.org       # custom output
  %(prog)s --json             # output as JSON
  %(prog)s -n                 # dry run (stdout)
"""

import argparse
import json
import logging
import re
import signal
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

__version__ = "0.1.0"
PROG = Path(__file__).name
LOGGER = logging.getLogger(PROG)

DIGESTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "digests"
DEFAULT_OUTPUT = Path(__file__).parent.parent.parent.parent.parent / "digests.org"

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def setup_logging(quiet: bool, verbose: int) -> None:
    level = logging.WARNING if quiet else logging.INFO
    level = max(logging.DEBUG, level - min(verbose, 2) * 10)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def parse_org_digest(path: Path) -> dict | None:
    """Extract metadata from an org digest file."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        LOGGER.warning("cannot read %s: %s", path, e)
        return None

    # Date from #+DATE:
    date_match = re.search(r"#\+DATE:\s*(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", content)
    if not date_match:
        LOGGER.warning("no #+DATE in %s", path)
        return None

    date_str, time_str = date_match.groups()
    year, month, day = date_str.split("-")

    # Story IDs from :ID: property
    story_ids = re.findall(r":ID:\s+(\d+)", content)

    # Vibe from * Vibe section
    vibe = ""
    vibe_match = re.search(r"^\* Vibe\n(.+?)$", content, re.MULTILINE)
    if vibe_match:
        vibe = vibe_match.group(1).strip()[:60]

    # Story titles for topics
    titles = re.findall(r"^\*\* (.+?)\s+:", content, re.MULTILINE)
    topics = [t[:30] for t in titles[:3]]  # First 3 titles, truncated

    return {
        "path": path,
        "year": year,
        "month": month,
        "day": day,
        "time": time_str,
        "date_str": date_str,
        "story_ids": story_ids[:5],
        "vibe": vibe,
        "topics": topics,
    }


def scan_digests() -> list[dict]:
    """Scan all digest files."""
    digests = []
    for f in DIGESTS_DIR.rglob("*.org"):
        d = parse_org_digest(f)
        if d:
            digests.append(d)
    return digests


def build_tree(digests: list[dict]) -> dict:
    """Build hierarchical tree from flat list."""
    tree = defaultdict(lambda: defaultdict(list))

    for d in digests:
        tree[d["year"]][d["month"]].append(d)

    # Sort days within each month
    for year in tree:
        for month in tree[year]:
            tree[year][month].sort(key=lambda x: (x["day"], x["time"]), reverse=True)

    return tree


def generate_org(tree: dict) -> str:
    """Generate org-mode tree index."""
    lines = [
        "#+TITLE: HN Digest Index",
        "#+STARTUP: overview",
        "",
        "AI-curated Hacker News digests. Story IDs for dedup.",
        "",
    ]

    # Collect all story IDs for quick lookup
    all_ids = set()
    for year in sorted(tree.keys(), reverse=True):
        for month in sorted(tree[year].keys(), reverse=True):
            for d in tree[year][month]:
                all_ids.update(d["story_ids"])

    lines.append(f"Total: {sum(len(tree[y][m]) for y in tree for m in tree[y])} digests, {len(all_ids)} unique stories")
    lines.append("")

    for year in sorted(tree.keys(), reverse=True):
        lines.append(f"* {year}")

        for month in sorted(tree[year].keys(), reverse=True):
            month_name = MONTHS[int(month)]
            lines.append(f"** {month_name}")

            # Group by day
            days = defaultdict(list)
            for d in tree[year][month]:
                days[d["day"]].append(d)

            for day in sorted(days.keys(), reverse=True):
                # Get weekday
                dt = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                weekday = WEEKDAYS[dt.weekday()]

                lines.append(f"*** {day} ({weekday})")

                for d in sorted(days[day], key=lambda x: x["time"], reverse=True):
                    rel_path = d["path"].relative_to(DIGESTS_DIR.parent)
                    time = d["time"]
                    ids = ", ".join(d["story_ids"])
                    topics = ", ".join(d["topics"]) if d["topics"] else d["vibe"][:40]

                    lines.append(f"- [[file:{rel_path}][{time}]] {topics} | {ids}")

        lines.append("")

    return "\n".join(lines)


def generate_json(tree: dict) -> str:
    """Generate JSON index."""
    result = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "digests": [],
        "story_ids": set(),
    }

    for year in sorted(tree.keys(), reverse=True):
        for month in sorted(tree[year].keys(), reverse=True):
            for d in tree[year][month]:
                result["digests"].append({
                    "path": str(d["path"].relative_to(DIGESTS_DIR.parent)),
                    "date": d["date_str"],
                    "time": d["time"],
                    "story_ids": d["story_ids"],
                    "topics": d["topics"],
                })
                result["story_ids"].update(d["story_ids"])

    result["story_ids"] = sorted(result["story_ids"], reverse=True)
    result["total_digests"] = len(result["digests"])
    result["total_stories"] = len(result["story_ids"])

    return json.dumps(result, indent=2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog=PROG,
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-n", "--dry-run", action="store_true", help="print to stdout")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress output")
    p.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
    p.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="output file")
    p.add_argument("--json", action="store_true", help="output as JSON instead of org")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.quiet, args.verbose)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))

    digests = scan_digests()
    if not digests:
        LOGGER.error("no digests found in %s", DIGESTS_DIR)
        return 1

    tree = build_tree(digests)

    if args.json:
        output = generate_json(tree)
        out_path = args.output.with_suffix(".json") if not args.output.suffix == ".json" else args.output
    else:
        output = generate_org(tree)
        out_path = args.output

    if args.dry_run:
        print(output)
    else:
        out_path.write_text(output, encoding="utf-8")
        LOGGER.info("wrote %s (%d digests)", out_path, len(digests))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
