#!/usr/bin/env python3
"""校验并规整一期日报 JSON：补编号、检查必填字段和链接、统计条数。

用法：python3 scripts/validate.py data/daily/2026-10-15.json
有错误时退出码为 1，并打印要修的地方（Claude 在 Actions 里会据此改正）。
"""
import json
import re
import sys
from pathlib import Path

SECTIONS = {
    # 栏目键: (编号前缀, 必填字段, 数量范围)
    "news": ("N", ["title", "url", "source_type", "summary"], (5, 25)),
    "tools": ("G", ["repo", "url", "what", "safety"], (3, 10)),
    "skills": ("S", ["name", "url", "what", "safety"], (0, 6)),
    "opportunities": ("B", ["name", "one_liner", "automation", "market", "fit", "verdict"], (0, 3)),
    "trends": ("P", ["topic", "brief", "evidence", "how"], (0, 5)),
}
SAFETY = {"绿", "黄", "红"}
VERDICTS = {"值得验证", "放进观察", "只是灵感"}
SIGNALS = {"爆款形式", "需求信号", "新玩法", "热点"}
SOURCE_TYPES = {"官方", "媒体", "社区", "X", "平台"}
URL = re.compile(r"^https?://[^\s<>\"']+$")


def popular(it):
    """红色条目只收热度很高的。"""
    return ((it.get("stars_total") or 0) >= 5000 or (it.get("stars_today") or 0) >= 500
            or (it.get("installs") or 0) >= 5000)


def width(s):
    """按字数算长度：中文算 1，英文和数字算半个。"""
    return sum(1 if ord(c) > 0x2E7F else 0.5 for c in str(s))


def check_card(key, it, problems):
    i = it["id"]
    brief = it.get("brief") or ""
    if not brief:
        problems.append(f"{i} 缺少 brief（一句话说清是什么，网站折叠时只显示这句）")
    elif width(brief) > 26 or "**" in brief:
        problems.append(f"{i} 的 brief 要在 26 个字以内，不加粗：{brief}")
    if it.get("safety") in ("黄", "红"):
        rb = it.get("risk_brief") or ""
        if not rb:
            problems.append(f"{i} 安全是{it['safety']}，要写 risk_brief（一句话最大风险）")
        elif width(rb) > 30 or "**" in rb:
            problems.append(f"{i} 的 risk_brief 要在 30 个字以内，不加粗：{rb}")
    uses = it.get("uses")
    if uses is None and not it.get("use_for_me" if key == "tools" else "how_i_use"):
        problems.append(f"{i} 缺少 uses（一人公司能怎么用）")
    if uses is not None:
        if not isinstance(uses, list) or not 2 <= len(uses) <= 5:
            problems.append(f"{i} 的 uses 要写 2–5 条")
        elif any(not (isinstance(u, dict) and u.get("area") and u.get("how")) for u in uses):
            problems.append(f"{i} 的 uses 每条都要有 area 和 how")
    if it.get("safety") in ("黄", "红") and not it.get("safety_note"):
        problems.append(f"{i} 安全是{it['safety']}，必须在 safety_note 写清风险")
    if it.get("safety") == "红" and not popular(it):
        problems.append(f"{i} 安全是红，但热度不够（要 5000 星以上、今日 500 星以上或安装 5000 以上），换掉")
    if key == "skills" and it.get("stars_total") is None and it.get("installs") is None and not it.get("popularity_note"):
        problems.append(f"{i} 要写出热度：stars_total、installs 或 popularity_note 至少一个")
    if key == "skills" and it.get("hot") not in (None, "新晋热门", "长期热门"):
        problems.append(f"{i} 的 hot 只能是 新晋热门 / 长期热门")
    imgs = it.get("images")
    if imgs is not None:
        if not isinstance(imgs, list) or any(not URL.match(str(u)) for u in imgs):
            problems.append(f"{i} 的 images 必须是图片链接数组")
        else:
            it["images"] = imgs[:6]


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
        problems.append(f"{i} 证据太少：至少 2 条帖子或热榜词，或者 1 条加用户原话")
    for q in it.get("quotes") or []:
        if not isinstance(q, dict) or not q.get("text"):
            problems.append(f"{i} 的 quotes 每条都要有 text（评论原话）")


def main(path):
    p = Path(path)
    doc = json.loads(p.read_text("utf-8"))
    problems = []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(doc.get("date", ""))):
        problems.append("date 必须是 YYYY-MM-DD")
    if not isinstance(doc.get("headline"), list) or len(doc["headline"]) != 3:
        problems.append("headline 必须是 3 句话的数组")

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
            for f in ("url",):
                if it.get(f) and not URL.match(it[f]):
                    problems.append(f"{it['id']} 的 {f} 不是合法链接: {it[f]}")
            if "safety" in required and it.get("safety") not in SAFETY:
                problems.append(f"{it['id']} 的 safety 只能是 绿/黄/红")
            if key in ("tools", "skills"):
                check_card(key, it, problems)
            if key == "news" and it.get("source_type") not in SOURCE_TYPES:
                problems.append(f"{it['id']} 的 source_type 只能是 {'/'.join(sorted(SOURCE_TYPES))}")
            if key == "trends":
                check_trend(it, problems)
            if key == "opportunities":
                if it.get("verdict") not in VERDICTS:
                    problems.append(f"{it['id']} 的 verdict 只能是 {'/'.join(VERDICTS)}")
                cost = (it.get("fit") or {}).get("startup_cost_usd")
                if not isinstance(cost, (int, float)) or cost > 500:
                    problems.append(f"{it['id']} 的 fit.startup_cost_usd 必须是不超过 500 的数字")
                for link in (it.get("market") or {}).get("evidence_links", []):
                    if not URL.match(link.get("url", "")):
                        problems.append(f"{it['id']} 的证据链接不合法: {link}")
        total += len(items)

    repos = {}
    for key in ("tools", "skills"):
        for it in doc[key]:
            r = str(it.get("repo") or it.get("url") or "").lower().rstrip("/")
            if r and r in repos:
                problems.append(f"{it['id']} 和 {repos[r]} 是同一个项目，只留一条")
            repos[r] = it["id"]

    actions = doc.get("actions") or []
    if len(actions) > 3:
        problems.append("actions 最多 3 条")
    stats = doc.setdefault("stats", {})
    stats["selected"] = total
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")

    if problems:
        print("需要修改：\n- " + "\n- ".join(problems))
        return 1
    print(f"通过：共 {total} 条（资讯 {len(doc['news'])}，工具 {len(doc['tools'])}，"
          f"Skills {len(doc['skills'])}，机会 {len(doc['opportunities'])}，平台风向 {len(doc.get('trends') or [])}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
