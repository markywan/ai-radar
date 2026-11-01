# AI 机会雷达

每天北京时间 7 点前自动出一期日报，发到 GitHub Pages 网站，并推送到飞书。日报的目的是每天告诉你一件该做的事和几件该知道的事，其余的折起来；整期 6000 字左右，刊头标出读完要几分钟。栏目按这个顺序：

| 栏目 | 每天 | 内容 |
|---|---|---|
| 今天做什么 | 1–3 件 | 5 / 15 / 30 分钟能做完的事，第一条是今天最值得做的 |
| 玩法风向 | 0–6 条 | X、小红书、抖音、TikTok、YouTube、B站上的 AI 新玩法、使用技巧、爆款形式和需求信号，附帖子数字、评论原话和一人公司怎么接 |
| 一人公司机会 | 0–2 个 | 能全自动运营、起步 100 美元左右的项目；要有打开过的收入证据、3 个竞品、5 条链接才收，凑不够就空着 |
| 跟进 | 0–6 条 | 前 7 天写过的东西今天的变化：赞涨了多少、仓库出了什么版本 |
| AI 资讯 | 5–15 条 | 分「影响你的」（带一句「对你」）和「行业动态」（默认折叠）；只取官方网站、大媒体和 X，摘要 80 字以内；代理工具更新每天合成一条 |
| GitHub 工具 | 3–8 个 | 分「大家都在用」和「刚冒出来」，每个标明为什么今天入选、能拿它做什么生意、许可证能不能托管来卖、issue 里有没有人在要；用法写外贸、SEO、自媒体、供需、宣传、做产品六个方向 |
| Skills | 2–5 个 | 流行的 SKILL.md 能力包，安装量来自 skills.sh，附安全检查 |

五条长期主线在 `config/tracks.json`，就是一个人做海外生意的五个方向（全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传），条目能挂上的会标出主线名。

每条都能「收藏」；机会、工具和 Skill 还能「收藏并深挖」：Claude 在云端研究这个项目怎么做、用在哪些场景、能实现什么、客户画像和未来走势，以及大陆个人怎么收款、合规红线和 90 天过关数字，写好后放进网站的收藏页，飞书通知你。

网站每条先只露出能做判断的一行：资讯是标题，工具和 Skill 是名字、一句话简介、为什么今天入选、星数、安全等级和能用在哪些方向，右侧一张 README 截图；点开才看详细说明、全部配图、一人公司的用法和风险说明。红色条目不点开也会显示一行风险提示。栏目标题左侧有色条，滚动时停在顶部。今天这期没看会在「今日」上亮红点，往期在「历史」里分成没看的和看过的。

## 怎么运转

```
每天 04:23 起 ─ daily.yml（5:23、6:23 补跑，7 点推飞书） ─ fetch.py 抓素材（RSS 含平台政策页、GitHub 含他行业的话题、中文区日榜、许可证三档、7 天增星和 issue 需求榜、skills.sh 榜、HN、Hugging Face、X、TrustMRR，platforms.py 用 TikHub 抓内容平台；前 7 天写过的会标 seen_before）
                         └ Claude 按 prompts/daily.md 写日报 → enrich.py 从 README 配图 → validate.py 校验
                         └ 提交 data/daily/日期.json → publish.yml 发布网站 → 飞书卡片

点「收藏 / 收藏并深挖」─ Cloudflare Worker 核对口令 ─ 触发 favorite.yml
                         └ favorite.py 存进 data/favorites/
                         └（深挖）Claude 按 prompts/deepdive.md 写 data/deepdive/编号.md
                         └ 发布网站 → 飞书通知
```

