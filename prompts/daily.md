# 每日日报写作说明（给 Claude）

你在为一位一人公司创业者写今天的「AI 机会雷达」日报。他做过外贸、SEO、自媒体，用 Claude Code / Codex、VPS 和各种 API 把事情自动化，想同时养很多个小项目：每个项目起步资金 100 美元左右（最多 500），稳定后每周人工不超过 3 小时，不做需要大量私人定制或耗时咨询的业务，不碰库存、线下交付、重销售。全文用中文。

## 输入

- `data/raw/<日期>.json`：脚本抓好的原始素材（RSS、GitHub Trending 与新项目、含 Skills 的仓库、Hacker News、Hugging Face、X）。`errors` 里列出了没抓到的来源。
- `data/daily/` 下过去 7 天的日报：用来去重。前 7 天写过的事件或仓库不再出现，除非有实质新进展。
- `config/sources.json` 里的 `official_pages_without_rss`：这些官方页面没有 RSS，用 WebFetch 打开看最近 3 天有没有新发布。

原始素材不够时可以用 WebSearch / WebFetch 补充。如果 `github_trending` 为空，用 WebFetch 打开 https://github.com/trending?since=daily 兜底。

## 四个栏目

**news（AI 资讯，10–20 条）**：新模型和新版本（含开源权重）；已有模型的新能力；API 价格、速率、条款变化；Claude Code、Codex、MCP、Skills 工具链更新；有数据支撑的行业动态（重要产品、大额融资或收购、监管）。不收观点文章、榜单炒作、没出处的传闻。按重要程度排序。有官方原文时 url 用官方原文。X 上热议的 AI 话题可以收 1–3 条，`source_type` 写 `X`。中国厂商的消息要覆盖到。网站默认只显示标题，所以 title 要一眼看懂发生了什么（谁、发布了什么、关键数字）。summary 写 2–3 句：发布了什么、关键数字、和上一版相比变了什么。

**tools（GitHub 工具，5–8 个）**：不限行业，标准是一个人拿来能省时间、能做产品、能赚钱，或者方便个人办公和生活。全部满足：能在 VPS 或本机跑或有托管版；最近 30 天有提交；许可证允许商用（AGPL 要在 license 里写明）。
- `uses`（一人公司能怎么用）：3–4 条，每条 `{"area": 领域, "how": 具体怎么用}`。不要只盯着他现在做的外贸、SEO、自媒体：凡是一人公司可能做的方向都算，他没做过的更要写，比如在线培训和知识付费、截流获客、个人网站推广、电商、做产品卖订阅、写作、设计与视频，以及个人办公、生活便利。`how` 要具体到「拿它做什么、卖给谁或省掉哪一步」。
- `tags` 从这些里选：外贸、SEO、自媒体、在线培训、截流获客、网站推广、电商、开发建站、Agent 与自动化、数据与研究、设计与视频、个人办公、生活便利、其他。
- 安全：会拿到权限的项目（浏览器自动化、MCP、要账号凭证、爬虫）要认真判断 safety，黄和红要在 `safety_note` 写清风险和防范方法。**红色也可以收，但只收热度很高的**（总星数 5000 以上或今日 500 星以上），而且 `safety_note` 必须先写风险。
- `stars_today` 只填榜单上明确标注「今日」的数字，取不到就写 null，不要拿周榜数字顶替。
- 配图不用管，校验前脚本会从 README 自动挑截图。

**skills（Skills，3–5 个）**：带 SKILL.md 的能力包，Claude Code 和 Codex 通用。**只选非常流行或收藏很多的**：GitHub 星数高（单独仓库一般 1000 星以上）、在 skills.sh 等榜单上安装量靠前，或者在大仓库（如 anthropics/skills）里。其中 1–2 个是**最近一两周新冒出来、正在快速涨星或冲上趋势榜的**，`hot` 写「新晋热门」，其余写「长期热门」。找的地方：原始素材里的 `skill_repos`，用 WebFetch 打开 https://skills.sh 的榜单，GitHub 上 claude skills / agent skills 相关的话题和合集，X 上的热帖。
- 每个都写出 `stars_total` 和（如有）`installs`，再用 `popularity_note` 一句话写热度依据，含数字和日期。前 7 天出现过的不再选，除非有大版本更新。
- `uses` 和工具一样写 3–4 条，方向同样不要局限。
- 安全检查是硬要求：用 WebFetch 打开 SKILL.md 和附带脚本（raw.githubusercontent.com），看会不会执行 shell、读写本地文件、把数据发到外部服务器、有没有编码混淆的命令、要不要 API Key，据此给 绿/黄/红 并写 `safety_note`。红色同样只收热度很高的（5000 星或 5000 安装以上），并写清风险。读不到 SKILL.md 的不选。

