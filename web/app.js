/* AI 机会雷达 前端。数据来自 data/*.json（GitHub Pages），或预览版里内嵌的 window.__RADAR__。
   每条先露出一行能做判断的信息（名字、一句话、热度、安全），点开才看细节和配图。 */
(function () {
  "use strict";
  var EMBED = window.__RADAR__ || null;
  var app = document.getElementById("app");
  var toastEl = document.getElementById("toast");
  var state = { index: null, config: {}, daily: {}, deep: {}, tab: "today", date: null, focus: null, gallery: {} };
  var SEC = [
    { key: "news", title: "AI 资讯", short: "资讯" },
    { key: "tools", title: "GitHub 工具", short: "工具" },
    { key: "skills", title: "Skills", short: "Skills" },
    { key: "opportunities", title: "一人公司机会", short: "机会" },
    { key: "trends", title: "玩法风向", short: "玩法" }
  ];
  var LEAD_KEYS = ["news", "tools", "opportunities"];

  /* ---------- 小工具 ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /* 正文里的 **重点** 和 `命令`。返回的是行内内容，调用处要放进一个块元素里 */
  function rich(s) {
    return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  function plain(s) { return String(s || "").replace(/\*\*|`/g, ""); }
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
  function shortDate(d) { return Number(d.slice(5, 7)) + " 月 " + Number(d.slice(8, 10)) + " 日"; }
  function longDate(d) { return shortDate(d) + " · 星期" + weekday(d); }
  function getJSON(path) { return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.json(); }); }
  function getText(path) { return fetch(path, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(path); return r.text(); }); }
  function num(n) { return n == null ? "–" : Number(n).toLocaleString("en-US"); }
  /* 6.7 万、1.04 万这种中文读法 */
  function wan(n) {
    if (n == null) return "–";
    n = Number(n);
    if (n < 10000) return n.toLocaleString("en-US");
    var v = n / 10000, d = v >= 100 ? 0 : v >= 10 ? 1 : 2;
    return String(Number(v.toFixed(d))) + " 万";
  }
  function worker() { return (state.config.worker_url || "").replace(/\/$/, ""); }
  function licenseShort(l) { return String(l || "").split(/[（(，,；;]/)[0].trim(); }
  /* 「anatomy（等距交互原理图）」拆成名字和注释 */
  function splitName(s) { var m = String(s || "").match(/^(.+?)\s*[（(](.+)[）)]\s*$/); return m ? [m[1], m[2]] : [String(s || ""), ""]; }
  function briefOf(it) {
    if (it.brief) return it.brief;
    var w = plain(it.what || it.one_liner || it.summary);
    var cut = w.search(/[。：:；]/);
    return cut > 8 ? w.slice(0, cut) : w.slice(0, 40);
  }
  function safeTag(s) {
    var cls = s === "绿" ? "g" : s === "黄" ? "y" : s === "红" ? "r" : "";
    return cls ? '<span class="safe ' + cls + '">安全 ' + esc(s) + "</span>" : "";
  }
  /* 安全说明：一句结论、「怎么防」，长的检查依据折起来，点开再看 */
  function riskBox(it) {
    var level = it.safety, note = String(it.safety_note || ""), rb = it.risk_brief;
    if (!note && !rb) return "";
    var long = function (s) { return plain(s).length > 120; };
    var fold = function (label, s) { return '<details class="audit"><summary>' + label + "</summary><p>" + rich(s) + "</p></details>"; };
    if (level === "红" || level === "黄") {
      var m = note.match(/^([\s\S]*?)\s*防范[:：]\s*([\s\S]+)$/);
      var basis = (m ? m[1] : note).trim(), fix = m ? m[2].trim() : "";
      return '<div class="risk ' + (level === "红" ? "bad" : "warn") + '"><span class="rh"><b>' + (level === "红" ? "⚠ 风险高" : "注意") + "</b>" + esc(rb || "") + "</span>" +
        (fix ? '<p class="fix"><b>怎么防</b>' + rich(fix) + "</p>" : "") +
        (!basis ? "" : long(basis) ? fold("看检查依据", basis) : "<p>" + rich(basis) + "</p>") + "</div>";
    }
    if (long(note)) return '<div class="risk ok">' + fold('<span class="rh">✓ 安全检查通过</span>看依据', note) + "</div>";
    return '<div class="risk ok"><p><span class="rh">✓ 安全检查</span>' + rich(note) + "</p></div>";
  }
  function verdictPill(v) {
    var cls = v === "值得验证" ? "good" : v === "放进观察" ? "warn" : "neutral";
    return '<span class="verdict ' + cls + '">' + esc(v) + "</span>";
  }

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
  function issueNo(date) { var ds = dates(); for (var i = 0; i < ds.length; i++) if (ds[i].date === date) return ds.length - i; return null; }
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
      ? '<b class="read">✓ 已读</b><button class="linkbtn" data-read="0" data-d="' + esc(date) + '">标为未读</button>'
      : '<b class="unread">未读</b><button class="linkbtn" data-read="1" data-d="' + esc(date) + '">标为已读</button>';
  }
  function updateReadState(date) { var el = document.getElementById("read-" + date); if (el) el.innerHTML = readStateHtml(date); }
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

  /* ---------- 配图：右侧一张封面，点开后一排缩略图，点任意一张看大图 ---------- */
  function images(gid, list) {
    var imgs = (list || []).filter(function (u) { return /^(https?:\/\/|data:image\/)/i.test(u); });
    state.gallery[gid] = imgs;
    return imgs;
  }
  function imgTag(u, k) { return '<img src="' + safeUrl(u) + '" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-k="' + k + '">'; }
  function cover(gid, imgs) {
    if (!imgs.length) return "";
    return '<span class="thumb" data-g="' + esc(gid) + '" data-i="0" role="img" aria-label="配图，共 ' + imgs.length + ' 张">' + imgTag(imgs[0], 0) +
      (imgs.length > 1 ? '<span class="n">' + imgs.length + " 图</span>" : "") + "</span>";
  }
  function strip(gid, imgs) {
    if (!imgs.length) return "";
    return '<div class="strip' + (imgs.length === 1 ? " one" : "") + '">' + imgs.map(function (u, i) {
      return '<button class="shot" data-g="' + esc(gid) + '" data-i="' + i + '" aria-label="看大图 ' + (i + 1) + "/" + imgs.length + '">' + imgTag(u, i) + "</button>";
    }).join("") + "</div>";
  }
  var lb = null;
  function openLightbox(gid, i) {
    var imgs = state.gallery[gid]; if (!imgs || !imgs.length) return;
    if (!lb) {
      lb = document.createElement("div"); lb.className = "lb"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-label", "看大图");
      lb.innerHTML = '<div class="lb-top"><span class="lb-n"></span><button class="lb-x">关闭</button></div><div class="lb-img"><img alt="" referrerpolicy="no-referrer"></div><div class="lb-nav"><button class="lb-p">上一张</button><button class="lb-nx">下一张</button></div>';
      document.body.appendChild(lb);
      lb.addEventListener("click", function (e) {
        if (e.target.closest(".lb-p")) lb.show(lb.i - 1);
        else if (e.target.closest(".lb-nx")) lb.show(lb.i + 1);
        else if (e.target.closest(".lb-x") || !e.target.closest("button, img")) close();
      });
      var x0 = null;
      lb.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
      lb.addEventListener("touchend", function (e) { if (x0 == null) return; var dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 50) lb.show(lb.i + (dx < 0 ? 1 : -1)); x0 = null; });
      document.addEventListener("keydown", function (e) {
        if (lb.hidden) return;
        if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") lb.show(lb.i - 1); else if (e.key === "ArrowRight") lb.show(lb.i + 1);
      });
      lb.show = function (k) {
        if (k < 0 || k >= lb.imgs.length) return;
        lb.i = k; lb.querySelector(".lb-img img").src = lb.imgs[k];
        lb.querySelector(".lb-n").textContent = (k + 1) + " / " + lb.imgs.length;
        lb.querySelector(".lb-p").disabled = k === 0; lb.querySelector(".lb-nx").disabled = k === lb.imgs.length - 1;
      };
    }
    function close() { lb.hidden = true; document.body.style.overflow = ""; }
    lb.imgs = imgs; lb.hidden = false; document.body.style.overflow = "hidden"; lb.show(i);
  }

  /* ---------- 今日 ---------- */
  function secHead(s, count, tool) {
    return '<div class="sec-h"><h2>' + esc(s.title) + '</h2><span class="cnt">' + count + "</span>" + (tool || "") + "</div>";
  }
  function expandTool(key) { return '<button class="tool" data-expand="' + key + '">全部展开</button>'; }
  var FOLD = '<button class="fold" data-fold>收起</button>';
  function renderNews(d) {
    if (!d.news.length) return '<p class="empty">今天没有入选的资讯。</p>';
    return '<ul class="list">' + d.news.map(function (n) {
      var fid = d.date + "-" + n.id, bid = "b-" + n.id;
      return '<li class="row news-row"><button class="row-h" aria-expanded="false" aria-controls="' + bid + '">' +
        '<span class="t">' + rich(n.title) + '</span><span class="chev" aria-hidden="true"></span></button>' +
        '<div class="row-b" id="' + bid + '" hidden><p class="sum">' + rich(n.summary) + "</p>" + actBtns(fid, false, link("看原文 ↗", n.url, "btn")) + FOLD + "</div></li>";
    }).join("") + "</ul>";
  }
  function itemRow(kind, d, it) {
    var gid = d.date + "-" + it.id, bid = "b-" + it.id, imgs = images(gid, it.images);
    var name, sub, meta = [];
    if (kind === "tools") {
      var parts = String(it.repo || "").split("/");
      name = parts[1] || it.repo; sub = parts[1] ? parts[0] : "";
      meta.push("<span>★ " + wan(it.stars_total) + "</span>");
      if (it.stars_today != null) meta.push('<span class="up">今日 +' + num(it.stars_today) + "</span>");
    } else {
      var nm = splitName(it.name); name = nm[0]; sub = it.brief ? "" : nm[1];
      if (it.hot === "新晋热门") meta.push('<span class="hot">新晋热门</span>');
      if (it.stars_total != null) meta.push("<span>★ " + wan(it.stars_total) + "</span>");
      if (it.installs != null) meta.push("<span>" + wan(it.installs) + " 安装</span>");
    }
    meta.push(safeTag(it.safety));
    var areas = (it.uses || []).map(function (u) { return u.area; });
    if (!areas.length) areas = it.tags || [];
    var head = '<button class="row-h" aria-expanded="false" aria-controls="' + bid + '">' + cover(gid, imgs) +
      '<span class="t">' + esc(name) + (sub ? '<span class="sub">' + esc(sub) + "</span>" : "") + "</span>" +
      '<span class="brief">' + esc(plain(briefOf(it))) + "</span>" +
      '<span class="m">' + meta.join("") + "</span>" +
      '<span class="areas"><span class="a">' + (areas.length ? "用在：" + esc(areas.join(" · ")) : "") + '</span><span class="more-l">详情</span></span></button>';
    var risk = it.safety === "红" ? '<p class="risk-line"><b>⚠ 风险高</b>' + esc(it.risk_brief || "点开看风险说明") + "</p>" : "";
    var uses = (it.uses || []).length
      ? '<div><p class="label">一人公司能怎么用</p><dl class="uses">' + it.uses.map(function (u) { return "<dt>" + esc(u.area) + "</dt><dd>" + rich(u.how) + "</dd>"; }).join("") + "</dl></div>"
      : (it.use_for_me || it.how_i_use ? '<div><p class="label">对我有用</p><p>' + rich(it.use_for_me || it.how_i_use) + "</p></div>" : "");
    var facts = [];
    if (it.setup) facts.push(["上手", rich(it.setup)]);
    if (it.install) facts.push(["安装", rich(it.install)]);
    if (it.popularity_note) facts.push(["热度", rich(it.popularity_note)]);
    if (kind === "tools" && it.license) facts.push(["许可证", esc(it.license)]);
    if (it.works_with) facts.push(["适用于", esc(it.works_with)]);
    var factsHtml = facts.length ? '<dl class="facts">' + facts.map(function (f) { return "<dt>" + f[0] + "</dt><dd>" + f[1] + "</dd>"; }).join("") + "</dl>" : "";
    var red = it.safety === "红";  /* 红色条目点开后先看风险 */
    var body = '<div class="row-b" id="' + bid + '" hidden>' + (red ? riskBox(it) : "") + '<p class="what">' + rich(it.what) + "</p>" + strip(gid, imgs) + uses + factsHtml + (red ? "" : riskBox(it)) +
      actBtns(gid, true, link(kind === "tools" ? "GitHub ↗" : "看仓库 ↗", it.url, "btn")) + FOLD + "</div>";
    return '<li class="row item' + (imgs.length ? " has-img" : "") + '">' + head + risk + body + "</li>";
  }
  function renderItems(kind) {
    return function (d) {
      var list = d[kind] || [];
      if (!list.length) return '<p class="empty">今天没有入选的' + (kind === "tools" ? "工具" : " Skills") + "。</p>";
      return '<ul class="list">' + list.map(function (it) { return itemRow(kind, d, it); }).join("") + "</ul>";
    };
  }
  function renderOpps(d) {
    if (!d.opportunities.length) return '<p class="empty">今天没有合格的机会，不凑数。</p>';
    return '<div class="opps">' + d.opportunities.map(function (b) {
      var a = b.automation || {}, m = b.market || {}, f = b.fit || {}, nm = splitName(b.name);
      var ev = (m.evidence_links || []).map(function (e) { return "<li>" + link(e.title, e.url) + "</li>"; }).join("");
      var dl = function (rows) { return '<dl class="facts">' + rows.filter(function (r) { return r[1]; }).map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + rich(r[1]) + "</dd>"; }).join("") + "</dl>"; };
      return '<article class="opp"><div class="top">' + verdictPill(b.verdict) + (b.category ? "<span>" + esc(b.category) + "</span>" : "") + "</div>" +
        "<h3>" + esc(nm[0]) + (nm[1] ? '<span class="sub">' + esc(nm[1]) + "</span>" : "") + "</h3>" +
        '<p class="one">' + rich(b.one_liner) + "</p>" +
        '<div class="metrics"><div><b>$' + num(f.startup_cost_usd) + "</b><small>起步资金</small></div><div><b>" + num(f.mvp_days) + " 天</b><small>做出 MVP</small></div><div><b>" + num(a.weekly_hours) + " 小时</b><small>稳定后每周</small></div></div>" +
        '<div class="fold-g"><details><summary>怎么自动化运营</summary>' + dl([["获客", a.acquisition], ["生产交付", a.production], ["收款客服", a.payment_support], ["仍要我做", a.manual]]) + "</details>" +
        "<details><summary>市场与机会</summary>" + dl([["需求", m.demand], ["收入证据", m.revenue_evidence], ["竞争", m.competition]]) + (ev ? '<ul class="evidence">' + ev + "</ul>" : "") + "</details>" +
        "<details><summary>适不适合我</summary>" + dl([["要用的服务", f.services], ["匹配度", f.match], ["最大风险", f.biggest_risk]]) + "</details></div>" +
        (b.source && b.source.url ? '<p class="src">灵感来源：' + link(b.source.title || b.source.url, b.source.url) + "</p>" : "") +
        actBtns(d.date + "-" + b.id, true) + "</article>";
    }).join("") + "</div>";
  }
  /* 玩法风向：X、小红书、抖音、TikTok 等平台上的新玩法、使用技巧、爆款形式和需求原话，证据带数字和链接 */
  function renderTrends(d) {
    var list = d.trends || [];
    if (!list.length) return '<p class="empty">今天平台上没有像样的信号，不凑数。</p>';
    return '<ul class="list">' + list.map(function (it) {
      var gid = d.date + "-" + it.id, bid = "b-" + it.id, ev = it.evidence || [], qs = it.quotes || [];
      var plats = (it.platforms && it.platforms.length ? it.platforms : ev.map(function (e) { return e.platform; }))
        .filter(function (x, i, a) { return x && a.indexOf(x) === i; });
      var meta = (it.signal ? '<span class="hot">' + esc(it.signal) + "</span>" : "") + (plats.length ? "<span>" + esc(plats.join(" · ")) + "</span>" : "");
      var head = '<button class="row-h" aria-expanded="false" aria-controls="' + bid + '">' +
        '<span class="t">' + esc(it.topic) + "</span>" +
        '<span class="brief">' + esc(plain(briefOf(it))) + "</span>" +
        '<span class="m">' + meta + "</span>" +
        '<span class="areas"><span class="a">证据 ' + ev.length + " 条" + (qs.length ? " · 用户原话 " + qs.length + " 条" : "") + '</span><span class="more-l">详情</span></span></button>';
      var evHtml = ev.length ? '<div><p class="label">证据</p><ul class="ev">' + ev.map(function (e) {
        return '<li><span class="pf">' + esc(e.platform || "") + '</span><span class="et">' + link(e.title || e.url, e.url) +
          (e.metrics ? "<small>" + esc(e.metrics) + "</small>" : "") + "</span></li>";
      }).join("") + "</ul></div>" : "";
      var qHtml = qs.length ? '<div><p class="label">用户原话</p><ul class="quotes">' + qs.map(function (q) {
        return "<li><p>" + esc(q.text) + "</p><small>" + esc([q.platform, q.likes != null ? wan(q.likes) + " 赞" : ""].filter(Boolean).join(" · ")) + "</small></li>";
      }).join("") + "</ul></div>" : "";
      var how = it.how ? '<div><p class="label">一人公司怎么接</p><p class="how">' + rich(it.how) + "</p></div>" : "";
      var risk = it.risk ? '<dl class="facts"><dt>风险</dt><dd>' + rich(it.risk) + "</dd></dl>" : "";
      var body = '<div class="row-b" id="' + bid + '" hidden>' + (it.why ? '<p class="what">' + rich(it.why) + "</p>" : "") +
        evHtml + qHtml + how + risk + actBtns(gid, true) + FOLD + "</div>";
      return '<li class="row item trend">' + head + body + "</li>";
    }).join("") + "</ul>";
  }
  function renderToday(d) {
    state.gallery = {};
    var isLatest = d.date === latest(), no = issueNo(d.date), st = d.stats || {};
    var lead = (d.headline || []).map(function (h, i) {
      return '<li data-k="' + (LEAD_KEYS[i] || "news") + '"><span class="n">' + (i + 1) + "</span><p>" + rich(h) + "</p></li>";
    }).join("");
    /* 没接平台数据的旧日报不显示「玩法风向」 */
    var secs = SEC.filter(function (s) { return s.key !== "trends" || Array.isArray(d.trends); });
    var toc = secs.map(function (s) {
      return '<a href="#sec-' + s.key + '" data-k="' + s.key + '"><b>' + (d[s.key] || []).length + "</b><small>" + s.short + "</small></a>";
    }).join("");
    var back = isLatest ? unreadPast() : [];
    var backlog = back.length ? '<div class="backlog"><span>还有 ' + back.length + " 期没看</span>" + back.slice(0, 6).map(function (x) { return '<button data-date="' + esc(x.date) + '">' + shortDate(x.date) + "</button>"; }).join("") + "</div>" : "";
    var fns = { news: renderNews, tools: renderItems("tools"), skills: renderItems("skills"), opportunities: renderOpps, trends: renderTrends };
    var body = secs.map(function (s) {
      var n = (d[s.key] || []).length;
      var tool = s.key !== "opportunities" && n ? expandTool(s.key) : "";
      return '<section class="sec" id="sec-' + s.key + '" data-k="' + s.key + '">' + secHead(s, n, tool) + fns[s.key](d) + "</section>";
    }).join("");
    var todo = (d.actions || []).length ? '<section class="sec" data-k="todo">' + secHead({ title: "今天做什么" }, d.actions.length) + '<ol class="todo">' +
      d.actions.map(function (t) { return '<li><span class="min">' + esc(t.minutes) + " 分钟</span><p>" + rich(t.text) + "</p></li>"; }).join("") + "</ol></section>" : "";
    app.innerHTML = '<div class="mast">' +
      '<div class="kicker"><span>' + (no ? "第 " + no + " 期 · " : "") + "扫描 " + num(st.scanned) + " 条，入选 " + num(st.selected) + ' 条</span><span class="rs" id="read-' + esc(d.date) + '">' + readStateHtml(d.date) + "</span></div>" +
      "<h1>" + longDate(d.date) + "</h1>" +
      '<p class="lead-l">' + (isLatest ? "今天先看这三件" : "这一期的三件事") + '</p><ol class="lead">' + lead + "</ol>" + backlog +
      '<nav class="toc" aria-label="栏目" style="--cols:' + secs.length + '">' + toc + "</nav></div>" + body + todo +
      '<div class="foot" id="foot"><span>生成于 ' + esc((d.generated_at || "").replace("T", " ").slice(0, 16)) + "。</span><span>看到这里，这一期就算看过了。</span></div>";
    watchFoot(d.date);
  }

  /* ---------- 历史：没看的和看过的分开 ---------- */
  function dayItem(x) {
    var c = x.counts || {}, r = isRead(x.date);
    return '<li class="row day ' + (r ? "read" : "unread") + '"><button class="row-h" data-date="' + esc(x.date) + '">' +
      '<span class="t">' + longDate(x.date) + (r ? "" : '<span class="tag">未读</span>') + "</span>" +
      '<span class="brief">' + esc(plain(x.headline)) + "</span>" +
      '<span class="m"><span>资讯 ' + (c.news || 0) + "</span><span>工具 " + (c.tools || 0) + "</span><span>Skills " + (c.skills || 0) + "</span><span>机会 " + (c.opportunities || 0) + "</span>" + (c.trends ? "<span>风向 " + c.trends + "</span>" : "") + "</span></button></li>";
  }
  function renderHistory() {
    var past = dates().slice(1);
    var head = '<div class="page-h"><h1>历史日报</h1><p>新的一期出来后，前一天的会移到这里。</p></div>';
    if (!past.length) { app.innerHTML = head + '<p class="empty">还没有往期。明天新的一期出来后，今天这期会出现在这里；没看过的会标红。</p>'; return; }
    var un = past.filter(function (x) { return !isRead(x.date); }), rd = past.filter(function (x) { return isRead(x.date); });
    app.innerHTML = head +
      (un.length ? '<section class="sec" data-k="unread">' + secHead({ title: "没看的" }, un.length) + '<ul class="list">' + un.map(dayItem).join("") + "</ul></section>" : "") +
      (rd.length ? '<section class="sec" data-k="done">' + secHead({ title: "看过的" }, rd.length) + '<ul class="list">' + rd.map(dayItem).join("") + "</ul></section>" : "");
  }

  /* ---------- 收藏 ---------- */
  function favName(f) { var it = f.item || {}; return it.name || it.repo || it.title || it.topic || f.id; }
  function renderFav() {
    var favs = state.index.favorites || [];
    var head = '<div class="page-h"><h1>收藏</h1><p>点「收藏并深挖」的条目，Claude 写完报告后放在这里。</p></div>';
    if (!favs.length) { app.innerHTML = head + '<p class="empty">还没有收藏。在日报里点「收藏」或「收藏并深挖」，几分钟后会出现在这里。</p>'; return; }
    var groups = {};
    favs.forEach(function (f) { (groups[f.library] = groups[f.library] || []).push(f); });
    var order = [["机会库", "opportunities"], ["工具库", "tools"], ["资讯库", "news"]];
    app.innerHTML = head + order.filter(function (g) { return groups[g[0]]; }).map(function (g) {
      return '<section class="sec" data-k="' + g[1] + '">' + secHead({ title: g[0] }, groups[g[0]].length) + '<ul class="list">' + groups[g[0]].map(function (f) {
        var it = f.item || {}, nm = splitName(favName(f));
        var dd = f.deepdive === "done" ? '<span class="st done">深挖完成</span>' : f.deepdive === "pending" ? '<span class="st pending">深挖中</span>' : "";
        return '<li class="row fav" id="fav-' + esc(f.id) + '"><div class="row-h" style="cursor:default">' +
          '<span class="t">' + (it.url ? link(nm[0], it.url) : esc(nm[0])) + '<span class="st">' + esc(f.status) + "</span>" + dd + "</span>" +
          '<span class="brief">' + esc(plain(it.brief || it.one_liner || it.what || it.summary || "")) + "</span>" +
          '<span class="m"><span>' + esc(f.saved_at ? String(f.saved_at).slice(0, 10) : "") + "</span></span></div>" +
          (f.deepdive === "done" ? '<details class="deep-d" data-deep="' + esc(f.id) + '"' + (state.focus === f.id ? " open" : "") + '><summary class="btn">看深挖报告</summary><div class="deep" id="deep-' + esc(f.id) + '"><p class="empty">加载中……</p></div></details>' : "") +
          "</li>";
      }).join("") + "</ul></section>";
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

  function toggleRow(btn, force) {
    var open = force != null ? force : btn.getAttribute("aria-expanded") !== "true";
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    var panel = document.getElementById(btn.getAttribute("aria-controls"));
    if (panel) panel.hidden = !open;
    var row = btn.closest(".row"); if (row) row.classList.toggle("open", open);
    var ml = btn.querySelector(".more-l"); if (ml) ml.textContent = open ? "收起" : "详情";
  }
  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;
    var g = e.target.closest("[data-g]");
    if (g) { openLightbox(g.getAttribute("data-g"), +g.getAttribute("data-i")); return; }
    var t = e.target.closest("button");
    if (!t) return;
    if (t.hasAttribute("data-tab")) { state.tab = t.getAttribute("data-tab"); if (state.tab === "today") state.date = null; state.focus = null; render(); window.scrollTo(0, 0); }
    else if (t.hasAttribute("data-op")) doAction(t);
    else if (t.hasAttribute("data-date")) { state.tab = "today"; state.date = t.getAttribute("data-date"); render(); window.scrollTo(0, 0); }
    else if (t.hasAttribute("data-read")) setRead(t.getAttribute("data-d"), t.getAttribute("data-read") === "1");
    else if (t.hasAttribute("data-expand")) {
      var all = t.closest(".sec").querySelectorAll(".row-h[aria-controls]");
      var anyClosed = Array.prototype.some.call(all, function (b) { return b.getAttribute("aria-expanded") !== "true"; });
      Array.prototype.forEach.call(all, function (b) { toggleRow(b, anyClosed); });
      t.textContent = anyClosed ? "全部收起" : "全部展开";
    }
    else if (t.hasAttribute("data-fold")) {
      /* 面板底部的「收起」：收起后如果标题已经滚出屏幕，把它拉回来 */
      var row = t.closest(".row"), head = row && row.querySelector(".row-h");
      if (!head) return;
      toggleRow(head, false);
      var sh = row.closest(".sec") && row.closest(".sec").querySelector(".sec-h");
      var top = (document.querySelector(".bar") || {}).offsetHeight + (sh ? sh.offsetHeight : 0);
      var y = head.getBoundingClientRect().top;
      if (y < top) { var de = document.documentElement; de.style.scrollBehavior = "auto"; window.scrollTo(0, window.scrollY + y - top - 6); de.style.scrollBehavior = ""; }
    }
    else if (t.hasAttribute("aria-controls")) toggleRow(t);
  });

  /* 打不开的图：封面换下一张，缩略图直接拿掉，一张都不剩时恢复纯文字 */
  document.addEventListener("error", function (e) {
    var img = e.target;
    if (!img || img.tagName !== "IMG" || !img.closest) return;
    var box = img.closest(".thumb, .shot"); if (!box) return;
    var gid = box.getAttribute("data-g"), list = state.gallery[gid] || [], row = box.closest(".row");
    if (box.classList.contains("thumb")) {
      var k = +img.getAttribute("data-k") + 1;
      if (list[k]) { img.setAttribute("data-k", k); box.setAttribute("data-i", k); img.src = list[k]; return; }
      box.remove(); if (row) row.classList.remove("has-img"); return;
    }
    var st = box.parentNode; box.remove();
    if (st && !st.querySelector(".shot")) st.remove();
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
