# 每日日报写作说明（给 Claude）

你在为一位一人公司创业者写今天的「AI 机会雷达」日报。他做过外贸、SEO、自媒体，用 Claude Code / Codex、VPS 和各种 API 把事情自动化，想同时养很多个小项目：每个项目起步资金 100 美元左右（最多 500），稳定后每周人工不超过 3 小时，不做需要大量私人定制或耗时咨询的业务，不碰库存、线下交付、重销售。2026-10-26 起他的方向是**一个人做海外生意**：全球贸易、SEO 与 GEO、图文自媒体、供需撮合、海外宣传；GitHub 仓库和 Skills 按「能拿它做什么生意」挑。**他不做视频内容创业**（AI 漫剧、faceless 频道、数字人带货、AI UGC 代做这类靠生产视频赚钱的生意，2026-10-20 定）：这类机会不写，视频工具只在本身好用时当工具收。全文用中文。

**2026-11-01 起日报只做三样**（他定的）：一人公司出海机会、GitHub 热门仓库、Skills。**不写 AI 资讯和新闻，不写玩法风向和跟进**。日报的目的是每天给他几个**已经有人在赚钱、他一个人能做的出海生意**，第一个会在你写完后被深挖成完整报告；再给几个能拿来做生意的仓库和 Skills。他在手机上扫读，整期 5000 字以内（校验脚本按字数算阅读时长，超过 7000 字不通过），机会的细节留给深挖报告。

## 输入

- `data/raw/<日期>.json`：脚本抓好的原始素材。`errors` 里列出了没抓到的来源。主要字段：
  - `feeds`：RSS。「Product Hunt」「V2EX 分享创造」（`kind` 是「机会」）是机会候选的线索；「HelloGitHub 月刊」是中文圈的仓库推荐，最新一期总会在，要核对某个仓库中文圈写没写过就打开看。
  - `github_trending`：日榜和周榜（`on_page` 标明出处，`stars_today` 是日榜今日涨星，`stars_week` 是周榜本周涨星），脚本已补好 `created_at`、`pushed_at`、`license`、`forks`、`fork_ratio`、`homepage`，并算了 `days_on_list`（前 7 天加今天上日榜的天数）、`screen`（要注意的地方）、`skip`（没有许可证、已归档或 30 天没提交，不选）、`also_on`（同一个仓库也出现在 HN 或 X 上，说明为什么上榜）、`zh_list`（也在中文区日榜上）。
  - GitHub 候选仓库（`github_trending`、`github_topics`、`github_new`）还有这几样：
    - `license_tier`：许可证三档。**能托管来卖**（MIT、Apache、BSD，以及 GPL 这类只在分发时要公开源码的）、**托管要公开改动**（AGPL 这类）、**不能托管来卖**（BUSL、Elastic、SSPL、n8n 的 Sustainable Use、非商用许可）。GitHub 认不出的许可证（`license` 是 NOASSERTION）脚本读了 LICENSE 原文猜，`screen` 里写着「按 LICENSE 原文猜的」，要打开核对；`license_tier` 是 null 的，你自己打开 LICENSE 定档。
    - `stars_7d`、`stars_by_day`：最近 7 天的增星和每天的数（GitHub 星数历史接口）。`screen` 里的「单日暴涨」是一天涨了 7 天的一半以上：`also_on` 有 HN、X，或 README、Release 里有发布消息的，是正常爆发；都没有、`fork_ratio` 又不到 0.02 的，按疑似刷星处理，不选或写明。
    - `zh_list: true`：也在中文区日榜（中文写的仓库）上。只在全球榜上、中文圈还没人写的，可以写中文教程或做中文版；只在中文区日榜上、海外还没火的，可以搬去海外（英文图文、托管版）。
  - `github_new`（最近 7 天新建、50 星以上、没归档的前 100 个，按星数排）、`github_topics`（他五个方向里的话题：Shopify、SEO 工具、程序化 SEO、开发信、邮件通讯、获客、WhatsApp API、AI 可见度，`topic` 字段标明）、`skill_repos`、`skills_sh.all-time`（skills.sh 总榜前 40，含 `installs`；趋势榜脚本抓不到，要看就用 WebFetch 打开 https://skills.sh 切到 Hot）。
  - `hn_show`：36 小时内 40 分以上的 Show HN，机会候选的线索。
  - `x`：`accounts` 是「实践者」组（晒做法、晒收入的独立开发者和一人公司）最近 24 小时的帖子；`hot` 是按主题搜的高赞帖：「Skills」给 Skills 栏，「一人公司」「AI 小工具与插件」「外贸与跨境 AI」「出海自动化生意」给机会候选。是 null 时表示今天没抓 X。
  - **`issue_demand`**：用户在 GitHub issue 里写的需求原话，比星数更接近生意。`searches` 是最近 30 天新开的「要托管版」「愿意付钱」两类 issue，按点赞排（`reactions` 是点赞数，`quote` 是正文原话，`in_repo` 是所在仓库）；`favorites` 是他收藏过的仓库里还开着、点赞最多的几条，是维护者还没做的东西。官方不做、很多人在要的，就是做开源替代、托管版、插件或教程的空档。用来写工具卡的 `demand` 和机会候选的 `market.demand`。
  - `trustmrr`：配了密钥时是 TrustMRR 的一人团队增长榜和在售项目（MRR、增长、售价），直接当收入证据；是 null 时，收入证据去 `evidence_pages` 列的页面找（TrustMRR、acquire.com、Product Hunt）。
  - **`seen_before`**：素材里任何一个仓库、链接，如果前 7 天的日报已经写过，脚本会标上 `{"date", "id", "stars_total"}`。标了的不再当新内容写，除非数字明显变化（星数翻倍、出了大版本、有了新的收入数字），变化写进 `why_today` 或 `revenue_evidence`。
  - **`recent`**：前 7 天日报所有条目的清单（哪天、编号、名字、链接、当时的数字），去重时用它，不必再翻 `data/daily/`。
  - **`deepdived`**：以前深挖过的条目（收藏后深挖的、每天自动深挖的今日机会）。这些不再当机会候选，尤其不能放第一个（校验会拦）。
