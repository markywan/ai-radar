#!/usr/bin/env python3
"""往飞书群推送卡片（群自定义机器人 webhook）。

  python3 scripts/notify_feishu.py daily 2026-11-02
  python3 scripts/notify_feishu.py deepdive 2026-11-02-B03
  python3 scripts/notify_feishu.py error "说明文字"
  python3 scripts/notify_feishu.py weekly 2026-11-28
  python3 scripts/notify_feishu.py stale 2026-11-24 3      # 停更提醒：最新一期的日期、距今几天

环境变量：FEISHU_WEBHOOK（必填）、FEISHU_SECRET（开了签名校验才要）、
SITE_URL（网站地址）、WORKER_URL 与 ACTION_KEY（卡片上的收藏和池子状态按钮要用）、RUN_URL（失败时附上运行记录）、
FALLBACK 与 HINT（今天主令牌失败、改用备用密钥写的，卡片最上面提醒换令牌）。
网站地址和收藏接口地址没给环境变量时，从 config/site.json 读。
"""
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pool  # noqa: E402

try:
    CONF = json.loads((ROOT / "config/site.json").read_text("utf-8"))
except (OSError, ValueError):
    CONF = {}


def default_site():
    owner, _, name = os.environ.get("GITHUB_REPOSITORY", "").partition("/")
    return f"https://{owner.lower()}.github.io/{name}/" if name else ""


SITE = (os.environ.get("SITE_URL") or CONF.get("site_url") or default_site()).rstrip("/") + "/"
WORKER = (os.environ.get("WORKER_URL") or CONF.get("worker_url") or "").rstrip("/")
KEY = "".join(os.environ.get("ACTION_KEY", "").split())


def site_link(**params):
    if KEY:
        params["k"] = KEY
    return SITE + ("?" + urllib.parse.urlencode(params) if params else "")


def action_link(op, fid):
    if not (WORKER and KEY):
        return None
    return f"{WORKER}/act?" + urllib.parse.urlencode({"op": op, "id": fid, "k": KEY})


STATUS_CODE = {"验证中": "start", "待研究": "watch", "淘汰": "drop", "已启动": "launch", "已变现": "paid", "暂停": "pause"}


def status_link(pid, status):
    """改机会池状态的按钮（Worker 的 op=status）。"""
    if not (WORKER and KEY and pid):
        return None
    return f"{WORKER}/act?" + urllib.parse.urlencode({"op": "status", "id": pid, "s": STATUS_CODE[status], "k": KEY})


def clean(text):
    return re.sub(r"[*`]", "", str(text or ""))


def md(text):
    return {"tag": "markdown", "content": text}


def buttons(*items):
    acts = [{"tag": "button", "text": {"tag": "plain_text", "content": label}, "type": kind, "url": url}
            for label, url, kind in items if url]
    return {"tag": "action", "actions": acts} if acts else None


def card(title, template, elements):
    return {"msg_type": "interactive", "card": {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": template},
        "elements": [e for e in elements if e]}}


def unread_before(date):
    """配了 Worker 存储时，查出最近 7 期里还没看的（不含今天这期）。"""
    if not (WORKER and KEY):
        return []
    try:
        with urllib.request.urlopen(f"{WORKER}/state?" + urllib.parse.urlencode({"k": KEY}), timeout=10) as r:
            state = json.loads(r.read().decode())
    except Exception:
        return []
    if not state.get("kv"):
        return []
    read = state.get("read") or {}
    past = sorted((p.stem for p in (ROOT / "data/daily").glob("*.json") if p.stem < date), reverse=True)[:7]
    return [d for d in past if not (read.get(d) or {}).get("v")]


def report_lead(fid, limit=200):
    """深挖报告开头那段结论（第一段不是标题的文字），去掉 Markdown 标记，太长时在句号处截断。"""
    path = ROOT / "data/deepdive" / f"{fid}.md"
    if not path.is_file():
        return ""
    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "|", ">", "---")):
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)  # 链接只留文字
            text = re.sub(r"[*`]", "", text)
            if len(text) <= limit:
                return text
            cut = text[:limit].rfind("。")
            return text[:cut + 1] if cut >= 40 else text[:limit - 1] + "…"
    return ""


def opp_numbers(b):
    f, a = b.get("fit") or {}, b.get("automation") or {}
    return f"起步 ${f.get('startup_cost_usd')} · MVP {f.get('mvp_days')} 天 · 每周 {a.get('weekly_hours')} 小时"


WEEKDAY = "一二三四五六日"


