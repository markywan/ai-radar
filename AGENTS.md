# 接手说明（给接手的人和 AI）

> **如果你是被每日任务叫来写日报、深挖或周报的，只按 `prompts/daily.md`、`prompts/deepdive.md` 或 `prompts/weekly.md` 做，这份文件不用看。**
> 这份文件给要维护、修改或迁移这个仓库的人和编程代理（Claude Code、Codex、Gemini CLI、Cursor 等）。

这个仓库每天自动出一期「AI 机会雷达」日报，只有三样：一人公司出海机会、GitHub、Skills。2026-11-26 起日报的目标是**每天把机会池往前推一步**：今天只做一件事、今日机会 0–1 个（7 条门槛 + 100 分）、GitHub 3–5 个、Skills 2–4 个；机会池在 `data/opportunities/`。流程：GitHub Actions 抓素材 → 一个 AI 代理按写作标准写成 JSON → 脚本校验、配图、进池子 → 75 分以上且池子里没有在验证的，更强的模型写 7 天验证设计 → 发布到 GitHub Pages → 推送飞书。每周六另出周报。读者是仓库主人一个人（一人公司创业者，背景见 `prompts/daily.md` 第一段）。用户怎么用、栏目是什么见 `README.md`，后台要填什么见 `docs/setup.md`。

## 每天怎么跑

| 步骤 | 文件 | 要 AI 吗 | 要什么密钥 |
|---|---|---|---|
| 定时触发：北京时间 1:23 到 6:23 每小时一次（共六次），当天已有日报就跳过 | `.github/workflows/daily.yml` | 否 | — |
| 补种子进机会池 | `scripts/pool.py seed`、`config/opportunity_seeds.json` | 否 | — |
| 抓素材，写 `data/raw/<日期>.json`（不提交）和 GitHub 日榜快照 `data/trending/<日期>.json`（提交，用来算连续上榜天数）；按星期轮的主线、这条线的页面和数据（TED、SAM.gov、Apify Store）、机会池现状也放进素材 | `scripts/fetch.py`、`config/sources.json`、`config/tracks.json` | 否 | X、TrustMRR、SAM.gov 都可选，缺了只跳过那部分 |
| **写日报，写 `data/daily/<日期>.json`** | `prompts/daily.md` | **是**，要能读写文件、上网搜索和打开网页、运行 `validate.py` 后按提示改 | Claude 令牌（见 `docs/setup.md` 第 3 步）；主令牌失败时自动改用备用 `ANTHROPIC_API_KEY` 重写一次 |
| 从 README 配图 | `scripts/enrich.py` | 否 | — |
| 校验和编号，算总分和 `verdict`，75 分以上在 `pick` 字段记下 B01 | `scripts/validate.py` | 否 | — |
| 今日机会进池子（60 分以上；推进已有项目的写 `pool_ref`），把 `pool_id` 写回日报 | `scripts/pool.py add-daily` | 否 | — |
| 提交日报和池子到 main | `daily.yml` 的「提交」步 | 否 | — |
| 找今日机会：没有 `pick`、池子里有「验证中」、已深挖过的都跳过 | `scripts/today_pick.py` | 否 | — |
| **写验证设计，写 `data/deepdive/<日期>-B01.md`，末尾「池子卡片」由 `pool.py card` 写回池子，一起提交**（失败或超时不挡发布） | `prompts/deepdive.md`、`daily.yml` 的「Claude 深挖今日机会」「提交深挖」步 | **是**，默认 `opus`（`DEEPDIVE_MODEL`），最多 40 分钟 | 同上 |
| 建站 | `publish.yml`、`scripts/build_site.py`、`web/` | 否 | — |
| 推飞书，定时任务等到 7 点再发 | `scripts/notify_feishu.py` | 否 | `FEISHU_WEBHOOK`、`FEISHU_SECRET` |
| 停更提醒：每天 9:30 查最新一期，前天或更早的就推飞书 | `.github/workflows/watchdog.yml` | 否 | 同上 |
| 周六周报：`metrics.py` 算信源转化，AI 写 `data/weekly/<日期>.md`，发布后推飞书 | `weekly.yml`、`prompts/weekly.md`、`scripts/metrics.py` | **是**（`DAILY_MODEL`） | 同写日报 |