- `config/tracks.json`：五条长期主线，就是他的五个方向（全球贸易、SEO与GEO、图文自媒体、供需撮合、海外宣传）。机会候选能挂到主线的就写 `track`，一个月后看每条线的走势；挂不上的不写。

原始素材不够时用 WebSearch / WebFetch 补充，找机会候选时一定要用。如果 `github_trending` 为空，用 WebFetch 打开 https://github.com/trending?since=daily 兜底。

## 先想清楚再写

按这个顺序：
1. 从 `recent`、`seen_before`、`deepdived` 看以前写过、深挖过什么，今天素材里哪些是老东西。
2. **先找机会候选，这是今天最重要的栏目，至少一半的功夫花在这里**。10 月 17 日到 11 月 1 日连续 16 期机会一个都没有，原因是写日报时没去查收入证据。每个候选至少打开两个页面核实。
3. 再挑工具和 Skills。
4. 最后写 `actions`、`headline`。

## 栏目

**opportunities（一人公司出海机会候选，3–5 个，至少 1 个）**
- 收什么：**已经有人在赚钱、他一个人能做的出海生意**。出海是客户在海外、收美元；高效自动化是获客、生产交付、收款客服都能交给脚本、AI 和 VPS 上的定时任务，稳定后每周 3 小时以内。起步资金 100 美元左右，最多 500。
- **第一个（B01）是今日机会**：你写完日报后，会有更强的模型按 `prompts/deepdive.md` 把它深挖成完整报告（怎么做、客户、获客定价、自动化、收款、合规、90 天过关数字），网站和飞书卡片把它放在最前面。所以 B01 放你认为**最值得他做**的那个：收入证据最硬、和他外贸、SEO、自媒体的经验最沾边、最能自动化、`deepdived` 里没有。其余按值得程度往下排。
- **入选条件**（校验会查，凑不够就换一个候选）：
  1. 至少一条**你打开过的收入证据**：TrustMRR 的项目页、Indie Hackers 的收入页、acquire.com 的挂牌（MRR、售价）、X 上带截图或数字的收入帖、产品公布的付费用户数、定价页加用户数。`market.revenue_evidence` 写数字和出处。估算、搜索摘要都不算。
  2. `market.evidence_links` 至少 2 条你打开过的链接：收入证据页，加上来源帖、竞品或需求帖。
  3. `market.competition` 点名 1–3 个在做同样事的产品，一句话说它们做到什么程度；细的留给深挖。
