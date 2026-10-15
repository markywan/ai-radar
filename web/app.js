/* AI 机会雷达 前端。数据来自 data/*.json（GitHub Pages），或预览版里内嵌的 window.__RADAR__。 */
(function () {
  "use strict";
  var EMBED = window.__RADAR__ || null;
  var app = document.getElementById("app");
  var toastEl = document.getElementById("toast");
  var state = { index: null, config: {}, daily: {}, deep: {}, tab: "today", date: null, focus: null, gallery: {} };
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
  /* 正文里的 **重点** 和 `命令` */
  function rich(s) {
    return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  function safeUrl(u) { return /^(https?:\/\/|data:image\/)/i.test(u || "") ? esc(u) : "#"; }
  function link(text, url, cls) { return '<a' + (cls ? ' class="' + cls + '"' : "") + ' href="' + safeUrl(url) + '" target="_blank" rel="noopener">' + esc(text) + "</a>"; }
  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; }
    return null;
  }
  function toast(msg) {
    toastEl.textContent = msg; toastEl.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(function () { toastEl.hidden = true; }, 3200);
  }
  function weekday(d) { return "日一二三四五六".charAt(new Date(Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10))).getUTCDay()); }
  function fmtDate(d) { return d.slice(0, 4) + " 年 " + Number(d.slice(5, 7)) + " 月 " + Number(d.slice(8, 10)) + " 日 · 星期" + weekday(d); }
  function shortDate(d) { return Number(d.slice(5, 7)) + "月" + Number(d.slice(8, 10)) + "日"; }
  function getJSON(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.json(); });
  }
  function getText(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.text(); });
  }
  function safetyLight(s) {
    var c = s === "绿" ? "var(--good)" : s === "黄" ? "var(--warn)" : s === "红" ? "var(--bad)" : "var(--muted)";
    return '<span class="light" style="--lc:' + c + '">安全 ' + esc(s || "未查") + "</span>";
  }
  function riskBox(level, note) {
    if (!note) return "";
    if (level === "红") return '<div class="risk bad"><b>⚠ 风险提示</b>' + rich(note) + "</div>";
    if (level === "黄") return '<div class="risk warn"><b>注意</b>' + rich(note) + "</div>";
    return '<div class="risk ok">安全检查：' + rich(note) + "</div>";
  }
  function verdictPill(v) {
    var cls = v === "值得验证" ? "good" : v === "放进观察" ? "warn" : "neutral";
    return '<span class="pill ' + cls + '">' + esc(v) + "</span>";
  }
  function num(n) { return n == null ? "–" : Number(n).toLocaleString("en-US"); }
  function worker() { return (state.config.worker_url || "").replace(/\/$/, ""); }

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

  /* ---------- 已读状态：存在本机，配了 Worker 存储时多设备同步 ---------- */
  function readMap() { try { return JSON.parse(store("radar-read") || "{}"); } catch (e) { return {}; } }
  function isRead(date) { var v = readMap()[date]; return !!(v && v.v); }
  function setRead(date, v, quiet) {
    var m = readMap(); m[date] = { v: v ? 1 : 0, t: Date.now() }; store("radar-read", JSON.stringify(m));
    var key = store("radar-key");
    if (!EMBED && worker() && key) {
      fetch(worker() + "/read?date=" + encodeURIComponent(date) + "&v=" + (v ? 1 : 0) + "&k=" + encodeURIComponent(key), { method: "POST" }).catch(function () {});
    }
    updateBadges();
    if (!quiet) updateReadState(date);
  }
  function pullRead() {
    var key = store("radar-key");
    if (EMBED || !worker() || !key) return Promise.resolve();
    return fetch(worker() + "/state?k=" + encodeURIComponent(key), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !j.read) return;
        var m = readMap();
        Object.keys(j.read).forEach(function (d) { var s = j.read[d], l = m[d]; if (!l || (s.t || 0) > (l.t || 0)) m[d] = s; });
        store("radar-read", JSON.stringify(m));
      }).catch(function () {});
  }
  function dates() { return (state.index && state.index.dates) || []; }
  function latest() { return (dates()[0] || {}).date; }
  function unreadPast() { return dates().slice(1).filter(function (x) { return !isRead(x.date); }); }
  function updateBadges() {
    var t = document.getElementById("tab-today"), h = document.getElementById("tab-history");
    var dot = latest() && !isRead(latest()), n = unreadPast().length;
    var td = t.querySelector(".dot"); if (dot && !td) t.insertAdjacentHTML("beforeend", '<span class="dot" aria-label="未读"></span>'); if (!dot && td) td.remove();
    var hb = h.querySelector(".badge");
    if (n) { if (!hb) { h.insertAdjacentHTML("beforeend", '<span class="badge"></span>'); hb = h.querySelector(".badge"); } hb.textContent = n > 9 ? "9+" : n; hb.setAttribute("aria-label", n + " 期未读"); }
    else if (hb) hb.remove();
  }
  function readStateHtml(date) {
    return isRead(date)
      ? '<span class="read-state read">✓ 已读</span><button class="linkbtn" data-read="0" data-d="' + esc(date) + '">标为未读</button>'
      : '<span class="read-state unread">未读</span><button class="linkbtn" data-read="1" data-d="' + esc(date) + '">标为已读</button>';
  }
  function updateReadState(date) {
    var el = document.getElementById("read-" + date);
    if (el) el.innerHTML = readStateHtml(date);
  }
  function watchFoot(date) {
    var foot = document.getElementById("foot");
    if (!foot || isRead(date) || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); if (!isRead(date)) { setRead(date, true); toast("这一期已标为已读"); } }
    });
    io.observe(foot);
  }

  /* ---------- 收藏按钮 ---------- */
  function savedSet() { try { return JSON.parse(store("radar-saved") || "{}"); } catch (e) { return {}; } }
  function actBtns(fid, withDeep, extra) {
    var s = savedSet()[fid];
    var fav = '<button class="btn" data-op="fav" data-id="' + esc(fid) + '"' + (s ? ' data-done="1"' : "") + ">" + (s ? "★ 已收藏" : "☆ 收藏") + "</button>";
    var deep = withDeep ? '<button class="btn primary" data-op="deep" data-id="' + esc(fid) + '"' + (s === "deep" ? " disabled" : "") + ">" + (s === "deep" ? "深挖中" : "收藏并深挖") + "</button>" : "";
    return '<div class="acts">' + (extra || "") + fav + deep + "</div>";
  }
  function doAction(btn) {
    var op = btn.getAttribute("data-op"), fid = btn.getAttribute("data-id");
    var key = store("radar-key");
    if (EMBED && EMBED.preview) { toast("这是预览版，网站部署后按钮才能用"); return; }
    if (!worker() || !key) { toast("还没连上收藏接口：请从飞书卡片里的链接打开一次网站"); return; }
    btn.disabled = true;
    fetch(worker() + "/act?op=" + op + "&id=" + encodeURIComponent(fid) + "&k=" + encodeURIComponent(key), { method: "POST" })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok || !j.ok) throw new Error(j.message || "失败"); return j; }); })
      .then(function () {
        var s = savedSet(); s[fid] = op === "deep" ? "deep" : (s[fid] || "fav"); store("radar-saved", JSON.stringify(s));
        toast(op === "deep" ? "已收藏，Claude 开始深挖，完成后飞书通知你" : "已收藏，几分钟后出现在收藏页");
        var box = btn.parentNode, fav = box && box.querySelector('[data-op="fav"]');
        if (fav) { fav.setAttribute("data-done", "1"); fav.textContent = "★ 已收藏"; fav.disabled = false; }
        if (op === "deep") { btn.textContent = "深挖中"; btn.disabled = true; }
      })
      .catch(function (e) { btn.disabled = false; toast("没成功：" + e.message); });
  }

  /* ---------- 配图与看大图 ---------- */
  function media(gid, imgs) {
    imgs = (imgs || []).filter(function (u) { return /^(https?:\/\/|data:image\/)/i.test(u); });
    if (!imgs.length) return "";
    state.gallery[gid] = imgs;
    var shown = imgs.slice(0, 3);
    return '<div class="media">' + shown.map(function (u, i) {
      var more = i === 2 && imgs.length > 3 ? '<span class="more">+' + (imgs.length - 3) + "</span>" : "";
      return '<button class="thumb" data-g="' + esc(gid) + '" data-i="' + i + '" aria-label="看大图 ' + (i + 1) + "/" + imgs.length + '"><img src="' + safeUrl(u) + '" alt="" loading="lazy" referrerpolicy="no-referrer">' + more + "</button>";
    }).join("") + "</div>";
  }
  var lb = null;
  function openLightbox(gid, i) {
    var imgs = state.gallery[gid]; if (!imgs) return;
    if (!lb) {
      lb = document.createElement("div"); lb.className = "lb"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-label", "看大图");
      lb.innerHTML = '<div class="lb-top"><span class="lb-n"></span><button class="lb-x">关闭</button></div><div class="lb-img"><img alt="" referrerpolicy="no-referrer"></div><div class="lb-nav"><button class="lb-p">上一张</button><button class="lb-nx">下一张</button></div>';
      document.body.appendChild(lb);
      lb.addEventListener("click", function (e) {
        if (e.target.closest(".lb-p")) show(lb.i - 1);
        else if (e.target.closest(".lb-nx")) show(lb.i + 1);
        else if (e.target.closest(".lb-x") || !e.target.closest("button, img")) close();
      });
      var x0 = null;
      lb.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
      lb.addEventListener("touchend", function (e) { if (x0 == null) return; var dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 50) show(lb.i + (dx < 0 ? 1 : -1)); x0 = null; });
      document.addEventListener("keydown", function (e) {
        if (lb.hidden) return;
        if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") show(lb.i - 1); else if (e.key === "ArrowRight") show(lb.i + 1);
      });
    }
    function show(k) {
      if (k < 0 || k >= lb.imgs.length) return;
      lb.i = k; lb.querySelector("img").src = lb.imgs[k];
      lb.querySelector(".lb-n").textContent = (k + 1) + " / " + lb.imgs.length;
      lb.querySelector(".lb-p").disabled = k === 0; lb.querySelector(".lb-nx").disabled = k === lb.imgs.length - 1;
    }
    function close() { lb.hidden = true; document.body.style.overflow = ""; }
    lb.show = show; lb.imgs = imgs; lb.hidden = false; document.body.style.overflow = "hidden"; show(i);
  }

  /* ---------- 今日 ---------- */
  function usesList(list, fallback) {
    if (list && list.length) return '<div><p class="label">一人公司能怎么用</p><ul class="uses">' + list.map(function (u) { return '<li><span class="area">' + esc(u.area) + "</span><span>" + rich(u.how) + "</span></li>"; }).join("") + "</ul></div>";
    return fallback ? '<div><p class="label">对我有用</p><div>' + rich(fallback) + "</div></div>" : "";
  }
  function renderNews(d) {
    if (!d.news.length) return '<p class="empty">今日无</p>';
    return '<ul class="news">' + d.news.map(function (n) {
      var fid = d.date + "-" + n.id;
      var meta = (n.source_type === "X" ? '<span class="x">X</span>' : "") + "<span>" + esc(n.source || n.source_type || "") + "</span>" + (n.published ? "<span>· " + esc(n.published.slice(5)) + "</span>" : "");
      return '<li><span class="id">' + esc(n.id) + '</span><div><button class="nw-t" aria-expanded="false" aria-controls="nd-' + esc(n.id) + '">' + rich(n.title) + '</button><div class="nw-m">' + meta + "</div>" +
        '<div class="nw-d" id="nd-' + esc(n.id) + '" hidden><p>' + rich(n.summary) + "</p>" + actBtns(fid, false, link("看原文 ↗", n.url, "btn")) + "</div></div></li>";
    }).join("") + "</ul>";
  }
  function renderTools(d) {
    if (!d.tools.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.tools.map(function (t) {
      var gid = d.date + "-" + t.id, m = media(gid, t.images);
      return '<article class="card' + (m ? " has-media" : "") + '"><div class="c-head"><div class="card-top"><span class="id">' + esc(t.id) + '</span><h3 class="repo">' + link(t.repo, t.url) + "</h3></div>" +
        '<div class="stats">' + (t.stars_today != null ? '<span class="up">▲ ' + num(t.stars_today) + " 今日</span>" : "") + "<span>★ " + num(t.stars_total) + "</span><span>" + esc(t.license || "许可证未知") + "</span>" + safetyLight(t.safety) + "</div>" +
        (t.uses && t.uses.length ? "" : '<div class="tags">' + (t.tags || []).map(function (g) { return '<span class="tag">' + esc(g) + "</span>"; }).join("") + "</div>") + "</div>" +
        '<p class="c-what">' + rich(t.what) + "</p>" + m +
        '<div class="c-rest">' + usesList(t.uses, t.use_for_me) +
        (t.setup ? '<dl class="kv"><dt>上手</dt><dd>' + rich(t.setup) + "</dd></dl>" : "") + riskBox(t.safety, t.safety_note) +
        actBtns(gid, true) + "</div></article>";
    }).join("") + "</div>";
  }
  function renderSkills(d) {
    if (!d.skills.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.skills.map(function (s) {
      var gid = d.date + "-" + s.id, m = media(gid, s.images);
      var hot = s.hot ? '<span class="pill ' + (s.hot === "新晋热门" ? "hot" : "evergreen") + '">' + esc(s.hot) + "</span>" : "";
      return '<article class="card' + (m ? " has-media" : "") + '"><div class="c-head"><div class="card-top"><span class="id">' + esc(s.id) + "</span><h3>" + link(s.name, s.url) + "</h3>" + hot + "</div>" +
        '<div class="stats">' + (s.stars_total != null ? "<span>★ " + num(s.stars_total) + "</span>" : "") + (s.installs != null ? "<span>⤓ " + num(s.installs) + " 安装</span>" : "") + "<span>" + esc(s.works_with || "") + "</span>" + safetyLight(s.safety) + "</div>" +
        (s.popularity_note ? '<p class="note">' + rich(s.popularity_note) + "</p>" : "") + "</div>" +
        '<p class="c-what">' + rich(s.what) + "</p>" + m +
        '<div class="c-rest">' + usesList(s.uses, s.how_i_use) + riskBox(s.safety, s.safety_note) +
        (s.install ? '<dl class="kv"><dt>安装</dt><dd>' + rich(s.install) + "</dd></dl>" : "") +
        actBtns(gid, true) + "</div></article>";
    }).join("") + "</div>";
  }
  function renderOpps(d) {
    if (!d.opportunities.length) return '<p class="empty">今日无</p>';
    return '<div class="cards">' + d.opportunities.map(function (b) {
      var a = b.automation || {}, m = b.market || {}, f = b.fit || {};
      var ev = (m.evidence_links || []).map(function (e) { return "<li>" + link(e.title, e.url) + "</li>"; }).join("");
      return '<article class="card opp"><div class="card-top"><span class="id">' + esc(b.id) + "</span><h3>" + esc(b.name) + "</h3>" + verdictPill(b.verdict) + "</div>" +
        (b.category ? '<div class="tags"><span class="tag">' + esc(b.category) + "</span></div>" : "") +
        '<p class="one">' + rich(b.one_liner) + "</p>" +
        '<div class="metrics"><div><b>$' + num(f.startup_cost_usd) + "</b><small>起步资金</small></div><div><b>" + num(f.mvp_days) + " 天</b><small>上线 MVP</small></div><div><b>" + num(a.weekly_hours) + " 小时</b><small>稳定后每周</small></div></div>" +
        "<details><summary>怎么自动化运营</summary><dl class=\"kv\"><dt>获客</dt><dd>" + rich(a.acquisition) + "</dd><dt>生产交付</dt><dd>" + rich(a.production) + "</dd><dt>收款客服</dt><dd>" + rich(a.payment_support) + "</dd><dt>仍要我做</dt><dd>" + rich(a.manual) + "</dd></dl></details>" +
        "<details><summary>市场与机会</summary><dl class=\"kv\"><dt>需求</dt><dd>" + rich(m.demand) + "</dd><dt>收入证据</dt><dd>" + rich(m.revenue_evidence) + "</dd><dt>竞争</dt><dd>" + rich(m.competition) + "</dd></dl>" + (ev ? '<ul class="evidence">' + ev + "</ul>" : "") + "</details>" +
        "<details><summary>适不适合我</summary><dl class=\"kv\"><dt>要用的服务</dt><dd>" + rich(f.services) + "</dd><dt>匹配度</dt><dd>" + rich(f.match) + "</dd><dt>最大风险</dt><dd>" + rich(f.biggest_risk) + "</dd></dl></details>" +
        (b.source && b.source.url ? '<div class="stats">灵感来源：' + link(b.source.title || b.source.url, b.source.url) + "</div>" : "") +
        actBtns(d.date + "-" + b.id, true) + "</article>";
    }).join("") + "</div>";
  }
  function renderToday(d) {
    state.gallery = {};
    var isLatest = d.date === latest();
    var counts = SEC.map(function (s) {
      return '<a href="#sec-' + s.key + '" data-k="' + s.key + '"><i>' + s.code + "</i><b>" + (d[s.key] || []).length + "</b><small>" + s.title + "</small></a>";
    }).join("");
    var body = SEC.map(function (s) {
      var fn = { news: renderNews, tools: renderTools, skills: renderSkills, opportunities: renderOpps }[s.key];
      var tool = s.key === "news" && d.news.length ? '<button class="linkbtn" data-expand="news">全部展开</button>' : "";
      return '<section class="sec" id="sec-' + s.key + '" data-k="' + s.key + '"><div class="sec-h"><span class="code">' + s.code + "</span><h2>" + s.title + "</h2>" + tool + '<span class="cnt">' + (d[s.key] || []).length + " 条</span></div>" + fn(d) + "</section>";
    }).join("");
    var todo = (d.actions || []).length ? '<section class="sec" data-k="todo"><div class="sec-h"><span class="code">→</span><h2>今天做什么</h2></div><ul class="todo">' +
      d.actions.map(function (t) { return '<li><span class="min">' + esc(t.minutes) + " 分钟</span><span>" + rich(t.text) + "</span></li>"; }).join("") + "</ul></section>" : "";
    var back = isLatest ? unreadPast() : [];
    var backlog = back.length ? '<div class="backlog"><span><b>●</b> 还有 ' + back.length + " 期没看：</span>" + back.slice(0, 6).map(function (x) { return '<button data-date="' + esc(x.date) + '">' + shortDate(x.date) + "</button>"; }).join("") + "</div>" : "";
    var st = d.stats || {};
    app.innerHTML = '<div class="mast" data-k="tools"><div class="mast-top"><span class="date">' + fmtDate(d.date) + '</span><span id="read-' + esc(d.date) + '" class="mast-top">' + readStateHtml(d.date) + "</span></div>" +
      "<h1>" + (isLatest ? "今天值得看的 AI 与一人公司机会" : shortDate(d.date) + "的日报") + "</h1>" +
      '<ol class="headline">' + (d.headline || []).map(function (h, i) { return '<li data-n="' + (i + 1) + '">' + rich(h) + "</li>"; }).join("") + "</ol>" + backlog + "</div>" +
      '<nav class="channels" aria-label="栏目">' + counts + "</nav>" + body + todo +
      '<div class="foot" id="foot"><span>扫描 ' + num(st.scanned) + " 条，入选 " + num(st.selected) + " 条。生成于 " + esc((d.generated_at || "").replace("T", " ").slice(0, 16)) + "。</span><span>看到这里就算这一期看过了。</span></div>";
    watchFoot(d.date);
  }

  /* ---------- 历史：没看的和看过的分开 ---------- */
  function dayItem(x) {
    var c = x.counts || {}, r = isRead(x.date);
    return '<li class="' + (r ? "read" : "unread") + '"><button data-date="' + esc(x.date) + '"><span class="d">' + (r ? "" : "● ") + esc(x.date) + " · 星期" + weekday(x.date) + (r ? " · 已读" : " · 未读") + '</span><span class="h">' + esc(String(x.headline || "").replace(/\*\*/g, "")) + '</span><span class="stats">资讯 ' + (c.news || 0) + " · 工具 " + (c.tools || 0) + " · Skills " + (c.skills || 0) + " · 机会 " + (c.opportunities || 0) + "</span></button></li>";
  }
  function renderHistory() {
    var past = dates().slice(1);
    if (!past.length) { app.innerHTML = '<div class="mast"><h1>历史日报</h1></div><p class="empty">还没有往期。明天新的一期出来后，今天这期会移到这里；没看过的会标红。</p>'; return; }
    var un = past.filter(function (x) { return !isRead(x.date); }), rd = past.filter(function (x) { return isRead(x.date); });
    app.innerHTML = '<div class="mast"><h1>历史日报</h1></div>' +
      (un.length ? '<h2 class="group-h unread">没看的 <small>' + un.length + ' 期</small></h2><ul class="days">' + un.map(dayItem).join("") + "</ul>" : "") +
      (rd.length ? '<h2 class="group-h">看过的 <small>' + rd.length + ' 期</small></h2><ul class="days">' + rd.map(dayItem).join("") + "</ul>" : "");
  }

  /* ---------- 收藏 ---------- */
  function favName(f) { var it = f.item || {}; return it.name || it.repo || it.title || f.id; }
  function renderFav() {
    var favs = state.index.favorites || [];
    if (!favs.length) { app.innerHTML = '<div class="mast"><h1>收藏</h1></div><p class="empty">还没有收藏。在日报里点「收藏」或「收藏并深挖」，几分钟后会出现在这里。</p>'; return; }
    var groups = {};
    favs.forEach(function (f) { (groups[f.library] = groups[f.library] || []).push(f); });
    var order = [["机会库", "opportunities"], ["工具库", "tools"], ["资讯库", "news"]];
    app.innerHTML = '<div class="mast"><h1>收藏</h1></div>' + order.filter(function (g) { return groups[g[0]]; }).map(function (g) {
      return '<section class="sec" data-k="' + g[1] + '"><div class="sec-h"><h2>' + g[0] + '</h2><span class="cnt">' + groups[g[0]].length + ' 条</span></div><div class="cards">' + groups[g[0]].map(function (f) {
        var dd = f.deepdive === "done" ? '<span class="pill good">深挖完成</span>' : f.deepdive === "pending" ? '<span class="pill warn">深挖中</span>' : "";
        var it = f.item || {};
        return '<article class="card" id="fav-' + esc(f.id) + '"><div class="card-top"><span class="id">' + esc(f.id) + "</span><h3>" + (it.url ? link(favName(f), it.url) : esc(favName(f))) + '</h3><span class="pill neutral">' + esc(f.status) + "</span>" + dd + "</div>" +
          '<p class="one">' + rich(it.one_liner || it.what || it.summary || "") + "</p>" +
          (f.deepdive === "done" ? '<details data-deep="' + esc(f.id) + '"' + (state.focus === f.id ? " open" : "") + '><summary>深挖报告</summary><div class="deep" id="deep-' + esc(f.id) + '"><p class="empty">加载中……</p></div></details>' : "") +
          "</article>";
      }).join("") + "</div></section>";
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
      if (t === tab && !(t === "today" && state.date && state.date !== latest())) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
  }
  function render() {
    setTab(state.tab);
    updateBadges();
    if (state.tab === "history") return renderHistory();
    if (state.tab === "fav") return renderFav();
    var date = state.date || latest();
    if (!date) { app.innerHTML = '<p class="empty">还没有日报。第一期会在明早 8 点前生成。</p>'; return; }
    loadDaily(date).then(renderToday).catch(function () { app.innerHTML = '<p class="empty">这一期没加载出来，刷新试试。</p>'; });
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("button") : null;
    if (!t) return;
    if (t.hasAttribute("data-tab")) { state.tab = t.getAttribute("data-tab"); if (state.tab === "today") state.date = null; state.focus = null; render(); window.scrollTo(0, 0); }
    else if (t.hasAttribute("data-op")) doAction(t);
    else if (t.hasAttribute("data-date")) { state.tab = "today"; state.date = t.getAttribute("data-date"); render(); window.scrollTo(0, 0); }
    else if (t.hasAttribute("data-g")) openLightbox(t.getAttribute("data-g"), +t.getAttribute("data-i"));
    else if (t.hasAttribute("data-read")) setRead(t.getAttribute("data-d"), t.getAttribute("data-read") === "1");
    else if (t.classList.contains("nw-t")) {
      var open = t.getAttribute("aria-expanded") !== "true";
      t.setAttribute("aria-expanded", open); document.getElementById(t.getAttribute("aria-controls")).hidden = !open;
    } else if (t.hasAttribute("data-expand")) {
      var all = app.querySelectorAll(".nw-t"), anyClosed = Array.prototype.some.call(all, function (b) { return b.getAttribute("aria-expanded") !== "true"; });
      Array.prototype.forEach.call(all, function (b) { b.setAttribute("aria-expanded", anyClosed); document.getElementById(b.getAttribute("aria-controls")).hidden = !anyClosed; });
      t.textContent = anyClosed ? "全部收起" : "全部展开";
    }
  });

  /* 打不开的配图直接拿掉，一张都不剩时卡片恢复单栏 */
  document.addEventListener("error", function (e) {
    var img = e.target;
    if (!img || img.tagName !== "IMG" || !img.closest) return;
    var th = img.closest(".thumb"); if (!th) return;
    var box = th.parentNode, card = box && box.closest(".card");
    th.remove();
    if (box && !box.querySelector(".thumb")) { box.remove(); if (card) card.classList.remove("has-media"); }
  }, true);

  /* 顶栏高度给吸顶的栏目标题定位 */
  function syncBar() {
    var bar = document.querySelector(".bar");
    if (bar) document.documentElement.style.setProperty("--bar-h", bar.offsetHeight + "px");
  }
  window.addEventListener("resize", syncBar);

  function boot() {
    syncBar();
    try {
      var qs = new URLSearchParams(location.search);
      if (qs.get("k")) { store("radar-key", qs.get("k")); qs.delete("k"); history.replaceState(null, "", location.pathname + (qs.toString() ? "?" + qs : "") + location.hash); }
      if (qs.get("tab")) state.tab = qs.get("tab");
      if (qs.get("date")) state.date = qs.get("date");
      if (qs.get("id")) state.focus = qs.get("id");
    } catch (e) { /* 预览环境里拿不到地址参数 */ }
    var ready = EMBED ? Promise.resolve([EMBED.index, EMBED.config || {}])
      : Promise.all([getJSON("data/index.json"), getJSON("config.json").catch(function () { return {}; })]);
    ready.then(function (r) { state.index = r[0]; state.config = r[1]; return pullRead(); })
      .then(render)
      .catch(function () { app.innerHTML = '<p class="empty">数据没加载出来，刷新试试。</p>'; });
  }
  boot();
})();
