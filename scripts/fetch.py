#!/usr/bin/env python3
"""抓取日报的原始素材，写到 data/raw/<日期>.json。

只用标准库。每个来源单独 try，抓不到就记进 errors，不影响其他来源。
环境变量：
  GITHUB_TOKEN       可选，提高 GitHub 搜索 API 的额度（Actions 里自动有）
  TWITTERAPI_IO_KEY  可选，有它才抓 X
  TIKHUB_API_KEY     可选，有它才抓抖音、小红书、TikTok、YouTube、B站（见 platforms.py）
  TRUSTMRR_API_KEY   可选，有它才抓 TrustMRR 的收入榜（机会卡的收入证据）

抓完会把前 7 天日报里出现过的帖子、文章、仓库标上 seen_before（哪天、哪条、当时的数字），
前 7 天的条目清单放在 recent，前一期日报的 watch_next 会在平台上追搜。

试抓 TikHub：python3 scripts/fetch.py --probe，只抓平台部分，并打印每个接口返回的结构。
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
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
    def __init__(self, limit, interval=5.2):
        self.left, self.interval, self.last = limit, interval, 0.0


def x_get(url, key, budget):
    """twitterapi.io 有每秒请求数上限（免费额度大约 5 秒一次），超了返回 429：两次请求之间留间隔，429 时等一会儿再试。"""
    for wait in (8, 16, 32, None):
        gap = budget.interval - (time.time() - budget.last)
        if gap > 0:
            time.sleep(gap)
        budget.last = time.time()
        try:
            return get_json(url, {"X-API-Key": key})
        except urllib.error.HTTPError as e:
            if e.code != 429 or wait is None:
                raise
            time.sleep(wait)


def x_search(query, qtype, key, budget, pages=1):
    """twitterapi.io 高级搜索。按返回条数计费，budget 控制每天总量。"""
    out, cursor = [], ""
    for _ in range(pages):
        if budget.left <= 0:
            break
        url = "https://api.twitterapi.io/twitter/tweet/advanced_search?" + urllib.parse.urlencode(
            {"query": query, "queryType": qtype, "cursor": cursor})
        try:
            data = x_get(url, key, budget)
        except Exception:  # noqa: BLE001
            if out:  # 第二页失败时保留第一页
                break
            raise
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
    budget = XBudget(cfg["max_tweets"], cfg.get("min_interval_s", 5.2))
    accounts, hot = [], {}
    groups = cfg["accounts"]
    if isinstance(groups, list):  # 老配置：不分组
        groups = {"账号": groups}
    n = cfg["accounts_per_query"]
    for gname, names in groups.items():
        for i in range(0, len(names), n):
            q = "(" + " OR ".join(f"from:{a}" for a in names[i:i + n]) + f") {cfg['account_window']} -filter:replies"
            try:
                for t in x_search(q, "Latest", key, budget, pages=2):
                    t["group"] = gname
                    accounts.append(t)
            except Exception as e:  # noqa: BLE001
                errors.append(f"X {gname}批次 {i // n + 1}: {e}")
    for hq in cfg["hot_queries"]:
        try:
            hot[hq["name"]] = x_search(hq["query"], hq.get("type", "Top"), key, budget)
        except Exception as e:  # noqa: BLE001
            errors.append(f"X 搜索「{hq['name']}」: {e}")
    accounts.sort(key=lambda t: (t.get("likes") or 0), reverse=True)
    return {"accounts": accounts, "hot": hot, "tweets_used": cfg["max_tweets"] - budget.left}


def fetch_topics(cfg, since_day):
    """他行业里的 GitHub 话题：最近有提交、有一定星数的仓库，补总榜看不到的外贸、SEO、电商工具。"""
    out, seen = [], set()
    for t in cfg["topics"]:
        try:
            for r in gh_search(f"topic:{t} pushed:>{since_day} stars:>{cfg.get('min_stars', 200)}", per_page=cfg.get("per_topic", 8)):
                if r["repo"] not in seen:
                    seen.add(r["repo"])
                    r["topic"] = t
                    out.append(r)
        except Exception as e:  # noqa: BLE001
            errors.append(f"GitHub 话题 {t}: {e}")
    return out


def fetch_skills_sh(cfg):
    """skills.sh 的公开榜单：热门（hot，带昨日对比）、趋势、总榜。接口变了就记进 errors，由模型自己打开网页。"""
    out = {}
    for view in cfg.get("views", ["hot", "trending"]):
        url = "https://skills.sh/api/v1/skills?" + urllib.parse.urlencode({"view": view, "limit": cfg.get("limit", 40)})
        try:
            data = get_json(url, {"Accept": "application/json"})
            out[view] = [{"id": x.get("id"), "name": x.get("name"), "source": x.get("source"), "installs": x.get("installs"),
                          "installs_yesterday": x.get("installsYesterday"), "change": x.get("change"),
                          "url": x.get("url") or f"https://skills.sh/{x.get('id')}"} for x in data.get("data", [])]
        except Exception as e:  # noqa: BLE001
            errors.append(f"skills.sh {view} 榜: {e}（请用 WebFetch 打开 https://skills.sh 看榜单）")
    return out


def fetch_trustmrr(cfg, key):
    """TrustMRR 公开 API：一人团队里增长最快的和最近挂牌出售的，给机会卡当收入证据。"""
    out = {}
    for q in cfg["queries"]:
        url = "https://trustmrr.com/api/v1/startups?" + urllib.parse.urlencode(q["params"])
        try:
            data = get_json(url, {"Authorization": f"Bearer {key}", "Accept": "application/json"})
            out[q["name"]] = [{"name": x.get("name"), "url": f"https://trustmrr.com/startup/{x.get('slug')}", "website": x.get("website"),
                               "category": x.get("category"), "team_size": x.get("teamSize"), "mrr_usd": round((x.get("revenue") or {}).get("mrr", 0) / 100),
                               "growth_30d": x.get("growthMRR30d") or x.get("growth30d"), "customers": x.get("customers"),
                               "asking_price_usd": (x.get("askingPrice") or 0) // 100 or None, "description": (x.get("description") or "")[:200]}
                              for x in data.get("data", [])]
        except Exception as e:  # noqa: BLE001
            errors.append(f"TrustMRR「{q['name']}」: {e}")
    return out


def norm_url(u):
    u = str(u or "").strip().lower().replace("twitter.com/", "x.com/")
    u = re.sub(r"^https?://(www\.)?", "", u).split("#")[0].split("?")[0].rstrip("/")
    return u


def recent_items(date, days=7):
    """前 7 天日报里出现过的链接和仓库，以及它们当时的数字。返回 (按链接查的字典, 给模型看的清单)。"""
    seen, listing = {}, []
    d0 = dt.date.fromisoformat(date)
    for p in sorted((ROOT / "data/daily").glob("*.json"), reverse=True):
        try:
            d = dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if not (d0 - dt.timedelta(days=days) <= d < d0):
            continue
        doc = json.loads(p.read_text("utf-8"))
        for key in ("news", "tools", "skills", "opportunities", "trends", "followups"):
            for it in doc.get(key) or []:
                base = {"date": p.stem, "id": it.get("id"), "section": key,
                        "title": it.get("title") or it.get("repo") or it.get("name") or it.get("topic") or ""}
                if it.get("stars_total") is not None:
                    base["stars_total"] = it["stars_total"]
                if it.get("installs") is not None:
                    base["installs"] = it["installs"]
                urls = [it.get("url"), (it.get("source") or {}).get("url") if isinstance(it.get("source"), dict) else None]
                if it.get("repo"):
                    urls.append(f"https://github.com/{it['repo']}")
                for e in (it.get("evidence") or []) + ((it.get("market") or {}).get("evidence_links") or []):
                    if isinstance(e, dict) and e.get("url"):
                        seen.setdefault(norm_url(e["url"]), {**base, "metrics": e.get("metrics")})
                for u in urls:
                    if u:
                        seen.setdefault(norm_url(u), base)
                listing.append({**base, "url": it.get("url") or (f"https://github.com/{it['repo']}" if it.get("repo") else None)})
    return seen, listing


def mark_seen(node, seen, depth=0):
    """把原始素材里前 7 天出现过的帖子、文章、仓库标上 seen_before（哪天、哪条、当时的数字）。"""
    if depth > 8:
        return
    if isinstance(node, dict):
        keys = [node.get("url"), node.get("hn_url"), f"https://github.com/{node['repo']}" if node.get("repo") else None]
        for u in keys:
            hit = seen.get(norm_url(u)) if u else None
            if hit:
                node["seen_before"] = {k: v for k, v in hit.items() if k in ("date", "id", "stars_total", "installs", "metrics")}
                break
        for v in node.values():
            mark_seen(v, seen, depth + 1)
    elif isinstance(node, list):
        for v in node:
            mark_seen(v, seen, depth + 1)


def watch_words(date):
    """前一期日报里模型写的 watch_next：明天要在平台上追搜的工具名或玩法。"""
    past = sorted(p for p in (ROOT / "data/daily").glob("*.json") if p.stem < date)
    if not past:
        return []
    try:
        doc = json.loads(past[-1].read_text("utf-8"))
        return [str(w)[:30] for w in (doc.get("watch_next") or []) if str(w).strip()]
    except (OSError, ValueError):
        return []


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

    raw["github_topics"] = fetch_topics(cfg["github"]["topic_searches"], d0) if cfg["github"].get("topic_searches") else []
    raw["skills_sh"] = fetch_skills_sh(cfg["skills_sh"]) if cfg.get("skills_sh") else {}
    tm = "".join(os.environ.get("TRUSTMRR_API_KEY", "").split())
    if tm and cfg.get("trustmrr"):
        raw["trustmrr"] = fetch_trustmrr(cfg["trustmrr"], tm)
    else:
        raw["trustmrr"] = None
        errors.append("没有配置 TRUSTMRR_API_KEY，收入证据请打开 config/sources.json 里 evidence_pages 的页面找")
    raw["policy_pages_without_rss"] = (cfg.get("policy_pages_without_rss") or {}).get("pages", [])
    raw["evidence_pages"] = (cfg.get("evidence_pages") or {}).get("pages", [])

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

    key = "".join(os.environ.get("TWITTERAPI_IO_KEY", "").split())  # 复制时折行、多出的空格都去掉
    if key:
        raw["x"] = fetch_x(cfg["x"], key)
    else:
        raw["x"] = None
        errors.append("没有配置 TWITTERAPI_IO_KEY，跳过 X")

    raw["watch_next_from_yesterday"] = watch_words(args.date)
    tk = "".join(os.environ.get("TIKHUB_API_KEY", "").split())
    if tk:
        raw["platforms"] = fetch_platforms(cfg["tikhub"], tk, args.date, errors, fresh=raw["watch_next_from_yesterday"])
    else:
        raw["platforms"] = None
        errors.append("没有配置 TIKHUB_API_KEY，跳过抖音、小红书等平台")

    seen, raw["recent"] = recent_items(args.date)
    mark_seen(raw, seen)
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
    key = "".join(os.environ.get("TIKHUB_API_KEY", "").split())
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
