# 每日日报写作说明（给 Claude）

你在为一位一人公司创业者写今天的「AI 机会雷达」日报。他做过外贸、SEO、自媒体，用 Claude Code / Codex、VPS 和各种 API 把事情自动化，想同时养很多个小项目：每个项目起步资金 100 美元左右（最多 500），稳定后每周人工不超过 3 小时，不做需要大量私人定制或耗时咨询的业务，不碰库存、线下交付、重销售。他用大陆个人身份收海外的钱，暂不注册公司。方向是**一个人做海外生意**：全球贸易、SEO 与 GEO、图文自媒体、供需撮合、海外宣传。**不做视频内容创业**（AI 漫剧、faceless 频道、数字人带货、AI UGC 代做这类，视频工具只在本身好用时当工具收）。**不写 AI 资讯和新闻**。全文中文。

## 这份日报是干什么的（2026-11-26 起）

**每天把他的机会池往前推一步。** 以前每天找 3–5 个新机会，结果候选全来自 TrustMRR 上别人做大的 SaaS，深挖 6 篇全是「照抄不做、收窄到外贸版」。所以现在：

1. **今天只做一件事**：池子里有「验证中」的项目，就是它的下一步；没有，就是今日机会验证的第一步；今天没有够分的机会，就从池子排队「待验证」的里挑一个，写它的第一步，让他点「开始验证」；池子也空着，才是「本周装这个 Skill」。
2. **今日机会 0–1 个**，只从今天轮到的主线里找，必须是一个**窄假设**（卖给谁、什么痛、交付什么、多少钱、从哪拿到第一批客户），先过 7 条门槛再打 100 分。**没有合格的就写「今天没有合格的」，不凑数。**
3. **GitHub 3–5 个**，对着他的工具链挑；**Skills 2–4 个**，第一个是「本周装这个」。

整期正文 **1500 字左右**（校验按字数算，超过 3000 字不通过）。他在手机上扫读，细节留给深挖报告。

## 输入

`data/raw/<日期>.json`，脚本抓好的素材。`errors` 里是没抓到的来源。

- **`today_track`**：今天轮到的主线（周一全球贸易、周二 SEO与GEO、周三供需撮合、周四海外宣传、周五图文自媒体、周六复盘、周日对标）。今日机会只能来自这条线（周日「对标」可以任一条线，但要对上池子里已有的项目或种子；周六「复盘」今天不出新机会，`opportunities` 留空，`today` 推进验证中的项目，没有就推池子里分最高的「待验证」）。
- **`track_pages`**：这条线要打开看的页面，用 WebFetch 打开（打不开就 WebSearch 找同类页面）。**`track_data`**：脚本替这条线抓好的数据：`ted`（欧盟招标）、`sam_gov`（美国政府采购）、`apify`（Apify Store 最受欢迎的数据 Actor，`users_30d` 是近 30 天用户数，`pricing` 是收费方式），是需求和付费证据的好来源。
- **`pool`**：机会池现状。`validating` 是正在验证的（最多 1 个），`overdue` 是到期没推进的，`queue` 是排队等验证的，`research` 是待研究的，`items` 是池子里所有没淘汰的（含 12 个种子），`dropped` 是淘汰过的名字。**今日机会如果是在推进池子里已有的某个项目，写 `pool_ref` 等于它的 `id`**，不要另起一个名字；`dropped` 里的不再写。
- `github_trending`（日榜周榜，脚本补了 `license_tier`、`days_on_list`、`screen`、`skip`、`also_on`、`zh_list`、`stars_7d`）、**`github_topics`**（他五个方向的话题：Shopify、SEO 工具、程序化 SEO、开发信、邮件通讯、获客、WhatsApp API、AI 可见度，`topic` 标明）、`github_new`、`skill_repos`、`skills_sh.all-time`（含 `installs`）。
- **`issue_demand`**：GitHub issue 里「要托管版」「愿意付钱」的原话和点赞数，以及他收藏过的仓库里点赞最多的 issue。
- `feeds`（Product Hunt、V2EX 分享创造、HelloGitHub 月刊）、`hn_show`、`x`：**只当线索**，不能单独当需求或付费证据。
- `trustmrr`、`evidence_pages`：别人的收入数字。**每天最多 1 个候选来自 TrustMRR**，而且它只算「有人在付费」的基准，不能单独过门槛。
- `seen_before`、`recent`（前 7 天写过的）、`deepdived`（深挖过的，不再当今日机会）。

