"""用 TikHub 抓国内外内容平台：热榜、关键词搜索、热帖评论。fetch.py 调用这里的 fetch_platforms。

各平台返回的 JSON 结构不一样，也可能改版，所以不按固定路径取值，而是在整棵 JSON 里找
「像一条帖子」的字典（有编号、有文字、有互动数），按常见字段名取标题、作者、播放、点赞、
收藏、评论、转发。哪个请求一条都没认出来，就把返回内容截一段放进 samples，日报照样能看。
"""
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("TIKHUB_BASE", "https://api.tikhub.io")  # 测试时可指向本地假服务
TIMEOUT = 45

ID_KEYS = ("aweme_id", "note_id", "video_id", "videoId", "bvid", "item_id", "noteId", "id")
TITLE_KEYS = ("title", "display_title", "name")
TEXT_KEYS = ("desc", "description", "content", "text", "caption")
LIKE_KEYS = ("digg_count", "liked_count", "like_count", "likes", "like", "likeCount", "diggCount", "likes_count", "voteup_count")
COMMENT_KEYS = ("comment_count", "comments_count", "commentCount", "review", "reply_count")
SHARE_KEYS = ("share_count", "shared_count", "shareCount", "forward_count", "reposts_count")
COLLECT_KEYS = ("collect_count", "collected_count", "favorites", "favorite_count", "collectCount", "favorited_count")
PLAY_KEYS = ("play_count", "view_count", "views", "play", "playCount", "viewCount", "number_of_views", "view_count_text")
FOLLOW_KEYS = ("follower_count", "followers", "fans", "followerCount", "fans_count", "subscriber_count", "subscriberCount")
TIME_KEYS = ("create_time", "timestamp", "pubdate", "publish_time", "published_time", "publishedTimeText", "time", "upload_date")
AUTHOR_OBJ = ("author", "user", "owner", "user_info", "author_info", "channel")
AUTHOR_NAME = ("nickname", "unique_id", "uname", "name", "nick_name", "channel_name", "title")
STAT_OBJ = ("statistics", "stats", "interact_info", "stat", "counts")
COUNT_KEYS = LIKE_KEYS + COMMENT_KEYS + SHARE_KEYS + COLLECT_KEYS + PLAY_KEYS

WORD_KEYS = ("word", "keyword", "trendingSearchWord", "show_name", "query", "sentence", "hot_word", "title", "name", "note", "text")
HOT_KEYS = ("hot_value", "num", "heat_score", "hot_score", "raw_hot", "score", "heat", "search_volume", "detail_text", "hot")

# 热榜里和他相关的词：AI、赚钱、创业、出海、自媒体
INTEREST = re.compile(
    r"AI|A\.I|人工智能|智能|大模型|模型|GPT|Claude|DeepSeek|豆包|Kimi|通义|千问|文心|元宝|智谱|Gemini|OpenAI|Sora|"
    r"机器人|算力|芯片|英伟达|数字人|智能体|Agent|编程|程序员|代码|App|软件|"
    r"副业|赚钱|变现|创业|一人公司|个体户|出海|外贸|跨境|电商|自媒体|博主|带货|直播|涨粉|流量|就业|裁员|"
    r"side hustle|startup|automation|robot|chatbot|LLM", re.I)
# 评论里的需求原话：求助、问价、要教程、要工具名
DEMAND = re.compile(
    r"求|怎么|如何|多少钱|收费|价格|教程|教学|链接|有没有|在哪|哪里|什么软件|什么工具|哪个软件|叫什么|能不能|可以教|"
    r"想学|带带|私信|蹲|已关注|how (do|to|much|did)|what (tool|app|software|ai)|which (tool|app|ai)|link|tutorial|"
    r"price|cost|course|teach", re.I)

TAG = re.compile(r"<[^>]+>")


class Budget:
    """只数成功的请求（失败的不收费）；另外限制总尝试次数，防止接口一直报错时空转。"""

    def __init__(self, limit):
        self.limit, self.used, self.tries = limit, 0, 0

    def ok(self):
        return self.used < self.limit and self.tries < self.limit * 2


class TikHubError(Exception):
    def __init__(self, status, msg):
        super().__init__(f"HTTP {status} {msg}")
        self.status = status