- 从哪找：
  - `trustmrr`，或用 WebFetch 打开 `evidence_pages`：TrustMRR 一人团队增长榜和在售项目、acquire.com 在售项目，看 MRR、增长和售价，挑他五个方向里、一个人在做的。
  - `x.hot` 的「一人公司」「AI 小工具与插件」「外贸与跨境 AI」「出海自动化生意」，以及 `x.accounts` 实践者帖里晒收入、晒做法的。
  - `hn_show`、`feeds` 里的 Product Hunt 和 V2EX 分享创造：新上线的产品要找到它的收入或付费用户数才收。
  - `issue_demand`：有人要托管版、说愿意付钱的 issue，加上工具栏里 `business` 写的托管版、数据订阅机会；`market.demand` 引用原话和点赞数。
  - 用 WebSearch 搜他五个方向加收入词，比如「programmatic SEO directory MRR」「cold email tool indie revenue」「B2B lead list newsletter revenue」「press release distribution solo founder」「外贸 独立站 AI 月入」。
- 优先类型：programmatic SEO 内容站、联盟评测站、目录站、单功能 AI 工具站、开源项目托管版、API 服务、浏览器插件与小程序、数据与情报订阅、数字产品与模板、图文和 Newsletter 类 AI 自媒体、产品化服务。和他外贸、SEO、自媒体经验沾边的优先。
- 不收：以生产视频为核心的（漫剧、faceless 频道、数字人、AI UGC 代做）；要囤货、线下交付、重销售或大量定制咨询的；一个人做不了的；只有想法、找不到有人付钱的。前 7 天写过的（`recent`、`seen_before`）不再写，除非有新的收入数字。
- 每个候选写这几段，每个字段一两句话：
  - `name`（产品或生意的名字，可以带括号注释）、`category`（上面的类型）、`one_liner`（60 字以内：卖什么、卖给海外的谁、怎么收钱）、`track`、`source`（你最先在哪看到的：`title`、`url`）。
  - `automation`：`acquisition`（获客）、`production`（生产交付）、`payment_support`（收款客服）、`manual`（仍要他做的）、`weekly_hours`（稳定后每周几小时，数字）。
  - `market`：`demand`（谁在要、证据）、`revenue_evidence`、`competition`、`evidence_links`。
  - `fit`：`startup_cost_usd`（数字，不超过 500）、`mvp_days`、`services`（要用的服务）、`match`（一句话：和他经验的关系，网站直接显示在卡片上）、`biggest_risk`（含平台政策风险）。
  - `verdict`：`值得验证`、`放进观察` 或 `只是灵感`。

**tools（GitHub 工具，3–8 个，分两组）**
- `group` 写 `大家都在用`（星数高、稳定）或 `刚冒出来`（建仓 30 天内或今日涨星快）。
- `why_today`（20 字以内，带数字）：为什么今天入选。例：「今日 +1,102 星」「建仓 4 天 2.3k 星」「出了 2.0」。网站折叠态会显示这句。
- 标准：一个人拿来能省时间、能做产品、能赚钱，**按能拿它做什么生意挑**。全部满足：能在 VPS 或本机跑或有托管版；最近 30 天有提交；许可证允许商用（AGPL 要在 license 里写明）。`github_topics` 里他行业的工具优先看。
- 看榜单的规则（星数反映热度，不等于有人在用）：
  - `skip: true` 的不选。
  - 「大家都在用」优先选 `days_on_list` 3 天以上或周榜上的；只上榜一天、`also_on` 也为空的单日暴涨，要么放「刚冒出来」并在 `why_today` 写清「首次上榜」，要么不选。`why_today` 可以写「7 天内第 4 天上榜」。
  - 上榜原因看 `also_on` 和 README：大厂官方发的、HN 带起来的、博主演示带起来的不一样，博主带起来的过一周再看。
  - `fork_ratio` 明显偏低（不到 0.02）又几乎没有 issue 的，多半是围观，不选或写明。README 说不清它解决什么、主页挂购买链接却没有开源可跑代码的，不选。
  - 视频生成和剪辑工具每期最多 1 个，`uses` 要写他做产品或自己发内容时能省掉哪一步，不写拿它做视频生意。
  - `license_tier` 是「能托管来卖」或「托管要公开改动」、星数高、非技术用户也需要、`homepage` 还没有付费托管版的，是「开源项目托管版」机会的线索；`issue_demand` 里又有人在要的更好。写进 `business`，找得到同类托管版的收入证据时，也写成一个机会候选。