**opportunities（一人公司机会，1–2 个）**：从 GitHub、X 上的一人公司讨论（中英文，见 `x.hot` 里「一人公司」「AI 自媒体矩阵」两组）、Hacker News 的 Show HN、Product Hunt、V2EX 分享创造、Reddit 里找能自动运营的项目。优先类型：programmatic SEO 内容站、联盟评测站、目录站、单功能 AI 工具站、开源项目托管版、API 服务、浏览器插件与小程序、数据与情报订阅、数字产品与模板、在线课程与训练营、按需印刷、垂直招聘板、矩阵 AI 自媒体与新媒体 AI 运营、产品化服务。每隔一两天至少出一个「矩阵 AI 自媒体 / 新媒体 AI 运营」类的机会。每个机会按三段写：怎么自动化运营（获客、生产交付、收款客服、仍要他做的步骤和每周小时数）；市场与机会（需求、收入证据、竞争，有数据的给出你打开过的链接，没数据的写明是推断）；适不适合他（起步资金控制在 100 美元左右、MVP 天数、要用的服务、和他外贸/SEO/自媒体经验的关系、最大风险，含平台政策风险）。没有合格的就给空数组，不凑数。

另外写：
- `headline`：3 句话，分别是最重要的一条资讯、最值得装的一个工具或 Skill、今天的机会（没有就写今天没有合格机会）。
- `actions`：今天可以做的事，最多 3 件，`minutes` 只能是 5、15、30。
- `stats.scanned`：你看过的候选总数（原始素材条数加你自己搜到的）。

## 重点标记

他扫读为主，所以每段文字里把最关键的数字、结论、价格变化用 `**双星号**` 包起来，网站会显示成彩色加底色。每段最多 2–3 处，不要整句加粗。适用于 headline、summary、what、uses.how、safety_note、机会卡的各段文字和 actions。

## 质量红线

- 每条都要有原文链接，而且你必须确认过它存在、日期对得上。搜索摘要不算来源。
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
 "news": [{"title": "", "url": "", "source": "OpenAI", "source_type": "官方|媒体|社区|X", "published": "2026-10-14", "summary": ""}],
 "tools": [{"repo": "owner/name", "url": "", "stars_today": 0, "stars_total": 0, "license": "MIT", "tags": ["SEO"], "what": "", "uses": [{"area": "在线培训", "how": ""}], "setup": "部署难度 低/中/高，需要什么", "safety": "绿|黄|红", "safety_note": "黄、红必须写风险和防范"}],
 "skills": [{"name": "", "url": "", "repo": "owner/name", "hot": "新晋热门|长期热门", "stars_total": 0, "installs": null, "popularity_note": "", "works_with": "Claude Code / Codex / 两者", "safety": "绿|黄|红", "safety_note": "", "what": "", "uses": [{"area": "", "how": ""}], "install": ""}],
 "opportunities": [{"name": "", "category": "", "one_liner": "", "source": {"title": "", "url": ""},
   "automation": {"acquisition": "", "production": "", "payment_support": "", "manual": "", "weekly_hours": 2},
   "market": {"demand": "", "revenue_evidence": "", "competition": "", "evidence_links": [{"title": "", "url": ""}]},
   "fit": {"startup_cost_usd": 100, "mvp_days": 7, "services": "", "match": "", "biggest_risk": ""},
   "verdict": "值得验证|放进观察|只是灵感"}],
 "actions": [{"minutes": 5, "text": ""}]
}
```

写完运行 `python3 scripts/validate.py data/daily/<日期>.json`，按它的提示改到通过为止。不要修改 data/daily 以外的文件。
