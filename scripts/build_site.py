#!/usr/bin/env python3
"""把 data/ 和 web/ 组装成静态网站。

  python3 scripts/build_site.py                 # 输出到 site/，给 GitHub Pages 用
  python3 scripts/build_site.py --single x.html # 输出一个内嵌全部数据的单页（预览用）
环境变量 WORKER_URL：收藏接口地址，会写进 site/config.json。
"""
import argparse
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600"
         "&family=Noto+Serif+SC:wght@700&display=swap")
TITLE = "AI 机会雷达"


def load():
    dailies = sorted((ROOT / "data/daily").glob("*.json"), reverse=True)
    daily = {p.stem: json.loads(p.read_text("utf-8")) for p in dailies}
    dates = [{
        "date": d,
        "headline": (doc.get("headline") or [""])[0],
        "counts": {k: len(doc.get(k) or []) for k in ("news", "tools", "skills", "opportunities")},
    } for d, doc in daily.items()]
    favs = [json.loads(p.read_text("utf-8")) for p in (ROOT / "data/favorites").glob("*.json")]
    favs.sort(key=lambda f: f.get("saved_at", ""), reverse=True)
    deep = {p.stem: p.read_text("utf-8") for p in (ROOT / "data/deepdive").glob("*.md")}
    index = {"dates": dates, "favorites": favs, "deepdives": sorted(deep)}
    return index, daily, deep


def full_page(head_extra, body_extra):
    body = (ROOT / "web/body.html").read_text("utf-8")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
{head_extra}
</head>
<body>
{body}
{body_extra}
</body>
</html>
"""


def build_pages(out):
    index, daily, deep = load()
    if out.exists():
        shutil.rmtree(out)
    (out / "data/daily").mkdir(parents=True)
    (out / "data/deepdive").mkdir(parents=True)
    for name in ("style.css", "app.js"):
        shutil.copy(ROOT / "web" / name, out / name)
    (out / "index.html").write_text(full_page('<link rel="stylesheet" href="style.css">',
                                              '<script src="app.js"></script>'), "utf-8")
    (out / "config.json").write_text(json.dumps({"worker_url": os.environ.get("WORKER_URL", "")}), "utf-8")
    (out / "data/index.json").write_text(json.dumps(index, ensure_ascii=False), "utf-8")
    for d, doc in daily.items():
        (out / "data/daily" / f"{d}.json").write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
    for k, md in deep.items():
        (out / "data/deepdive" / f"{k}.md").write_text(md, "utf-8")
    (out / ".nojekyll").write_text("", "utf-8")
    print(f"网站已生成：{out}（{len(daily)} 期日报，{len(index['favorites'])} 条收藏）")


def build_single(path, preview):
    index, daily, deep = load()
    data = {"index": index, "daily": daily, "deepdive": deep, "config": {}, "preview": preview}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    css = (ROOT / "web/style.css").read_text("utf-8")
    js = (ROOT / "web/app.js").read_text("utf-8")
    body = (ROOT / "web/body.html").read_text("utf-8")
    page = (f'<title>{TITLE}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{css}\n</style>\n{body}\n'
            f"<script>window.__RADAR__ = {blob};</script>\n<script>\n{js}\n</script>\n")
    Path(path).write_text(page, "utf-8")
    print(f"单页已生成：{path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--single")
    ap.add_argument("--preview", action="store_true", help="单页里的按钮只提示，不真正调用")
    a = ap.parse_args()
    if a.single:
        build_single(a.single, a.preview)
    else:
        build_pages(Path(a.out))


if __name__ == "__main__":
    main()
