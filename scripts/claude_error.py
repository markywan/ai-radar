"""Claude 那一步失败时，从运行记录里只取出错误原因打印出来（完整输出默认隐藏）。

认得出的原因（令牌失效、额度用完）还会写一句该怎么办到 GITHUB_OUTPUT 的 hint，
飞书失败通知会带上这句话，不用点进运行记录才知道要做什么。
"""
import json
import os
import sys

HINTS = [
    (("oauth token revoked", "failed to authenticate", "invalid api key", "authentication_error"),
     "原因：Claude 令牌失效了。在自己电脑终端运行 claude setup-token 拿新令牌，"
     "替换仓库 Secrets 里的 CLAUDE_CODE_OAUTH_TOKEN，再手动运行一次「每日日报」。"),
    (("usage limit", "rate limit", "rate_limit", "credit balance", "quota"),
     "原因：Claude 额度用完或被限流了，等额度恢复后手动运行一次「每日日报」。"),
]


def hint_for(text):
    low = text.lower()
    for keys, hint in HINTS:
        if any(k in low for k in keys):
            return hint
    return ""


try:
    msgs = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print(f"读不到 Claude 的运行记录：{e}")
    sys.exit(0)
for m in reversed(msgs if isinstance(msgs, list) else [msgs]):
    if isinstance(m, dict) and m.get("type") == "result":
        text = str(m.get("result") or m.get("error") or json.dumps({k: m.get(k) for k in ("subtype", "is_error", "num_turns")}, ensure_ascii=False))
        print(f"::error::Claude 没跑成功：{text[:400]}")
        hint = hint_for(text)
        if hint and os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"hint={hint}\n")
        break
else:
    print("运行记录里没有结果，可能是 Claude 一开始就没启动。")
