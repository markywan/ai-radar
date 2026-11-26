#!/usr/bin/env python3
"""机会池：每个机会一个文件 data/opportunities/<编号>.json，记它走到哪一步、下一步做什么、什么时候到期。

2026-11-26 起日报的目标是「每天把池子往前推一步」，不再是每天找新机会：
  待研究 → 待验证 → 验证中 → 已启动 → 已变现，另有 暂停、淘汰。收藏是动作，不是状态。
同一时间只能有 1 个「验证中」，开始验证新的会把旧的自动改成「暂停」。

  python3 scripts/pool.py seed                     # 把 config/opportunity_seeds.json 里还没进池子的种子放进去
  python3 scripts/pool.py add-daily 2026-11-27     # 日报的今日机会进池子（60 分以上；75 分以上直接「待验证」）
  python3 scripts/pool.py card 2026-11-27-B01      # 深挖报告末尾的「池子卡片」写回池子（下一步、到期日、过关指标）
  python3 scripts/pool.py set <编号> 验证中 [--note 说明] [--result 结果]   # 飞书、网站上的状态按钮
  python3 scripts/pool.py summary                  # 打印池子概况（JSON），fetch.py、网站、飞书都用

仓库是公开的，这里只存脱敏的状态和数字：客户名单、报价、订单别写进来。
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "data/opportunities"
SEEDS = ROOT / "config/opportunity_seeds.json"
STATUSES = ["待研究", "待验证", "验证中", "已启动", "已变现", "暂停", "淘汰"]
ACTIVE = {"待研究", "待验证", "验证中", "已启动", "已变现"}
ID = re.compile(r"^(seed-[a-z0-9-]{2,40}|\d{4}-\d{2}-\d{2}-B\d{2})$")
PASS, DEEP = 60, 75  # 60 分以上进池子，75 分以上值得深挖、直接「待验证」


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def norm(s):
    """名字去掉括号注释、空白和标点后比较，「外贸询盘筛选（AI）」和「外贸询盘筛选」算同一个。"""
    s = re.sub(r"[（(][^）)]*[）)]", "", str(s or "").lower())
    return re.sub(r"[\s\-_·・,，。:：/「」\"'“”]+", "", s)


def load_all():
    items = []
    for p in sorted(POOL.glob("*.json")):
        try:
            items.append(json.loads(p.read_text("utf-8")))
        except (OSError, ValueError):
            print(f"读不了 {p.name}，跳过", file=sys.stderr)
    return items


def get(pid):
    p = POOL / f"{pid}.json"
    return json.loads(p.read_text("utf-8")) if p.is_file() else None


def save(item):
    POOL.mkdir(parents=True, exist_ok=True)
    (POOL / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=1) + "\n", "utf-8")


def new_item(pid, name, **kw):
    item = {"id": pid, "name": name, "track": kw.get("track"), "status": kw.get("status", "待研究"),
            "hypothesis": kw.get("hypothesis") or {}, "score": kw.get("score"), "origin": kw.get("origin") or {},
            "deepdive": kw.get("deepdive"), "next_action": kw.get("next_action") or "", "due_at": kw.get("due_at"),
            "experiment_metric": kw.get("experiment_metric") or "", "stop_condition": kw.get("stop_condition") or "",
            "result": "", "links": kw.get("links") or {"tools": [], "skills": []},
            "created_at": now(), "last_reviewed_at": today(), "history": []}
    log(item, item["status"], kw.get("note") or "进池子")
    return item


def log(item, status, note):
    item.setdefault("history", []).append({"at": now(), "status": status, "note": note})


def find_same(items, name, ref=None):
    if ref:
        hit = next((x for x in items if x["id"] == ref), None)
        if hit:
            return hit
    key = norm(name)
    return next((x for x in items if key and norm(x.get("name")) == key), None)


def summary(items=None, day=None):
    """池子概况：各状态多少个、验证中那个、到期没推进的、排队等验证的（按分数）。"""
    items = load_all() if items is None else items
    day = day or today()
    counts = {s: sum(1 for x in items if x.get("status") == s) for s in STATUSES}
    lite = lambda x: {k: x.get(k) for k in ("id", "name", "track", "status", "next_action", "due_at",
                                             "experiment_metric", "stop_condition", "deepdive")} | {
        "score": (x.get("score") or {}).get("total"), "days_in_status": days_in_status(x, day)}
    validating = [lite(x) for x in items if x.get("status") == "验证中"]
    overdue = [lite(x) for x in items if x.get("status") in ("验证中", "待验证", "已启动")
               and x.get("due_at") and x["due_at"] < day]
    queue = sorted((lite(x) for x in items if x.get("status") == "待验证"), key=lambda x: -(x["score"] or 0))
    research = [lite(x) for x in items if x.get("status") == "待研究"]
    return {"date": day, "counts": counts, "validating": validating, "overdue": overdue, "queue": queue,
            "research": research, "line": status_line(counts, validating)}


def days_in_status(x, day):
    hist = [h for h in x.get("history") or [] if h.get("status") == x.get("status")]
    if not hist:
        return None
    try:
        return (dt.date.fromisoformat(day) - dt.date.fromisoformat(hist[-1]["at"][:10])).days
    except ValueError:
        return None


def status_line(counts, validating):
    """一行池子状态，日报第二行、飞书卡片都用。"""
    parts = [f"{s} {counts[s]}" for s in ("验证中", "待验证", "待研究", "已启动", "已变现") if counts.get(s)]
    head = f"正在验证：{validating[0]['name']}" if validating else "现在没有在验证的项目"
    return head + "　池子：" + ("，".join(parts) if parts else "空")


def cmd_seed(_):
    seeds = json.loads(SEEDS.read_text("utf-8"))["seeds"]
    items, added = load_all(), 0
    for s in seeds:
        if get(s["id"]) or find_same(items, s["name"]):
            continue
        item = new_item(s["id"], s["name"], track=s.get("track"), status=s.get("status", "待研究"), hypothesis=s.get("hypothesis"),
                        origin={"kind": "种子", "ref": s.get("from"), "note": s.get("note", "")},
                        deepdive=s.get("deepdive"), note="种子：" + (s.get("from") or ""))
        save(item)
        items.append(item)
        added += 1
    print(f"种子进池子 {added} 个，池子共 {len(items)} 个")
    return 0


def cmd_add_daily(a):
    path = ROOT / "data/daily" / f"{a.date}.json"
    doc = json.loads(path.read_text("utf-8"))
    items = load_all()
    changed = False
    for b in doc.get("opportunities") or []:
        total = (b.get("score") or {}).get("total")
        if not isinstance(total, (int, float)) or total < PASS:
            continue
        fid = f"{a.date}-{b['id']}"
        status = "待验证" if total >= DEEP else "待研究"
        fields = {"track": b.get("track"), "hypothesis": b.get("hypothesis"), "score": b.get("score")}
        hit = find_same(items, b.get("name"), b.get("pool_ref"))
        if hit:
            hit.update({k: v for k, v in fields.items() if v})
            hit.setdefault("origin", {}).setdefault("seen_in", [])
            if fid not in hit["origin"]["seen_in"]:
                hit["origin"]["seen_in"].append(fid)
            if hit["status"] in ("待研究", "暂停") and status == "待验证":
                hit["status"] = status
                log(hit, status, f"{fid} 打了 {total} 分")
            hit["last_reviewed_at"] = a.date
            save(hit)
            b["pool_id"], changed = hit["id"], True
            print(f"{fid} 推进了池子里的 {hit['id']}（{hit['status']}）")
        else:
            item = new_item(fid, b["name"], status=status, origin={"kind": "日报", "ref": fid},
                            note=f"{a.date} 日报，{total} 分", **fields)
            save(item)
            items.append(item)
            b["pool_id"], changed = fid, True
            print(f"{fid} 进池子（{status}，{total} 分）")
    if changed:  # 网站和飞书上的状态按钮按 pool_id 改池子
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
    return 0


CARD = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def cmd_card(a):
    """深挖报告最后的「池子卡片」（一段 json 代码块）写回池子。深挖说不做的直接淘汰。"""
    md = ROOT / "data/deepdive" / f"{a.fid}.md"
    if not md.is_file():
        print(f"没有 {md.name}，跳过")
        return 0
    text = md.read_text("utf-8")
    tail = text[text.rfind("池子卡片"):] if "池子卡片" in text else text
    m = CARD.search(tail)
    if not m:
        print(f"{md.name} 里没有池子卡片（json 代码块），池子不变")
        return 0
    try:
        card = json.loads(m.group(1))
    except ValueError as e:
        print(f"{md.name} 的池子卡片不是合法 JSON（{e}），池子不变")
        return 0
    items = load_all()
    date, bid = a.fid[:10], a.fid[11:]
    doc = json.loads((ROOT / "data/daily" / f"{date}.json").read_text("utf-8")) if (ROOT / "data/daily" / f"{date}.json").is_file() else {}
    b = next((x for x in doc.get("opportunities") or [] if x.get("id") == bid), {})
    item = get(a.fid) or find_same(items, b.get("name") or card.get("name"), b.get("pool_ref"))
    if not item:
        item = new_item(a.fid, card.get("name") or b.get("name") or a.fid, track=b.get("track"),
                        origin={"kind": "深挖", "ref": a.fid}, note="深挖后进池子")
    item["deepdive"] = a.fid
    for k in ("next_action", "experiment_metric", "stop_condition"):
        if card.get(k):
            item[k] = str(card[k])
    if card.get("chosen_cut"):
        item["name"] = str(card["chosen_cut"])[:60]
    if isinstance(card.get("hypothesis"), dict):
        item["hypothesis"] = card["hypothesis"]
    days = card.get("due_in_days")
    if isinstance(days, int) and 0 < days <= 30:
        item["due_at"] = (dt.date.fromisoformat(date) + dt.timedelta(days=days)).isoformat()
    verdict = str(card.get("verdict") or "")
    new = "淘汰" if verdict.startswith("不做") else ("待验证" if item["status"] in ("待研究", "暂停") else item["status"])
    if new != item["status"]:
        item["status"] = new
        log(item, new, f"深挖 {a.fid}：{verdict or '可以验证'}" + (f"，{card.get('reason')}" if card.get("reason") else ""))
    item["last_reviewed_at"] = date
    save(item)
    print(f"池子卡片已写回 {item['id']}：{item['status']}，下一步「{item.get('next_action', '')[:30]}」，到期 {item.get('due_at')}")
    return 0


def cmd_set(a):
    if a.status not in STATUSES:
        print(f"状态只能是 {'/'.join(STATUSES)}")
        return 2
    item = get(a.id)
    if not item:
        print(f"池子里没有 {a.id}")
        return 2
    day = today()
    if a.status == "验证中":
        for other in load_all():
            if other["id"] != item["id"] and other.get("status") == "验证中":
                other["status"] = "暂停"
                log(other, "暂停", f"开始验证 {item['name']}，这个先停（一次只验证一个）")
                other["last_reviewed_at"] = day
                save(other)
                print(f"{other['id']} 改成暂停")
        if not item.get("due_at") or item["due_at"] < day:
            item["due_at"] = (dt.date.fromisoformat(day) + dt.timedelta(days=7)).isoformat()
    if a.result:
        item["result"] = a.result
    if item.get("status") != a.status or a.note:
        item["status"] = a.status
        log(item, a.status, a.note or "按钮")
    item["last_reviewed_at"] = day
    save(item)
    print(f"{item['id']}「{item['name']}」→ {a.status}")
    return 0


def cmd_summary(_):
    print(json.dumps(summary(), ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="op", required=True)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)
    p = sub.add_parser("add-daily")
    p.add_argument("date")
    p.set_defaults(fn=cmd_add_daily)
    p = sub.add_parser("card")
    p.add_argument("fid")
    p.set_defaults(fn=cmd_card)
    p = sub.add_parser("set")
    p.add_argument("id")
    p.add_argument("status")
    p.add_argument("--note", default="")
    p.add_argument("--result", default="")
    p.set_defaults(fn=cmd_set)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    a = ap.parse_args()
    if getattr(a, "id", None) and not ID.match(a.id):
        print(f"编号格式不对：{a.id}")
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
