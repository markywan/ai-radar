#!/usr/bin/env python3
"""把日报里的一条加入收藏，或标记深挖完成。

  python3 scripts/favorite.py add 2026-10-15-B01 [--deep]
  python3 scripts/favorite.py done 2026-10-15-B01

每条收藏单独一个文件 data/favorites/<id>.json，多次点击同时运行也不会互相覆盖。
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-([NGSB])(\d{2})$")
KEYS = {"N": "news", "G": "tools", "S": "skills", "B": "opportunities"}
LIBRARY = {"N": "资讯库", "G": "工具库", "S": "工具库", "B": "机会库"}
DEFAULT_STATUS = {"N": "已存", "G": "待试", "S": "待试", "B": "观察"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("op", choices=["add", "done"])
    ap.add_argument("id")
    ap.add_argument("--deep", action="store_true")
    a = ap.parse_args()

    m = ID.match(a.id)
    if not m:
        print(f"编号格式不对：{a.id}，应为 YYYY-MM-DD-B01 这种")
        return 2
    date, prefix, _ = m.groups()
    path = ROOT / "data/favorites" / f"{a.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    if a.op == "done":
        fav = json.loads(path.read_text("utf-8"))
        fav["deepdive"] = "done"
        fav["deepdive_at"] = now()
        path.write_text(json.dumps(fav, ensure_ascii=False, indent=1), "utf-8")
        print(f"已标记深挖完成：{a.id}")
        return 0

    daily = ROOT / "data/daily" / f"{date}.json"
    doc = json.loads(daily.read_text("utf-8"))
    item_id = a.id[len(date) + 1:]
    item = next((x for x in doc.get(KEYS[prefix], []) if x.get("id") == item_id), None)
    if item is None:
        print(f"{date} 的日报里没有 {item_id}")
        return 2

    fav = json.loads(path.read_text("utf-8")) if path.exists() else {
        "id": a.id, "date": date, "type": KEYS[prefix], "library": LIBRARY[prefix],
        "status": DEFAULT_STATUS[prefix], "saved_at": now(), "item": item, "deepdive": None,
    }
    if a.deep and fav.get("deepdive") != "done":
        fav["deepdive"] = "pending"
    path.write_text(json.dumps(fav, ensure_ascii=False, indent=1), "utf-8")
    print(f"已收藏：{a.id}" + ("，等待深挖" if a.deep else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