- `brief`：一句话说清它是什么，26 个字以内，不加粗。`what` 120 字以内。
- `uses`：**只写 1–2 条，`area` 只能是 外贸 / SEO / 自媒体 / 供需 / 宣传 / 做产品**（供需＝供需撮合：目录、名单、数据 API、需求情报；宣传＝海外宣传：新闻稿、媒体外联、AI 可见度），`how` 60 字以内，具体到「拿它做什么、卖给谁或省掉哪一步」。套不上这六个方向的工具就不要选。
- `business`（40 字以内，必填）：**能拿它做什么生意**，写清卖什么、卖给谁、怎么收钱，比如「做托管版卖给不会部署的外贸小团队，按月收费」「把它抓的数据做成周报卖给跨境卖家」。和 `uses` 不重复：`uses` 写他自己的业务里怎么用，`business` 写拿它赚谁的钱。想不出生意的工具不要选。网站把这句放在卡片展开后的第一行，飞书卡片也会挑一条。
- `license_tier`（必填）：照抄素材里的三档；素材里是 null 的，打开 LICENSE 看完再写。`license` 写 SPDX 名，没有就写 LICENSE 里的名字。
- `demand`（0–3 条，可不写）：需求证据，从 `issue_demand` 或这个仓库的 issue 区（按点赞排：`https://github.com/<仓库>/issues?q=is%3Aissue+is%3Aopen+sort%3Areactions-%2B1-desc`）挑真有人在要、和 `business` 对得上的，写 `title`（原标题，可以截短）、`url`、`reactions`（点赞数）。
- `stars_7d`：照抄素材里的数，没有就不写。
- `tags` 从这些里选：外贸、SEO、自媒体、供需、宣传、做产品、Agent 与自动化、数据与研究、设计与视频、其他。
- 安全：**只有会拿到权限或凭证的（浏览器自动化、MCP、要账号、爬虫、读写本地文件）或建仓不到 30 天的才给黄**，其余给绿；红只给热度很高（总星 5000 以上或今日 500 星以上）且风险明确的。黄和红在 `safety_note` 写：先一句结论，再最多两句依据，最后一段以「防范：」开头写怎么防；另写 `risk_brief`（30 字以内）。三期里 30 个工具 21 个黄，黄就没有意义了。
- `stars_today` 只填榜单上明确标注「今日」的数字，取不到就写 null。配图不用管，脚本会从 README 自动挑。

**skills（Skills，4–6 个）**
- 带 SKILL.md 的能力包，Claude Code 和 Codex 通用。只选非常流行或正在冲榜的：`skills_sh` 榜上的（`installs` 直接从那里抄）、GitHub 星数高的（单独仓库一般 1000 星以上）、大仓库（如 anthropics/skills）里的、`x.hot`「Skills」里被很多人转的。1–2 个是新晋热门（`hot` 写「新晋热门」），其余「长期热门」。他五个方向用得上的优先（写开发信、做 SEO 页面、整理名单、写英文图文、做外贸资料）。
- `installs` 从 `skills_sh` 里取；`skills_sh` 为空时才用 WebFetch 打开 https://skills.sh。`popularity_note` 一句话写热度依据，含数字和日期。
- `brief`、`what`、`uses`、`risk_brief` 的写法同工具（`uses` 同样只写 1–2 条、六个方向）。同一个项目不要既放工具又放 Skills。
- 安全检查是硬要求：用 WebFetch 打开 SKILL.md 和附带脚本（raw.githubusercontent.com），看会不会执行 shell、读写本地文件、把数据发到外部服务器、有没有编码混淆的命令、要不要 API Key。黄的标准同工具。读不到 SKILL.md 的不选。

