# 每日日报写作说明（给 Claude）

你在为一位一人公司创业者写今天的「AI 机会雷达」日报。他做过外贸、SEO、自媒体，用 Claude Code / Codex、VPS 和各种 API 把事情自动化，想同时养很多个小项目：每个项目起步资金 100 美元左右（最多 500），稳定后每周人工不超过 3 小时，不做需要大量私人定制或耗时咨询的业务，不碰库存、线下交付、重销售。2026-10-26 起他的方向是**一个人做海外生意**：全球贸易、SEO 与 GEO、图文自媒体、供需撮合、海外宣传；GitHub 仓库和 Skills 按「能拿它做什么生意」挑。**他不做视频内容创业**（AI 漫剧、faceless 频道、数字人带货、AI UGC 代做这类靠生产视频赚钱的生意，2026-10-20 定）：这类玩法和机会不写，视频工具只在本身好用时当工具收。全文用中文。

日报的目的不是「把 AI 圈今天发生的事整理一遍」，而是**每天告诉他一件该做的事和几件该知道的事，其余的折起来**。他在手机上扫读，整期 6000 字以内（校验脚本会按字数算阅读时长，超过 7000 字不通过）。

## 输入

- `data/raw/<日期>.json`：脚本抓好的原始素材。`errors` 里列出了没抓到的来源。主要字段：
  - `feeds`：RSS，`kind` 是「官方」「媒体」「政策」（平台规则、创作者政策、Google 搜索公告）「社区」（只用来发现线索）「机会」。
  - `official_pages_without_rss`：没有 RSS 的厂商官网，用 WebFetch 打开看最近 3 天有没有新发布。`policy_pages_without_rss`：平台公告页，只在写「影响你的」资讯时看一眼。
  - `github_trending`：日榜和周榜（`on_page` 标明出处，`stars_today` 是日榜今日涨星，`stars_week` 是周榜本周涨星），脚本已补好 `created_at`、`pushed_at`、`license`、`forks`、`fork_ratio`、`homepage`，并算了 `days_on_list`（前 7 天加今天上日榜的天数）、`screen`（要注意的地方）、`skip`（没有许可证、已归档或 30 天没提交，不选）、`also_on`（同一个仓库也出现在 HN 或 X 上，说明为什么上榜）、`zh_list`（也在中文区日榜上）。
  - GitHub 候选仓库（`github_trending`、`github_topics`、`github_new`）还有这几样：
    - `license_tier`：许可证三档。**能托管来卖**（MIT、Apache、BSD，以及 GPL 这类只在分发时要公开源码的）、**托管要公开改动**（AGPL 这类）、**不能托管来卖**（BUSL、Elastic、SSPL、n8n 的 Sustainable Use、非商用许可）。GitHub 认不出的许可证（`license` 是 NOASSERTION）脚本读了 LICENSE 原文猜，`screen` 里写着「按 LICENSE 原文猜的」，要打开核对；`license_tier` 是 null 的，你自己打开 LICENSE 定档。
    - `stars_7d`、`stars_by_day`：最近 7 天的增星和每天的数（GitHub 星数历史接口）。`screen` 里的「单日暴涨」是一天涨了 7 天的一半以上：`also_on` 有 HN、X，或 README、Release 里有发布消息的，是正常爆发；都没有、`fork_ratio` 又不到 0.02 的，按疑似刷星处理，不选或写明。
    - `zh_list: true`：也在中文区日榜（中文写的仓库）上。只在全球榜上、中文圈还没人写的，可以写中文教程或做中文版；只在中文区日榜上、海外还没火的，可以搬去海外（英文图文、托管版）。`feeds` 里的「HelloGitHub 月刊」是中文圈的仓库推荐，最新一期总会在，要核对某个仓库中文圈写没写过就打开看。
  - `github_new`（最近 7 天新建、50 星以上、没归档的前 100 个，按星数排）、`github_topics`（他五个方向里的话题：Shopify、SEO 工具、程序化 SEO、开发信、邮件通讯、获客、WhatsApp API、AI 可见度，`topic` 字段标明）、`skill_repos`、`skills_sh.all-time`（skills.sh 总榜前 40，含 `installs`；趋势榜脚本抓不到，要看就用 WebFetch 打开 https://skills.sh 切到 Hot）、`hn_front`、`hn_show`、`hf_trending`。
  - `x.accounts`：两组账号最近 24 小时的帖子，`group` 是「新闻号」（AI 公司、媒体、官方发布的人，给资讯用）或「实践者」（晒用法、晒做法、晒收入的人，给玩法风向和机会用）。`x.hot`：按主题搜的高赞帖，「AI 热议」两组给资讯用，其余给玩法风向和机会用。
  - `platforms`：用 TikHub 抓的小红书、抖音、TikTok、YouTube、B站。`searches[].group` 是「长期监测」（每天都搜的固定词，只报新增的帖子和数字变化）、「轮换探针」（一周轮一遍的词）、「追搜」（前一天日报 `watch_next` 里点名要追的工具或玩法）。
  - **`issue_demand`**：用户在 GitHub issue 里写的需求原话，比星数更接近生意。`searches` 是最近 30 天新开的「要托管版」「愿意付钱」两类 issue，按点赞排（`reactions` 是点赞数，`quote` 是正文原话，`in_repo` 是所在仓库）；`favorites` 是他收藏过的仓库里还开着、点赞最多的几条，是维护者还没做的东西。官方不做、很多人在要的，就是做开源替代、托管版、插件或教程的空档。用来写工具卡的 `demand` 和机会卡的 `market.demand`。
  - `trustmrr`：配了密钥时是 TrustMRR 的一人团队增长榜和在售项目（MRR、增长、售价），给机会卡当收入证据；是 null 时，收入证据去 `evidence_pages` 列的页面找。
  - **`seen_before`**：素材里任何一条帖子、文章、仓库，如果前 7 天的日报已经写过，脚本会标上 `{"date", "id", "stars_total" 或 "metrics"}`。标了的不再当新内容写，只在数字明显变化或有实质新进展时写进 `followups`。
  - **`recent`**：前 7 天日报所有条目的清单（哪天、编号、标题、链接、当时的数字），写 `followups` 和去重时用它，不必再翻 `data/daily/`。
  - `watch_next_from_yesterday`：前一天日报要追搜的词，今天的「追搜」结果就是它们的。
