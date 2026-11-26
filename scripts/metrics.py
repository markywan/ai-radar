#!/usr/bin/env python3
"""信源转化统计：每个来源、每条主线出了多少机会，有多少进了池子、走到验证、启动、变现。

  python3 scripts/metrics.py                 # 最近 30 天，写 data/metrics.json，并打印一张表
  python3 scripts/metrics.py --days 90

用来回答「哪个来源真的出能做的机会」：2026-11-01 到 11-25 每天 3–5 个候选 100% 来自 TrustMRR，
深挖全是「照抄不做」。跑满 30 天（约 2026-12-26）后按这张表删掉不出货的来源、给出货的加量。
周六周报（weekly.yml）会先跑这个，把结果交给写周报的模型。
"""
import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pool  # noqa: E402

STAGES = ["出现", "进池子", "待验证", "验证中", "已启动", "已变现", "淘汰"]
REACHED = {"待验证": {"待验证", "验证中", "已启动", "已变现"}, "验证中": {"验证中", "已启动", "已变现"},
           "已启动": {"已启动", "已变现"}, "已变现": {"已变现"}, "淘汰": {"淘汰"}}
NAMES = {"trustmrr.com": "TrustMRR", "news.ycombinator.com": "Show HN", "producthunt.com": "Product Hunt",
         "v2ex.com": "V2EX", "x.com": "X", "twitter.com": "X", "github.com": "GitHub issue 和仓库",
         "apify.com": "Apify Store", "ted.europa.eu": "TED 招标", "sam.gov": "SAM.gov", "ungm.org": "UNGM",
         "acquire.com": "acquire.com", "indiehackers.com": "Indie Hackers", "wordpress.org": "WordPress 插件",
         "chromewebstore.google.com": "Chrome 应用商店", "fiverr.com": "Fiverr", "upwork.com": "Upwork",
         "microns.io": "Microns", "flippa.com": "Flippa", "substack.com": "Substack"}


def source_of(url):
    host = re.sub(r"^https?://", "", str(url or "")).split("/")[0].split(":")[0].lower()
    host = re.sub(r"^www\.", "", host)
    for d, name in NAMES.items():
        if host == d or host.endswith("." + d):
            return name
    return host or "没写来源"


def reached(item):
    seen = {h.get("status") for h in item.get("history") or []} | {item.get("status")}
    return {stage for stage, ok in REACHED.items() if seen & ok}


def collect(days, today=None):
    today = today or pool.today()
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=days)).isoformat()
    items = pool.load_all()
    by_fid = {}
    for x in items:
        for fid in [x["id"]] + ((x.get("origin") or {}).get("seen_in") or []):
            by_fid[fid] = x
    rows = {"source": defaultdict(lambda: defaultdict(int)), "track": defaultdict(lambda: defaultdict(int))}
    for p in sorted((ROOT / "data/daily").glob("*.json")):
        if p.stem < since or p.stem > today:
            continue
        try:
            doc = json.loads(p.read_text("utf-8"))
        except ValueError:
            continue
        for b in doc.get("opportunities") or []:
            fid = f"{p.stem}-{b.get('id')}"
            keys = {"source": source_of((b.get("source") or {}).get("url")), "track": b.get("track") or "没挂主线"}
            item = by_fid.get(fid) or (pool.get(b["pool_id"]) if b.get("pool_id") else None)
            for dim, key in keys.items():
                r = rows[dim][key]
                r["出现"] += 1
                if item:
                    r["进池子"] += 1
                    for stage in reached(item):
                        r[stage] += 1
    seeds = [x for x in items if (x.get("origin") or {}).get("kind") == "种子"]
    seed_row = defaultdict(int)
    for x in seeds:
        seed_row["出现"] += 1
        seed_row["进池子"] += 1
        for stage in reached(x):
            seed_row[stage] += 1
    out = {"date": today, "days": days, "since": since,
           "by_source": {k: dict(v) for k, v in sorted(rows["source"].items(), key=lambda kv: -kv[1]["出现"])},
           "by_track": {k: dict(v) for k, v in sorted(rows["track"].items(), key=lambda kv: -kv[1]["出现"])},
           "seeds": dict(seed_row), "pool": pool.summary(items, today)["counts"]}
    return out


def table(title, rows):
    if not rows:
        return f"### {title}\n\n还没有数据。\n"
    head = "| " + title + " | " + " | ".join(STAGES) + " |\n|" + "---|" * (len(STAGES) + 1) + "\n"
    return f"### {title}\n\n" + head + "".join(
        f"| {k} | " + " | ".join(str(v.get(s, 0)) for s in STAGES) + " |\n" for k, v in rows.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    m = collect(a.days)
    if not a.no_write:
        (ROOT / "data/metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"最近 {a.days} 天（{m['since']} 起）\n")
    print(table("来源", m["by_source"]))
    print(table("主线", m["by_track"]))
    print(table("种子", {f"种子 {m['seeds']['出现']} 个": m["seeds"]} if m["seeds"] else {}))
    print("池子现在：" + "，".join(f"{k} {v}" for k, v in m["pool"].items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
