# AI 机会雷达

每天北京时间 7 点前自动出一期日报，发到 GitHub Pages 网站，并推送到飞书。**2026-11-26 起日报的目标是每天把机会池往前推一步**，不再是每天找一堆新机会：只做三样（一人公司出海机会、GitHub、Skills），不写 AI 资讯，正文 1500 字左右。

| 栏目 | 每天 | 内容 |
|---|---|---|
| 今天只做一件事 | 1 件 | 池子里有「验证中」的项目就是它的下一步；没有就是今日机会验证的第一步；再没有就是从排队的里挑一个开始验证，或者装本周的 Skill。下面一行是池子状态和到期提醒 |
| 今日机会 | 0–1 个 | 只从当天轮到的主线里找（周一全球贸易、周二 SEO与GEO、周三供需撮合、周四海外宣传、周五图文自媒体、周六复盘、周日对标）。必须是窄假设（卖给谁、什么痛、交付什么、多少钱、第一批客户从哪来），先过 7 条硬门槛，再按 100 分打分。75 分以上、池子里又没有在验证的，由 Opus 做成 7 天验证设计；60–74 分进池子待研究；不够就写「今天没有合格的」和查过的线索 |
| GitHub | 3–5 个 + 日榜速览 3 条 | 七成以上来自五个方向的话题和 issue 需求，每个标出补工具链的哪一环（找客户、抓数据、写内容、发布、收款客服、监控）、和收藏里的哪个搭着用。没有需求证据不许写「做托管版」 |
| Skills | 2–4 个 | 第一个是「本周装这个」，带安装命令 |

**机会池**（网站「池子」页，`data/opportunities/`）：待研究 → 待验证 → 验证中 → 已启动 → 已变现，另有暂停、淘汰；一次只验证一个。起步放了 13 个种子（10-26 研究报告和 11 月深挖里收窄出来的外贸切口）。飞书卡片和网站上有「开始验证」「继续观察」「淘汰」等按钮。每周六出一份周报：这周验证过没过、池子变化、下周只做哪个实验、工具链缺哪一环、各主线和信源出了什么。

五条长期主线在 `config/tracks.json`，按星期轮的表也在那里。每条都能「收藏」；机会、工具和 Skill 还能「收藏并深挖」。2026-11-26 以前的日报照原来的栏目显示。

## 怎么运转

```
每天 01:23 起 ─ daily.yml（Worker 定时器 1:23、3:23、5:23 准点启动，GitHub 定时兜底，7 点推飞书）
   ├ pool.py seed 补种子 → fetch.py 抓素材（今天这条主线的页面和数据：TED 招标、SAM.gov、Apify Store；GitHub 榜单、话题、issue 需求榜；Skills；线索；机会池现状）
   ├ Claude（Sonnet）按 prompts/daily.md 写日报（主令牌失败时自动改用备用 ANTHROPIC_API_KEY）
   ├ enrich.py 配图 → validate.py 校验门槛和分数 → pool.py add-daily 今日机会进池子 → 提交
   ├ 75 分以上且没有在验证的：Claude（Opus）按 prompts/deepdive.md 写验证设计 → pool.py card 把「池子卡片」写回池子
   └ publish.yml 发布网站 → 飞书卡片
每天 09:30 ─ watchdog.yml：最新一期是前天或更早的，单独推一张「已经 N 天没有新日报」
每周六 08:00 ─ weekly.yml：metrics.py 算信源转化 → Claude 按 prompts/weekly.md 写周报 → 发布 → 飞书

点「收藏 / 收藏并深挖 / 开始验证…」─ Cloudflare Worker 核对口令 ─ 触发 favorite.yml
   ├ 收藏：favorite.py 存进 data/favorites/（深挖时 Claude 写 data/deepdive/编号.md）
   └ 池子状态：pool.py set 改 data/opportunities/编号.json
```

| 文件 | 作用 |
|---|---|
| `config/sources.json` | 信息源：每条主线要看的页面和抓的数据（`track_sources`、`ted`、`sam_gov`、`apify`）、GitHub 榜单和话题、issue 需求榜、Skills、X、TrustMRR |
| `config/tracks.json` | 五条主线和按星期轮的表 |
| `config/opportunity_seeds.json` | 机会池的种子 |
| `prompts/daily.md` | 日报的写作标准（门槛、打分、栏目、红线） |
| `prompts/deepdive.md` | 深挖：机会写成 7 天验证设计，末尾一段「池子卡片」；工具和 Skill 写怎么拿它赚钱 |
| `prompts/weekly.md` | 周六周报 |
| `scripts/` | 抓取、校验、机会池（`pool.py`）、信源统计（`metrics.py`）、收藏、建站、飞书推送，只用 Python 标准库 |
| `web/` | 网站页面（手机优先，深浅色自动切换） |
| `worker/worker.js` | 收藏和池子状态按钮的中转服务，部署到 Cloudflare Workers |