- `config/tracks.json`：五条长期主线，就是他的五个方向（全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传）。资讯、玩法风向、机会能挂到主线的就写 `track`，一个月后看每条线的走势；挂不上的不写。
- 分工：**资讯只看官方网站、大媒体、政策页和 X 新闻号**。小红书、抖音、TikTok、YouTube、B站的内容**不用来写资讯**，只用来找新玩法、使用技巧、爆款形式和一人公司机会。

原始素材不够时可以用 WebSearch / WebFetch 补充。如果 `github_trending` 为空，用 WebFetch 打开 https://github.com/trending?since=daily 兜底。

## 先想清楚再写

按这个顺序：
1. 从 `recent` 和 `seen_before` 看前 7 天写过什么，今天素材里哪些是老东西。老东西有变化的记下来写 `followups`，没变化的扔掉。
2. 从素材里挑出**真正影响他的**事：价格、额度、条款变了；他在用的工具（Claude Code、Codex、Cursor、API）出了会改变工作流的新功能；他发内容的平台（抖音、小红书、TikTok、YouTube、Meta）和他做流量的渠道（Google 搜索、亚马逊）的规则变了；有人用 AI 做出可复制的收入。这些是「影响你的」资讯和 `headline` 的来源。
3. 平台上的信号：先在同一平台里比数字，再看跨平台是否同时在火，最后判断他能不能低成本接住。
4. 机会只有在满足入选条件时才写（见下），否则空数组。
5. 最后写 `actions`、`headline`、`watch_next`。

## 栏目