收藏和深挖：网站或飞书上的按钮 → Cloudflare Worker（`worker/worker.js`）核对 `ACTION_KEY` → 触发 `favorite.yml` → `favorite.py` 存进 `data/favorites/`；池子状态按钮（`op=status`，「开始验证」「继续观察」「淘汰」「已启动」等）走同一个 Worker 和 `favorite.yml`，由 `pool.py set` 改状态；深挖时 AI 按 `prompts/deepdive.md` 写 `data/deepdive/<编号>.md`。这条也要 AI。收藏今日机会时，`favorite.py` 看到当天已有深挖就直接标成已深挖，不再重挖。

**只有「写日报」「深挖」（每天的今日机会、收藏后的深挖）和「周报」用 AI，其余全是 Python 标准库脚本，换 AI 不用动。**

## 格式契约

- 日报 JSON 的结构写在 `prompts/daily.md` 的「输出」一节，`scripts/validate.py` 是最终裁判：必填字段、条数范围、门槛和分数、枚举值（`area`、`stage`、`from`、`safety`、`license_tier`、证据 `type`）、链接、字数上限。网站（`web/app.js`）和飞书卡片（`notify_feishu.py`）都按这个结构读。改结构时四处一起改：`prompts/daily.md`、`validate.py`、`web/app.js`、`notify_feishu.py`。
- 2026-11-26 起的日报带 `"format": 3`（`validate.py` 写），网站和飞书按新版显示；没有这个字段的是老日报：11-01 到 11-25 有 3–5 个候选和 `actions`，11-01 以前还有 `news`（N）、`trends`（P）、`followups`。老日报照原样显示，不要删，也不再校验。
- 编号（`B01`、`S02`、`G03`…）、`pick`、`score.total`、`verdict`、`track`、`format` 由 `validate.py` 补，`pool_id` 由 `pool.py add-daily` 补，AI 不写。收藏、深挖都靠「日期-编号」找条目，已发布的日报不要重新编号。
- 机会池每个项目一个文件 `data/opportunities/<编号>.json`（种子 `seed-xxx`，日报来的 `日期-B01`），结构见 `scripts/pool.py` 开头。深挖报告末尾的「池子卡片」是一段 json 代码块，`pool.py card` 读它；网站显示深挖时会把这段去掉。

## 已定的规则和原因

改这些之前先问仓库主人。

- **日报改成「每天把机会池往前推一步」**（2026-11-26 仓库主人在综合策划上选了「四步一起做」，策划见 https://claude.ai/artifact/QkcH5KJYLvEzipkkhLsD6N ）。原因：11-01 到 11-25 每天 3–5 个候选 100% 来自 TrustMRR 上别人做大的 SaaS，6 篇深挖全是「照抄不做、收窄到外贸版」；目标函数奖励的是别人的收入，不是他够不够得着渠道、收不收得到钱、有没有直接需求。具体：
  - 今日机会 0–1 个，先过 7 条硬门槛（MVP ≤14 天、起步 ≤$500、稳定后每周 ≤3 小时、不重销售不定制、有够得着的渠道、大陆个人收得到钱、至少一条直接需求证据），再按 100 分打分（需求和付费证据 25、获客渠道 25、经验匹配 20、自动化 15、7 天首单路径 10、收款合规 5）。75 分以上且池子里没有「验证中」才深挖，60–74 分进池子待研究，不到 60 分不进日报、写进 `leads`。没有合格的就写「今天没有合格的」，不凑数。
  - Show HN、Product Hunt、V2EX、X 只当线索；TrustMRR 每天最多 1 个候选、只算别人的收入基准，都不能单独当直接需求证据（`validate.py` 查证据域名）。
  - 五条主线按星期轮（`config/tracks.json` 的 `rotation`）：周一全球贸易、周二 SEO与GEO、周三供需撮合、周四海外宣传、周五图文自媒体、周六复盘（不出新机会）、周日对标。每条线那天看的页面和抓的数据在 `config/sources.json` 的 `track_sources`。
  - 深挖改成 7 天验证设计（三个窄切口对比、最可能错的假设、第一批 10 个客户、样品和报价、7 天实验和停止条件），保留收款、合规、90 天五道关，末尾「池子卡片」写回池子。
  - 机会池一次只验证 1 个，开始验证新的会把旧的自动改成暂停。收藏是动作，不是状态。仓库公开，池子只存脱敏的状态和数字。
  - GitHub 3–5 个，七成以上来自主线话题或 issue 需求，标 `stage`（工具链哪一环）和 `pairs_with`（和收藏里哪个搭）；没有 issue 需求或同类收入证据不许写「做托管版」。Skills 2–4 个，第一个是「本周装这个」。正文 1500 字左右，超过 3000 字校验不过。
