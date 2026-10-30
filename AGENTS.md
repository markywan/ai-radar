# 接手说明（给接手的人和 AI）

> **如果你是被每日任务叫来写日报或深挖的，只按 `prompts/daily.md` 或 `prompts/deepdive.md` 做，这份文件不用看。**
> 这份文件给要维护、修改或迁移这个仓库的人和编程代理（Claude Code、Codex、Gemini CLI、Cursor 等）。

这个仓库每天自动出一期「AI 机会雷达」日报：GitHub Actions 抓素材 → 一个 AI 代理按写作标准写成 JSON → 脚本校验、配图 → 发布到 GitHub Pages → 推送飞书。读者是仓库主人一个人（一人公司创业者，背景见 `prompts/daily.md` 第一段）。用户怎么用、栏目是什么见 `README.md`，后台要填什么见 `docs/setup.md`。

## 每天怎么跑

| 步骤 | 文件 | 要 AI 吗 | 要什么密钥 |
|---|---|---|---|
| 定时触发：北京时间 4:23、5:23、6:23 各一次，当天已有日报就跳过 | `.github/workflows/daily.yml` | 否 | — |
| 抓素材，写 `data/raw/<日期>.json`（不提交）和 GitHub 日榜快照 `data/trending/<日期>.json`（提交，用来算连续上榜天数） | `scripts/fetch.py`、`scripts/platforms.py`、`config/sources.json` | 否 | X、TikHub、TrustMRR 都可选，缺了只跳过那部分 |
| **写日报，写 `data/daily/<日期>.json`** | `prompts/daily.md` | **是**，要能读写文件、上网搜索和打开网页、运行 `validate.py` 后按提示改 | Claude 令牌（三选一，见 `docs/setup.md` 第 3 步） |
| 从 README 配图 | `scripts/enrich.py` | 否 | — |
| 校验和编号 | `scripts/validate.py` | 否 | — |
| 提交到 main、建站 | `daily.yml` 的「提交」步、`publish.yml`、`scripts/build_site.py`、`web/` | 否 | — |
| 推飞书，定时任务等到 7 点再发 | `scripts/notify_feishu.py` | 否 | `FEISHU_WEBHOOK`、`FEISHU_SECRET` |

收藏和深挖：网站或飞书上的按钮 → Cloudflare Worker（`worker/worker.js`）核对 `ACTION_KEY` → 触发 `favorite.yml` → `favorite.py` 存进 `data/favorites/`；深挖时 AI 按 `prompts/deepdive.md` 写 `data/deepdive/<编号>.md`。这条也要 AI。

**只有「写日报」和「深挖」两步用 AI，其余全是 Python 标准库脚本，换 AI 不用动。**

## 格式契约

- 日报 JSON 的结构写在 `prompts/daily.md` 的「输出」一节，`scripts/validate.py` 是最终裁判：必填字段、条数范围、枚举值（`tier`、`group`、`area`、`safety`、`verdict`、`signal`、`license_tier`）、链接、字数上限。网站（`web/app.js`）和飞书卡片都按这个结构读。改结构时三处一起改：`prompts/daily.md`、`validate.py`、`web/app.js`（飞书卡片在 `notify_feishu.py`）。
- 编号（`N01`、`G02`、`B01`…）由 `validate.py` 补，AI 不写。收藏、深挖、跟进栏都靠「日期-编号」找条目，已发布的日报不要重新编号。

## 已定的规则和原因

改这些之前先问仓库主人。