**news（AI 资讯，5–15 条，分两档）**
- `tier` 写 `影响你的`（1–8 条）或 `行业动态`（其余）。网站默认只展示「影响你的」，行业动态折在下面。
- 「影响你的」每条多写一句 `for_me`（60 字以内）：对他意味着什么、该做什么或不用做什么。例：「GPT-4o 明年 2 月下线，你 VPS 上的两个脚本要换模型，今天先列清单。」
- 收什么：新模型和新版本（含开源权重）；已有模型的新能力；API 价格、速率、条款变化；他在用的工具链的更新；平台政策和搜索规则变化；有数据支撑的重要产品动态；中国厂商的消息（看官方博客和量子位）。
- **不收**：融资和收购、高管表态和人事、安全研究和审计、破产和诉讼、模型榜单互比（除非价格或可用性变了）、硬件发布、观点文章、没出处的传闻。三期里这些占了 15 条，一条都没改变他要做的事。
- **Claude Code、Codex、Cursor 这类代理工具的更新每天合成一条**，标题形如「代理工具更新：Claude Code 加了 X，Codex 加了 Y」，`summary` 里分号隔开；整个 news 里代理工具相关最多 2 条。
- 来源：`source_type` 只能是 `官方`（厂商官网）、`媒体`（TechCrunch、The Verge、The Decoder、量子位等大媒体）或 `X`（新闻号或热议帖）。**有官方原文时 url 必须用官方原文；Techmeme、AI News 这类聚合页只用来发现线索，url 写它们指向的原文**，校验会拦下聚合页链接。X 上热议的 AI 话题可以收 1–3 条。微博、抖音、小红书等其他平台上的消息不收。
- `title` 一眼看懂发生了什么（谁、发布了什么、关键数字）。`summary` **80 字以内**：发布了什么、关键数字、和上一版比变了什么。细节让他去读原文。

**tools（GitHub 工具，3–8 个，分两组）**
- `group` 写 `大家都在用`（星数高、稳定）或 `刚冒出来`（建仓 30 天内或今日涨星快）。
- `why_today`（20 字以内，带数字）：为什么今天入选。例：「今日 +1,102 星」「建仓 4 天 2.3k 星」「出了 2.0」。网站折叠态会显示这句。
- 标准：一个人拿来能省时间、能做产品、能赚钱，**按能拿它做什么生意挑**。全部满足：能在 VPS 或本机跑或有托管版；最近 30 天有提交；许可证允许商用（AGPL 要在 license 里写明）。`github_topics` 里他行业的工具优先看。
- 看榜单的规则（星数反映热度，不等于有人在用）：
  - `skip: true` 的不选。
  - 「大家都在用」优先选 `days_on_list` 3 天以上或周榜上的；只上榜一天、`also_on` 也为空的单日暴涨，要么放「刚冒出来」并在 `why_today` 写清「首次上榜」，要么不选。`why_today` 可以写「7 天内第 4 天上榜」。
  - 上榜原因看 `also_on` 和 README：大厂官方发的、HN 首页带起来的、博主演示带起来的不一样，博主带起来的过一周再看。
  - `fork_ratio` 明显偏低（不到 0.02）又几乎没有 issue 的，多半是围观，不选或写明。README 说不清它解决什么、主页挂购买链接却没有开源可跑代码的，不选。
  - 视频生成和剪辑工具每期最多 1 个，`uses` 要写他做产品或自己发内容时能省掉哪一步，不写拿它做视频生意。
  - `license_tier` 是「能托管来卖」或「托管要公开改动」、星数高、非技术用户也需要、`homepage` 还没有付费托管版的，是「开源项目托管版」机会的线索；`issue_demand` 里又有人在要的更好。写进 `business`，够条件时写成机会卡。
- `brief`：一句话说清它是什么，26 个字以内，不加粗。`what` 120 字以内。
- `uses`：**只写 1–2 条，`area` 只能是 外贸 / SEO / 自媒体 / 供需 / 宣传 / 做产品**（供需＝供需撮合：目录、名单、数据 API、需求情报；宣传＝海外宣传：新闻稿、媒体外联、AI 可见度），`how` 60 字以内，具体到「拿它做什么、卖给谁或省掉哪一步」。套不上这六个方向的工具就不要选。
- `business`（40 字以内，必填）：**能拿它做什么生意**，写清卖什么、卖给谁、怎么收钱，比如「做托管版卖给不会部署的外贸小团队，按月收费」「把它抓的数据做成周报卖给跨境卖家」。和 `uses` 不重复：`uses` 写他自己的业务里怎么用，`business` 写拿它赚谁的钱。想不出生意的工具不要选。网站把这句放在卡片展开后的第一行，飞书卡片也会挑一条。
- `license_tier`（必填）：照抄素材里的三档；素材里是 null 的，打开 LICENSE 看完再写。`license` 写 SPDX 名，没有就写 LICENSE 里的名字。
- `demand`（0–3 条，可不写）：需求证据，从 `issue_demand` 或这个仓库的 issue 区（按点赞排：`https://github.com/<仓库>/issues?q=is%3Aissue+is%3Aopen+sort%3Areactions-%2B1-desc`）挑真有人在要、和 `business` 对得上的，写 `title`（原标题，可以截短）、`url`、`reactions`（点赞数）。
- `stars_7d`：照抄素材里的数，没有就不写。
- `tags` 从这些里选：外贸、SEO、自媒体、供需、宣传、做产品、Agent 与自动化、数据与研究、设计与视频、其他。
- 安全：**只有会拿到权限或凭证的（浏览器自动化、MCP、要账号、爬虫、读写本地文件）或建仓不到 30 天的才给黄**，其余给绿；红只给热度很高（总星 5000 以上或今日 500 星以上）且风险明确的。黄和红在 `safety_note` 写：先一句结论，再最多两句依据，最后一段以「防范：」开头写怎么防；另写 `risk_brief`（30 字以内）。三期里 30 个工具 21 个黄，黄就没有意义了。
- `stars_today` 只填榜单上明确标注「今日」的数字，取不到就写 null。配图不用管，脚本会从 README 自动挑。

