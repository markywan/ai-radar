#!/usr/bin/env python3
"""抓取日报的原始素材，写到 data/raw/<日期>.json。

只用标准库。每个来源单独 try，抓不到就记进 errors，不影响其他来源。
环境变量：
  GITHUB_TOKEN       可选，提高 GitHub 搜索 API 的额度（Actions 里自动有）
  TWITTERAPI_IO_KEY  可选，有它才抓 X
  TIKHUB_API_KEY     可选，有它才抓抖音、小红书、TikTok、YouTube、B站、微博、知乎（见 platforms.py）

试抓 TikHub：python3 scripts/fetch.py --probe，只抓平台部分，并打印每个接口返回的结构。
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from platforms import fetch_platforms

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; ai-radar/1.0; +https://github.com)"
TIMEOUT = 25
errors = []


def get(url, headers=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def get_json(url, headers=None):
    return json.loads(get(url, headers))


def strip_tags(s, limit=400):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(re.sub(r"\s+", " ", s)).strip()
    return s[:limit]


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(s.replace("Z", "+0000") if "%z" in fmt else s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_feed(feed, since):
    """解析 RSS 2.0 或 Atom，只保留 since 之后的条目。"""
    text = get(feed["url"])
    root = ET.fromstring(text.encode("utf-8"))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        for it in root.iter("item"):
            items.append({
                "title": strip_tags(it.findtext("title"), 200),
                "url": (it.findtext("link") or "").strip(),
                "published": it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"),
                "summary": strip_tags(it.findtext("description")),
            })
    else:
        for it in root.findall("a:entry", ns):
            link = it.find("a:link[@rel='alternate']", ns)
            if link is None:
                link = it.find("a:link", ns)
            items.append({
                "title": strip_tags(it.findtext("a:title", default="", namespaces=ns), 200),
                "url": link.get("href") if link is not None else "",
                "published": it.findtext("a:published", namespaces=ns) or it.findtext("a:updated", namespaces=ns),
                "summary": strip_tags(it.findtext("a:summary", default="", namespaces=ns)
                                      or it.findtext("a:content", default="", namespaces=ns)),
            })
    out = []
    for i in items:
        d = parse_date(i["published"])
        if d and d < since:
            continue
        i["published"] = d.isoformat() if d else None
        i.update(source=feed["name"], kind=feed["kind"])
        out.append(i)
    return out[:25]


def fetch_trending(url):
    """解析 github.com/trending 页面。页面结构变了就返回空，由 Claude 用 WebFetch 兜底。"""
    page = get(url)
    repos = []
    for block in page.split('<article class="Box-row')[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"', block)
        if not m:
            continue
        name = m.group(1)
        desc = re.search(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', block, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
        total = re.search(r'href="/%s/stargazers"[^>]*>.*?([\d,]+)\s*</a>' % re.escape(name), block, re.S)
        today = re.search(r'([\d,]+)\s+stars? (today|this week)', block)
        repos.append({
            "repo": name,
            "url": f"https://github.com/{name}",
            "description": strip_tags(desc.group(1) if desc else "", 300),
            "language": lang.group(1).strip() if lang else None,
            "stars_total": int(total.group(1).replace(",", "")) if total else None,
            "stars_today": int(today.group(1).replace(",", "")) if today else None,
        })
    return repos


def gh_search(q, per_page=30):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": per_page})
    data = get_json(url, headers)
    return [{
        "repo": r["full_name"], "url": r["html_url"], "description": (r.get("description") or "")[:300],
        "stars_total": r.get("stargazers_count"), "created_at": r.get("created_at"),
        "pushed_at": r.get("pushed_at"), "license": (r.get("license") or {}).get("spdx_id"),
        "topics": r.get("topics", [])[:8], "language": r.get("language"),
    } for r in data.get("items", [])]


def fetch_hn(cfg):
    front = get_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=%d" % cfg["front_page_limit"])
    since = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=36)).timestamp())
    show = get_json("https://hn.algolia.com/api/v1/search?tags=show_hn&hitsPerPage=30&numericFilters="
                    + urllib.parse.quote(f"points>{cfg['show_hn_min_points']},created_at_i>{since}"))

    def slim(h):
        return {"title": h.get("title"), "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                "hn_url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                "points": h.get("points"), "comments": h.get("num_comments")}
    return [slim(h) for h in front.get("hits", [])], [slim(h) for h in show.get("hits", [])]


def fetch_hf(limit):
    data = get_json(f"https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit={limit}")
    return [{"model": m.get("id"), "url": f"https://huggingface.co/{m.get('id')}", "likes": m.get("likes"),
             "downloads": m.get("downloads"), "pipeline": m.get("pipeline_tag")} for m in data]


class XBudget:
    def __init__(self, limit):
        self.left = limit


def x_search(query, qtype, key, budget, pages=1):
    """twitterapi.io 高级搜索。按返回条数计费，budget 控制每天总量。"""
    out, cursor = [], ""
    for _ in range(pages):
        if budget.left <= 0:
            break
        url = "https://api.twitterapi.io/twitter/tweet/advanced_search?" + urllib.parse.urlencode(
            {"query": query, "queryType": qtype, "cursor": cursor})
        data = get_json(url, {"X-API-Key": key})
        for t in data.get("tweets", []):
            a = t.get("author") or {}
            out.append({
                "url": t.get("url") or f"https://x.com/{a.get('userName')}/status/{t.get('id')}",
                "author": a.get("userName"), "author_name": a.get("name"),
                "text": (t.get("text") or "")[:600], "created_at": t.get("createdAt"),
                "likes": t.get("likeCount"), "retweets": t.get("retweetCount"),
                "replies": t.get("replyCount"), "views": t.get("viewCount"),
            })
        budget.left -= len(data.get("tweets", []))
        cursor = data.get("next_cursor") or ""
        if not data.get("has_next_page") or not cursor:
            break
    return out


def fetch_x(cfg, key):
    budget = XBudget(cfg["max_tweets"])
    accounts, hot = [], {}
    names = cfg["accounts"]
    n = cfg["accounts_per_query"]
    for i in range(0, len(names), n):
        q = "(" + " OR ".join(f"from:{a}" for a in names[i:i + n]) + f") {cfg['account_window']} -filter:replies"
        try:
            accounts += x_search(q, "Latest", key, budget, pages=2)
        except Exception as e:  # noqa: BLE001
            errors.append(f"X 账号批次 {i // n + 1}: {e}")
    for hq in cfg["hot_queries"]:
        try:
            hot[hq["name"]] = x_search(hq["query"], hq.get("type", "Top"), key, budget)
        except Exception as e:  # noqa: BLE001
            errors.append(f"X 搜索「{hq['name']}」: {e}")
    accounts.sort(key=lambda t: (t.get("likes") or 0), reverse=True)
    return {"accounts": accounts, "hot": hot, "tweets_used": cfg["max_tweets"] - budget.left}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d"))
    ap.add_argument("--hours", type=int, default=48, help="RSS 只保留最近多少小时")
    ap.add_argument("--probe", action="store_true", help="只抓 TikHub，并打印每个接口返回的结构")
    args = ap.parse_args()
    if args.probe:
        return probe(args.date)

    cfg = json.loads((ROOT / "config/sources.json").read_text("utf-8"))
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=args.hours)
    raw = {"date": args.date, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "official_pages_without_rss": cfg["official_pages_without_rss"]}

    raw["feeds"] = []
    for f in cfg["feeds"]:
        try:
            raw["feeds"] += fetch_feed(f, since)
        except Exception as e:  # noqa: BLE001
            errors.append(f"RSS {f['name']}: {e}")

    raw["github_trending"] = []
    seen = set()
    for url in cfg["github"]["trending_pages"]:
        try:
            for r in fetch_trending(url):
                if r["repo"] not in seen:
                    seen.add(r["repo"])
                    raw["github_trending"].append(r)
        except Exception as e:  # noqa: BLE001
            errors.append(f"GitHub Trending {url}: {e}")
    if not raw["github_trending"]:
        errors.append("GitHub Trending 解析为空，请用 WebFetch 打开 trending 页面兜底")

    d0 = (dt.date.fromisoformat(args.date) - dt.timedelta(days=cfg["github"]["new_repo_days"])).isoformat()
    try:
        raw["github_new"] = gh_search(f"created:>{d0} stars:>50")
    except Exception as e:  # noqa: BLE001
        raw["github_new"] = []
        errors.append(f"GitHub 新项目搜索: {e}")
    raw["skill_repos"] = []
    for topic in cfg["github"]["skill_topics"]:
        try:
            raw["skill_repos"] += gh_search(f"topic:{topic} pushed:>{d0}", per_page=15)
        except Exception as e:  # noqa: BLE001
            errors.append(f"GitHub Skills 搜索 {topic}: {e}")
    try:
        raw["skill_repos"] += gh_search(f"SKILL.md in:readme pushed:>{d0} stars:>20", per_page=20)
    except Exception as e:  # noqa: BLE001
        errors.append(f"GitHub SKILL.md 搜索: {e}")

    try:
        raw["hn_front"], raw["hn_show"] = fetch_hn(cfg["hackernews"])
    except Exception as e:  # noqa: BLE001
        raw["hn_front"], raw["hn_show"] = [], []
        errors.append(f"Hacker News: {e}")
    try:
        raw["hf_trending"] = fetch_hf(cfg["huggingface_trending_limit"])
    except Exception as e:  # noqa: BLE001
        raw["hf_trending"] = []
        errors.append(f"Hugging Face: {e}")

    key = os.environ.get("TWITTERAPI_IO_KEY")
    if key:
        raw["x"] = fetch_x(cfg["x"], key)
    else:
        raw["x"] = None
        errors.append("没有配置 TWITTERAPI_IO_KEY，跳过 X")

    tk = os.environ.get("TIKHUB_API_KEY")
    if tk:
        raw["platforms"] = fetch_platforms(cfg["tikhub"], tk, args.date, errors)
    else:
        raw["platforms"] = None
        errors.append("没有配置 TIKHUB_API_KEY，跳过抖音、小红书等平台")

    raw["errors"] = errors
    raw["counts"] = {k: len(v) for k, v in raw.items() if isinstance(v, list)}
    out = ROOT / "data/raw" / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps({"out": str(out.relative_to(ROOT)), "counts": raw["counts"],
                      "x_tweets": (raw["x"] or {}).get("tweets_used"),
                      "tikhub_requests": (raw["platforms"] or {}).get("requests_used"), "errors": errors},
                     ensure_ascii=False, indent=1))


def probe(date):
    """试抓：只跑 TikHub，打印每个请求认出了几条、返回的结构，原始结果写到 data/raw/<日期>-tikhub.json。"""
    key = os.environ.get("TIKHUB_API_KEY")
    if not key:
        print("没有配置 TIKHUB_API_KEY")
        return 1
    cfg = json.loads((ROOT / "config/sources.json").read_text("utf-8"))
    shapes = []
    res = fetch_platforms(cfg["tikhub"], key, date, errors, probe=shapes)
    for s in shapes:
        print(f"\n===== {s['request']}：认出 {s['found']} 条")
        print("列表：", "  ".join(s["lists"]))
        for item in s["parsed"]:
            print("认出：", json.dumps(item, ensure_ascii=False)[:600])
        print("结构：", json.dumps(s["shape"], ensure_ascii=False)[:1500])
    out = ROOT / "data/raw" / f"{date}-tikhub.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    print("\n===== 汇总")
    print(json.dumps({"requests_used": res["requests_used"], "hot_lists": {k: len(v) for k, v in res["hot_lists"].items()},
                      "searches": [f"{x['platform']}「{x['keyword']}」{x['found']}" for x in res["searches"]],
                      "comments": [f"{x['platform']} {len(x['comments'])}" for x in res["comments"]],
                      "notes": res.get("notes"), "errors": errors}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
