#!/usr/bin/env python3
"""校验并规整一期日报 JSON：补编号、检查必填字段和链接、算阅读时长、统计条数。

用法：python3 scripts/validate.py data/daily/2026-10-15.json
有错误时退出码为 1，并打印要修的地方（Claude 在 Actions 里会据此改正）。
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = {
    # 栏目键: (编号前缀, 必填字段, 数量范围)
    "news": ("N", ["title", "url", "source_type", "summary", "tier"], (5, 15)),
    "tools": ("G", ["repo", "url", "what", "safety", "group", "why_today"], (3, 8)),
    "skills": ("S", ["name", "url", "what", "safety"], (0, 5)),
    "opportunities": ("B", ["name", "one_liner", "automation", "market", "fit", "verdict"], (0, 2)),
    "trends": ("P", ["topic", "brief", "evidence", "how"], (0, 6)),
    "followups": ("F", ["title", "update", "url"], (0, 6)),
}
SAFETY = {"绿", "黄", "红"}
VERDICTS = {"值得验证", "放进观察", "只是灵感"}
SIGNALS = {"爆款形式", "需求信号", "新玩法", "使用技巧"}
TIERS = {"影响你的", "行业动态"}
GROUPS = {"大家都在用", "刚冒出来"}
# 用法只写他的方向，其他方向不写：三期里 66 条用法只有 31 条在原来的四个方向里，其余他不会去做。
# 2026-10-30 他转做海外生意，从四个扩到六个：加了供需（供需撮合）和宣传（海外宣传）
AREAS = {"外贸", "SEO", "自媒体", "供需", "宣传", "做产品"}
# 许可证三档：能不能拿它做托管版来卖（fetch.py 按 SPDX 先定档，认不出的由模型读 LICENSE 定）
LICENSE_TIERS = {"能托管来卖", "托管要公开改动", "不能托管来卖"}
# 资讯只取官方网站、大媒体和 X；其他社交和自媒体平台上的内容只用于玩法风向和机会
SOURCE_TYPES = {"官方", "媒体", "X"}
SOCIAL = ("xiaohongshu.com", "xhslink.com", "douyin.com", "iesdouyin.com", "tiktok.com",
          "youtube.com", "youtu.be", "bilibili.com", "b23.tv", "weibo.com", "weibo.cn", "zhihu.com", "reddit.com",
          "v2ex.com", "news.ycombinator.com", "threads.net", "mp.weixin.qq.com", "medium.com", "substack.com")
AGGREGATORS = ("techmeme.com", "news.smol.ai", "smol.ai")  # 只用来发现线索，收录时要换成原文
URL = re.compile(r"^https?://[^\s<>\"']+$")
MAX_WIDTH = 7000        # 全文字数上限（中文算 1，英文数字算 0.5），约 14 分钟读完；目标是 6000 字以内
READ_SPEED = 500        # 每分钟读多少字，算「读完约 N 分钟」
# 不算进阅读量的字段：链接、编号、枚举值
SKIP_KEYS = {"url", "id", "repo", "published", "platform", "platforms", "source_type", "safety", "hot", "verdict",
             "category", "tier", "group", "track", "works_with", "license", "area", "minutes", "images", "ref",
             "stars_total", "stars_today", "installs", "generated_at", "date", "signal", "name",
             "safety_note", "tags", "license_tier", "stars_7d", "reactions"}  # 安全依据默认折叠，不算阅读量，但单条限 200 字


def host_of(url):
    return re.sub(r"^https?://", "", str(url)).split("/")[0].split(":")[0].lower()


def host_in(url, domains):
    host = host_of(url)
    return any(host == d or host.endswith("." + d) for d in domains)


def social(url):
    return host_in(url, SOCIAL)


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
        if it.get("group") not in GROUPS:
            problems.append(f"{i} 的 group 只能是 大家都在用 / 刚冒出来")
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
    if width(it.get("what") or "") > 120:
        problems.append(f"{i} 的 what 要在 120 字以内，细节让他自己去仓库看")
    imgs = it.get("images")
    if imgs is not None:
        if not isinstance(imgs, list) or any(not URL.match(str(u)) for u in imgs):
            problems.append(f"{i} 的 images 必须是图片链接数组")
        else:
            it["images"] = imgs[:6]


def check_news(it, problems):
    i = it["id"]
    if it.get("source_type") not in SOURCE_TYPES:
        problems.append(f"{i} 的 source_type 只能是 {'/'.join(sorted(SOURCE_TYPES))}（资讯只取官方网站、大媒体和 X）")
    url = it.get("url") or ""
    if social(url):
        problems.append(f"{i} 的链接是 X 以外的社交或自媒体平台：{url}。资讯要换成官方原文、大媒体报道或 X 帖子，找不到就删掉这条")
    if host_in(url, AGGREGATORS):
        problems.append(f"{i} 的链接是聚合页：{url}。换成它指向的原文链接")
    if it.get("tier") not in TIERS:
        problems.append(f"{i} 的 tier 只能是 影响你的 / 行业动态")
    if width(it.get("summary") or "") > 80:
        problems.append(f"{i} 的 summary 要在 80 字以内（现在 {int(width(it.get('summary')))} 字），细节让他去读原文")
    if it.get("tier") == "影响你的":
        fm = it.get("for_me") or ""
        if not fm:
            problems.append(f"{i} 是「影响你的」，要写 for_me：一句话说对他意味着什么、该做什么")
        elif width(fm) > 60:
            problems.append(f"{i} 的 for_me 要在 60 字以内：{plain(fm)[:30]}…")


def check_trend(it, problems):
    i = it["id"]
    brief = it.get("brief") or ""
    if brief and (width(brief) > 26 or "**" in brief):
        problems.append(f"{i} 的 brief 要在 26 个字以内，不加粗：{brief}")
    if it.get("signal") not in SIGNALS:
        problems.append(f"{i} 的 signal 只能是 {'/'.join(sorted(SIGNALS))}")
    ev = it.get("evidence")
    if not isinstance(ev, list) or not ev:
        problems.append(f"{i} 的 evidence 要写成数组，至少 1 条")
        return
    for e in ev:
        if not isinstance(e, dict) or not e.get("platform") or not e.get("title") or not URL.match(str(e.get("url", ""))):
            problems.append(f"{i} 的每条证据都要有 platform、title 和合法的 url：{e}")
        elif not e.get("metrics"):
            problems.append(f"{i} 的证据「{e['title'][:20]}」缺少 metrics（点赞、收藏、播放等数字）")
    if len(ev) < 2 and not it.get("quotes"):
        problems.append(f"{i} 证据太少：至少 2 条帖子，或者 1 条加用户原话")
    for q in it.get("quotes") or []:
        if not isinstance(q, dict) or not q.get("text"):
            problems.append(f"{i} 的 quotes 每条都要有 text（评论原话）")


def check_opp(it, problems):
    i = it["id"]
    if it.get("verdict") not in VERDICTS:
        problems.append(f"{i} 的 verdict 只能是 {'/'.join(VERDICTS)}")
    cost = (it.get("fit") or {}).get("startup_cost_usd")
    if not isinstance(cost, (int, float)) or cost > 500:
        problems.append(f"{i} 的 fit.startup_cost_usd 必须是不超过 500 的数字")
    m = it.get("market") or {}
    links = m.get("evidence_links") or []
    for link in links:
        if not isinstance(link, dict) or not URL.match(link.get("url", "")):
            problems.append(f"{i} 的证据链接不合法: {link}")
    if len(links) < 5:
        problems.append(f"{i} 的 market.evidence_links 只有 {len(links)} 条，机会卡至少要 5 条你打开过的链接（收入页、竞品、需求帖）；凑不够就删掉这个机会，不凑数")
    rev = plain(m.get("revenue_evidence") or "")
    if not re.search(r"\d", rev) or not re.search(r"\$|美元|元|MRR|月入|收入|营收|revenue", rev, re.I):
        problems.append(f"{i} 的 market.revenue_evidence 要有你打开过的收入数字（MRR、月入、售价之类，带数字）；没有收入证据的机会不收")
    if width(m.get("competition") or "") < 20:
        problems.append(f"{i} 的 market.competition 要点名至少 3 个竞品并说它们怎么样，现在太短")


def main(path):
    p = Path(path)
    doc = json.loads(p.read_text("utf-8"))
    problems = []
    tracks = {re.sub(r"\s+", "", t): t for t in load_tracks()}  # 「SEO 与 GEO」和「SEO与GEO」算同一条
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc.get("date", ""))):
        problems.append("date 必须是 YYYY-MM-DD")
    if not isinstance(doc.get("headline"), list) or len(doc["headline"]) != 3:
        problems.append("headline 必须是 3 句话的数组：影响他的一条资讯、最强的平台信号、今天最值得做的一件事")

    total = 0
    for key, (prefix, required, (lo, hi)) in SECTIONS.items():
        if key == "trends" and doc.get("trends") is None:
            continue  # 没抓平台数据的那天可以不写这个栏目
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
                    problems.append(f"{it['id']} 的 track 只能是 {'/'.join(sorted(tracks.values()))}，或者不写")
            if key in ("tools", "skills"):
                check_card(key, it, problems)
            elif key == "news":
                check_news(it, problems)
            elif key == "trends":
                check_trend(it, problems)
            elif key == "opportunities":
                check_opp(it, problems)
            elif key == "followups" and width(it.get("update") or "") > 60:
                problems.append(f"{it['id']} 的 update 要在 60 字以内：只写变化（数字从多少到多少、出了什么新东西）")
        total += len(items)

    if doc["news"] and not any(n.get("tier") == "影响你的" for n in doc["news"]):
        problems.append("news 里至少要有 1 条「影响你的」；实在没有就把最接近他业务的一条升上去并写 for_me")
    if sum(1 for n in doc["news"] if n.get("tier") == "影响你的") > 8:
        problems.append("「影响你的」资讯最多 8 条，其余降为行业动态")

    repos = {}
    for key in ("tools", "skills"):
        for it in doc[key]:
            r = str(it.get("repo") or it.get("url") or "").lower().rstrip("/")
            if r and r in repos:
                problems.append(f"{it['id']} 和 {repos[r]} 是同一个项目，只留一条")
            repos[r] = it["id"]

    actions = doc.get("actions") or []
    if not 1 <= len(actions) <= 3:
        problems.append("actions 要写 1–3 条，今天做什么是读者最先看的")
    for a in actions:
        if not isinstance(a, dict) or a.get("minutes") not in (5, 15, 30) or not a.get("text"):
            problems.append(f"actions 每条要有 minutes（5/15/30）和 text：{a}")
    watch = doc.get("watch_next")
    if watch is not None:
        if not isinstance(watch, list) or len(watch) > 4 or any(not isinstance(w, str) or not 1 <= len(w) <= 20 for w in watch):
            problems.append("watch_next 是最多 4 个词的数组（明天要在平台上追搜的工具名或玩法），每个 20 字以内")

    w = text_width({k: doc.get(k) for k in ("headline", "news", "tools", "skills", "opportunities", "trends", "followups", "actions")})
    stats = doc.setdefault("stats", {})
    stats["selected"] = total
    stats["chars"] = int(w)
    stats["read_minutes"] = max(1, math.ceil(w / READ_SPEED))
    if w > MAX_WIDTH:
        problems.append(f"全文约 {int(w)} 字，读完要 {stats['read_minutes']} 分钟，超过 {MAX_WIDTH} 字的上限：先删行业动态和工具的细节，再压缩机会卡")
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")

    if problems:
        print("需要修改：\n- " + "\n- ".join(problems))
        return 1
    print(f"通过：共 {total} 条（资讯 {len(doc['news'])}，工具 {len(doc['tools'])}，Skills {len(doc['skills'])}，"
          f"机会 {len(doc['opportunities'])}，玩法风向 {len(doc.get('trends') or [])}，跟进 {len(doc['followups'])}），"
          f"约 {int(w)} 字、读完 {stats['read_minutes']} 分钟")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
