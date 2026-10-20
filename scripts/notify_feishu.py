#!/usr/bin/env python3
"""往飞书群推送卡片（群自定义机器人 webhook）。

  python3 scripts/notify_feishu.py daily 2026-10-15
  python3 scripts/notify_feishu.py deepdive 2026-10-15-B01
  python3 scripts/notify_feishu.py error "说明文字"

环境变量：FEISHU_WEBHOOK（必填）、FEISHU_SECRET（开了签名校验才要）、
FEISHU_WEBHOOK_2 与 FEISHU_SECRET_2（另一个群，比如家人群，可选：只收日报，卡片不带收藏口令）、
SITE_URL（网站地址）、WORKER_URL 与 ACTION_KEY（卡片上的收藏按钮要用）、RUN_URL（失败时附上运行记录）。
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


def daily_card(date):
    """三分钟版：一句头条、今天做什么、最强的平台信号、机会一句话、影响你的资讯标题。工具和 Skills 去网站看。"""
    doc = json.loads((ROOT / "data/daily" / f"{date}.json").read_text("utf-8"))
    m, d = int(date[5:7]), int(date[8:10])
    st = doc.get("stats") or {}
    head = re.sub(r"[*`]", "", (doc.get("headline") or [""])[0])
    els = [md(f"**{head}**" if head else ""),
           md("　".join(x for x in [f"读完约 {st['read_minutes']} 分钟" if st.get("read_minutes") else "",
                                   f"资讯 {len(doc['news'])} · 工具 {len(doc['tools'])} · Skills {len(doc['skills'])}"
                                   + (f" · 玩法 {len(doc['trends'])}" if doc.get("trends") else "")
                                   + (f" · 跟进 {len(doc['followups'])}" if doc.get("followups") else "")] if x))]
    acts = doc.get("actions") or []
    if acts:
        els.append({"tag": "hr"})
        els.append(md("**今天做什么**\n" + "\n".join(f"{i}. {a['text']}（{a.get('minutes')} 分钟）" for i, a in enumerate(acts, 1))))
    trends = doc.get("trends") or []
    if trends:
        t = trends[0]
        ev = (t.get("evidence") or [{}])[0]
        els.append({"tag": "hr"})
        els.append(md(f"**玩法风向** {t['topic']}（{t.get('signal', '')}）：{t.get('brief', '')}"
                      + (f"\n[{ev.get('platform', '')}：{ev.get('title', '')[:30]}]({ev['url']}) {ev.get('metrics', '')}" if ev.get("url") else "")
                      + (f"\n还有 {len(trends) - 1} 条在网站上" if len(trends) > 1 else "")))
    for b in doc["opportunities"]:
        fid = f"{date}-{b['id']}"
        els.append({"tag": "hr"})
        els.append(md(f"**机会：{b['name']}**（{b['verdict']}）\n{b['one_liner']}\n"
                      f"起步 ${b['fit'].get('startup_cost_usd')} · MVP {b['fit'].get('mvp_days')} 天 · "
                      f"每周 {b['automation'].get('weekly_hours')} 小时"))
        els.append(buttons(("收藏", action_link("fav", fid), "default"),
                           ("收藏并深挖", action_link("deep", fid), "primary")))
    top = [n for n in doc["news"] if n.get("tier") == "影响你的"] or doc["news"][:3]
    if top:
        els.append({"tag": "hr"})
        els.append(md("**影响你的资讯**\n" + "\n".join(f"- [{n['title']}]({n['url']})" for n in top[:6])))
    fus = doc.get("followups") or []
    if fus:
        els.append(md("**跟进** " + "；".join(f"{f['title']}：{re.sub(r'[*`]', '', f['update']).rstrip('。；;')}" for f in fus[:3])))
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
    md_path = ROOT / "data/deepdive" / f"{fid}.md"
    lead = ""
    if md_path.exists():
        for line in md_path.read_text("utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                lead = line.strip()[:200]
                break
    return card(f"深挖完成：{name}", "green", [
        md(lead or "分析已经放进网站的收藏页。"),
        buttons(("查看深挖", site_link(tab="fav", id=fid), "primary"))])


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


def webhook_and_secret(suffix=""):
    """取出飞书机器人地址和签名密钥（复制时折行、多出的空格都去掉），并纠正几种常见填法。

    suffix 是 "" 时读自己的群（FEISHU_WEBHOOK），是 "_2" 时读另一个群（FEISHU_WEBHOOK_2）。
    """
    hook, sec = f"FEISHU_WEBHOOK{suffix}", f"FEISHU_SECRET{suffix}"
    url = "".join(os.environ.get(hook, "").split())
    secret = "".join(os.environ.get(sec, "").split())
    if not url.startswith("http") and secret.startswith("http"):
        url, secret = secret, url  # 两个值填反了
        print(f"{hook} 和 {sec} 好像填反了，已按调换后的值推送。")
    if not url.startswith("http") and HOOK.fullmatch(url):
        url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{url}"  # 只填了地址最后那段编号
        print(f"{hook} 只填了机器人编号，已补成完整地址。")
    if not url.startswith("https://"):
        raise SystemExit(
            f"{hook} 应该是飞书群机器人的完整地址，形如 https://open.feishu.cn/open-apis/bot/v2/hook/…；"
            f"现在它{describe(url)}；{sec} {describe(secret)}。")
    return url, secret


def send(payload, suffix=""):
    url, secret = webhook_and_secret(suffix)
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
    print("飞书已推送" + ("到另一个群" if suffix else ""))


def main():
    global KEY
    kind, arg = sys.argv[1], sys.argv[2]
    build = {"daily": daily_card, "deepdive": deepdive_card, "error": error_card}[kind]
    if not os.environ.get("FEISHU_WEBHOOK", "").strip():
        print("没有配置 FEISHU_WEBHOOK，只打印卡片：")
        print(json.dumps(build(arg), ensure_ascii=False, indent=1))
        return 0
    send(build(arg))
    # 另一个群只收日报；收藏口令能触发深挖、花 AI 额度，不发给别人，卡片上就没有收藏按钮和未读提醒
    if kind == "daily" and os.environ.get("FEISHU_WEBHOOK_2", "").strip():
        KEY = ""
        try:
            send(build(arg), "_2")
        except (SystemExit, Exception) as e:  # noqa: BLE001
            print(f"另一个群没推送成功：{e}")
            send(error_card(f"日报已推到这个群，但另一个群（FEISHU_WEBHOOK_2）没推送成功：{e}"))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
