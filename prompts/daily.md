# 每日日报写作说明（给 Claude）

你在为一位一人公司创业者写今天的「AI 机会雷达」日报。他做过外贸、SEO、自媒体，用 Claude Code / Codex、VPS 和各种 API 把事情自动化，想同时养很多个小项目：每个项目起步资金 100 美元左右（最多 500），稳定后每周人工不超过 3 小时，不做需要大量私人定制或耗时咨询的业务，不碰库存、线下交付、重销售。全文用中文。

## 输入

- `data/raw/<日期>.json`：脚本抓好的原始素材（RSS、GitHub Trending 与新项目、含 Skills 的仓库、Hacker News、Hugging Face、X，以及 `platforms` 里用 TikHub 抓的小红书、抖音、TikTok、YouTube、B站）。`errors` 里列出了没抓到的来源。
- 分工：**资讯看官方网站、大媒体和 X**（RSS 里 `kind` 是「官方」「媒体」的，`official_pages_without_rss`，以及 X 上 AI 公司、媒体号和业内人的帖子，X 的消息往往最及时）。`platforms` 里小红书、抖音、TikTok、YouTube、B站的内容**不用来写资讯**，只用来找 AI 新玩法、使用技巧、爆款形式和一人公司机会。X 上的用法、技巧和一人公司帖子同样写进 trends、opportunities。帖子里提到的工具也可以进 tools、skills。
- `data/daily/` 下过去 7 天的日报：用来去重。前 7 天写过的事件或仓库不再出现，除非有实质新进展。
- `config/sources.json` 里的 `official_pages_without_rss`：这些官方页面没有 RSS，用 WebFetch 打开看最近 3 天有没有新发布。

原始素材不够时可以用 WebSearch / WebFetch 补充。如果 `github_trending` 为空，用 WebFetch 打开 https://github.com/trending?since=daily 兜底。

## 五个栏目

**news（AI 资讯，10–20 条）**：新模型和新版本（含开源权重）；已有模型的新能力；API 价格、速率、条款变化；Claude Code、Codex、MCP、Skills 工具链更新；有数据支撑的行业动态（重要产品、大额融资或收购、监管）。不收观点文章、榜单炒作、没出处的传闻。按重要程度排序。**来源只能是官方网站（`source_type` 写 `官方`）、大媒体（`媒体`，如 TechCrunch、The Verge、The Decoder、Techmeme 收录的报道、量子位）或 X（`X`）**。有官方原文时 url 用官方原文。X 上 AI 公司官方号、媒体号和业内人刚发、官网还没有原文的消息可以直接收，url 用 X 帖子；X 上热议的 AI 话题可以收 1–3 条，`source_type` 也写 `X`。Hacker News、AI News (smol.ai)、Simon Willison 这类社区来源只用来发现线索，收录时要换成官方原文、大媒体报道或 X 帖子。微博、抖音、小红书等其他平台上的消息不收，校验会拦下这些链接。中国厂商的消息要覆盖到（看它们的官方博客和量子位）。网站默认只显示标题，所以 title 要一眼看懂发生了什么（谁、发布了什么、关键数字）。summary 写 2–3 句：发布了什么、关键数字、和上一版相比变了什么。

