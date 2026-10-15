/* AI 机会雷达 前端。数据来自 data/*.json（GitHub Pages），或预览版里内嵌的 window.__RADAR__。 */
(function () {
  "use strict";
  var EMBED = window.__RADAR__ || null;
  var app = document.getElementById("app");
  var toastEl = document.getElementById("toast");
  var state = { index: null, config: {}, daily: {}, deep: {}, tab: "today", date: null, focus: null };
  var SEC = [
    { key: "news", code: "N", title: "AI 资讯" },
    { key: "tools", code: "G", title: "GitHub 工具" },
    { key: "skills", code: "S", title: "Skills" },
    { key: "opportunities", code: "B", title: "一人公司机会" }
  ];

  /* ---------- 小工具 ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function rich(s) { return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? esc(u) : "#"; }
  function link(text, url) { return '<a href="' + safeUrl(url) + '" target="_blank" rel="noopener">' + esc(text) + "</a>"; }
  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; }
    return null;
  }
  function toast(msg) {
    toastEl.textContent = msg; toastEl.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(function () { toastEl.hidden = true; }, 3200);
  }
  function fmtDate(d) {
    var w = "日一二三四五六".charAt(new Date(Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10))).getUTCDay());
    return d.slice(0, 4) + " 年 " + Number(d.slice(5, 7)) + " 月 " + Number(d.slice(8, 10)) + " 日 · 星期" + w;
  }
  function getJSON(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.json(); });
  }
  function getText(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.text(); });
  }
  function safetyLight(s) {
    var c = s === "绿" ? "var(--good)" : s === "黄" ? "var(--warn)" : s === "红" ? "var(--bad)" : "var(--muted)";
    return '<span class="light" style="--c:' + c + '">安全 ' + esc(s || "未查") + "</span>";
  }
  function verdictPill(v) {
    var cls = v === "值得验证" ? "good" : v === "放进观察" ? "warn" : "neutral";
    return '<span class="pill ' + cls + '">' + esc(v) + "</span>";
  }
  function num(n) { return n == null ? "–" : Number(n).toLocaleString("en-US"); }

  /* ---------- 极简 Markdown（深挖报告用） ---------- */
  function inline(s) {
    s = esc(s);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }
  function markdown(src) {
    var lines = String(src || "").replace(/\r/g, "").split("\n"), out = [], i = 0;
    while (i < lines.length) {
      var l = lines[i];
      if (!l.trim()) { i++; continue; }
      var h = l.match(/^(#{1,4})\s+(.*)$/);
      if (h) { var lv = Math.min(4, h[1].length + 1); out.push("<h" + lv + ">" + inline(h[2]) + "</h" + lv + ">"); i++; continue; }
      if (/^---+\s*$/.test(l)) { out.push("<hr>"); i++; continue; }
      if (/^\|/.test(l)) {
        var rows = [];
        while (i < lines.length && /^\|/.test(lines[i])) { rows.push(lines[i]); i++; }
        var cells = function (r) { return r.replace(/^\||\|\s*$/g, "").split("|").map(function (c) { return c.trim(); }); };
        var html = "<table><thead><tr>" + cells(rows[0]).map(function (c) { return "<th>" + inline(c) + "</th>"; }).join("") + "</tr></thead><tbody>";
        rows.slice(2).forEach(function (r) { html += "<tr>" + cells(r).map(function (c) { return "<td>" + inline(c) + "</td>"; }).join("") + "</tr>"; });
        out.push('<div style="overflow-x:auto">' + html + "</tbody></table></div>"); continue;
      }
      if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
        var ordered = /^\s*\d+\./.test(l), items = [];
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          var depth = lines[i].match(/^\s*/)[0].length >= 2 ? ' style="margin-left:1.2em"' : "";
          items.push("<li" + depth + ">" + inline(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, "")) + "</li>"); i++;
        }
        out.push((ordered ? "<ol>" : "<ul>") + items.join("") + (ordered ? "</ol>" : "</ul>")); continue;
      }
      if (/^>\s?/.test(l)) {
        var q = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) { q.push(lines[i].replace(/^>\s?/, "")); i++; }
        out.push("<blockquote>" + inline(q.join(" ")) + "</blockquote>"); continue;
      }
      var p = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\||\s*([-*]|\d+\.)\s|>|---)/.test(lines[i])) { p.push(lines[i]); i++; }
      out.push("<p>" + inline(p.join(" ")) + "</p>");
    }
    return out.join("\n");
  }

  /* ---------- 收藏按钮 ---------- */
  function savedSet() { try { return JSON.parse(store("radar-saved") || "{}"); } catch (e) { return {}; } }
  function actBtns(fid, withDeep) {
    var s = savedSet()[fid];
    var fav = '<button class="btn" data-op="fav" data-id="' + esc(fid) + '"' + (s ? ' data-done="1"' : "") + ">" + (s ? "★ 已收藏" : "☆ 收藏") + "</button>";
    var deep = withDeep ? '<button class="btn primary" data-op="deep" data-id="' + esc(fid) + '"' + (s === "deep" ? " disabled" : "") + ">" + (s === "deep" ? "深挖中" : "收藏并深挖") + "</button>" : "";
    return '<div class="acts">' + fav + deep + "</div>";
  }
  function doAction(btn) {
    var op = btn.getAttribute("data-op"), fid = btn.getAttribute("data-id");
    var key = store("radar-key"), worker = (state.config.worker_url || "").replace(/\/$/, "");
    if (EMBED && EMBED.preview) { toast("这是预览版，网站部署后按钮才能用"); return; }
    if (!worker || !key) { toast("还没连上收藏接口：请从飞书卡片里的链接打开一次网站"); return; }
    btn.disabled = true;
    fetch(worker + "/act?op=" + op + "&id=" + encodeURIComponent(fid) + "&k=" + encodeURIComponent(key), { method: "POST" })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok || !j.ok) throw new Error(j.message || "失败"); return j; }); })
      .then(function () {
        var s = savedSet(); s[fid] = op === "deep" ? "deep" : (s[fid] || "fav"); store("radar-saved", JSON.stringify(s));
        toast(op === "deep" ? "已收藏，Claude 开始深挖，完成后飞书通知你" : "已收藏，几分钟后出现在收藏页");
        render();
      })
      .catch(function (e) { btn.disabled = false; toast("没成功：" + e.message); });
  }

  /* ---------- 今日 ---------- */
  function renderNews(d) {
    if (!d.news.length) return '<p class="empty">今日无</p>';
    return '<ul class="news">' + d.news.map(function (n) {
      return '<li><span class="id">' + esc(n.id) + "</span><div><h3>" + link(n.title, n.url) + "</h3><p>" + esc(n.summary) + '</p><div class="meta"><span class="tag">' + esc(n.source_type) + "</span>" + (n.source ? '<span class="tag">' + esc(n.source) + "</span>" : "") + actBtns(d.date + "-" + n.id, false) + "</div></div></li>";
    }).join("") + "</ul>";
  }
  function renderTools(d) {
    if (!d.tools.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.tools.map(function (t) {
      return '<article class="card"><div class="card-top"><span class="id">' + esc(t.id) + '</span><h3 class="repo">' + link(t.repo, t.url) + '</h3></div><div class="stats">' +
        (t.stars_today != null ? '<span class="up">▲ ' + num(t.stars_today) + " 今日</span>" : "") + "<span>★ " + num(t.stars_total) + "</span><span>" + esc(t.license || "许可证未知") + "</span>" + safetyLight(t.safety) + "</div>" +
        '<div class="acts">' + (t.tags || []).map(function (g) { return '<span class="tag">' + esc(g) + "</span>"; }).join("") + "</div>" +
        '<dl class="kv"><dt>做什么</dt><dd>' + rich(t.what) + "</dd><dt>对我有用</dt><dd>" + rich(t.use_for_me) + "</dd><dt>上手</dt><dd>" + rich(t.setup) + "</dd>" + (t.safety_note ? "<dt>安全</dt><dd>" + rich(t.safety_note) + "</dd>" : "") + "</dl>" +
        actBtns(d.date + "-" + t.id, true) + "</article>";
    }).join("") + "</div>";
  }
  function renderSkills(d) {
    if (!d.skills.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.skills.map(function (s) {
      return '<article class="card"><div class="card-top"><span class="id">' + esc(s.id) + "</span><h3>" + link(s.name, s.url) + '</h3></div><div class="stats"><span>' + esc(s.works_with) + "</span>" + safetyLight(s.safety) + "</div>" +
        '<dl class="kv"><dt>有什么用</dt><dd>' + rich(s.what) + "</dd><dt>我怎么用</dt><dd>" + rich(s.how_i_use) + "</dd><dt>安全检查</dt><dd>" + rich(s.safety_note) + "</dd><dt>安装</dt><dd>" + rich(s.install) + "</dd></dl>" +
        actBtns(d.date + "-" + s.id, true) + "</article>";
    }).join("") + "</div>";
  }
  function renderOpps(d) {
    if (!d.opportunities.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.opportunities.map(function (b) {
      var a = b.automation || {}, m = b.market || {}, f = b.fit || {};
      var ev = (m.evidence_links || []).map(function (e) { return "<li>" + link(e.title, e.url) + "</li>"; }).join("");
      return '<article class="card opp"><div class="card-top"><span class="id">' + esc(b.id) + "</span><h3>" + esc(b.name) + "</h3>" + verdictPill(b.verdict) + "</div>" +
        (b.category ? '<div class="acts"><span class="tag">' + esc(b.category) + "</span></div>" : "") +
        '<p class="one">' + esc(b.one_liner) + "</p>" +
        '<div class="metrics"><div><b>$' + num(f.startup_cost_usd) + "</b><small>起步资金</small></div><div><b>" + num(f.mvp_days) + " 天</b><small>上线 MVP</small></div><div><b>" + num(a.weekly_hours) + " 小时</b><small>稳定后每周</small></div></div>" +
        "<details><summary>怎么自动化运营</summary><dl class=\"kv\"><dt>获客</dt><dd>" + esc(a.acquisition) + "</dd><dt>生产交付</dt><dd>" + esc(a.production) + "</dd><dt>收款客服</dt><dd>" + esc(a.payment_support) + "</dd><dt>仍要我做</dt><dd>" + esc(a.manual) + "</dd></dl></details>" +
        "<details><summary>市场与机会</summary><dl class=\"kv\"><dt>需求</dt><dd>" + esc(m.demand) + "</dd><dt>收入证据</dt><dd>" + esc(m.revenue_evidence) + "</dd><dt>竞争</dt><dd>" + esc(m.competition) + "</dd></dl>" + (ev ? '<ul class="evidence">' + ev + "</ul>" : "") + "</details>" +
        "<details><summary>适不适合我</summary><dl class=\"kv\"><dt>要用的服务</dt><dd>" + esc(f.services) + "</dd><dt>匹配度</dt><dd>" + esc(f.match) + "</dd><dt>最大风险</dt><dd>" + esc(f.biggest_risk) + "</dd></dl></details>" +
        (b.source && b.source.url ? '<div class="stats">灵感来源：' + link(b.source.title || b.source.url, b.source.url) + "</div>" : "") +
        actBtns(d.date + "-" + b.id, true) + "</article>";
    }).join("") + "</div>";
  }
  function renderToday(d) {
    var counts = SEC.map(function (s) {
      return '<a href="#sec-' + s.key + '"><i>' + s.code + "</i><b>" + (d[s.key] || []).length + "</b><small>" + s.title + "</small></a>";
    }).join("");
    var body = SEC.map(function (s) {
      var fn = { news: renderNews, tools: renderTools, skills: renderSkills, opportunities: renderOpps }[s.key];
      return '<section class="sec" id="sec-' + s.key + '"><div class="sec-h"><span class="code">' + s.code + "</span><h2>" + s.title + '</h2><span class="cnt">' + (d[s.key] || []).length + " 条</span></div>" + fn(d) + "</section>";
    }).join("");
    var todo = (d.actions || []).length ? '<section class="sec"><div class="sec-h"><span class="code">→</span><h2>今天做什么</h2></div><ul class="todo">' +
      d.actions.map(function (t) { return '<li><span class="min">' + esc(t.minutes) + " 分钟</span><span>" + esc(t.text) + "</span></li>"; }).join("") + "</ul></section>" : "";
    var st = d.stats || {};
    app.innerHTML = '<div class="mast"><div class="date">' + fmtDate(d.date) + "</div><h1>今天值得看的 AI 与一人公司机会</h1>" +
      '<ol class="headline">' + (d.headline || []).map(function (h, i) { return '<li data-n="' + (i + 1) + '">' + esc(h) + "</li>"; }).join("") + "</ol></div>" +
      '<nav class="channels" aria-label="栏目">' + counts + "</nav>" + body + todo +
      '<p class="foot">今日扫描 ' + num(st.scanned) + " 条，入选 " + num(st.selected) + " 条。生成于 " + esc((d.generated_at || "").replace("T", " ").slice(0, 16)) + "。</p>";
  }

  /* ---------- 历史 ---------- */
  function renderHistory() {
    var ds = (state.index.dates || []);
    app.innerHTML = '<div class="mast"><h1>历史日报</h1></div><ul class="list">' + ds.map(function (x) {
      return '<li><button class="link" data-date="' + esc(x.date) + '">' + esc(x.date) + "</button><span>" + esc(x.headline || "") + '</span><span class="stats">资讯 ' + x.counts.news + " · 工具 " + x.counts.tools + " · Skills " + x.counts.skills + " · 机会 " + x.counts.opportunities + "</span></li>";
    }).join("") + "</ul>";
  }

  /* ---------- 收藏 ---------- */
  function favName(f) { var it = f.item || {}; return it.name || it.repo || it.title || f.id; }
  function renderFav() {
    var favs = state.index.favorites || [];
    if (!favs.length) { app.innerHTML = '<div class="mast"><h1>收藏</h1></div><p class="empty">还没有收藏。在日报里点「收藏」或「收藏并深挖」，几分钟后会出现在这里。</p>'; return; }
    var groups = {};
    favs.forEach(function (f) { (groups[f.library] = groups[f.library] || []).push(f); });
    var order = ["机会库", "工具库", "资讯库"];
    app.innerHTML = '<div class="mast"><h1>收藏</h1></div>' + order.filter(function (g) { return groups[g]; }).map(function (g) {
      return '<h2 class="group-h">' + g + '</h2><div class="cards">' + groups[g].map(function (f) {
        var dd = f.deepdive === "done" ? '<span class="pill good">深挖完成</span>' : f.deepdive === "pending" ? '<span class="pill warn">深挖中</span>' : "";
        var it = f.item || {};
        return '<article class="card" id="fav-' + esc(f.id) + '"><div class="card-top"><span class="id">' + esc(f.id) + "</span><h3>" + (it.url ? link(favName(f), it.url) : esc(favName(f))) + '</h3><span class="pill neutral">' + esc(f.status) + "</span>" + dd + "</div>" +
          "<p class=\"one\">" + esc(it.one_liner || it.what || it.summary || "") + "</p>" +
          (f.deepdive === "done" ? '<details data-deep="' + esc(f.id) + '"' + (state.focus === f.id ? " open" : "") + '><summary>深挖报告</summary><div class="deep" id="deep-' + esc(f.id) + '"><p class="empty">加载中……</p></div></details>' : "") +
          "</article>";
      }).join("") + "</div>";
    }).join("");
    Array.prototype.forEach.call(app.querySelectorAll("details[data-deep]"), function (el) {
      var load = function () { if (el.open) loadDeep(el.getAttribute("data-deep")); };
      el.addEventListener("toggle", load); load();
    });
    if (state.focus) { var t = document.getElementById("fav-" + state.focus); if (t) t.scrollIntoView(); }
  }
  function loadDeep(id) {
    var box = document.getElementById("deep-" + id);
    var put = function (md) { if (box) box.innerHTML = markdown(md); };
    if (state.deep[id]) return put(state.deep[id]);
    if (EMBED) return put((EMBED.deepdive || {})[id] || "没有找到深挖内容。");
    getText("data/deepdive/" + id + ".md").then(function (t) { state.deep[id] = t; put(t); }).catch(function () { put("没有找到深挖内容。"); });
  }

  /* ---------- 路由 ---------- */
  function loadDaily(date) {
    if (state.daily[date]) return Promise.resolve(state.daily[date]);
    if (EMBED) return Promise.resolve(EMBED.daily[date]);
    return getJSON("data/daily/" + date + ".json").then(function (d) { state.daily[date] = d; return d; });
  }
  function setTab(tab) {
    state.tab = tab;
    ["today", "history", "fav"].forEach(function (t) {
      var b = document.getElementById("tab-" + t);
      if (t === tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
  }
  function render() {
    setTab(state.tab);
    if (state.tab === "history") return renderHistory();
    if (state.tab === "fav") return renderFav();
    var date = state.date || (state.index.dates[0] || {}).date;
    if (!date) { app.innerHTML = '<p class="empty">还没有日报。第一期会在明早 8 点前生成。</p>'; return; }
    loadDaily(date).then(renderToday).catch(function () { app.innerHTML = '<p class="empty">这一期没加载出来，刷新试试。</p>'; });
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("button") : null;
    if (!t) return;
    if (t.hasAttribute("data-tab")) { state.tab = t.getAttribute("data-tab"); if (state.tab === "today") state.date = null; state.focus = null; render(); window.scrollTo(0, 0); }
    else if (t.hasAttribute("data-op")) doAction(t);
    else if (t.hasAttribute("data-date")) { state.tab = "today"; state.date = t.getAttribute("data-date"); render(); window.scrollTo(0, 0); }
  });

  function boot() {
    try {
      var qs = new URLSearchParams(location.search);
      if (qs.get("k")) { store("radar-key", qs.get("k")); qs.delete("k"); history.replaceState(null, "", location.pathname + (qs.toString() ? "?" + qs : "") + location.hash); }
      if (qs.get("tab")) state.tab = qs.get("tab");
      if (qs.get("date")) state.date = qs.get("date");
      if (qs.get("id")) state.focus = qs.get("id");
    } catch (e) { /* 预览环境里拿不到地址参数 */ }
    var ready = EMBED ? Promise.resolve([EMBED.index, EMBED.config || {}])
      : Promise.all([getJSON("data/index.json"), getJSON("config.json").catch(function () { return {}; })]);
    ready.then(function (r) { state.index = r[0]; state.config = r[1]; render(); })
      .catch(function () { app.innerHTML = '<p class="empty">数据没加载出来，刷新试试。</p>'; });
  }
  boot();
})();