## 每月花费

| 项目 | 花费 |
|---|---|
| Claude | 用你的 Claude 订阅额度（Pro / Max），或者 Anthropic API / OpenRouter 按量付费。每天一次写日报（Sonnet）加一次深挖今日机会（Opus，和点一次「收藏并深挖」一样） |
| X 抓取（twitterapi.io） | 每天最多 600 条推文，实际约 250 条，约 1 美元/月 |
| GitHub Actions、Pages | 公开仓库免费 |
| Cloudflare Workers | 免费额度够用 |
| 飞书机器人 | 免费 |

## 配置

完整步骤见 [`docs/setup.md`](docs/setup.md)。要接手维护、修改或换成别的 AI，先看 [`AGENTS.md`](AGENTS.md)。要填的东西：

**仓库 Settings → Secrets and variables → Actions → Secrets**

| 名字 | 从哪来 |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | 本机运行 `claude setup-token` 得到（用订阅额度）；或者改填 `ANTHROPIC_API_KEY`，或者 OpenRouter 的 Key 填成 `OPENROUTER_API_KEY`（前两个都没有时才用，按量计费） |
| `TWITTERAPI_IO_KEY` | twitterapi.io 后台的 API Key |
| `ANTHROPIC_API_KEY` | 建议配上当备用：主令牌失效时自动改用它（按量付费），日报不停 |
| `TRUSTMRR_API_KEY` | 可选。TrustMRR 网站免费申请的 API Key |
| `SAM_GOV_API_KEY` | 可选。SAM.gov 免费注册后申请，周一全球贸易那天抓美国政府采购招标 |
| `FEISHU_WEBHOOK` | 飞书群 → 设置 → 群机器人 → 自定义机器人 的 Webhook 地址 |
| `FEISHU_SECRET` | 同一个机器人勾选「签名校验」后给的密钥 |
| `ACTION_KEY` | 自己编一串 30 位以上的随机字符，Worker 里填同一串 |

**不是密码的设置写在 `config/site.json`**：网站地址 `site_url`（已填 `https://markywan.github.io/ai-radar/`）和收藏接口地址 `worker_url`（部署好 Worker 后填上）。也可以在同一页的 Variables 里填同名的 `SITE_URL`、`WORKER_URL`，仓库变量优先。可选变量 `DAILY_MODEL`（写日报，默认 `sonnet`）、`DEEPDIVE_MODEL`（深挖今日机会和收藏后的深挖，默认 `opus`）。`TIKHUB_API_KEY` 2026-11-01 起不用了，可以在 Secrets 里删掉。

**Settings → Pages → Source** 选 GitHub Actions。

**Cloudflare Worker** 只要填两个密钥：`GITHUB_TOKEN`（细粒度令牌，只授权这个仓库，Contents 读写）和 `ACTION_KEY`。仓库名和网站地址在 `worker.js` 里有默认值。

每天运行时第一步会检查配置，结果写在那次运行的摘要页；缺 Claude 令牌会直接停下并说明原因，缺 X、TrustMRR 或飞书只跳过对应部分。

## 手动运行

- 立刻出一期：Actions → 每日日报 → Run workflow
- 手动收藏或深挖：Actions → 收藏与深挖 → Run workflow，填编号（如 `2026-11-02-B03`）
- 手动改池子状态：同一个任务，编号填池子编号（如 `seed-tender-digest`），「改机会池状态」填 `验证中`、`淘汰` 等
- 立刻出周报：Actions → 周六周报 → Run workflow；看信源统计：`python3 scripts/metrics.py`
- 本地预览：`python3 scripts/build_site.py --single preview.html --preview`，用浏览器打开 `preview.html`

## 注意

- 公开仓库的网站和数据所有人都能看到，包括收藏夹和机会池。池子里只放脱敏的状态和数字，客户名单、报价、订单放在别处。收藏和深挖按钮要口令，别人点不了。
- X 抓取的上限在 `config/sources.json` 的 `x.max_tweets`，想更省就调小；不填 `TWITTERAPI_IO_KEY` 时自动跳过 X，其他来源照常。2026-11-01 起只抓「实践者」组和机会、Skills 相关的搜索，AI 新闻号和 AI 热议搜索停了。
- 今日机会的深挖失败或超时（比如订阅额度用完）不影响日报发布：网站上写「深挖报告还没出来」，点「收藏并深挖」能补一份。