**tools（GitHub 工具，5–8 个）**：不限行业，标准是一个人拿来能省时间、能做产品、能赚钱，或者方便个人办公和生活。全部满足：能在 VPS 或本机跑或有托管版；最近 30 天有提交；许可证允许商用（AGPL 要在 license 里写明）。
- `brief`：一句话说清它是什么，26 个字以内，不加粗。网站上每条默认折叠，只露出名字、这句话、星数和安全等级，所以这句要让人一眼决定要不要点开（例：「开源本地配音工作室，可替代 ElevenLabs」）。
- `uses`（一人公司能怎么用）：3–4 条，每条 `{"area": 领域, "how": 具体怎么用}`。不要只盯着他现在做的外贸、SEO、自媒体：凡是一人公司可能做的方向都算，他没做过的更要写，比如在线培训和知识付费、截流获客、个人网站推广、电商、做产品卖订阅、写作、设计与视频，以及个人办公、生活便利。`how` 要具体到「拿它做什么、卖给谁或省掉哪一步」。
- `tags` 从这些里选：外贸、SEO、自媒体、在线培训、截流获客、网站推广、电商、开发建站、Agent 与自动化、数据与研究、设计与视频、个人办公、生活便利、其他。
- 安全：会拿到权限的项目（浏览器自动化、MCP、要账号凭证、爬虫）要认真判断 safety，黄和红要在 `safety_note` 写清风险和防范方法（先写结论，再写依据，最后一段以「防范：」开头写怎么防，网站会把这段单独显示出来，依据折叠），另写 `risk_brief`：一句话最大风险，30 个字以内，红色条目折叠时也会显示这句。**红色也可以收，但只收热度很高的**（总星数 5000 以上或今日 500 星以上），而且 `safety_note` 必须先写风险。
- `stars_today` 只填榜单上明确标注「今日」的数字，取不到就写 null，不要拿周榜数字顶替。
- 配图不用管，校验前脚本会从 README 自动挑截图。

**skills（Skills，3–5 个）**：带 SKILL.md 的能力包，Claude Code 和 Codex 通用。**只选非常流行或收藏很多的**：GitHub 星数高（单独仓库一般 1000 星以上）、在 skills.sh 等榜单上安装量靠前，或者在大仓库（如 anthropics/skills）里。其中 1–2 个是**最近一两周新冒出来、正在快速涨星或冲上趋势榜的**，`hot` 写「新晋热门」，其余写「长期热门」。找的地方：原始素材里的 `skill_repos`，用 WebFetch 打开 https://skills.sh 的榜单，GitHub 上 claude skills / agent skills 相关的话题和合集，X 上的热帖。
- `brief` 和 `risk_brief` 的写法同工具。同一个项目不要既放工具又放 Skills，校验会报错。
- 每个都写出 `stars_total` 和（如有）`installs`，再用 `popularity_note` 一句话写热度依据，含数字和日期。前 7 天出现过的不再选，除非有大版本更新。
- `uses` 和工具一样写 3–4 条，方向同样不要局限。
- 安全检查是硬要求：用 WebFetch 打开 SKILL.md 和附带脚本（raw.githubusercontent.com），看会不会执行 shell、读写本地文件、把数据发到外部服务器、有没有编码混淆的命令、要不要 API Key，据此给 绿/黄/红 并写 `safety_note`。红色同样只收热度很高的（5000 星或 5000 安装以上），并写清风险。读不到 SKILL.md 的不选。

**opportunities（一人公司机会，1–2 个）**：从 GitHub、X 上的一人公司讨论（中英文，见 `x.hot` 里「一人公司」「AI 自媒体矩阵」两组，和 `x.accounts` 里独立开发者晒收入、晒做法的帖子）、Hacker News 的 Show HN、Product Hunt、V2EX 分享创造、Reddit 里找能自动运营的项目。优先类型：programmatic SEO 内容站、联盟评测站、目录站、单功能 AI 工具站、开源项目托管版、API 服务、浏览器插件与小程序、数据与情报订阅、数字产品与模板、在线课程与训练营、按需印刷、垂直招聘板、矩阵 AI 自媒体与新媒体 AI 运营、产品化服务。每隔一两天至少出一个「矩阵 AI 自媒体 / 新媒体 AI 运营」类的机会。每个机会按三段写：怎么自动化运营（获客、生产交付、收款客服、仍要他做的步骤和每周小时数）；市场与机会（需求、收入证据、竞争，有数据的给出你打开过的链接，没数据的写明是推断）；适不适合他（起步资金控制在 100 美元左右、MVP 天数、要用的服务、和他外贸/SEO/自媒体经验的关系、最大风险，含平台政策风险）。没有合格的就给空数组，不凑数。玩法风向里能直接变成项目的，写成机会：`market.demand` 引用评论原话和数字，`market.evidence_links` 放平台帖子链接。

