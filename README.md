# AI 机会雷达

每天北京时间 7 点前自动出一期日报，发到 GitHub Pages 网站，并推送到飞书。2026-11-01 起日报只做三样：**一人公司出海机会**（几个候选，每天深挖一个）、**GitHub 热门仓库**、**Skills**；不写 AI 资讯，不用 TikHub 搜抖音、小红书。整期 5000 字以内（深挖报告另算），刊头标出读完要几分钟。栏目按这个顺序：

| 栏目 | 每天 | 内容 |
|---|---|---|
| 今天做什么 | 1–3 件 | 5 / 15 / 30 分钟能做完的事，第一条是今天最值得做的 |
| 今日机会 | 1 个 | 候选里最值得做的那个。日报写好后由更强的模型（默认 Opus）深挖：怎么做、客户、获客定价、自动化架构、大陆个人怎么收款、合规红线、90 天过关数字。网站上直接露出深挖结论，完整报告折在卡片里；飞书卡片也放结论和「看深挖报告」按钮 |
| 机会候选 | 3–5 个（至少 1 个） | 已经有人在赚钱、一个人能自动化的出海生意，起步 100 美元左右；每个要有打开过的收入证据、2 条以上链接、点名的竞品。想细看哪个，点「收藏并深挖」 |
| Skills | 4–6 个 | 流行的 SKILL.md 能力包，安装量来自 skills.sh，附安全检查 |
| GitHub 工具 | 3–8 个 | 分「大家都在用」和「刚冒出来」，每个标明为什么今天入选、能拿它做什么生意、许可证能不能托管来卖、issue 里有没有人在要；用法写外贸、SEO、自媒体、供需、宣传、做产品六个方向 |

五条长期主线在 `config/tracks.json`，就是一个人做海外生意的五个方向（全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传），机会候选能挂上的会标出主线名。

每条都能「收藏」；机会、工具和 Skill 还能「收藏并深挖」：Claude 在云端研究这个项目怎么做、用在哪些场景、能实现什么、客户画像和未来走势，以及大陆个人怎么收款、合规红线和 90 天过关数字，写好后放进网站的收藏页，飞书通知你。收藏今日机会时直接接上当天那份深挖，不再重挖。

网站每条先只露出能做判断的一行：工具和 Skill 是名字、一句话简介、为什么今天入选、星数、安全等级和能用在哪些方向，右侧一张 README 截图；点开才看详细说明、全部配图、一人公司的用法和风险说明。红色条目不点开也会显示一行风险提示。栏目标题左侧有色条，滚动时停在顶部。今天这期没看会在「今日」上亮红点，往期在「历史」里分成没看的和看过的。2026-11-01 以前的日报照原来的栏目显示（有 AI 资讯、玩法风向和跟进）。

## 怎么运转

```
每天 04:23 起 ─ daily.yml（5:23、6:23 补跑，7 点推飞书） ─ fetch.py 抓素材（GitHub 日榜周榜、中文区日榜、他行业的话题、新项目、许可证三档、7 天增星和 issue 需求榜；skills.sh 榜和 Skills 仓库；机会线索：Product Hunt、V2EX、Show HN、X 实践者和一人公司搜索、TrustMRR；前 7 天写过的标 seen_before，深挖过的列在 deepdived）
                         └ Claude（Sonnet）按 prompts/daily.md 写日报 → enrich.py 从 README 配图 → validate.py 校验 → 提交 data/daily/日期.json
                         └ Claude（Opus）按 prompts/deepdive.md 深挖今日机会（第一个候选）→ 提交 data/deepdive/日期-B01.md
                         └ publish.yml 发布网站 → 飞书卡片

点「收藏 / 收藏并深挖」─ Cloudflare Worker 核对口令 ─ 触发 favorite.yml
                         └ favorite.py 存进 data/favorites/
                         └（深挖）Claude 按 prompts/deepdive.md 写 data/deepdive/编号.md
                         └ 发布网站 → 飞书通知
```

| 文件 | 作用 |
|---|---|
| `config/sources.json` | 所有信息源：机会线索的 RSS、GitHub 榜单和话题、issue 需求榜、Skills 来源、X 实践者账号和搜索词、每日 X 抓取上限 |
| `prompts/daily.md` | 日报的写作标准（栏目、数量、机会候选的条件、质量红线） |
| `prompts/deepdive.md` | 深挖报告的结构（今日机会每天自动深挖，收藏后点深挖也用它） |
| `scripts/` | 抓取、校验、收藏、建站、飞书推送，只用 Python 标准库 |
| `web/` | 网站页面（手机优先，深浅色自动切换） |
| `worker/worker.js` | 收藏按钮的中转服务，部署到 Cloudflare Workers；绑定 KV（变量名 `RADAR_KV`）后还能多设备同步已读状态 |

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
| `TRUSTMRR_API_KEY` | 可选。TrustMRR 网站免费申请的 API Key，有它机会候选的收入证据会自动抓 |
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
- 本地预览：`python3 scripts/build_site.py --single preview.html --preview`，用浏览器打开 `preview.html`

## 注意

- 公开仓库的网站和数据所有人都能看到，包括收藏夹。收藏和深挖按钮要口令，别人点不了。
- X 抓取的上限在 `config/sources.json` 的 `x.max_tweets`，想更省就调小；不填 `TWITTERAPI_IO_KEY` 时自动跳过 X，其他来源照常。2026-11-01 起只抓「实践者」组和机会、Skills 相关的搜索，AI 新闻号和 AI 热议搜索停了。
- 今日机会的深挖失败或超时（比如订阅额度用完）不影响日报发布：网站和飞书卡片上写「深挖没写出来」，点「收藏并深挖」能补一份。