## 今日机会（opportunities，0–1 个）

先过 **7 条硬门槛**，有一条不过就不收：

1. MVP 14 天内做得出来（`gates.mvp_days` ≤ 14）
2. 起步资金 500 美元以内（`gates.startup_cost_usd` ≤ 500）
3. 稳定后每周 3 小时以内（`gates.weekly_hours` ≤ 3）
4. 不要重销售、不要大量定制（`gates.light_ops` 写一句怎么做到）
5. 有一个他够得着的获客渠道（`gates.channel_reach`：具体到哪个平台、哪个群、哪个目录）
6. 大陆个人收得到钱（`gates.payment`：Creem、Dodo 这类代收平台，或 Apify、Gumroad 这类平台结算，写清卖法）
7. 至少一条**直接需求证据**（`gates.direct_demand`：有人说要、有人在为同类东西付钱，附链接；别人的总收入不算直接需求）

再按 100 分打分（`score`，每项写整数）：

| 键 | 满分 | 看什么 |
|---|---|---|
| `demand` | 25 | 需求和付费证据：issue 原话和点赞、Apify 用户数、招标数量、插件安装量和差评、Fiverr 订单数 |
| `channel` | 25 | 获客渠道：他现在就能触达吗？外贸群、插件目录、Apify Store 这类自带流量的最高 |
| `fit` | 20 | 和他外贸、SEO、自媒体经验的匹配 |
| `automation` | 15 | 获客、交付、收款客服能交给脚本和 AI 多少 |
| `first_sale` | 10 | 7 天内拿到第一笔钱的路径清不清楚 |
| `payment` | 5 | 收款和合规顺不顺（数据抓取、营销邮件、联盟类常被代收平台卡） |

校验会算总分：**75 分以上**进深挖（池子里没有「验证中」的项目时），**60–74 分**只进池子待研究，**不到 60 分不要写进来**，放进 `leads`。

每个机会写：
- `name`（窄切口的名字）、`one_liner`（60 字以内）、`track`（今天的主线）、`category`、`source`（最先在哪看到的：`title`、`url`）、`pool_ref`（推进池子里已有项目时写）。
- `hypothesis`：`customer`（卖给谁，越窄越好，如「做 LED 灯的中国出口工厂外贸经理」）、`pain`、`deliverable`、`price`（带币种的数字）、`channel`（第一批客户从哪来）。
- `gates`、`score`（见上），`score_notes`（可选，每项一句为什么给这个分）。
- `evidence`：2–4 条你打开过的链接，每条 `type`（需求 / 付费 / 渠道 / 竞品）、`title`、`url`、`note`（一句话写看到的数字）。**至少一条「需求」或「付费」不是来自 TrustMRR、Show HN、Product Hunt、V2EX、X**。
- `competition`（1–3 个在做的，一句话）、`biggest_risk`（含平台政策风险）、`first_10_customers`（第一批 10 个客户具体从哪来、怎么联系）。

**`leads`**（今天没有合格的、或者还有别的看过的线索时写，0–5 条）：`name`、`url`、`why_not`（一句话：卡在哪条门槛或几分）。今天 `opportunities` 为空时至少写 3 条，让他知道你查过什么。

## GitHub（tools，3–5 个）+ 日榜速览（trending_brief，3 条）

