# 配置指南

从零搭一套（或者把仓库交给别人、换个账号重搭）时照这个做。所有密钥只填在 GitHub 和 Cloudflare 后台，不要写进仓库，也不要发到聊天里。

## 要填的东西一览

| 名字 | 填在哪 | 从哪来 | 必填 |
|---|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | GitHub 仓库 Secrets | 第 3 步，`claude setup-token` | 和下面两行三选一 |
| `ANTHROPIC_API_KEY` | GitHub 仓库 Secrets | 第 3 步，Anthropic 控制台 | 三选一 |
| `OPENROUTER_API_KEY` | GitHub 仓库 Secrets | 第 3 步，OpenRouter 后台 | 三选一，前两个都没有时才用 |
| `FEISHU_WEBHOOK` | GitHub 仓库 Secrets | 第 4 步，飞书自定义机器人 | 不填就不推送 |
| `FEISHU_SECRET` | GitHub 仓库 Secrets | 第 4 步，签名校验密钥 | 建议 |
| `TWITTERAPI_IO_KEY` | GitHub 仓库 Secrets | 第 5 步，twitterapi.io 后台 | 不填就不抓 X |
| `TIKHUB_API_KEY` | GitHub 仓库 Secrets | 第 5 步，TikHub 用户后台 | 不填就不抓抖音、小红书等平台 |
| `TRUSTMRR_API_KEY` | GitHub 仓库 Secrets | 第 5 步，trustmrr.com 免费申请 | 可选 |
| `ACTION_KEY` | GitHub 仓库 Secrets **和** Cloudflare Worker | 第 6 步，自己生成 | 要收藏按钮时必填 |
| `GITHUB_TOKEN` | Cloudflare Worker | 第 7 步 | 要收藏按钮时必填 |
| Worker 地址 | `config/site.json` 的 `worker_url`，或仓库变量 `WORKER_URL` | 第 8 步 | 要收藏按钮时必填 |

GitHub 密钥的填写页：仓库 → Settings → Secrets and variables → Actions → **New repository secret**，Name 填表里的名字，Secret 填值。

## 第 1 步：仓库

仓库要公开：GitHub 免费账号只能用公开仓库发布网站，公开仓库的 Actions 运行时长也不限。代价是网站和收藏夹别人能看到；收藏、深挖按钮要口令，别人点不了。

换仓库或换账号时，要改的地方：`config/site.json` 的 `site_url`；`worker/worker.js` 里的 `DEFAULT_REPO`、`DEFAULT_SITE`（或在 Worker 里配 `GITHUB_REPO`、`SITE_URL`）。

## 第 2 步：开启网站

仓库 → Settings → Pages，**Build and deployment → Source** 选 **GitHub Actions**。网址形如 `https://<用户名>.github.io/ai-radar/`。

## 第 3 步：让 AI 能在云端干活

三选一（都填了时优先用订阅，其次 Anthropic API，最后 OpenRouter）：

- **用 Claude 订阅（Pro 或 Max）**：在自己电脑上装好 Claude Code，终端运行 `claude setup-token`，按提示在浏览器登录，得到一串以 `sk-ant-oat` 开头的令牌，存为 `CLAUDE_CODE_OAUTH_TOKEN`。日报和深挖会占用订阅额度。从终端复制时被折成两行也没关系，工作流会去掉空白。
- **用 Anthropic API 按量付费**：console.anthropic.com → API Keys → Create Key，存为 `ANTHROPIC_API_KEY`。
- **用 OpenRouter 按量付费**：OpenRouter 后台建一个 API Key，存为 `OPENROUTER_API_KEY`。按 OpenRouter 官方的 Claude Code 接法调用 Claude，花 OpenRouter 余额。

想换成别家的 AI（Codex、Gemini 等）见 `AGENTS.md` 的「换成别的 AI」。

可选的仓库变量（Settings → Secrets and variables → Actions → **Variables**）：`DAILY_MODEL`（写日报的模型，默认 `sonnet`）、`DEEPDIVE_MODEL`（深挖的模型，默认 `opus`）。

## 第 4 步：飞书机器人

1. 在飞书里新建一个群，或用已有的群。
2. 群设置 → **群机器人 → 添加机器人 → 自定义机器人**，起名「AI 机会雷达」。
3. 复制 **Webhook 地址**，存为 `FEISHU_WEBHOOK`。
4. 安全设置里勾选 **签名校验**，复制密钥，存为 `FEISHU_SECRET`。不要勾「自定义关键词」和「IP 白名单」，GitHub 的出口 IP 不固定。
5. Actions → **飞书推送测试** → Run workflow，把最近一期推到飞书，确认配置对。