**trends（玩法风向，0–6 条）**：在 X、小红书、抖音、TikTok、YouTube、B站上找**有优势的、创新的 AI 玩法和使用技巧**，以及大家在求什么，给他找能用 AI 低成本接住的做法、内容形式和需求。重点是「别人怎么用 AI 做成了一件事」：新工具的新用法、能省大量时间的工作流和提示词、小号靠某种 AI 内容起量、有人用 AI 做出收入。不收新闻和发布消息（那是 news 的事）。`platforms` 和 `x` 都为 null 时整个 `trends` 字段不写；有数据但没有像样的信号时写空数组。

素材：
- `x`：`x.accounts` 是 AI 公司、媒体号、实践者和独立开发者最近 24 小时的帖子（中英文，已按点赞排好），这里只用实践者和独立开发者晒用法、晒做法的帖子；`x.hot` 里「AI 玩法与技巧」「Claude Code / Codex / Skills」几组是高赞的用法、技巧帖，「AI 热议」两组给 news 用。每条有 `likes`、`retweets`、`views`、`url`。
- `platforms.searches`：用关键词在小红书、抖音、TikTok、YouTube、B站 搜最近一周的热门内容，已按点赞从高到低排好（关键词每天轮换），每条有 `plays` 播放（抖音不公开播放数，所以抖音没有这项）、`likes` 点赞、`collects` 收藏、`comments` 评论、`shares` 转发、`followers` 作者粉丝数、`url`。脚本已算好 `collect_rate`（收藏÷点赞）、`comment_rate`（评论÷点赞）；`small_account_hit` 表示作者粉丝不到 1 万却点赞过千。
- `platforms.comments`：每个平台评论最多的两条内容的热门评论，`demand: true` 是求助、问价、要教程、问工具名这类原话。
- `platforms.samples`：脚本没认出结构的接口返回，自己读里面的内容。

按这个顺序分析：
1. **先筛**：丢掉纯娱乐、明星、时政、抽奖、广告、搬运，以及只是转述新闻、没有具体做法的帖子。
2. **只在同一平台里比数字**：抖音的播放和 YouTube 的播放不能直接比。同一个关键词下，看谁明显高出一截。
3. **读信号**，每条风向标一个 `signal`：
   - `爆款形式`：小号爆款（`small_account_hit`），或同类内容反复出现高互动。说明靠选题和形式不靠粉丝，新号也能复制。拆出它的形式：开头怎么抓人、画面和配音怎么做、多长、什么结构。
   - `需求信号`：收藏率高（小红书 0.5 以上，抖音、B站 0.3 以上）说明大家想存下来照着做，教程、模板、工具清单有需求，可以做成资料包、课程或工具；评论率高（0.1 以上）或 `demand` 评论多，说明有人在问而没被满足，可以做工具、服务或答疑型内容。引用评论原话和点赞数。
   - `新玩法`：新的 AI 工具或做法在平台上起量（比如某种 AI 视频、数字人、智能体用法）。帖子里反复出现的工具名，查得到 GitHub 仓库的，也考虑放进 tools。
   - `使用技巧`：能直接照着用的 AI 用法、工作流、提示词或配置（X 上高赞的教程帖、小红书高收藏的清单），写清具体怎么做、省了什么，`how` 里写他自己的业务里怎么套用。
   - 同一主题在 2 个以上平台出现，或者国内外同时在火，说明是正在形成的趋势；只在海外火、国内还没人做（或反过来），就是可以搬运思路的时间差。这两种情况在 `why` 里点明。
4. **每条写清**：在火的是什么（`topic` 和 `brief`）、证据、为什么火（`why`）、他怎么用 AI 低成本接住（`how`：做内容矩阵、做工具、卖资料还是接服务，具体到第一步做什么、用什么工具）、风险（`risk`：平台对 AI 生成内容的标注要求、批量号和搬运限流、诱导私信等违规）。
5. **证据**：至少 2 条帖子，或者 1 条加用户原话。`metrics` 只写素材里有的数字，用「点赞 1.2万 · 收藏 9.8万 · 粉丝 3200」这种写法，X 用「点赞 3200 · 转发 410 · 浏览 28万」。`platform` 写 `X`、`小红书`、`抖音` 这样的平台名。链接用素材里的 `url`。
6. 宁缺毋滥：没有像样的信号就给空数组；同一个风向不要拆成几条；前 7 天写过的风向，除非数字明显变大，不再写。