def call(key, path, params=None, method="GET", budget=None):
    budget.tries += 1
    url = BASE + path
    data = None
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "ai-radar/1.0"}
    if method == "POST":
        data = json.dumps(params or {}).encode()
        headers["Content-Type"] = "application/json"
    elif params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:200]
        raise TikHubError(e.code, re.sub(r"\s+", " ", detail)) from None
    finally:
        time.sleep(0.15)  # TikHub 限 10 QPS
    budget.used += 1
    if isinstance(body, dict) and isinstance(body.get("code"), int) and body["code"] >= 400:
        raise TikHubError(body["code"], str(body.get("message") or body.get("detail") or "")[:200])
    if isinstance(body, dict) and body.get("data") is not None:
        return body["data"]
    return body


def call_relaxed(key, spec, params, budget):
    """先带全部筛选条件请求；被拒（4xx）时去掉 relax 里的参数再试一次。"""
    method = spec.get("method", "GET")
    try:
        return call(key, spec["path"], params, method, budget), None
    except TikHubError as e:
        drop = [k for k in spec.get("relax", []) if k in params]
        if not drop or not (400 <= (e.status or 0) < 500) or not budget.ok():
            raise
        loose = {k: v for k, v in params.items() if k not in drop}
        return call(key, spec["path"], loose, method, budget), f"去掉 {'、'.join(drop)} 后重试成功（{e}）"


# ---------- 取值 ----------

def num(v):
    """把 12345、"1.2万"、"3.4K views"、{"count": 5} 都变成整数。"""
    if v is None or isinstance(v, bool) or isinstance(v, list):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, dict):
        for k in ("count", "value", "text", "simpleText", "num"):
            if k in v:
                return num(v[k])
        return None
    s = str(v).replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万|亿|千|[kKmMbB](?![a-z]))?", s)
    if not m:
        return None
    mult = {"万": 1e4, "亿": 1e8, "千": 1e3, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6, "b": 1e9, "B": 1e9}
    return int(float(m.group(1)) * mult.get(m.group(2) or "", 1))


def text_of(v):
    if isinstance(v, str):
        return re.sub(r"\s+", " ", TAG.sub("", v)).strip()
    if isinstance(v, dict):  # B站评论 content.message、YouTube runs
        for k in ("message", "text", "simpleText", "content"):
            if isinstance(v.get(k), str):
                return text_of(v[k])
    return ""


def pick_text(d, keys):
    for k in keys:
        t = text_of(d.get(k))
        if t:
            return t
    return ""


def pick_num(ds, keys):
    for d in ds:
        for k in keys:
            if k in d:
                n = num(d[k])
                if n is not None:
                    return n
    return None


