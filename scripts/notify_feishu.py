#!/usr/bin/env python3
"""往飞书群推送卡片（群自定义机器人 webhook）。

  python3 scripts/notify_feishu.py daily 2026-10-15
  python3 scripts/notify_feishu.py deepdive 2026-10-15-B01
  python3 scripts/notify_feishu.py error "说明文字"

环境变量：FEISHU_WEBHOOK（必填）、FEISHU_SECRET（开了签名校验才要）、
SITE_URL（网站地址）、WORKER_URL 与 ACTION_KEY（卡片上的收藏按钮要用）、RUN_URL（失败时附上运行记录）。
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = os.environ.get("SITE_URL", "").rstrip("/") + "/"
WORKER = os.environ.get("WORKER_URL", "").rstrip("/")
KEY = os.environ.get("ACTION_KEY", "")


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


def daily_card(date):
    doc = json.loads((ROOT / "data/daily" / f"{date}.json").read_text("utf-8"))
    m, d = int(date[5:7]), int(date[8:10])
    els = [md("\n".join(f"**{i}.** {h}" for i, h in enumerate(doc.get("headline", []), 1))),
           md(f"资讯 {len(doc['news'])} · 工具 {len(doc['tools'])} · Skills {len(doc['skills'])} · "
              f"机会 {len(doc['opportunities'])}"),
           {"tag": "hr"}]
    for n in doc["news"][:3]:
        els.append(md(f"**{n['id']}** [{n['title']}]({n['url']})"))
    for key in ("tools", "skills"):
        for it in doc[key][:1]:
            name = it.get("repo") or it.get("name")
            els.append(md(f"**{it['id']}** [{name}]({it['url']})：{it['what']}"))
    for b in doc["opportunities"]:
        fid = f"{date}-{b['id']}"
        els.append({"tag": "hr"})
        els.append(md(f"**{b['id']} {b['name']}**（{b['verdict']}）\n{b['one_liner']}\n"
                      f"起步 ${b['fit'].get('startup_cost_usd')} · MVP {b['fit'].get('mvp_days')} 天 · "
                      f"每周 {b['automation'].get('weekly_hours')} 小时"))
        els.append(buttons(("收藏", action_link("fav", fid), "default"),
                           ("收藏并深挖", action_link("deep", fid), "primary")))
    els.append({"tag": "hr"})
    els.append(buttons(("打开今日日报", site_link(), "primary")))
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


def send(payload):
    url = os.environ["FEISHU_WEBHOOK"]
    secret = os.environ.get("FEISHU_SECRET")
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
    kind, arg = sys.argv[1], sys.argv[2]
    payload = {"daily": daily_card, "deepdive": deepdive_card, "error": error_card}[kind](arg)
    if not os.environ.get("FEISHU_WEBHOOK"):
        print("没有配置 FEISHU_WEBHOOK，只打印卡片：")
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0
    send(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