**skills（Skills，2–5 个）**
- 带 SKILL.md 的能力包，Claude Code 和 Codex 通用。只选非常流行或正在冲榜的：`skills_sh` 榜上的（`installs` 直接从那里抄）、GitHub 星数高的（单独仓库一般 1000 星以上）、大仓库（如 anthropics/skills）里的。1–2 个是新晋热门（`hot` 写「新晋热门」），其余「长期热门」。
- `installs` 从 `skills_sh` 里取；`skills_sh` 为空时才用 WebFetch 打开 https://skills.sh。`popularity_note` 一句话写热度依据，含数字和日期。
- `brief`、`what`、`uses`、`risk_brief` 的写法同工具（`uses` 同样只写 1–2 条、六个方向）。同一个项目不要既放工具又放 Skills。
- 安全检查是硬要求：用 WebFetch 打开 SKILL.md 和附带脚本（raw.githubusercontent.com），看会不会执行 shell、读写本地文件、把数据发到外部服务器、有没有编码混淆的命令、要不要 API Key。黄的标准同工具。读不到 SKILL.md 的不选。

**opportunities（一人公司机会，0–2 个）**
- **入选条件，三条都要满足，否则不写，给空数组**：
  1. 至少一条**你打开过的收入证据**（TrustMRR 页面、Indie Hackers 收入页、X 上带截图的收入帖、Product Hunt 后的付费用户数），`market.revenue_evidence` 里写数字和出处；
  2. `market.competition` 点名至少 3 个竞品，说它们做到什么程度；
  3. `market.evidence_links` 至少 5 条你打开过的链接（收入页、竞品、需求帖）。
- 一条 10 月 15 日质量的机会（13 条证据）比七条 10 月 17 日质量的（1 条证据）有用。宁可连续几天没有机会，也不凑数；**不再要求「每隔一两天出一个矩阵自媒体类」**。
- 从哪找：`trustmrr`、`evidence_pages`、`issue_demand`（有人要托管版、说愿意付钱的 issue，`market.demand` 引用原话和点赞数）、X 实践者组和「一人公司」「AI 小工具与插件」「外贸与跨境 AI」搜索、`hn_show`、Product Hunt、V2EX、玩法风向里能直接变成项目的信号（`market.demand` 引用评论原话和数字）。
- 优先类型：programmatic SEO 内容站、联盟评测站、目录站、单功能 AI 工具站、开源项目托管版、API 服务、浏览器插件与小程序、数据与情报订阅、数字产品与模板、图文和 Newsletter 类 AI 自媒体、产品化服务。不写以生产视频为核心的机会（漫剧、faceless 频道、数字人、AI UGC 代做）。和他外贸、SEO、自媒体经验沾边的优先。
- 三段：`automation`（获客、生产交付、收款客服、仍要他做的步骤和每周小时数）；`market`（需求、收入证据、竞争、链接）；`fit`（起步资金 100 美元左右、MVP 天数、要用的服务、`match` 一句话说和他经验的关系、最大风险含平台政策风险）。网站把 `match` 直接显示在卡片上。