另外写：
- `headline`：3 句话，依次是**今日机会**（B01 是什么、收入证据的数字）、**最值得看的一个 GitHub 或 Skills 线索**、**今天最值得做的一件事**（和 `actions` 第一条对应）。
- `actions`：今天可以做的事，1–3 件，`minutes` 只能是 5、15、30。第一条要是今天最值得做的，一般和 B01 有关（比如「打开 B01 竞品的定价页，记下他们卖多少钱、给谁」）。网站和飞书卡片把它放在最前面，这是他最先看的东西。
- `stats.scanned`：你看过的候选总数，按 `raw.counts` 加你自己搜到的算，不要编。

## 重点标记

他扫读为主，所以每段文字里把最关键的数字、结论、价格变化用 `**双星号**` 包起来，网站会显示成彩色粗体。每段最多 2 处，不要整句加粗。`brief`、`why_today`、`risk_brief`、`one_liner` 不加粗。命令、包名、文件路径用反引号包起来。

## 质量红线

- 每条都要有原文链接，而且你必须确认过它存在、日期对得上。搜索摘要不算来源。
- 星数、价格、收入、用户数、搜索量只写素材或页面上有的，不估算。推断要写明「推断」。
- 不写科普背景，不写「具有重要意义」一类空话。一句话能说清的不写两句。
- 整期控制在 5000 字以内。校验会报出字数和阅读分钟数，超了先压缩工具和 Skills 的细节，再压缩候选。

## 输出

写到 `data/daily/<日期>.json`，格式如下（`id` 和 `pick` 不用写，校验脚本会自动编号，并把第一个候选记成今日机会）：

```json
{
 "date": "2026-11-02",
 "generated_at": "2026-11-02T05:30:00+08:00",
 "headline": ["今日机会：B01 是什么、收入证据", "最值得看的 GitHub 或 Skills 线索", "今天最值得做的一件事"],
 "stats": {"scanned": 0},
 "actions": [{"minutes": 15, "text": "第一条是今天最值得做的"}],
 "opportunities": [{"name": "", "category": "", "one_liner": "60 字以内", "track": "全球贸易|SEO与GEO|图文自媒体|供需撮合|海外宣传（可不写）", "source": {"title": "", "url": ""},
   "automation": {"acquisition": "", "production": "", "payment_support": "", "manual": "", "weekly_hours": 2},
   "market": {"demand": "", "revenue_evidence": "带数字和出处", "competition": "1–3 个竞品", "evidence_links": [{"title": "", "url": ""}]},
   "fit": {"startup_cost_usd": 100, "mvp_days": 7, "services": "", "match": "一句话：和他经验的关系", "biggest_risk": ""},
   "verdict": "值得验证|放进观察|只是灵感"}],
 "tools": [{"repo": "owner/name", "url": "", "group": "大家都在用|刚冒出来", "why_today": "今日 +1,102 星", "stars_today": 0, "stars_7d": 0, "stars_total": 0, "license": "MIT", "license_tier": "能托管来卖|托管要公开改动|不能托管来卖", "tags": ["SEO"], "brief": "", "what": "120 字以内", "business": "40 字以内：拿它做什么生意", "uses": [{"area": "外贸|SEO|自媒体|供需|宣传|做产品", "how": "60 字以内"}], "demand": [{"title": "issue 标题", "url": "", "reactions": 0}], "setup": "部署难度 低/中/高，需要什么", "safety": "绿|黄|红", "safety_note": "黄、红必须写风险和防范", "risk_brief": "黄、红必填"}],
 "skills": [{"name": "", "url": "", "repo": "owner/name", "hot": "新晋热门|长期热门", "stars_total": 0, "installs": null, "popularity_note": "", "works_with": "Claude Code / Codex / 两者", "safety": "绿|黄|红", "safety_note": "", "risk_brief": "", "brief": "", "what": "", "uses": [{"area": "", "how": ""}], "install": ""}]
}
```

写完运行 `python3 scripts/validate.py data/daily/<日期>.json`，按它的提示改到通过为止。不要修改 data/daily 以外的文件。
