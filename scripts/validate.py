#!/usr/bin/env python3
"""校验并规整一期日报 JSON：补编号、检查必填字段和链接、算阅读时长、统计条数。

用法：python3 scripts/validate.py data/daily/2026-11-02.json
有错误时退出码为 1，并打印要修的地方（Claude 在 Actions 里会据此改正）。

2026-11-26 起（format 3）日报的目标是「每天把机会池往前推一步」：
  今天只做一件事（today）、今日机会 0–1 个（先过 7 条门槛再按 100 分打分，75 分以上记进 pick 去深挖）、
  GitHub 3–5 个（对着工具链挑）加日榜速览 3 条、Skills 2–4 个（第一个是本周装这个）。
2026-11-01 到 11-25 的老格式（3–5 个候选、actions）不再校验，网站照老样子显示。
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = {
    # 栏目键: (编号前缀, 必填字段, 数量范围)。编号前缀 N（资讯）、P（玩法风向）、F（跟进）留给老日报，不再用
    "tools": ("G", ["repo", "url", "what", "safety", "why_today", "stage", "pairs_with", "from"], (3, 5)),
    "skills": ("S", ["name", "url", "what", "safety"], (2, 4)),
    # 今日机会 0–1 个：没有合格的就空着、写 leads。2026-11-01 到 11-25 每天 3–5 个候选全来自 TrustMRR，深挖 6 篇全是「照抄不做」
    "opportunities": ("B", ["name", "one_liner", "hypothesis", "gates", "score", "evidence", "competition",
                            "biggest_risk", "first_10_customers"], (0, 1)),
}
FORMAT = 3
# 100 分：需求和付费证据 25、获客渠道 25、经验匹配 20、自动化 15、7 天首单路径 10、收款合规 5
SCORE = {"demand": 25, "channel": 25, "fit": 20, "automation": 15, "first_sale": 10, "payment": 5}
PASS, DEEP = 60, 75
HYPOTHESIS = ["customer", "pain", "deliverable", "price", "channel"]
GATE_TEXT = ["light_ops", "channel_reach", "payment", "direct_demand"]
EVIDENCE_TYPES = {"需求", "付费", "渠道", "竞品"}
# 只当线索、不能单独当需求或付费证据的来源；TrustMRR 只算别人的收入基准
LEAD_ONLY = ("trustmrr.com", "news.ycombinator.com", "producthunt.com", "v2ex.com", "x.com", "twitter.com")
STAGES = {"找客户", "抓数据", "写内容", "发布", "收款客服", "监控"}
FROM = {"主线话题", "issue需求", "日榜", "新项目"}
# 谁都能套的空话
CLICHES = ("降本增效", "赋能", "具有重要意义", "一站式", "全方位", "助力企业", "颠覆")
SAFETY = {"绿", "黄", "红"}
# 用法只写他的方向，其他方向不写：三期里 66 条用法只有 31 条在原来的四个方向里，其余他不会去做。
# 2026-10-30 他转做海外生意，从四个扩到六个：加了供需（供需撮合）和宣传（海外宣传）
AREAS = {"外贸", "SEO", "自媒体", "供需", "宣传", "做产品"}
# 许可证三档：能不能拿它做托管版来卖（fetch.py 按 SPDX 先定档，认不出的由模型读 LICENSE 定）
LICENSE_TIERS = {"能托管来卖", "托管要公开改动", "不能托管来卖"}
URL = re.compile(r"^https?://[^\s<>\"']+$")
MAX_WIDTH = 3000        # 全文字数上限（中文算 1，英文数字算 0.5）；目标 1500 字左右（深挖报告另算）
READ_SPEED = 500        # 每分钟读多少字，算「读完约 N 分钟」
# 不算进阅读量的字段：链接、编号、枚举值
SKIP_KEYS = {"url", "id", "repo", "published", "platform", "platforms", "source_type", "safety", "hot", "verdict",
             "category", "tier", "group", "track", "works_with", "license", "area", "minutes", "images", "ref",
             "stars_total", "stars_today", "installs", "generated_at", "date", "signal", "name",
             "safety_note", "tags", "license_tier", "stars_7d", "reactions", "score", "score_notes", "gates",
             "type", "stage", "pairs_with", "from", "pool_ref", "format", "evidence", "leads", "business_evidence",
             "minutes"}  # 门槛、打分、证据默认折叠，不算阅读量  # 安全依据默认折叠，不算阅读量，但单条限 200 字


def host_of(url):
    return re.sub(r"^https?://", "", str(url)).split("/")[0].split(":")[0].lower()


def host_in(url, domains):
    host = host_of(url)
    return any(host == d or host.endswith("." + d) for d in domains)


def popular(it):
    """红色条目只收热度很高的。"""
    return ((it.get("stars_total") or 0) >= 5000 or (it.get("stars_today") or 0) >= 500
            or (it.get("installs") or 0) >= 5000)


def plain(s):
    return re.sub(r"\*\*|`", "", str(s or ""))


def width(s):
    """按字数算长度：中文算 1，英文和数字算半个。加粗和反引号标记不算。"""
    return sum(1 if ord(c) > 0x2E7F else 0.5 for c in plain(s))


def text_width(node, key=None):
    """整篇的字数：递归加总所有正文字段。"""
    if isinstance(node, dict):
        return sum(text_width(v, k) for k, v in node.items() if k not in SKIP_KEYS)
    if isinstance(node, list):
        return sum(text_width(v, key) for v in node)
    if isinstance(node, str) and not URL.match(node):
        return width(node)
    return 0


def load_tracks():
    try:
        return {t["name"] for t in json.loads((ROOT / "config/tracks.json").read_text("utf-8"))["tracks"]}
    except (OSError, ValueError, KeyError):
        return set()


def norm(s):
    return re.sub(r"^https?://(www\.)?|/+$", "", re.sub(r"\s+", "", str(s or "").lower()))


def deepdived_opps(date):
    """以前深挖过的机会（名字和来源链接）：今日机会不要重复挖。"""
    seen = set()
    for p in (ROOT / "data/deepdive").glob("*-B[0-9][0-9].md"):
        day, bid = p.stem[:10], p.stem[11:]
        if day >= date:
            continue
        try:
            doc = json.loads((ROOT / "data/daily" / f"{day}.json").read_text("utf-8"))
        except (OSError, ValueError):
            continue
        for b in doc.get("opportunities") or []:
            if b.get("id") == bid:
                seen |= {norm(b.get("name")), norm((b.get("source") or {}).get("url"))} - {""}
    return seen


def check_uses(i, it, key, problems):
    uses = it.get("uses")
    if uses is None and not it.get("use_for_me" if key == "tools" else "how_i_use"):
        problems.append(f"{i} 缺少 uses（他能怎么用）")
    if uses is None:
        return
    if not isinstance(uses, list) or not 1 <= len(uses) <= 2:
        problems.append(f"{i} 的 uses 只写 1–2 条，挑最像他会做的")
        return
    for u in uses:
        if not (isinstance(u, dict) and u.get("area") and u.get("how")):
            problems.append(f"{i} 的 uses 每条都要有 area 和 how")
        elif u["area"] not in AREAS:
            problems.append(f"{i} 的用法方向「{u['area']}」不在他的六个方向里（{'/'.join(sorted(AREAS))}），换一条或删掉")
        elif width(u["how"]) > 60:
            problems.append(f"{i} 的用法「{u['area']}」要在 60 字以内：{plain(u['how'])[:30]}…")


def check_business(i, it, problems):
    """工具卡按能做什么生意挑（2026-10-30 起）：生意一句话、许可证档、需求证据。"""
    biz = it.get("business") or ""
    if not biz:
        problems.append(f"{i} 缺少 business（能拿它做什么生意：卖什么、卖给谁、怎么收钱）；想不出生意的工具不要选")
    elif width(biz) > 40:
        problems.append(f"{i} 的 business 要在 40 字以内：{plain(biz)[:30]}…")
    if "托管" in biz and not it.get("demand") and not re.search(r"\d", plain(it.get("business_evidence") or "")):
        problems.append(f"{i} 的 business 写了托管版，但没有 issue 需求证据（demand）也没有同类托管版的收入（business_evidence）："
                        "要么补证据，要么换一个更实在的生意")
    if it.get("license_tier") not in LICENSE_TIERS:
        problems.append(f"{i} 的 license_tier 只能是 {'/'.join(sorted(LICENSE_TIERS))}：照抄素材，素材里是 null 就打开 LICENSE 看完再定")
    demand = it.get("demand")
    if demand is not None:
        if not isinstance(demand, list) or len(demand) > 3:
            problems.append(f"{i} 的 demand 是最多 3 条的数组（issue 标题、链接、点赞数），没有就不写")
        else:
            for e in demand:
                if not (isinstance(e, dict) and e.get("title") and URL.match(str(e.get("url", ""))) and host_in(e["url"], ("github.com",))):
                    problems.append(f"{i} 的 demand 每条都要有 title 和 GitHub 上的 url：{e}")
                elif not isinstance(e.get("reactions"), int):
                    problems.append(f"{i} 的 demand「{e['title'][:20]}」要写 reactions（点赞数，整数）")
    if it.get("stars_7d") is not None and not isinstance(it["stars_7d"], int):
        problems.append(f"{i} 的 stars_7d 是素材里的整数，没有就不写")


def check_card(key, it, problems):
    i = it["id"]
    brief = it.get("brief") or ""
    if not brief:
        problems.append(f"{i} 缺少 brief（一句话说清是什么，网站折叠时只显示这句）")
    elif width(brief) > 26 or "**" in brief:
        problems.append(f"{i} 的 brief 要在 26 个字以内，不加粗：{brief}")
    if key == "tools":
        if it.get("from") not in FROM:
            problems.append(f"{i} 的 from 只能是 {'/'.join(sorted(FROM))}")
        if not it.get("pairs_with"):
            problems.append(f"{i} 要写 pairs_with：和他收藏里的哪个工具搭着用，没有就写「无」")
        wt = it.get("why_today") or ""
        if wt and (width(wt) > 20 or "**" in wt):
            problems.append(f"{i} 的 why_today 要在 20 个字以内，不加粗，写数字：{wt}")
        check_business(i, it, problems)
    if it.get("safety") in ("黄", "红"):
        rb = it.get("risk_brief") or ""
        if not rb:
            problems.append(f"{i} 安全是{it['safety']}，要写 risk_brief（一句话最大风险）")
        elif width(rb) > 30 or "**" in rb:
            problems.append(f"{i} 的 risk_brief 要在 30 个字以内，不加粗：{rb}")
        if not it.get("safety_note"):
            problems.append(f"{i} 安全是{it['safety']}，必须在 safety_note 写清风险")
        elif width(it["safety_note"]) > 200:
            problems.append(f"{i} 的 safety_note 要在 200 字以内：一句结论、最多两句依据、一段「防范：」")
    if it.get("safety") == "红" and not popular(it):
        problems.append(f"{i} 安全是红，但热度不够（要 5000 星以上、今日 500 星以上或安装 5000 以上），换掉")
    check_uses(i, it, key, problems)
    if key == "skills" and it.get("stars_total") is None and it.get("installs") is None and not it.get("popularity_note"):
        problems.append(f"{i} 要写出热度：stars_total、installs 或 popularity_note 至少一个")
    if key == "skills" and it.get("hot") not in (None, "新晋热门", "长期热门"):
        problems.append(f"{i} 的 hot 只能是 新晋热门 / 长期热门")
    if it.get("stage") is not None and it["stage"] not in STAGES:
        problems.append(f"{i} 的 stage 只能是 {'/'.join(sorted(STAGES))}")
    if width(it.get("what") or "") > 100:
        problems.append(f"{i} 的 what 要在 100 字以内，细节让他自己去仓库看")
    imgs = it.get("images")
    if imgs is not None:
        if not isinstance(imgs, list) or any(not URL.match(str(u)) for u in imgs):
            problems.append(f"{i} 的 images 必须是图片链接数组")
        else:
            it["images"] = imgs[:6]


def check_opp(it, problems):
    """今日机会：先过 7 条硬门槛，再按 100 分打分；证据里要有不是线索来源的直接需求或付费证据。"""
    i = it["id"]
    if width(it.get("one_liner") or "") > 60:
        problems.append(f"{i} 的 one_liner 要在 60 字以内：卖什么、卖给海外的谁、怎么收钱")
    hyp = it.get("hypothesis") or {}
    for k in HYPOTHESIS:
        if not str(hyp.get(k) or "").strip():
            problems.append(f"{i} 的 hypothesis.{k} 没写：窄假设要写清卖给谁、什么痛、交付什么、多少钱、第一批客户从哪来")
    if hyp.get("price") and not re.search(r"\d", str(hyp["price"])):
        problems.append(f"{i} 的 hypothesis.price 要有数字和币种，比如「$29 一份」")
    g = it.get("gates") or {}
    limits = (("mvp_days", 14, "MVP 要 14 天内做得出来"), ("startup_cost_usd", 500, "起步资金不超过 500 美元"),
              ("weekly_hours", 3, "稳定后每周不超过 3 小时"))
    for k, hi, why in limits:
        v = g.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            problems.append(f"{i} 的 gates.{k} 要写数字（{why}）")
        elif v > hi:
            problems.append(f"{i} 没过门槛：gates.{k} 是 {v}，{why}。过不了就不收，放进 leads")
    for k in GATE_TEXT:
        if not str(g.get(k) or "").strip():
            problems.append(f"{i} 的 gates.{k} 没写（7 条门槛每条都要写清怎么过）")
    sc = it.get("score") or {}
    total = 0
    for k, hi in SCORE.items():
        v = sc.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= hi:
            problems.append(f"{i} 的 score.{k} 要是 0–{hi} 的整数")
        else:
            total += v
    extra = set(sc) - set(SCORE) - {"total"}
    if extra:
        problems.append(f"{i} 的 score 只有这几项：{'/'.join(SCORE)}，多出来的 {'/'.join(sorted(extra))} 删掉")
    sc["total"] = total
    if total < PASS and not any(p.startswith(f"{i} 的 score.") for p in problems):
        problems.append(f"{i} 只有 {total} 分，不到 {PASS} 分不进日报：挪到 leads，写清卡在哪")
    it["verdict"] = "值得验证" if total >= DEEP else "待研究"
    ev = it.get("evidence") or []
    if not isinstance(ev, list) or not 2 <= len(ev) <= 4:
        problems.append(f"{i} 的 evidence 要 2–4 条你打开过的链接")
        ev = ev if isinstance(ev, list) else []
    direct = False
    for e in ev:
        if not (isinstance(e, dict) and e.get("title") and URL.match(str(e.get("url", "")))):
            problems.append(f"{i} 的 evidence 每条要有 title 和合法的 url：{e}")
            continue
        if e.get("type") not in EVIDENCE_TYPES:
            problems.append(f"{i} 的 evidence「{e['title'][:20]}」的 type 只能是 {'/'.join(sorted(EVIDENCE_TYPES))}")
        if not e.get("note"):
            problems.append(f"{i} 的 evidence「{e['title'][:20]}」要写 note：一句话写你在页面上看到的数字")
        if e.get("type") in ("需求", "付费") and not host_in(e["url"], LEAD_ONLY):
            direct = True
    if ev and not direct:
        problems.append(f"{i} 缺一条直接需求或付费证据（type 是 需求 或 付费，且不是 TrustMRR、Show HN、Product Hunt、V2EX、X）："
                        "issue 原话、Apify 用户数、招标公告、插件差评、Fiverr 订单数这类。TrustMRR 只算别人的收入基准")
    src = (it.get("source") or {}).get("url")
    if src and not URL.match(str(src)):
        problems.append(f"{i} 的 source.url 不是合法链接")


def check_cliches(doc, problems):
    for key in ("opportunities", "tools", "skills"):
        for it in doc.get(key) or []:
            text = json.dumps({k: v for k, v in it.items() if k not in ("url", "repo", "evidence")}, ensure_ascii=False)
            hit = [c for c in CLICHES if c in text]
            if hit:
                problems.append(f"{it['id']} 里有空话「{'、'.join(hit)}」，换成具体的人、数字和动作")


def pool_now():
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import pool  # noqa: PLC0415
        return pool.load_all()
    except Exception:  # noqa: BLE001
        return []


def weekday_track(date):
    try:
        conf = json.loads((ROOT / "config/tracks.json").read_text("utf-8"))
        import datetime as dt  # noqa: PLC0415
        return (conf.get("rotation") or {}).get(str(dt.date.fromisoformat(date).isoweekday()))
    except (OSError, ValueError, KeyError):
        return None


def main(path):
    p = Path(path)
    doc = json.loads(p.read_text("utf-8"))
    problems = []
    tracks = {re.sub(r"\s+", "", t): t for t in load_tracks()}  # 「SEO 与 GEO」和「SEO与GEO」算同一条
    date = str(doc.get("date", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        problems.append("date 必须是 YYYY-MM-DD")
    doc["format"] = FORMAT
    track = weekday_track(date) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else None
    if track:
        doc["track"] = track
    if not isinstance(doc.get("headline"), list) or not 1 <= len(doc["headline"]) <= 2:
        problems.append("headline 写 1–2 句：第一句说今天最重要的事（今日机会是什么、几分，或今天没有合格的）")
    for old in ("news", "trends", "followups", "watch_next", "actions"):
        if doc.get(old):
            problems.append(f"{old} 栏目不用了（2026-11-26 起「今天做什么」只写一件，放在 today），脚本已经删掉")
        doc.pop(old, None)

    total = 0
    for key, (prefix, required, (lo, hi)) in SECTIONS.items():
        items = doc.get(key) or []
        doc[key] = items
        if not (lo <= len(items) <= hi):
            problems.append(f"{key} 条数 {len(items)} 不在 {lo}–{hi} 之间")
        for i, it in enumerate(items, 1):
            it["id"] = f"{prefix}{i:02d}"
            for f in required:
                if it.get(f) in (None, "", [], {}):
                    problems.append(f"{it['id']} 缺少 {f}")
            if it.get("url") and not URL.match(it["url"]):
                problems.append(f"{it['id']} 的 url 不是合法链接: {it['url']}")
            if "safety" in required and it.get("safety") not in SAFETY:
                problems.append(f"{it['id']} 的 safety 只能是 绿/黄/红")
            if it.get("track") and tracks:
                t = tracks.get(re.sub(r"\s+", "", str(it["track"])))
                if t:
                    it["track"] = t
                else:
                    problems.append(f"{it['id']} 的 track 只能是 {'/'.join(sorted(tracks.values()))}")
            if key in ("tools", "skills"):
                check_card(key, it, problems)
            elif key == "opportunities":
                check_opp(it, problems)
        total += len(items)

    pool = pool_now()
    pool_ids = {x["id"]: x for x in pool}
    validating = [x for x in pool if x.get("status") == "验证中"]
    dropped = {norm(x.get("name")) for x in pool if x.get("status") == "淘汰"}

    # 今日机会：只来自今天这条线；75 分以上记进 pick，没有在验证的项目时去深挖（today_pick.py 再查一次）
    opps = doc["opportunities"]
    doc.pop("pick", None)
    if track == "复盘" and opps:
        problems.append("周六复盘不出新机会：opportunities 留空，today 推进池子里的项目")
    for b in opps:
        if track in tracks.values() and b.get("track") != track:
            problems.append(f"{b['id']} 的 track 是 {b.get('track')}，今天轮到的是 {track}：今日机会只从今天这条线找")
        ref = b.get("pool_ref")
        if ref and ref not in pool_ids:
            problems.append(f"{b['id']} 的 pool_ref「{ref}」池子里没有（看素材 pool.items 的 id），不是推进已有项目就不写")
        if norm(b.get("name")) in dropped:
            problems.append(f"{b['id']}「{b.get('name')}」池子里已经淘汰过，换一个")
        if {norm(b.get("name")), norm((b.get("source") or {}).get("url"))} & deepdived_opps(date):
            problems.append(f"{b['id']}「{b.get('name')}」以前深挖过（见素材里的 deepdived），换一个，或者写 pool_ref 推进池子里那个")
        if (b.get("score") or {}).get("total", 0) >= DEEP:
            doc["pick"] = b["id"]

    leads = doc.get("leads") or []
    doc["leads"] = leads
    if len(leads) > 5:
        problems.append("leads 最多 5 条")
    for l in leads:
        if not (isinstance(l, dict) and l.get("name") and l.get("why_not") and URL.match(str(l.get("url", "")))):
            problems.append(f"leads 每条要有 name、url、why_not：{l}")
    if not opps and track not in ("复盘", None) and len(leads) < 3:
        problems.append("今天没有合格的今日机会，leads 至少写 3 条你查过的线索和卡在哪，让他知道查过什么")

    tools = doc["tools"]
    on_track = sum(1 for t in tools if t.get("from") in ("主线话题", "issue需求"))
    if tools and on_track < math.ceil(len(tools) * 0.7):
        problems.append(f"GitHub {len(tools)} 个里只有 {on_track} 个来自主线话题或 issue 需求，至少要七成（{math.ceil(len(tools) * 0.7)} 个）")
    tb = doc.get("trending_brief") or []
    doc["trending_brief"] = tb
    if len(tb) != 3:
        problems.append("trending_brief 要 3 条：日榜上今天最热的，每条 repo、url、line（30 字以内）")
    for x in tb:
        if not (isinstance(x, dict) and x.get("repo") and x.get("line") and URL.match(str(x.get("url", "")))):
            problems.append(f"trending_brief 每条要有 repo、url、line：{x}")
        elif width(x["line"]) > 30 or "**" in x["line"]:
            problems.append(f"trending_brief「{x['repo']}」的 line 要在 30 字以内，不加粗")
    if doc["skills"]:
        s1 = doc["skills"][0]
        if not s1.get("install") or not s1.get("why_now"):
            problems.append(f"{s1['id']} 是「本周装这个」，要写 install（安装命令）和 why_now（为什么是这周）")

    repos = {}
    for key in ("tools", "skills"):
        for it in doc[key]:
            r = str(it.get("repo") or it.get("url") or "").lower().rstrip("/")
            if r and r in repos:
                problems.append(f"{it['id']} 和 {repos[r]} 是同一个项目，只留一条")
            repos[r] = it["id"]
    for x in tb:
        r = str(x.get("repo") or "").lower()
        if r in repos:
            problems.append(f"trending_brief 里的 {x.get('repo')} 已经在 {repos[r]} 写过，换一个")
    check_cliches(doc, problems)

    today = doc.get("today")
    if not isinstance(today, dict) or not today.get("text") or today.get("minutes") not in (15, 30, 60) or not today.get("ref"):
        problems.append("today 要有 text、minutes（15/30/60）、ref（推进的是谁）：今天只做一件事是他最先看的")
    else:
        names = {s.get("name") for s in doc["skills"]}
        if validating and today["ref"] != validating[0]["id"]:
            problems.append(f"池子里「{validating[0]['name']}」正在验证，today.ref 要写 {validating[0]['id']}，text 写它的下一步")
        elif not validating and doc.get("pick") and today["ref"] != doc["pick"]:
            problems.append(f"今天的 {doc['pick']} 够 {DEEP} 分、池子里又没有在验证的，today.ref 写 {doc['pick']}，text 写验证它的第一步")
        elif not validating and not doc.get("pick") and today["ref"] not in names and today["ref"] not in pool_ids:
            problems.append("今天没有要验证的：today.ref 写第一个 Skill 的名字（本周装这个），或池子里要推进的项目编号")

    w = text_width({k: doc.get(k) for k in ("headline", "today", "tools", "skills", "opportunities", "trending_brief")})
    stats = doc.setdefault("stats", {})
    stats["selected"] = total
    stats["chars"] = int(w)
    stats["read_minutes"] = max(1, math.ceil(w / READ_SPEED))
    if w > MAX_WIDTH:
        problems.append(f"全文约 {int(w)} 字，超过 {MAX_WIDTH} 字的上限（目标 1500 字）：先压缩工具和 Skills 的 what，再压缩机会的文字（深挖会写全）")
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")

    if problems:
        print("需要修改：\n- " + "\n- ".join(problems))
        return 1
    pick = doc.get("pick")
    first = opps[0] if opps else None
    print(f"通过：今日机会 {len(opps)} 个" + (f"（{first['name']}，{first['score']['total']} 分）" if first else "") +
          f"，Skills {len(doc['skills'])}，GitHub {len(tools)}，" +
          (f"{pick} 待深挖，" if pick else "今天不深挖，") + f"约 {int(w)} 字、读完 {stats['read_minutes']} 分钟")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