- **主令牌失效时自动用备用密钥**（2026-11-26）：11-08 到 11-25 订阅令牌被吊销，日报停了 18 天。现在主令牌失败、配了 `ANTHROPIC_API_KEY` 就用它重写一次（按量付费），飞书卡片最上面提醒换令牌；另有 `watchdog.yml` 每天 9:30 查，两天没日报单独推一条。

- **7 点前做好、7 点推送**：他早上起来看。GitHub 定时任务常晚到很久（2026-10-31 到 11-02 每次都晚近 3 小时），加上每天要深挖今日机会，所以从 1:23 到 6:23 每小时排一次（2026-11-02 从 4:23 起的三次改成六次）；6 点前失败不发失败通知，等下一次重跑，6 点后还失败才通知。
- **日报只做三样**（2026-11-01 仓库主人定）：一人公司出海机会（高效、能自动化的那种）、GitHub 热门仓库、Skills。不写 AI 资讯，不用 TikHub 搜抖音、小红书（`platforms.py` 和「TikHub 试抓」已删），玩法风向和跟进栏也去掉了；X 只抓实践者账号和机会、Skills 相关的搜索。原因：他只要创业机会和能拿来用的工具，之前说过不看资讯，但一直没改到位。
- **机会分两步**（2026-11-01 到 11-25，已被上面的机会池取代，留作历史）：写日报时找 3–5 个候选（至少 1 个），每个要有打开过的、带数字的收入证据，2 条以上链接，点名的竞品，`validate.py` 检查；第一个候选是今日机会，由单独一步用更强的模型按 `prompts/deepdive.md` 深挖，网站和飞书卡片把深挖结论放在最前面。原因：10-17 定的门槛（收入证据 + 3 个竞品 + 5 条链接，凑不够就空）让 `sonnet` 在一次写日报里从没凑齐过，10-17 到 11-01 连续 16 期机会都是 0。深挖过的机会不再当今日机会（素材里的 `deepdived`，`validate.py` 也会拦）。
- **用法只写外贸、SEO、自媒体、供需、宣传、做产品六个方向**（2026-10-30 从四个扩到六个，跟着他转做海外生意）；安全「黄」只给要权限或凭证的、建仓不到 30 天的。
- **整期 1500 字左右（2026-11-26 起，深挖报告另算），超过 3000 字校验不过**：他在手机上扫读。11-01 到 11-25 是 5000 字以内。
- **跨期去重**：`fetch.py` 给前 7 天写过的条目标 `seen_before`，没有明显变化（星数翻倍、大版本、新的收入数字）的不再写。
- **五条长期主线**在 `config/tracks.json`，2026-10-17 定下，2026-10-20 把「AI短视频」换成「AI小工具」。2026-10-30 仓库主人转做「一个人做海外生意」，主线整个换成他的五个方向：全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传；小工具、托管版和 API 是五个方向共用的产品形态，不再单列，Claude Code、Codex 和 Skills 的更新归 Skills 栏。
- **不做视频内容创业**（2026-10-20 仓库主人定）：AI 漫剧、faceless、数字人、AI UGC 这类靠生产视频赚钱的机会不写；视频工具只在本身好用时当工具收，每期最多 1 个。之前抖音、小红书搜回来的多是视频生意，他觉得太窄。
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
  - `python3 scripts/pool.py summary`：看机会池；`python3 scripts/metrics.py --no-write`：看信源转化。
  - `python3 scripts/notify_feishu.py daily <日期>`：不配 `FEISHU_WEBHOOK` 时只打印卡片 JSON。
- 线上试跑：Actions → 每日日报 → Run workflow（手动运行总会重新生成当天这期并立刻推送；第一个候选没变就不重新深挖，变了且旧深挖没被收藏就删掉重挖）；只试飞书用「飞书推送测试」。
- 每次运行第一步「检查配置」把缺了哪些密钥写在运行摘要页。AI 那一步失败时，`scripts/claude_error.py` 把错误原因打在日志里。