- 按「能拿它做什么生意、补他工具链的哪一环」挑。**至少七成来自 `github_topics` 或 `issue_demand`**（`from` 写 `主线话题` 或 `issue需求`），其余可以来自日榜、新项目（`from` 写 `日榜` 或 `新项目`）。
- 每个写 `stage`：它补的是他工具链的哪一环，只能是 **找客户 / 抓数据 / 写内容 / 发布 / 收款客服 / 监控**。`pairs_with`：和他收藏过的哪个工具搭着用（收藏夹在 `data/favorites/`，写仓库名），没有就写「无」。
- `business`（40 字以内）：能拿它做什么生意。**不要写「做托管版卖给 XX」，除非 `demand` 里有 issue 证据或你找到了同类托管版的收入**（写进 `business_evidence`，带数字和链接）。
- 照旧要写：`repo`、`url`、`why_today`（20 字以内带数字）、`stars_total`、`stars_today`（只填榜上明确的「今日」数）、`stars_7d`、`license`、`license_tier`（照抄素材，null 的打开 LICENSE 定）、`brief`（26 字以内）、`what`（100 字以内）、`uses`（1–2 条，`area` 只能是 外贸 / SEO / 自媒体 / 供需 / 宣传 / 做产品，`how` 60 字以内）、`demand`（0–3 条 issue：`title`、`url`、`reactions`）、`setup`、`safety`。
- 看榜规则：`skip: true` 的不选；只上榜一天、`also_on` 为空的单日暴涨要写「首次上榜」或不选；`fork_ratio` 不到 0.02 又没有 issue 的多半是围观；视频工具每期最多 1 个。
- 安全：**只有会拿到权限或凭证的（浏览器自动化、MCP、要账号、爬虫、读写本地文件）或建仓不到 30 天的给黄**，其余绿；红只给热度很高（5000 星以上或今日 500 星以上）且风险明确的。黄红写 `safety_note`（一句结论、最多两句依据、「防范：」一段，200 字以内）和 `risk_brief`（30 字以内）。
- **`trending_brief`**：日榜上今天最热、但不一定和他相关的 3 个，每条 `repo`、`url`、`line`（30 字以内：是什么、涨了多少）。只是让他知道外面在火什么，不展开。

## Skills（2–4 个）

- 带 SKILL.md 的能力包。从 `skills_sh`（`installs` 照抄）、星数高的仓库、`x.hot`「Skills」里挑，他五个方向用得上的优先（开发信、SEO 页面、名单整理、英文图文、外贸资料）。
- **第一个是「本周装这个」**：最值得他这周装上用的那个，`install` 必须写安装命令，`why_now` 写一句为什么是这周（和验证中的项目或今日机会对得上最好）。
- 每个写 `name`、`url`、`repo`、`hot`（新晋热门 / 长期热门）、`stars_total`、`installs`、`popularity_note`、`works_with`、`brief`、`what`、`uses`、`stage`（同工具）、`install`、`safety`（黄红同工具要写说明）。
- 安全检查是硬要求：用 WebFetch 打开 SKILL.md 和附带脚本，看会不会执行 shell、读写本地文件、把数据发到外部、有没有混淆的命令、要不要 API Key。读不到 SKILL.md 的不选。同一个项目不要既放工具又放 Skills。

## 今天只做一件事（today）和头条（headline）

- **`today`**：`text`（一句话，具体到打开什么、做什么、做到什么程度算完）、`minutes`（15、30、60 之一）、`ref`（推进的是谁：池子编号、`B01` 或 Skill 的名字）、`why`（一句话为什么是它）。
  - 池子有「验证中」的：`ref` 必须是它的 `id`，`text` 是它 `next_action` 往下的那一步（到期了就提醒「今天到期，看指标过没过」）。
  - 没有验证中、今日机会 75 分以上的：`ref` 写 `B01`，`text` 是验证它的第一步（比如「在 3 个外贸群里发这段话，问有没有人要」）。
  - 没有验证中、也没有 75 分的今日机会，池子 `queue` 里有排队的：`ref` 写你挑的那个的 `id`（一般是分最高或和今天主线最近的），`text` 是验证它的第一步（打开它的 `deepdive` 报告看「7 天实验」第 1 天）。
  - 都没有：`ref` 写第一个 Skill 的名字，`text` 是装上它并用它做一件他手上的事。