def daily_card_v3(date, doc):
    """2026-11-26 起：第一屏是正在验证的项目、今天只做的那一件事和池子状态；再是今日机会（分数、两条证据、风险、状态按钮）；
    最后一个 GitHub 和本周装的 Skill。"""
    m, d = int(date[5:7]), int(date[8:10])
    import datetime as dt  # noqa: PLC0415
    wd = WEEKDAY[dt.date.fromisoformat(date).weekday()]
    items = pool.load_all()
    by_id = {x["id"]: x for x in items}
    summ = pool.summary(items, date)
    els = []
    if os.environ.get("FALLBACK") == "true":
        els.append(md("⚠️ **主令牌失败了，今天这期是用备用密钥（按量付费）写的。**\n" + (os.environ.get("HINT") or "去运行记录看原因，换好令牌后备用密钥就不再用。")))
    today = doc.get("today") or {}
    ref = by_id.get(today.get("ref"))
    if today.get("text"):
        els.append(md(f"**今天只做一件事**（{today.get('minutes', 30)} 分钟）\n{clean(today['text'])}"
                      + (f"\n<font color='grey'>{clean(today.get('why'))}</font>" if today.get("why") else "")))
    val = summ["validating"][0] if summ["validating"] else None
    lines = [summ["line"]]
    if val:
        days = val.get("days_in_status")
        lines.append(f"验证到第 {days + 1} 天" if isinstance(days, int) else "")
        if val.get("experiment_metric"):
            lines.append(f"过关指标：{clean(val['experiment_metric'])}")
        if val.get("due_at"):
            lines.append(f"到期 {val['due_at']}")
    for o in summ["overdue"]:
        lines.append(f"🔴 「{o['name']}」{o['due_at']} 到期了，看指标过没过")
    els.append(md("\n".join(x for x in lines if x)))
    if val:
        els.append(buttons(("已启动", status_link(val["id"], "已启动"), "primary"),
                           ("暂停", status_link(val["id"], "暂停"), "default"),
                           ("淘汰", status_link(val["id"], "淘汰"), "danger")))
    elif ref and ref.get("status") in ("待验证", "待研究", "暂停"):
        els.append(buttons((f"开始验证「{ref['name'][:12]}」", status_link(ref["id"], "验证中"), "primary"),
                           ("看深挖", site_link(tab="pool", id=ref["id"]), "default")))

    opps = doc.get("opportunities") or []
    els.append({"tag": "hr"})
    if opps:
        b = opps[0]
        sc = b.get("score") or {}
        fid = f"{date}-{b['id']}"
        pid = b.get("pool_id") or fid
        ev = [e for e in b.get("evidence") or [] if e.get("type") in ("需求", "付费")][:2] or (b.get("evidence") or [])[:2]
        ev_lines = "\n".join("· {}：{} [{}]({})".format(e.get("type", ""), clean(e.get("note")),
                                                     re.sub(r"[\[\]]", "", e.get("title", ""))[:30], e["url"]) for e in ev)
        lead = report_lead(fid, 120)
        els.append(md(f"**今日机会 · {doc.get('track') or b.get('track', '')}**\n**{b['name']}**　{sc.get('total', '?')} 分（{b.get('verdict', '')}）\n"
                      f"{clean(b.get('one_liner'))}\n{ev_lines}\n最大风险：{clean(b.get('biggest_risk'))}"
                      + (f"\n**深挖结论**　{lead}" if lead else "")))
        els.append(buttons(("开始验证", status_link(pid, "验证中"), "primary"),
                           ("继续观察", status_link(pid, "待研究"), "default"),
                           ("淘汰", status_link(pid, "淘汰"), "danger"),
                           ("看证据", site_link(date=date, id=fid), "default")))
    else:
        leads = doc.get("leads") or []
        els.append(md(f"**今日机会 · {doc.get('track') or ''}**\n今天没有合格的" + (f"，查了 {len(leads)} 条线索：" + "；".join(f"{clean(l['name'])}（{clean(l.get('why_not'))}）" for l in leads[:3]) if leads else "。")))

    tools, skills = doc.get("tools") or [], doc.get("skills") or []
    if tools or skills:
        els.append({"tag": "hr"})
    if tools:
        t = next((t for t in tools if t.get("demand")), tools[0])
        dm = (t.get("demand") or [{}])[0]
        dm_title = re.sub(r"[\[\]]", "", dm.get("title") or "")[:48]
        els.append(md(f"**GitHub · {t.get('stage', '')}** [{t['repo']}]({t['url']})　{clean(t.get('why_today'))}\n{clean(t.get('business'))}"
                      + (f"\n有人在要：[{dm_title}]({dm['url']}) {dm.get('reactions', 0)} 赞" if dm.get("url") else "")
                      + (f"\n搭配：{clean(t['pairs_with'])}" if t.get("pairs_with") and t["pairs_with"] != "无" else "")))
    if skills:
        sk = skills[0]
        els.append(md(f"**本周装这个 Skill** [{sk['name']}]({sk['url']})\n{clean(sk.get('why_now') or sk.get('brief'))}"
                      + (f"\n`{sk['install']}`" if sk.get("install") else "")))
    els.append({"tag": "hr"})
    backlog = unread_before(date)
    if backlog:
        els.append(md(f"🔴 还有 {len(backlog)} 期没看：" + "、".join(f"{int(x[5:7])}月{int(x[8:10])}日" for x in backlog)))
    els.append(buttons(("打开今日日报", site_link(), "primary"), ("看机会池", site_link(tab="pool"), "default")))
    return card(f"AI 机会雷达 · {m}月{d}日 · 星期{wd}" + (f" · {doc['track']}" if doc.get("track") else ""), "turquoise", els)