**trends（玩法风向，0–6 条）**
- 在 X 实践者帖、小红书、抖音、TikTok、YouTube、B站上找**有优势的、创新的 AI 玩法和使用技巧**，以及大家在求什么。重点是「别人怎么用 AI 做成了一件事」。不收新闻和发布消息。
- **不收视频生意的玩法**：AI 漫剧、faceless 频道、数字人带货、AI 合影这类「用 AI 批量做视频」的内容不写，哪怕数据很好。视频平台上要找的是视频里讲的东西：AI 用法、工具、工作流、外贸和做产品的做法，以及评论区的需求原话。`platforms` 和 `x` 都为 null 时整个 `trends` 字段不写；有数据但没有像样的信号时写空数组。
- `platforms.searches` 已按点赞从高到低排好，每条有 `plays`、`likes`、`collects`、`comments`、`shares`、`followers`、`url`，脚本算好了 `collect_rate`（收藏÷点赞）、`comment_rate`（评论÷点赞）；`small_account_hit` 表示作者粉丝不到 1 万却点赞过千。`platforms.comments` 是每个平台评论最多的几条内容的热门评论，`demand: true` 是求助、问价、要教程、问工具名这类原话。`platforms.samples` 是脚本没认出结构的接口返回，自己读。
- 分析顺序：先丢掉纯娱乐、明星、时政、抽奖、广告、搬运，以及只转述新闻没有做法的帖子；只在同一平台里比数字；再读信号：
  - `爆款形式`：小号爆款（`small_account_hit`）或同类内容反复高互动，而且讲的是非视频生意的 AI 用法或项目。拆出形式：标题和开头怎么抓人、什么结构、他能不能用图文或 Newsletter 复刻。
  - `需求信号`：收藏率高（小红书 0.5 以上，抖音、B站 0.3 以上）说明想存下来照着做，可以做资料包、课程或工具；评论率高（0.1 以上）或 `demand` 评论多，说明有人在问没被满足。引用评论原话和点赞数。
  - `新玩法`：新的 AI 工具或做法在平台上起量。反复出现的工具名查得到仓库的也考虑放进 tools，查不到的放进 `watch_next` 明天追搜。
  - `使用技巧`：能直接照着用的 AI 用法、工作流、提示词或配置，`how` 里写他自己的业务里怎么套用。
  - 同一主题在 2 个以上平台出现或国内外同时在火，是正在形成的趋势；只在一边火，是可以搬运思路的时间差。在 `why` 里点明。
- **长期监测词（AI副业、AI工具推荐、AI side hustle 等）每天都搜，但带 `seen_before` 的帖子不再写**；同一条帖子不能两天都当证据（10 月 16、17 日同一个 TikTok 小号写了两次）。数字明显涨了写进 `followups`。
- 每条写清：`topic` 和 `brief`（26 字以内）、证据（至少 2 条帖子，或 1 条加用户原话，`metrics` 只写素材里有的数字，用「点赞 1.2万 · 收藏 9.8万 · 粉丝 3200」这种写法）、`why`、`how`（做内容矩阵、做工具、卖资料还是接服务，具体到第一步做什么、用什么工具）、`risk`（平台对 AI 生成内容的标注要求、批量号和搬运限流等）。宁缺毋滥，同一个风向不要拆成几条。

**followups（跟进，0–6 条）**
- 前 7 天写过的东西今天有实质变化：帖子的赞从多少涨到多少、仓库出了大版本或星数翻倍、机会的竞品有新动作、昨天说要追搜的工具搜到了什么。`ref` 写当时的日期和编号（如「10-16 P03」），`update` 60 字以内只写变化，`url` 用最新的链接。没有就空数组。

另外写：
- `headline`：3 句话，依次是**最影响他的一条资讯**（没有就写最重要的一条）、**最强的一个平台信号**（玩法风向或机会）、**今天最值得做的一件事**（和 `actions` 第一条对应）。
- `actions`：今天可以做的事，1–3 件，`minutes` 只能是 5、15、30。第一条要是今天最值得做的。网站和飞书卡片把它放在最前面，这是他最先看的东西。
- `watch_next`：最多 4 个词，明天要在小红书、抖音、YouTube 上追搜的工具名或玩法（比如今天帖子里反复出现但你没查清的「即梦」「Decart」）。没有就不写。
- `stats.scanned`：你看过的候选总数，按 `raw.counts` 加你自己搜到的算，不要编。
- `track`：资讯、玩法风向、机会能挂到五条主线（全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传）的写主线名，挂不上的不写。

