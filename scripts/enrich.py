#!/usr/bin/env python3
"""给日报里的 GitHub 工具和 Skills 配图：从仓库 README 里挑截图和演示图。

  python3 scripts/enrich.py data/daily/2026-10-15.json [--no-check]

已经有 images 的条目不动。徽章、Logo、头像、Star 曲线这类图会被过滤掉，
每个条目最多留 4 张，并逐张确认链接能打开、确实是图片（--no-check 跳过确认）。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "ai-radar/1.0"}
MAX_IMAGES = 4
SKIP = re.compile(
    r"shields\.io|badgen|badge|travis-ci|codecov|circleci|coveralls|star-history|starchart|contrib\.rocks|"
    r"opencollective|buymeacoffee|ko-fi|sponsor|discord|twitter\.com|x\.com/|logo|icon|avatar|favicon|wordmark|"
    r"qr|wechat|weixin|group|alipay|donate|"
    r"producthunt\.com/widgets|trendshift\.io|vercel\.com/button|deploy|\.svg(\?|$)",
    re.I,
)
IMG_EXT = re.compile(r"\.(png|jpe?g|gif|webp)(\?|$)", re.I)
ATTACH = re.compile(r"github\.com/(user-attachments/assets|[^/]+/[^/]+/assets)/", re.I)


def get(url, method="GET", timeout=15):
    req = urllib.request.Request(url, headers=UA, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def readme(repo):
    for name in ("README.md", "readme.md", "Readme.md", "README.MD", "README.zh-CN.md", "README_CN.md"):
        try:
            with get(f"https://raw.githubusercontent.com/{repo}/HEAD/{name}") as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            continue
    return ""


SKIP_SECTION = re.compile(r"sponsor|backer|donat|support (us|me|the project)|contributor|star history|stargazer|community|"
                          r"赞助|支持|贡献者|交流群|社群|加群|联系", re.I)


def useful_text(text):
    """去掉赞助、贡献者、交流群这类小节，它们的图基本都是 Logo 和二维码。"""
    keep, skipping, level, skipped = [], False, 0, 0
    for line in text.splitlines():
        h = re.match(r"^(#{1,6})\s+(.*)", line)
        html_h = re.search(r"<h[1-6][\s>]", line, re.I)
        if skipping and ((h and len(h.group(1)) <= level) or html_h or skipped > 30):
            skipping = False
        if not skipping and h and SKIP_SECTION.search(h.group(2)):
            skipping, level, skipped = True, len(h.group(1)), 0
        if skipping:
            skipped += 1
        else:
            keep.append(line)
    return "\n".join(keep)


def candidates(repo, text):
    text = useful_text(text)
    found = []
    for m in re.finditer(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)|<img[^>]+>", text, re.I):
        around = text[max(0, m.start() - 300): m.end() + 200]
        before = text[max(0, m.start() - 300): m.start()]
        if re.search(r"utm_|[?&]ref=|affiliate", around):  # 广告位和赞助商横幅
            continue
        cell = re.findall(r"<td[^>]*width=[\"']?(\d+)(?:px)?[\"'\s>]", before)
        if cell and int(cell[-1]) < 300:  # 表格里的小格子，多半是赞助商 Logo
            continue
        if m.group(1):
            found.append(m.group(1))
            continue
        tag = m.group(0)
        src = re.search(r"src=[\"']([^\"']+)[\"']", tag)
        width = re.search(r"width=[\"']?(\d+)(?:px)?(?=[\"'\s/>])", tag)
        small = re.search(r"(?:max-)?height:\s*(\d+)px", tag)
        if src and not (width and int(width.group(1)) < 240) and not (small and int(small.group(1)) < 160):
            found.append(src.group(1))
    out = []
    for u in found:
        u = u.strip()
        if u.startswith("//"):
            u = "https:" + u
        elif not re.match(r"https?://", u):
            u = f"https://raw.githubusercontent.com/{repo}/HEAD/" + re.sub(r"^(\./|/)+", "", u)
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/(?:blob|raw)/([^?#]+)", u)
        if m:
            u = f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}"
        if SKIP.search(u):
            continue
        if not (IMG_EXT.search(u) or ATTACH.search(u)):
            continue
        if u not in out:
            out.append(u)
    return out


def is_image(url):
    try:
        with get(url, method="HEAD") as r:
            return r.status == 200 and r.headers.get("Content-Type", "").startswith("image/")
    except Exception:
        try:
            with get(url) as r:
                return r.headers.get("Content-Type", "").startswith("image/")
        except Exception:
            return False


def repo_of(item):
    if item.get("repo") and "/" in item["repo"]:
        return item["repo"].strip()
    m = re.match(r"https://github\.com/([^/]+/[^/#?]+)", item.get("url", ""))
    return m.group(1) if m else None


def main(path, check=True):
    p = Path(path)
    doc = json.loads(p.read_text("utf-8"))
    for key in ("tools", "skills"):
        for item in doc.get(key) or []:
            if item.get("images"):
                continue
            repo = repo_of(item)
            if not repo:
                continue
            keep = []
            for u in candidates(repo, readme(repo))[: MAX_IMAGES * 3]:
                if not check or is_image(u):
                    keep.append(u)
                if len(keep) >= MAX_IMAGES:
                    break
            if keep:
                item["images"] = keep
            print(f"{repo}: {len(keep)} 张图")
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], check="--no-check" not in sys.argv)