| 文件 | 作用 |
|---|---|
| `config/sources.json` | 所有信息源：RSS、GitHub 榜单、X 账号和热议搜索词、每日 X 抓取上限；`tikhub` 里是各平台的热榜、搜索关键词池和每日请求上限 |
| `prompts/daily.md` | 日报的写作标准（栏目、数量、机会类型、质量红线） |
| `prompts/deepdive.md` | 深挖报告的结构 |
| `scripts/` | 抓取、校验、收藏、建站、飞书推送，只用 Python 标准库 |
| `web/` | 网站页面（手机优先，深浅色自动切换） |
| `worker/worker.js` | 收藏按钮的中转服务，部署到 Cloudflare Workers；绑定 KV（变量名 `RADAR_KV`）后还能多设备同步已读状态 |

## 每月花费

| 项目 | 花费 |
|---|---|
| Claude | 用你的 Claude 订阅额度（Pro / Max），或者 Anthropic API / OpenRouter 按量付费 |
| X 抓取（twitterapi.io） | 每天最多 600 条推文，约 1–3 美元/月 |
| 平台抓取（TikHub） | 每天约 31 次请求、上限 40 次，按每次 0.001 美元约 1 美元/月 |
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
| `TIKHUB_API_KEY` | TikHub 用户后台创建的 API Token |
| `TRUSTMRR_API_KEY` | 可选。TrustMRR 网站免费申请的 API Key，有它机会卡的收入证据会自动抓 |
| `FEISHU_WEBHOOK` | 飞书群 → 设置 → 群机器人 → 自定义机器人 的 Webhook 地址 |
| `FEISHU_SECRET` | 同一个机器人勾选「签名校验」后给的密钥 |
| `ACTION_KEY` | 自己编一串 30 位以上的随机字符，Worker 里填同一串 |

**不是密码的设置写在 `config/site.json`**：网站地址 `site_url`（已填 `https://markywan.github.io/ai-radar/`）和收藏接口地址 `worker_url`（部署好 Worker 后填上）。也可以在同一页的 Variables 里填同名的 `SITE_URL`、`WORKER_URL`，仓库变量优先。可选变量 `DAILY_MODEL`（默认 `sonnet`）、`DEEPDIVE_MODEL`（默认 `opus`）。

**Settings → Pages → Source** 选 GitHub Actions。

**Cloudflare Worker** 只要填两个密钥：`GITHUB_TOKEN`（细粒度令牌，只授权这个仓库，Contents 读写）和 `ACTION_KEY`。仓库名和网站地址在 `worker.js` 里有默认值。

每天运行时第一步会检查配置，结果写在那次运行的摘要页；缺 Claude 令牌会直接停下并说明原因，缺 X、TikHub 或飞书只跳过对应部分。

## 手动运行

- 立刻出一期：Actions → 每日日报 → Run workflow
- 手动收藏或深挖：Actions → 收藏与深挖 → Run workflow，填编号（如 `2026-10-15-B01`）
- 试抓 TikHub：Actions → TikHub 试抓 → Run workflow。只跑平台那部分（约 0.03 美元），日志里列出每个接口认出了几条、返回的结构，用来核对解析
- 本地预览：`python3 scripts/build_site.py --single preview.html --preview`，用浏览器打开 `preview.html`

## 注意

- 公开仓库的网站和数据所有人都能看到，包括收藏夹。收藏和深挖按钮要口令，别人点不了。
- X 抓取的上限在 `config/sources.json` 的 `x.max_tweets`，想更省就调小；不填 `TWITTERAPI_IO_KEY` 时自动跳过 X，其他来源照常。
- TikHub 的上限在 `tikhub.max_requests`；每个平台的关键词分三组：`monitor` 长期监测词每天都搜（日报只报新增和数字变化），`probe` 轮换探针每天按顺序取 `probe_per_day` 个，前一天日报 `watch_next` 里点名的工具会在 `fresh_platforms` 上追搜，加词不加钱。不填 `TIKHUB_API_KEY` 时自动跳过。X 账号分「新闻号」和「实践者」两组，前者给资讯，后者给玩法和机会；TikHub 只用来找玩法、技巧和机会，不当新闻源，各平台热搜榜已停用，配置留在 `tikhub._停用的热搜榜`。