def daily_card(date):
    doc = json.loads((ROOT / "data/daily" / f"{date}.json").read_text("utf-8"))
    if doc.get("format") == 3:
        return daily_card_v3(date, doc)
    return daily_card_v2(date, doc)


def daily_card_v2(date, doc):
    """2026-11-01 到 11-25 的三分钟版：一句头条、今天做什么、今日机会（深挖结论和报告按钮）、其他候选、一条 GitHub 生意线索。
    2026-11-01 起日报只有机会候选、GitHub 工具和 Skills 三栏，资讯、玩法风向和跟进不再推。"""
    m, d = int(date[5:7]), int(date[8:10])
    st = doc.get("stats") or {}
    opps, tools, skills = doc.get("opportunities") or [], doc.get("tools") or [], doc.get("skills") or []
    head = re.sub(r"[*`]", "", (doc.get("headline") or [""])[0])
    els = [md(f"**{head}**" if head else ""),
           md("　".join(x for x in [f"读完约 {st['read_minutes']} 分钟" if st.get("read_minutes") else "",
                                   f"机会候选 {len(opps)} · Skills {len(skills)} · GitHub {len(tools)}"] if x))]
    acts = doc.get("actions") or []
    if acts:
        els.append({"tag": "hr"})
        els.append(md("**今天做什么**\n" + "\n".join(f"{i}. {a['text']}（{a.get('minutes')} 分钟）" for i, a in enumerate(acts, 1))))
    pick = next((b for b in opps if b.get("id") == doc.get("pick")), None)
    if pick:
        fid = f"{date}-{pick['id']}"
        lead = report_lead(fid, 120)
        els.append({"tag": "hr"})
        els.append(md(f"**今日机会**\n**{pick['name']}**（{pick.get('verdict', '')}）{re.sub(r'[*`]', '', pick.get('one_liner', ''))}\n{opp_numbers(pick)}"
                      + (f"\n**深挖结论**　{lead}" if lead else "\n深挖报告没写出来，点「收藏并深挖」补一份。")))
        els.append(buttons(("看深挖报告", site_link(date=date, id=fid) if lead else None, "primary"),
                           ("收藏", action_link("fav", fid), "default"),
                           ("收藏并深挖", None if lead else action_link("deep", fid), "primary")))
    others = [b for b in opps if b is not pick]
    if others:
        els.append({"tag": "hr"})
        els.append(md("**其他候选**"))
        for b in others[:3]:
            els.append(md(f"**{b['name']}**（{b.get('verdict', '')}）{re.sub(r'[*`]', '', b.get('one_liner', ''))}"))
            els.append(buttons(("收藏并深挖", action_link("deep", f"{date}-{b['id']}"), "default")))
        if len(others) > 3:
            els.append(md(f"还有 {len(others) - 3} 个在网站上"))
    biz = [t for t in tools if t.get("business")]
    if biz:  # 2026-10-30 起工具按能做什么生意挑：挑一条，有需求证据的优先
        t = next((t for t in biz if t.get("demand")), biz[0])
        dm = (t.get("demand") or [{}])[0]
        dm_title = re.sub(r"[\[\]]", "", dm.get("title") or "")  # 方括号会弄坏 markdown 链接
        dm_title = dm_title if len(dm_title) <= 50 else dm_title[:48] + "…"
        fid = f"{date}-{t['id']}"
        els.append({"tag": "hr"})
        els.append(md(f"**GitHub 生意线索** [{t['repo']}]({t['url']})" + (f"（{t['license_tier']}）" if t.get("license_tier") else "")
                      + f"\n{re.sub(r'[*`]', '', t['business'])}"
                      + (f"\n有人在要：[{dm_title}]({dm['url']}) {dm.get('reactions', 0)} 赞" if dm.get("url") else "")))
        els.append(buttons(("收藏", action_link("fav", fid), "default"),
                           ("收藏并深挖", action_link("deep", fid), "primary")))
    els.append({"tag": "hr"})
    backlog = unread_before(date)
    if backlog:
        days = "、".join(f"{int(x[5:7])}月{int(x[8:10])}日" for x in backlog)
        els.append(md(f"🔴 还有 {len(backlog)} 期没看：{days}"))
    els.append(buttons(("打开今日日报", site_link(), "primary"),
                       ("看没看的往期", site_link(tab="history") if backlog else None, "default")))
    return card(f"AI 机会雷达 · {m}月{d}日", "turquoise", els)