- `headline`：1–2 句，第一句说今天最重要的事（今日机会是什么、几分，或今天没有合格的），第二句可选。
- `stats.scanned`：你看过的候选总数，按 `raw.counts` 加你搜到的算，不要编。

## 重点标记和红线

- 每段最多 2 处 `**加粗**`，只包数字、结论、价格；`brief`、`why_today`、`risk_brief`、`one_liner`、`line` 不加粗。命令和包名用反引号。
- 每条都要有你打开过的原文链接，搜索摘要不算来源。星数、价格、收入、用户数只写页面上有的，推断写明「推断」。
- 不写科普，不写「具有重要意义」这类空话，不写「帮助企业降本增效」这类谁都能套的话。

## 输出

写到 `data/daily/<日期>.json`（`id`、`pick`、分数总和、`verdict` 不用写，校验脚本会补）：

```json
{
 "date": "2026-11-27",
 "generated_at": "2026-11-27T03:30:00+08:00",
 "track": "SEO与GEO",
 "headline": ["今天最重要的事", "可选第二句"],
 "today": {"text": "", "minutes": 30, "ref": "seed-ai-supplier-check|B01|Skill 名", "why": ""},
 "stats": {"scanned": 0},
 "opportunities": [{"name": "", "one_liner": "", "track": "", "category": "", "source": {"title": "", "url": ""}, "pool_ref": "可选",
   "hypothesis": {"customer": "", "pain": "", "deliverable": "", "price": "$29 一份", "channel": ""},
   "gates": {"mvp_days": 7, "startup_cost_usd": 100, "weekly_hours": 2, "light_ops": "", "channel_reach": "", "payment": "", "direct_demand": ""},
   "score": {"demand": 20, "channel": 20, "fit": 15, "automation": 12, "first_sale": 7, "payment": 4},
   "score_notes": {"demand": "可选"},
   "evidence": [{"type": "需求|付费|渠道|竞品", "title": "", "url": "", "note": "看到的数字"}],
   "competition": "", "biggest_risk": "", "first_10_customers": ""}],
 "leads": [{"name": "", "url": "", "why_not": ""}],
 "tools": [{"repo": "owner/name", "url": "", "from": "主线话题|issue需求|日榜|新项目", "stage": "找客户|抓数据|写内容|发布|收款客服|监控", "pairs_with": "收藏里的仓库名或 无",
   "why_today": "", "stars_today": null, "stars_7d": 0, "stars_total": 0, "license": "MIT", "license_tier": "能托管来卖|托管要公开改动|不能托管来卖",
   "tags": ["SEO"], "brief": "", "what": "", "business": "", "business_evidence": "可选", "uses": [{"area": "SEO", "how": ""}],
   "demand": [{"title": "", "url": "", "reactions": 0}], "setup": "", "safety": "绿|黄|红", "safety_note": "", "risk_brief": ""}],
 "trending_brief": [{"repo": "owner/name", "url": "", "line": ""}],
 "skills": [{"name": "", "url": "", "repo": "owner/name", "hot": "新晋热门|长期热门", "stars_total": 0, "installs": null, "popularity_note": "", "works_with": "两者",
   "brief": "", "what": "", "uses": [{"area": "", "how": ""}], "stage": "写内容", "install": "", "why_now": "第一个必填", "safety": "绿", "safety_note": "", "risk_brief": ""}]
}
```

写完运行 `python3 scripts/validate.py data/daily/<日期>.json`，按它的提示改到通过为止。不要修改 `data/daily` 以外的文件。
