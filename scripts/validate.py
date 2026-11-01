#!/usr/bin/env python3
"""校验并规整一期日报 JSON：补编号、检查必填字段和链接、算阅读时长、统计条数。

用法：python3 scripts/validate.py data/daily/2026-11-02.json
有错误时退出码为 1，并打印要修的地方（Claude 在 Actions 里会据此改正）。

2026-11-01 起日报只有三个栏目：GitHub 工具、Skills、一人公司出海机会候选。资讯、玩法风向、跟进停了。
第一个候选（B01）是今日机会：日报写好后由更强的模型深挖，脚本在 pick 字段记下它的编号。
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = {
    # 栏目键: (编号前缀, 必填字段, 数量范围)。编号前缀 N（资讯）、P（玩法风向）、F（跟进）留给老日报，不再用
    "tools": ("G", ["repo", "url", "what", "safety", "group", "why_today"], (3, 8)),
    "skills": ("S", ["name", "url", "what", "safety"], (3, 6)),
    # 机会候选：目标 3–5 个，至少 1 个。10-17 到 11-01 连续 16 期一个都没有，所以不再允许空着
    "opportunities": ("B", ["name", "one_liner", "automation", "market", "fit", "verdict"], (1, 5)),
}
SAFETY = {"绿", "黄", "红"}
VERDICTS = {"值得验证", "放进观察", "只是灵感"}
GROUPS = {"大家都在用", "刚冒出来"}
# 用法只写他的方向，其他方向不写：三期里 66 条用法只有 31 条在原来的四个方向里，其余他不会去做。
# 2026-10-30 他转做海外生意，从四个扩到六个：加了供需（供需撮合）和宣传（海外宣传）
AREAS = {"外贸", "SEO", "自媒体", "供需", "宣传", "做产品"}
# 许可证三档：能不能拿它做托管版来卖（fetch.py 按 SPDX 先定档，认不出的由模型读 LICENSE 定）
LICENSE_TIERS = {"能托管来卖", "托管要公开改动", "不能托管来卖"}
URL = re.compile(r"^https?://[^\s<>\"']+$")
MAX_WIDTH = 7000        # 全文字数上限（中文算 1，英文数字算 0.5），约 14 分钟读完；目标是 5000 字以内（深挖报告另算）
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


def check_opp(it, problems):
    """机会候选：有打开过的收入证据就收，竞品和怎么做留给深挖。首选（B01）当天会被深挖。"""
    i = it["id"]
    if it.get("verdict") not in VERDICTS:
        problems.append(f"{i} 的 verdict 只能是 {'/'.join(VERDICTS)}")
    if width(it.get("one_liner") or "") > 60:
        problems.append(f"{i} 的 one_liner 要在 60 字以内：卖什么、卖给海外的谁、怎么收钱")
    cost = (it.get("fit") or {}).get("startup_cost_usd")
    if not isinstance(cost, (int, float)) or cost > 500:
        problems.append(f"{i} 的 fit.startup_cost_usd 必须是不超过 500 的数字")
    hours = (it.get("automation") or {}).get("weekly_hours")
    if not isinstance(hours, (int, float)):
        problems.append(f"{i} 的 automation.weekly_hours 要写稳定后每周要他花几小时（数字）")
    m = it.get("market") or {}
    links = m.get("evidence_links") or []
    for link in links:
        if not isinstance(link, dict) or not link.get("title") or not URL.match(str(link.get("url", ""))):
            problems.append(f"{i} 的证据链接要有 title 和合法的 url: {link}")
    if len(links) < 2:
        problems.append(f"{i} 的 market.evidence_links 只有 {len(links)} 条，候选至少要 2 条你打开过的链接（收入证据页，加上来源、竞品或需求帖）")
    rev = plain(m.get("revenue_evidence") or "")
    if not re.search(r"\d", rev) or not re.search(r"\$|美元|元|MRR|ARR|月入|收入|营收|售价|revenue|sales", rev, re.I):
        problems.append(f"{i} 的 market.revenue_evidence 要有你打开过的收入数字（MRR、月入、售价、付费用户数之类，带数字和出处）；找不到收入证据的换一个候选")
    if not m.get("competition"):
        problems.append(f"{i} 缺少 market.competition：点名 1–3 个在做同样事的产品，深挖时再细看")


def main(path):
    p = Path(path)
    doc = json.loads(p.read_text("utf-8"))
    problems = []
    tracks = {re.sub(r"\s+", "", t): t for t in load_tracks()}  # 「SEO 与 GEO」和「SEO与GEO」算同一条
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc.get("date", ""))):
        problems.append("date 必须是 YYYY-MM-DD")
    if not isinstance(doc.get("headline"), list) or len(doc["headline"]) != 3:
        problems.append("headline 必须是 3 句话的数组：今天首选的机会（B01）、最值得看的 GitHub 或 Skills 线索、今天最值得做的一件事")
    for old in ("news", "trends", "followups", "watch_next"):
        if doc.get(old):
            problems.append(f"{old} 栏目 2026-11-01 停了（不写 AI 资讯、玩法风向、跟进和追搜词），脚本已经删掉，以后不要写")
        doc.pop(old, None)

    total = 0
    for key, (prefix, required, (lo, hi)) in SECTIONS.items():
        items = doc.get(key) or []
        doc[key] = items
        if key == "opportunities" and not items:
            problems.append("opportunities 至少要 1 个机会候选（目标 3–5 个）：去 TrustMRR、acquire.com、X 实践者帖、Show HN、"
                            "Product Hunt 和 issue_demand 找有收入证据、一个人能自动化的出海生意，这是今天最重要的栏目")
        elif not (lo <= len(items) <= hi):
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
            elif key == "opportunities":
                check_opp(it, problems)
        total += len(items)
    # 今日机会：第一个候选，日报写好后由更强的模型深挖（daily.yml「Claude 深挖今日机会」）
    if doc["opportunities"]:
        first = doc["opportunities"][0]
        doc["pick"] = first["id"]
        if {norm(first.get("name")), norm((first.get("source") or {}).get("url"))} & deepdived_opps(str(doc.get("date"))):
            problems.append(f"B01「{first.get('name')}」以前深挖过（见素材里的 deepdived），换一个没挖过的放第一个")
    else:
        doc.pop("pick", None)

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

    w = text_width({k: doc.get(k) for k in ("headline", "tools", "skills", "opportunities", "actions")})
    stats = doc.setdefault("stats", {})
    stats["selected"] = total
    stats["chars"] = int(w)
    stats["read_minutes"] = max(1, math.ceil(w / READ_SPEED))
    if w > MAX_WIDTH:
        problems.append(f"全文约 {int(w)} 字，读完要 {stats['read_minutes']} 分钟，超过 {MAX_WIDTH} 字的上限：先压缩工具和 Skills 的细节，再压缩候选（深挖会写全）")
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")

    if problems:
        print("需要修改：\n- " + "\n- ".join(problems))
        return 1
    print(f"通过：共 {total} 条（机会候选 {len(doc['opportunities'])}，Skills {len(doc['skills'])}，工具 {len(doc['tools'])}），"
          f"今日机会 {doc['pick']} 待深挖，约 {int(w)} 字、读完 {stats['read_minutes']} 分钟")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
