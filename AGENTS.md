# 接手说明（给接手的人和 AI）

> **如果你是被每日任务叫来写日报或深挖的，只按 `prompts/daily.md` 或 `prompts/deepdive.md` 做，这份文件不用看。**
> 这份文件给要维护、修改或迁移这个仓库的人和编程代理（Claude Code、Codex、Gemini CLI、Cursor 等）。

这个仓库每天自动出一期「AI 机会雷达」日报：GitHub Actions 抓素材 → 一个 AI 代理按写作标准写成 JSON → 脚本校验、配图 → 发布到 GitHub Pages → 推送飞书。读者是仓库主人一个人（一人公司创业者，背景见 `prompts/daily.md` 第一段）。用户怎么用、栏目是什么见 `README.md`，后台要填什么见 `docs/setup.md`。

## 每天怎么跑

| 步骤 | 文件 | 要 AI 吗 | 要什么密钥 |
|---|---|---|---|
| 定时触发：北京时间 4:23、5:23、6:23 各一次，当天已有日报就跳过 | `.github/workflows/daily.yml` | 否 | — |
| 抓素材，写 `data/raw/<日期>.json`（不提交） | `scripts/fetch.py`、`scripts/platforms.py`、`config/sources.json` | 否 | X、TikHub、TrustMRR 都可选，缺了只跳过那部分 |
| **写日报，写 `data/daily/<日期>.json`** | `prompts/daily.md` | **是**，要能读写文件、上网搜索和打开网页、运行 `validate.py` 后按提示改 | Claude 令牌（三选一，见 `docs/setup.md` 第 3 步） |
| 从 README 配图 | `scripts/enrich.py` | 否 | — |
| 校验和编号 | `scripts/validate.py` | 否 | — |
| 提交到 main、建站 | `daily.yml` 的「提交」步、`publish.yml`、`scripts/build_site.py`、`web/` | 否 | — |
| 推飞书，定时任务等到 7 点再发 | `scripts/notify_feishu.py` | 否 | `FEISHU_WEBHOOK`、`FEISHU_SECRET`；可选 `FEISHU_WEBHOOK_2`、`FEISHU_SECRET_2` 推另一个群（只发日报，不带收藏口令，因为口令能触发深挖、花 AI 额度） |

收藏和深挖：网站或飞书上的按钮 → Cloudflare Worker（`worker/worker.js`）核对 `ACTION_KEY` → 触发 `favorite.yml` → `favorite.py` 存进 `data/favorites/`；深挖时 AI 按 `prompts/deepdive.md` 写 `data/deepdive/<编号>.md`。这条也要 AI。

**只有「写日报」和「深挖」两步用 AI，其余全是 Python 标准库脚本，换 AI 不用动。**

## 格式契约

- 日报 JSON 的结构写在 `prompts/daily.md` 的「输出」一节，`scripts/validate.py` 是最终裁判：必填字段、条数范围、枚举值（`tier`、`group`、`area`、`safety`、`verdict`、`signal`）、链接、字数上限。网站（`web/app.js`）和飞书卡片都按这个结构读。改结构时三处一起改：`prompts/daily.md`、`validate.py`、`web/app.js`（飞书卡片在 `notify_feishu.py`）。
- 编号（`N01`、`G02`、`B01`…）由 `validate.py` 补，AI 不写。收藏、深挖、跟进栏都靠「日期-编号」找条目，已发布的日报不要重新编号。

## 已定的规则和原因

改这些之前先问仓库主人。

- **7 点前做好、7 点推送**：他早上起来看。GitHub 定时任务常晚到一两个小时，所以排三次；前两次失败不发失败通知，6 点后那次也失败才通知。
- **资讯只取官方网站、大媒体、政策页和 X 新闻号**，聚合页链接会被 `validate.py` 拦下；抖音、小红书等平台只用于「玩法风向」和机会。
- **机会卡门槛**：打开过的收入证据 + 3 个竞品 + 5 条链接，凑不够就空着。前三期复盘发现证据少的机会没用。
- **用法只写外贸、SEO、自媒体、做产品四个方向**；安全「黄」只给要权限或凭证的、建仓不到 30 天的。
- **整期 6000 字左右，超过 7000 字校验不过**：他在手机上扫读。
- **跨期去重**：`fetch.py` 给前 7 天写过的条目标 `seen_before`，没有变化的不再写，有变化的进「跟进」栏。
- **五条长期主线**在 `config/tracks.json`，2026-10-17 定下，计划看一周后再调。
- 脚本只用 Python 标准库，Actions 里不装依赖。
- 仓库是公开的（免费账号的 Pages 和 Actions 时长要求），所以数据和收藏夹别人能看到；**任何密钥都只放在 GitHub Secrets 和 Cloudflare 后台，不写进仓库**。