## 第 5 步：抓取用的 API

- **X（twitterapi.io）**：注册后后台首页有 API Key，充几美元，存为 `TWITTERAPI_IO_KEY`。每天最多抓 600 条推文，约 1–3 美元/月；想更省调小 `config/sources.json` 的 `x.max_tweets`。
- **TikHub（抖音、小红书、TikTok、YouTube、B站）**：tikhub.io 注册，用户后台创建 API Token（要选接口权限时把这几个平台都勾上），Add credit 页充值（最低 5 美元，支持支付宝、PayPal、USDT），存为 `TIKHUB_API_KEY`。每天约 31 次请求、上限 40 次，约 1 美元/月。配好后 Actions → **TikHub 试抓** → Run workflow（约 0.03 美元），看日志确认各平台字段认对了。
- **TrustMRR（可选）**：trustmrr.com 免费申请 API Key，存为 `TRUSTMRR_API_KEY`。有它时机会卡的收入证据由脚本抓；没有时 AI 自己去页面找。

## 第 6 步：生成收藏口令

终端运行 `openssl rand -hex 20`，或用密码管理器生成 30 位以上的随机字符，存为 `ACTION_KEY`。第 7 步 Cloudflare 里填同一串。

## 第 7 步：Cloudflare Worker（收藏按钮的中转）

**先在 GitHub 建一个令牌**：头像 → Settings → Developer settings → Personal access tokens → **Fine-grained tokens → Generate new token**。Repository access 选 **Only select repositories**，只选 `ai-radar`；Repository permissions → **Contents** 选 **Read and write**，其他不用。过期时间最长一年，到期后换新的。

**再建 Worker**：

1. 登录 Cloudflare，**Workers & Pages → Create → Create Worker**，名字填 `ai-radar-act`，Deploy。
2. **Edit code**，把仓库里 `worker/worker.js` 的全部内容粘进去替换，Deploy。（用命令行部署的话用 `worker/wrangler.toml`。）
3. Worker → **Settings → Variables and Secrets → Add**，加两项 Secret：`GITHUB_TOKEN`（刚才的令牌）、`ACTION_KEY`（第 6 步那串）。
4. 记下 Worker 地址，形如 `https://ai-radar-act.xxx.workers.dev`。

**（可选）已读状态多设备同步**：**Storage & Databases → KV → Create**，名字 `ai-radar`；回到 Worker → **Settings → Bindings → Add → KV namespace**，变量名 `RADAR_KV`，选刚建的。不配时已读状态只记在当前浏览器。

## 第 8 步：填 Worker 地址

把 Worker 地址填进 `config/site.json` 的 `worker_url` 并提交，或者填仓库变量 `WORKER_URL`（变量优先）。

## 第 9 步：跑第一期

1. Actions → **每日日报** → Run workflow。之后每天北京时间 4:23 起自动运行（5:23、6:23 补跑），7 点推送飞书。第一步会检查密钥，缺什么写在那次运行的摘要页；没有 AI 密钥会直接停下。
2. 飞书收到卡片后点 **打开今日日报**：这一下会把口令存进手机浏览器，之后网站上的收藏按钮就能用。换手机或浏览器时从飞书卡片再进一次。
3. 点任一机会的 **收藏并深挖** 试一下：确认页显示「已收藏，开始深挖」，写完后飞书再推一张卡片，报告在网站的「收藏」页。

## 出问题时

- **飞书没收到**：看 Actions 里那次运行哪一步红了；失败时机器人会推一张带运行记录链接的卡片。什么卡片都收不到，多半是 `FEISHU_WEBHOOK` 或 `FEISHU_SECRET` 填错。
- **AI 那一步红了**：日志里「查 Claude 出错原因」一步打印了原因，常见是令牌过期或额度用完。
- **点收藏提示「口令不对」**：Worker 里的 `ACTION_KEY` 和 GitHub 里的不一致。
- **提示「GitHub 没有接受请求」**：Worker 的 `GITHUB_TOKEN` 没有 Contents 写权限，或生成时没选中 `ai-radar`。
- **网站显示「还没连上收藏接口」**：从飞书卡片的「打开今日日报」进一次网站。
- **想换信息源或写作标准**：改 `config/sources.json` 和 `prompts/daily.md`。