def when(v):
    if v in (None, ""):
        return None
    n = v if isinstance(v, (int, float)) else (int(v) if str(v).isdigit() else None)
    if n:
        if n > 1e12:
            n /= 1000
        if n > 1e9:
            return dt.datetime.fromtimestamp(n, dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d")
    return str(v)[:40]


def post_url(platform, d, pid, author):
    if platform == "抖音":
        return f"https://www.douyin.com/video/{pid}"
    if platform == "小红书":
        tok = d.get("xsec_token")
        return f"https://www.xiaohongshu.com/explore/{pid}" + (f"?xsec_token={tok}&xsec_source=pc_search" if tok else "")
    if platform == "B站" and str(pid).startswith("BV"):
        return f"https://www.bilibili.com/video/{pid}"
    if platform == "YouTube":
        return f"https://www.youtube.com/watch?v={pid}"
    if platform == "TikTok" and isinstance(author, dict) and author.get("unique_id"):
        return f"https://www.tiktok.com/@{author['unique_id']}/video/{pid}"
    for k in ("share_url", "arcurl", "url", "link", "note_url", "video_url"):
        u = d.get(k)
        if isinstance(u, str) and u.startswith("http"):
            return u.split("?")[0].replace("http://", "https://")
    return None


def as_post(platform, d):
    """一个字典像不像一条帖子：有编号、有文字、有至少一个互动数。像就整理成统一格式。"""
    pid = next((d[k] for k in ID_KEYS if isinstance(d.get(k), (str, int)) and str(d.get(k)).strip()), None)
    title, desc = pick_text(d, TITLE_KEYS), pick_text(d, TEXT_KEYS)
    if pid is None or not (title or desc):
        return None
    stats = [d] + [d[k] for k in STAT_OBJ if isinstance(d.get(k), dict)]
    if not any(k in s for s in stats for k in COUNT_KEYS):
        return None
    author_obj = next((d[k] for k in AUTHOR_OBJ if isinstance(d.get(k), dict)), {})
    author = pick_text(author_obj, AUTHOR_NAME) or text_of(d.get("author")) or pick_text(d, ("channel_name", "channelName", "nickname", "uname"))
    followers = pick_num([author_obj, d], FOLLOW_KEYS)
    p = {
        "platform": platform, "id": str(pid),
        "title": (title or desc)[:160], "desc": desc[:300] if title and desc != title else "",
        "url": post_url(platform, d, pid, author_obj), "author": author[:40], "followers": followers,
        "plays": pick_num(stats, PLAY_KEYS), "likes": pick_num(stats, LIKE_KEYS),
        "comments": pick_num(stats, COMMENT_KEYS), "collects": pick_num(stats, COLLECT_KEYS),
        "shares": pick_num(stats, SHARE_KEYS), "published": when(next((d[k] for k in TIME_KEYS if d.get(k)), None)),
    }
    likes = p["likes"] or 0
    if likes >= 50:
        if p["collects"] is not None:
            p["collect_rate"] = round(p["collects"] / likes, 2)
        if p["comments"] is not None:
            p["comment_rate"] = round(p["comments"] / likes, 2)
    if followers is not None and followers < 10000 and likes >= 1000:
        p["small_account_hit"] = True  # 小号爆款：靠内容不靠粉丝，形式可以照搬
    return {k: v for k, v in p.items() if v not in (None, "")}


def walk(node, fn, out, depth=0):
    if depth > 12:
        return
    if isinstance(node, dict):
        got = fn(node)
        if got is not None:
            out.append(got)
            return
        for v in node.values():
            walk(v, fn, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn, out, depth + 1)


def find_posts(platform, data):
    out, seen = [], set()
    walk(data, lambda d: as_post(platform, d), out)
    uniq = []
    for p in out:
        if p["id"] not in seen:
            seen.add(p["id"])
            uniq.append(p)
    return uniq


def find_comments(data):
    def as_comment(d):
        t = text_of(d.get("text")) or text_of(d.get("content")) or text_of(d.get("comment")) or text_of(d.get("textDisplay"))
        if not t or len(t) < 2:
            return None
        likes = pick_num([d], ("digg_count", "like_count", "like", "likes", "liked_count", "vote_count", "likeCount"))
        if likes is None:
            return None
        c = {"text": t[:200], "likes": likes}
        if DEMAND.search(t):
            c["demand"] = True
        return c
    out = []
    walk(data, as_comment, out)
    out.sort(key=lambda c: (c.get("demand", False), c["likes"]), reverse=True)
    return out


def find_words(data):
    """热榜：找最长的一串「词 + 热度」；纯字符串列表也算。"""
    best = []

    def entry(d):
        w = pick_text(d, WORD_KEYS)
        if not w:
            for v in d.values():
                if isinstance(v, dict):
                    w = pick_text(v, WORD_KEYS)
                    if w:
                        break
        if not w:
            return None
        h = pick_num([d], HOT_KEYS)
        if h is None:
            for v in d.values():
                if isinstance(v, dict):
                    h = pick_num([v], HOT_KEYS)
                    if h is not None:
                        break
        return {"word": w[:60], "hot": h}

    def scan(node, depth=0):
        nonlocal best
        if depth > 8:
            return
        if isinstance(node, list) and node:
            if all(isinstance(x, str) for x in node) and len(node) >= 5:
                cand = [{"word": x[:60], "hot": None} for x in node]
            else:
                cand = [e for e in (entry(x) for x in node if isinstance(x, dict)) if e]
                if len(cand) < len(node) / 2:
                    cand = []
            if len(cand) > len(best):
                best = cand
            for x in node:
                scan(x, depth + 1)
        elif isinstance(node, dict):
            for v in node.values():
                scan(v, depth + 1)
    scan(data)
    for i, e in enumerate(best, 1):
        e["rank"] = i
        if INTEREST.search(e["word"]):
            e["match"] = True
    return best


def sample(data, limit=1500):
    """认不出结构时留一段原文，日报照样能读。"""
    return json.dumps(data, ensure_ascii=False)[:limit]


def shape(node, depth=0):
    """返回结构的骨架：每个列表只看第一项，字符串截短。试抓时打印出来，方便核对字段。"""
    if depth > 9:
        return "…"
    if isinstance(node, dict):
        return {k: shape(v, depth + 1) for k, v in list(node.items())[:40]}
    if isinstance(node, list):
        return [shape(node[0], depth + 1), f"…共 {len(node)} 项"] if node else []
    if isinstance(node, str):
        return node[:40]
    return node


def lists(node, path="", out=None, depth=0):
    """试抓用：列出返回里每个列表的位置和长度，看帖子是不是只认出了一部分。"""
    out = [] if out is None else out
    if depth > 9:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            lists(v, f"{path}.{k}" if path else k, out, depth + 1)
    elif isinstance(node, list):
        if len(node) >= 2:
            out.append(f"{path}[{len(node)}]")
        if node:
            lists(node[0], f"{path}[0]", out, depth + 1)
    return out


# ---------- 主流程 ----------

def todays_keywords(spec, day):
    pool, k = spec["keywords"], spec.get("per_day", len(spec["keywords"]))
    start = (day * k) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(min(k, len(pool)))]