- **7 点前做好、7 点推送**：他早上起来看。GitHub 定时任务常晚到一两个小时，所以排三次；前两次失败不发失败通知，6 点后那次也失败才通知。
- **资讯只取官方网站、大媒体、政策页和 X 新闻号**，聚合页链接会被 `validate.py` 拦下；抖音、小红书等平台只用于「玩法风向」和机会。
- **机会卡门槛**：打开过的收入证据 + 3 个竞品 + 5 条链接，凑不够就空着。前三期复盘发现证据少的机会没用。
- **用法只写外贸、SEO、自媒体、供需、宣传、做产品六个方向**（2026-10-30 从四个扩到六个，跟着他转做海外生意）；安全「黄」只给要权限或凭证的、建仓不到 30 天的。
- **整期 6000 字左右，超过 7000 字校验不过**：他在手机上扫读。
- **跨期去重**：`fetch.py` 给前 7 天写过的条目标 `seen_before`，没有变化的不再写，有变化的进「跟进」栏。
- **五条长期主线**在 `config/tracks.json`，2026-10-17 定下，2026-10-20 把「AI短视频」换成「AI小工具」。2026-10-30 仓库主人转做「一个人做海外生意」，主线整个换成他的五个方向：全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传；小工具、托管版和 API 是五个方向共用的产品形态，不再单列，Claude Code、Codex 和 Skills 的更新归 Skills 栏。
- **不做视频内容创业**（2026-10-20 仓库主人定）：AI 漫剧、faceless、数字人、AI UGC 这类靠生产视频赚钱的玩法和机会不写，TikHub 关键词也不再监测这些；视频工具只在本身好用时当工具收，每期最多 1 个。之前抖音、小红书搜回来的多是视频生意，他觉得太窄。
- **GitHub 榜单先由脚本预筛**：`fetch.py` 给日榜、周榜上的仓库补许可证、最后提交、fork 比例，记每日快照算前 7 天上榜天数，标出 HN、X 上同时出现的；没许可证、已归档、30 天没提交的标 `skip`。原因：星数只反映热度，单日暴涨里营销和围观多，连续上榜和有人讨论的才可能真有人用。
- **GitHub 按「能拿它做什么生意」挑**（2026-10-30 起，仓库主人在研究报告第六节第一批上点了「全做」）：
  - 候选仓库（日榜、行业话题、新项目）补许可证三档：能托管来卖（MIT、Apache、BSD、GPL 这类）、托管要公开改动（AGPL 这类）、不能托管来卖（BUSL、Elastic、SSPL、非商用）。GitHub 认不出的（NOASSERTION）读 LICENSE 原文按字样猜，猜的会标出来让 AI 核对。
  - 用 GitHub 2026-09-04 新出的星数历史接口（`/repos/{owner}/{repo}/stargazers/history`）补最近 7 天每天的增星，单日暴涨的标出来查刷星。
  - 日榜加中文区日榜（`spoken_language_code=zh`），两边对照找海外在火、中文圈还没写的；HelloGitHub 月刊 RSS 总留最新一期。新项目雷达一次取 100 个。
  - issue 需求榜（`raw.issue_demand`）：每天搜「要托管版」「愿意付钱」两类 issue，再查收藏过的仓库里点赞最多、还开着的 5 条。短语必须配 `in:title`，不然混进大量无关结果；「愿意付钱」排除 Claude Code、Codex 的额度抱怨。
  - 工具卡必填 `business`（能做什么生意，40 字以内）和 `license_tier`，可选 `demand`（issue 标题、链接、点赞数）和 `stars_7d`；网站和飞书卡片都显示。
  - 每天的 GitHub 搜索约 30 次，搜索接口每分钟最多 30 次，所以脚本每次搜索隔 2 秒；用 Actions 自带的 `GITHUB_TOKEN` 就够。
  - 不做的：抓 github.com 的搜索网页（robots.txt 禁止）；用 OSS Insight 趋势榜（2026-03-01 起没数据）；抓 star 用户名单（2026-07 起只有仓库管理员能看）。
- **Reddit RSS 不用了**：Reddit 2026-11-13 停 RSS，r/SideProject、r/microsaas 两个源 2026-10-30 去掉；机会候选改从 Show HN、Product Hunt、V2EX、acquire 和 issue 需求榜找。
- **深挖报告末尾三段固定写**：大陆个人怎么收款（先用 Creem 或 Dodo 这类代收平台，回款万里汇，不急着注册公司）、合规红线（发信、LinkedIn、WhatsApp、抓数据、开源许可证）、90 天五道关的过关数字。
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

## 还没定的事（2026-10-30）

- `TRUSTMRR_API_KEY`（可选）还没申请；没有时机会卡的收入证据由 AI 自己找。
- X「实践者」组还要加仓库主人常看的中文外贸、跨境电商账号（`config/sources.json` 的 `x.accounts`）。
- Cloudflare Worker：2026-10-21 已部署并测通（`https://ai-radar-act.markyradar2.workers.dev`，写在 `config/site.json` 的 `worker_url`；仓库变量 `WORKER_URL` 填了则以它为准）。原子域 `markywan916` 在 Cloudflare 一直签不出证书，改名为 `markyradar2` 后一分钟就好了。`ACTION_KEY` 10-21 换过，Worker 和仓库 secrets 一致。注意：`*.workers.dev` 在国内不开代理基本打不开，按钮要开着代理点；以后想不开代理也能点，备选是飞书多维表格工作流（卡片按钮由飞书服务器调 GitHub），见项目文件 `ai-radar-analysis/飞书一键收藏方案比较-2026-10-21.md`。可选的 KV（已读状态多设备同步）没配。
- 2026-10-25 提的日报改版方案还在等仓库主人选（卡片在项目的主线程里：每天深挖、隔天深挖、不自动深挖、先不改）：砍资讯、TikHub 平台搜索、玩法风向和跟进栏，每天深挖一个机会，Skills 加到约 5 个，X 只留实践者。选了再改 `prompts/daily.md`、`validate.py`、`web/app.js` 和飞书卡片。
- GitHub 挖掘第二批等第一批跑两周（约 2026-11-13）后再定：Skills 趋势榜、按 SKILL.md 内容搜外贸和开发信类 Skill（代码搜索要一个只读令牌）、awesome 清单的新增条目、每周一份 GitHub 需求周报（可以并进周六周报）。
- 机会研究是否换更强的模型、周六是否出周报，还没定。2026-10-17 到 10-19 三期机会卡都是 0 条，整期也只有约 3000 字（目标 6000）：门槛是对的，但默认的 `sonnet` 在一次写日报里凑不齐收入证据、三个竞品和五条链接。可选做法是机会研究拆成单独一步、用 `opus`（要多花订阅额度），等仓库主人定。