## 换成别的 AI

写作标准（`prompts/daily.md`、`prompts/deepdive.md`）是普通中文说明，任何能干活的代理都能照着做；里面的 `WebSearch`、`WebFetch` 指「上网搜索」「打开网页」。和 Claude 绑定的只有三处：

1. `daily.yml` 的「Claude 写日报」（含备用密钥那步）「Claude 深挖今日机会」、`weekly.yml` 的「Claude 写周报」和 `favorite.yml` 的「Claude 深挖」用的是 `anthropics/claude-code-action@v1`，`--allowedTools` 里是 Claude Code 的工具名。
2. 两个工作流里「检查配置」「准备 Claude 令牌」两步只认 `CLAUDE_CODE_OAUTH_TOKEN`、`ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY`，没有就停。
3. `scripts/claude_error.py` 读的是 Claude Code 的运行记录格式。

换的时候把这三处换成对应代理的 GitHub Action，提示词照旧，例如：

| 代理 | Action | 密钥 | 要注意 |
|---|---|---|---|
| OpenAI Codex | `openai/codex-action@v1`，`prompt` 写法同现在，`sandbox: workspace-write` | `OPENAI_API_KEY` | 默认沙箱可能不让联网，要打开网页搜索和网络访问，第一次接时手动跑一次确认 |
| Google Gemini | `google-github-actions/run-gemini-cli` | Gemini API Key | 自带网页搜索和打开网页工具；它默认读 `GEMINI.md`，可以配置成读 `AGENTS.md` |
| 经 OpenRouter 用别家模型 | 不换 Action，只改 `DAILY_MODEL` 为 OpenRouter 的模型名 | `OPENROUTER_API_KEY` | Claude Code 配非 Claude 模型不保证能用，搜索等工具可能失效，不推荐 |

换完先手动跑一期，确认三件事：`validate.py` 通过；机会候选的收入证据和 Skills 安全检查里的链接真的打开过；今日机会的深挖写出来了；字数和条数接近之前几期。写作质量取决于模型，`DAILY_MODEL` 默认 `sonnet`，深挖默认 `opus`。

只想用不带工具的普通对话接口（一次请求出一份 JSON）也行，但要先把「打开网页核实链接、找收入证据、读 SKILL.md 做安全检查」这些事挪到脚本里做，再把核实结果放进素材，这是较大的改造。

## 还没定的事（2026-11-26）

- **合并后要做**：Cloudflare Worker 要把新的 `worker/worker.js` 重新粘一次，池子状态按钮才能用；建议在 Secrets 加 `ANTHROPIC_API_KEY` 当备用。
- 机会池以后搬到飞书多维表格（可以填客户和报价、不公开），还是一直放仓库（只存脱敏状态），还没定。
- 招标种子做哪个品类还没定：`config/sources.json` 的 `ted.keywords`、`sam_gov.keywords` 先放了 LED、太阳能、医疗耗材、包装、家具，定了换成那个品类。`SAM_GOV_API_KEY` 还没申请。
- TED 搜索接口的查询语法（`ted.query`）和 Apify Store 接口是按官方文档写的，写代码的环境连不上这两个站，第一次跑后看「errors」里有没有报错。
- 跑满 30 天（约 2026-12-26）后按 `metrics.py` 的信源转化表删掉不出货的来源。
- `TRUSTMRR_API_KEY`（可选）还没申请。
- X「实践者」组还要加仓库主人常看的中文外贸、跨境电商账号（`config/sources.json` 的 `x.accounts`）。
- Cloudflare Worker：2026-10-21 已部署并测通（`https://ai-radar-act.markyradar2.workers.dev`，写在 `config/site.json` 的 `worker_url`；仓库变量 `WORKER_URL` 填了则以它为准）。注意：`*.workers.dev` 在国内不开代理基本打不开，按钮要开着代理点；以后想不开代理也能点，备选是飞书多维表格工作流，见项目文件 `ai-radar-analysis/飞书一键收藏方案比较-2026-10-21.md`。可选的 KV（已读状态多设备同步）没配。
- 每天用 `opus` 深挖一次比原来多花订阅额度；现在只有 75 分以上且没有在验证的项目时才深挖，次数会少很多。额度紧时把仓库变量 `DEEPDIVE_MODEL` 改成 `sonnet`。