def deepdive_card(fid):
    fav = json.loads((ROOT / "data/favorites" / f"{fid}.json").read_text("utf-8"))
    it = fav["item"]
    name = it.get("name") or it.get("repo") or it.get("title")
    return card(f"深挖完成：{name}", "green", [
        md(report_lead(fid) or "分析已经放进网站的收藏页。"),
        buttons(("查看深挖", site_link(tab="fav", id=fid), "primary"))])


def weekly_card(date):
    path = ROOT / "data/weekly" / f"{date}.md"
    text = path.read_text("utf-8")
    lead = ""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "|", ">", "---")):
            lead = clean(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line))[:240]
            break
    summ = pool.summary(day=date)
    return card(f"AI 机会雷达 · 周报 {int(date[5:7])}月{int(date[8:10])}日", "blue", [
        md(lead or "这周的周报已经放到网站上。"), md(summ["line"]),
        buttons(("看周报", site_link(tab="history", week=date), "primary"), ("看机会池", site_link(tab="pool"), "default"))])


def stale_card(last, days=None):
    days = int(days) if days else None
    run = os.environ.get("RUN_URL")
    return card(f"AI 机会雷达：已经 {days or '好几'} 天没有新日报了", "red", [
        md(f"最新一期是 **{last}**。每天的定时任务没做出日报，失败通知可能被当成偶发。\n"
           "最常见的原因是 Claude 令牌失效：在自己电脑终端运行 `claude setup-token` 拿新令牌，替换仓库 Secrets 里的 "
           "CLAUDE_CODE_OAUTH_TOKEN，再手动运行一次「每日日报」。配上 ANTHROPIC_API_KEY 当备用，以后令牌失效也不会停。"),
        buttons(("看每日日报的运行记录", run, "primary"))])


def error_card(msg):
    run = os.environ.get("RUN_URL")
    return card("AI 机会雷达：运行失败", "red", [
        md(msg), buttons(("查看运行记录", run, "default"))])


HOOK = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def describe(v):
    """不泄露内容地说明一个值长什么样，方便对照飞书后台检查。"""
    if not v:
        return "是空的"
    head = "以 https:// 开头" if v.startswith("https://") else ("以 http 开头" if v.startswith("http") else "不是网址")
    return f"{len(v)} 个字符，{head}" + ("，里面有机器人编号" if HOOK.search(v) else "")


def webhook_and_secret():
    """取出飞书机器人地址和签名密钥（复制时折行、多出的空格都去掉），并纠正几种常见填法。"""
    url = "".join(os.environ.get("FEISHU_WEBHOOK", "").split())
    secret = "".join(os.environ.get("FEISHU_SECRET", "").split())
    if not url.startswith("http") and secret.startswith("http"):
        url, secret = secret, url  # 两个值填反了
        print("FEISHU_WEBHOOK 和 FEISHU_SECRET 好像填反了，已按调换后的值推送。")
    if not url.startswith("http") and HOOK.fullmatch(url):
        url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{url}"  # 只填了地址最后那段编号
        print("FEISHU_WEBHOOK 只填了机器人编号，已补成完整地址。")
    if not url.startswith("https://"):
        raise SystemExit(
            "FEISHU_WEBHOOK 应该是飞书群机器人的完整地址，形如 https://open.feishu.cn/open-apis/bot/v2/hook/…；"
            f"现在它{describe(url)}；FEISHU_SECRET {describe(secret)}。")
    return url, secret


def send(payload):
    url, secret = webhook_and_secret()
    if secret:
        ts = str(int(time.time()))
        sign = base64.b64encode(hmac.new(f"{ts}\n{secret}".encode(), digestmod=hashlib.sha256).digest()).decode()
        payload = {"timestamp": ts, "sign": sign, **payload}
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = json.loads(r.read().decode() or "{}")
    if body.get("code", 0) != 0:
        raise SystemExit(f"飞书返回错误：{body}")
    print("飞书已推送")


def main():
    kind, args = sys.argv[1], sys.argv[2:]
    payload = {"daily": daily_card, "deepdive": deepdive_card, "error": error_card,
               "weekly": weekly_card, "stale": stale_card}[kind](*args)
    if not os.environ.get("FEISHU_WEBHOOK", "").strip():
        print("没有配置 FEISHU_WEBHOOK，只打印卡片：")
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0
    send(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