更细的原因写在各次提交说明里（`git log`），每条规则在 `prompts/daily.md` 里也附了依据。

## 改代码时注意

- 机器人每天往 main 提交 `data/daily/`、`data/favorites/`、`data/deepdive/`。改代码前先拉最新的 main。
- 本地自测（不用任何密钥）：
  - `python3 scripts/validate.py data/daily/<某天>.json`：校验一期（会就地补编号，先复制一份再试）。
  - `python3 scripts/build_site.py --single preview.html --preview`：生成单页预览。
  - `python3 scripts/fetch.py --date <日期>`：抓素材，没有密钥时只抓公开来源。
- 线上试跑：Actions → 每日日报 → Run workflow（手动运行总会重新生成当天这期并立刻推送）；只试飞书用「飞书推送测试」；只试 TikHub 用「TikHub 试抓」。
- 每次运行第一步「检查配置」把缺了哪些密钥写在运行摘要页。AI 那一步失败时，`scripts/claude_error.py` 把错误原因打在日志里。

## 换成别的 AI

写作标准（`prompts/daily.md`、`prompts/deepdive.md`）是普通中文说明，任何能干活的代理都能照着做；里面的 `WebSearch`、`WebFetch` 指「上网搜索」「打开网页」。和 Claude 绑定的只有三处：

1. `daily.yml`「Claude 写日报」和 `favorite.yml`「Claude 深挖」两步用的是 `anthropics/claude-code-action@v1`，`--allowedTools` 里是 Claude Code 的工具名。
2. 两个工作流里「检查配置」「准备 Claude 令牌」两步只认 `CLAUDE_CODE_OAUTH_TOKEN`、`ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY`，没有就停。
3. `scripts/claude_error.py` 读的是 Claude Code 的运行记录格式。

换的时候把这三处换成对应代理的 GitHub Action，提示词照旧，例如：

| 代理 | Action | 密钥 | 要注意 |
|---|---|---|---|
| OpenAI Codex | `openai/codex-action@v1`，`prompt` 写法同现在，`sandbox: workspace-write` | `OPENAI_API_KEY` | 默认沙箱可能不让联网，要打开网页搜索和网络访问，第一次接时手动跑一次确认 |
| Google Gemini | `google-github-actions/run-gemini-cli` | Gemini API Key | 自带网页搜索和打开网页工具；它默认读 `GEMINI.md`，可以配置成读 `AGENTS.md` |
| 经 OpenRouter 用别家模型 | 不换 Action，只改 `DAILY_MODEL` 为 OpenRouter 的模型名 | `OPENROUTER_API_KEY` | Claude Code 配非 Claude 模型不保证能用，搜索等工具可能失效，不推荐 |

换完先手动跑一期，确认三件事：`validate.py` 通过；机会卡和 Skills 安全检查里的链接真的打开过；字数和条数接近之前几期。写作质量取决于模型，`DAILY_MODEL` 默认 `sonnet`，深挖默认 `opus`。

只想用不带工具的普通对话接口（一次请求出一份 JSON）也行，但要先把「打开网页核实链接、找收入证据、读 SKILL.md 做安全检查」这些事挪到脚本里做，再把核实结果放进素材，这是较大的改造。

## 还没定的事（2026-10-19）

- `TRUSTMRR_API_KEY`（可选）还没申请；没有时机会卡的收入证据由 AI 自己找。
- X「实践者」组还要加仓库主人常看的中文外贸、跨境电商账号（`config/sources.json` 的 `x.accounts`）。
- Cloudflare Worker：`config/site.json` 的 `worker_url` 还空着（仓库变量 `WORKER_URL` 填了则以它为准），Worker 本身也还没部署，所以网站和飞书上的收藏、深挖按钮都不可用；`ACTION_KEY` 已在仓库 secrets 里。2026-10-19 已把部署步骤（`docs/setup.md` 第 7、8 步）交给仓库主人，等他在 Cloudflare 上操作。没配时网站点收藏会提示去看配置指南，每次运行的「检查配置」摘要也会列出。
- 另一个飞书群（2026-10-20）：仓库主人想让家人的飞书个人账号也收日报。脚本已支持 `FEISHU_WEBHOOK_2`，等他用电脑版飞书建外部群、加自定义机器人，把地址和密钥存进 secrets（`docs/setup.md` 第 4 步）。
- 机会研究是否换更强的模型、周六是否出周报，还没定。2026-10-17 到 10-19 三期机会卡都是 0 条，整期也只有约 3000 字（目标 6000）：门槛是对的，但默认的 `sonnet` 在一次写日报里凑不齐收入证据、三个竞品和五条链接。可选做法是机会研究拆成单独一步、用 `opus`（要多花订阅额度），等仓库主人定。