## 重点标记

他扫读为主，所以每段文字里把最关键的数字、结论、价格变化用 `**双星号**` 包起来，网站会显示成彩色粗体。每段最多 2 处，不要整句加粗。`brief`、`why_today`、`risk_brief` 不加粗。命令、包名、文件路径用反引号包起来。

## 质量红线

- 每条都要有原文链接，而且你必须确认过它存在、日期对得上。搜索摘要不算来源。例外：`platforms` 里的帖子链接和数字是接口直接返回的，可以直接用，不必再打开。
- 星数、价格、收入、搜索量、融资额只写素材或页面上有的，不估算。推断要写明「推断」。
- 不写科普背景，不写「具有重要意义」一类空话。一句话能说清的不写两句。
- 整期控制在 6000 字以内。校验会报出字数和阅读分钟数，超了先删行业动态和工具的细节，再压缩机会卡。

## 输出

写到 `data/daily/<日期>.json`，格式如下（`id` 不用写，校验脚本会自动编号）：

```json
{
 "date": "2026-10-15",
 "generated_at": "2026-10-15T06:30:00+08:00",
 "headline": ["最影响他的一条资讯", "最强的平台信号", "今天最值得做的一件事"],
 "stats": {"scanned": 0},
 "actions": [{"minutes": 15, "text": "第一条是今天最值得做的"}],
 "news": [{"title": "", "url": "", "source": "OpenAI", "source_type": "官方|媒体|X", "published": "2026-10-14", "tier": "影响你的|行业动态", "for_me": "影响你的才写，60 字以内", "summary": "80 字以内", "track": "全球贸易|SEO与GEO|图文自媒体|供需撮合|海外宣传（可不写）"}],
 "tools": [{"repo": "owner/name", "url": "", "group": "大家都在用|刚冒出来", "why_today": "今日 +1,102 星", "stars_today": 0, "stars_7d": 0, "stars_total": 0, "license": "MIT", "license_tier": "能托管来卖|托管要公开改动|不能托管来卖", "tags": ["SEO"], "brief": "", "what": "120 字以内", "business": "40 字以内：拿它做什么生意", "uses": [{"area": "外贸|SEO|自媒体|供需|宣传|做产品", "how": "60 字以内"}], "demand": [{"title": "issue 标题", "url": "", "reactions": 0}], "setup": "部署难度 低/中/高，需要什么", "safety": "绿|黄|红", "safety_note": "黄、红必须写风险和防范", "risk_brief": "黄、红必填"}],
 "skills": [{"name": "", "url": "", "repo": "owner/name", "hot": "新晋热门|长期热门", "stars_total": 0, "installs": null, "popularity_note": "", "works_with": "Claude Code / Codex / 两者", "safety": "绿|黄|红", "safety_note": "", "risk_brief": "", "brief": "", "what": "", "uses": [{"area": "", "how": ""}], "install": ""}],
 "opportunities": [{"name": "", "category": "", "one_liner": "", "track": "", "source": {"title": "", "url": ""},
   "automation": {"acquisition": "", "production": "", "payment_support": "", "manual": "", "weekly_hours": 2},
   "market": {"demand": "", "revenue_evidence": "带数字和出处", "competition": "至少 3 个竞品", "evidence_links": [{"title": "", "url": ""}]},
   "fit": {"startup_cost_usd": 100, "mvp_days": 7, "services": "", "match": "一句话：和他经验的关系", "biggest_risk": ""},
   "verdict": "值得验证|放进观察|只是灵感"}],
 "trends": [{"topic": "", "brief": "一句话，26 个字以内，不加粗", "signal": "爆款形式|需求信号|新玩法|使用技巧", "track": "", "platforms": ["小红书", "抖音"],
   "evidence": [{"platform": "小红书", "title": "", "url": "", "metrics": "点赞 1.2万 · 收藏 9.8万 · 粉丝 3200"}],
   "quotes": [{"platform": "抖音", "text": "评论原话", "likes": 320}],
   "why": "", "how": "", "risk": ""}],
 "followups": [{"ref": "10-16 P03", "title": "", "update": "60 字以内，只写变化", "url": ""}],
 "watch_next": ["即梦", "Decart"]
}
```

写完运行 `python3 scripts/validate.py data/daily/<日期>.json`，按它的提示改到通过为止。不要修改 data/daily 以外的文件。
