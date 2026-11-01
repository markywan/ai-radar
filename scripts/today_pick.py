#!/usr/bin/env python3
"""找今日机会：日报 pick 字段记的那个候选（第一个，validate.py 写的），给 daily.yml 的深挖步骤用。

  python3 scripts/today_pick.py 2026-11-02

要深挖时输出两行 id=2026-11-02-B01、pick=B01（daily.yml 直接写进 GITHUB_OUTPUT），不用深挖时什么都不输出，
原因打在标准错误里。已经有这份深挖就不重做。手动重跑同一天、第一个候选换了时：旧深挖没被收藏就删掉重挖，
被收藏了就保留（收藏页要用它）。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pick_name(doc):
    pick = doc.get("pick")
    return next((b.get("name") for b in doc.get("opportunities") or [] if b.get("id") == pick), None)


def previous_version(path):
    """这个文件上一次提交时的内容（重跑同一天时就是重写之前那份）；第一次提交的返回 None。
    Actions 里是浅克隆，检出的那个提交也算「上一次」，正好是重写之前的版本。"""
    rel = str(path.relative_to(ROOT))
    revs = subprocess.run(["git", "log", "--format=%H", "-n", "2", "--", rel],
                          capture_output=True, text=True, cwd=ROOT).stdout.split()
    if len(revs) < 2:
        return None
    shown = subprocess.run(["git", "show", f"{revs[1]}:{rel}"], capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(shown.stdout) if shown.returncode == 0 else None
    except ValueError:
        return None


def main(date):
    path = ROOT / "data/daily" / f"{date}.json"
    doc = json.loads(path.read_text("utf-8"))
    pick = doc.get("pick")
    if not pick:
        print("今天没有机会候选，不深挖", file=sys.stderr)
        return 0
    fid = f"{date}-{pick}"
    md = ROOT / "data/deepdive" / f"{fid}.md"
    if md.is_file() and md.stat().st_size:
        old = previous_version(path)
        old_name, new_name = (pick_name(old) if old else None), pick_name(doc)
        if not old_name or old_name == new_name:
            print(f"{fid} 已经深挖过", file=sys.stderr)
            return 0
        if (ROOT / "data/favorites" / f"{fid}.json").exists():
            print(f"{fid} 换了候选（{old_name} → {new_name}），但旧的深挖已被收藏，保留不重挖", file=sys.stderr)
            return 0
        md.unlink()
        print(f"{fid} 换了候选（{old_name} → {new_name}），删掉旧深挖重挖", file=sys.stderr)
    print(f"id={fid}\npick={pick}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