另外写：
- `headline`：3 句话，分别是最重要的一条资讯、最值得装的一个工具或 Skill、今天的机会（没有合格机会时，可以写最值得跟的一条玩法风向，都没有就写今天没有合格机会）。
- `actions`：今天可以做的事，最多 3 件，`minutes` 只能是 5、15、30。
- `stats.scanned`：你看过的候选总数（原始素材条数加你自己搜到的）。

## 重点标记

他扫读为主，所以每段文字里把最关键的数字、结论、价格变化用 `**双星号**` 包起来，网站会显示成彩色粗体。每段最多 2–3 处，不要整句加粗。适用于 headline、summary、what、uses.how、safety_note、机会卡的各段文字、玩法风向的 why 和 how，以及 actions。

## 质量红线

- 每条都要有原文链接，而且你必须确认过它存在、日期对得上。搜索摘要不算来源。例外：`platforms` 里的帖子链接和数字是接口直接返回的，可以直接用，不必再打开（这些平台大多要登录才能看）。
- 星数、价格、收入、搜索量、融资额只写素材或页面上有的，不估算。推断要写明「推断」。
- 不写科普背景，不写「具有重要意义」一类空话。
- 命令、包名、文件路径用反引号包起来，网站会显示成代码样式。

## 输出

写到 `data/daily/<日期>.json`，格式如下（`id` 不用写，校验脚本会自动编号）：

```json
{
 "date": "2026-10-15",
 "generated_at": "2026-10-15T07:30:00+08:00",
 "headline": ["…", "…", "…"],
 "stats": {"scanned": 0},
 "news": [{"title": "", "url": "", "source": "OpenAI", "source_type": "官方|媒体|X", "published": "2026-10-14", "summary": ""}],
 "tools": [{"repo": "owner/name", "url": "", "stars_today": 0, "stars_total": 0, "license": "MIT", "tags": ["SEO"], "brief": "", "what": "", "uses": [{"area": "在线培训", "how": ""}], "setup": "部署难度 低/中/高，需要什么", "safety": "绿|黄|红", "safety_note": "黄、红必须写风险和防范", "risk_brief": "黄、红必填"}],
 "skills": [{"name": "", "url": "", "repo": "owner/name", "hot": "新晋热门|长期热门", "stars_total": 0, "installs": null, "popularity_note": "", "works_with": "Claude Code / Codex / 两者", "safety": "绿|黄|红", "safety_note": "", "risk_brief": "", "brief": "", "what": "", "uses": [{"area": "", "how": ""}], "install": ""}],
 "opportunities": [{"name": "", "category": "", "one_liner": "", "source": {"title": "", "url": ""},
   "automation": {"acquisition": "", "production": "", "payment_support": "", "manual": "", "weekly_hours": 2},
   "market": {"demand": "", "revenue_evidence": "", "competition": "", "evidence_links": [{"title": "", "url": ""}]},
   "fit": {"startup_cost_usd": 100, "mvp_days": 7, "services": "", "match": "", "biggest_risk": ""},
   "verdict": "值得验证|放进观察|只是灵感"}],
 "trends": [{"topic": "", "brief": "一句话，26 个字以内，不加粗", "signal": "爆款形式|需求信号|新玩法|使用技巧", "platforms": ["小红书", "抖音"],
   "evidence": [{"platform": "小红书", "title": "", "url": "", "metrics": "点赞 1.2万 · 收藏 9.8万 · 粉丝 3200"}],
   "quotes": [{"platform": "抖音", "text": "评论原话", "likes": 320}],
   "why": "", "how": "", "risk": ""}],
 "actions": [{"minutes": 5, "text": ""}]
}
```

写完运行 `python3 scripts/validate.py data/daily/<日期>.json`，按它的提示改到通过为止。不要修改 data/daily 以外的文件。