def fill(params, now):
    subs = {"{now}": str(int(now.timestamp())), "{week_ago}": str(int((now - dt.timedelta(days=7)).timestamp()))}
    return {k: subs.get(v, v) if isinstance(v, str) else v for k, v in params.items()}


def fetch_platforms(cfg, key, date, errors, probe=None):
    """probe 是一个列表时，把每个请求的返回骨架放进去（试抓用）。"""
    budget = Budget(cfg["max_requests"])
    now = dt.datetime.now(dt.timezone.utc)
    day = dt.date.fromisoformat(date).toordinal()
    keep = cfg.get("keep_per_search", 10)
    out = {"hot_lists": {}, "searches": [], "comments": [], "samples": [], "notes": []}

    def record(label, data, n, items=()):
        if probe is not None:
            probe.append({"request": label, "found": n, "shape": shape(data), "lists": lists(data)[:12], "parsed": list(items)[:3]})
        if n == 0:
            out["samples"].append({"request": label, "raw": sample(data)})

    for h in cfg["hot_lists"]:
        if not budget.ok():
            break
        try:
            data = call(key, h["path"], h.get("params"), "GET", budget)
            words = find_words(data)
            record(h["name"], data, len(words), words)
            out["hot_lists"][h["name"]] = [w for w in words if w["rank"] <= 10 or w.get("match")][:40]
        except Exception as e:  # noqa: BLE001
            errors.append(f"TikHub {h['name']}: {e}")

    for spec in cfg["searches"]:
        for kw in todays_keywords(spec, day):
            if not budget.ok():
                errors.append("TikHub 今天的请求额度用完了，后面的搜索没做")
                break
            label = f"{spec['platform']}「{kw}」"
            params = fill(dict(spec.get("params", {}), **{spec["keyword_param"]: kw}), now)
            try:
                data, note = call_relaxed(key, spec, params, budget)
                if note:
                    out["notes"].append(f"{label}：{note}")
                posts = find_posts(spec["platform"], data)
                record(label, data, len(posts), posts)
                posts.sort(key=lambda p: (p.get("likes") or 0, p.get("plays") or 0), reverse=True)
                out["searches"].append({"platform": spec["platform"], "keyword": kw, "found": len(posts), "items": posts[:keep]})
            except Exception as e:  # noqa: BLE001
                errors.append(f"TikHub {label}: {e}")

    cc = cfg.get("comments") or {}
    for platform, ep in (cc.get("endpoints") or {}).items():
        posts = list({p["id"]: p for s in out["searches"] if s["platform"] == platform for p in s["items"]}.values())
        posts.sort(key=lambda p: (p.get("comments") or 0, p.get("likes") or 0), reverse=True)
        for p in posts[:cc.get("per_platform", 2)]:
            if not budget.ok():
                break
            label = f"{platform} 评论：{p['title'][:20]}"
            try:
                data = call(key, ep["path"], dict(ep.get("params", {}), **{ep["id_param"]: p["id"]}), ep.get("method", "GET"), budget)
                found = find_comments(data)
                record(label, data, len(found), found)
                out["comments"].append({"platform": platform, "post_title": p["title"], "post_url": p.get("url"),
                                        "post_likes": p.get("likes"), "comments": found[:cc.get("keep", 20)]})
            except Exception as e:  # noqa: BLE001
                errors.append(f"TikHub {label}: {e}")

    out["requests_used"] = budget.used
    out["max_requests"] = budget.limit
    if not out["samples"]:
        del out["samples"]
    if not out["notes"]:
        del out["notes"]
    return out
