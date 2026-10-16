"""Claude 那一步失败时，从运行记录里只取出错误原因打印出来（完整输出默认隐藏）。"""
import json
import sys

try:
    msgs = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print(f"读不到 Claude 的运行记录：{e}")
    sys.exit(0)
for m in reversed(msgs if isinstance(msgs, list) else [msgs]):
    if isinstance(m, dict) and m.get("type") == "result":
        text = m.get("result") or m.get("error") or json.dumps({k: m.get(k) for k in ("subtype", "is_error", "num_turns")}, ensure_ascii=False)
        print(f"::error::Claude 没跑成功：{str(text)[:400]}")
        break
else:
    print("运行记录里没有结果，可能是 Claude 一开始就没启动。")
