// AI 机会雷达 · 收藏按钮中转（Cloudflare Worker）
//
// 飞书卡片和网站上的「收藏」「收藏并深挖」按钮都打到这里：
//   GET  /act?op=fav|deep&id=2026-10-15-B01&k=口令   打开一个确认页，页面自动提交（防止链接预览误触发）
//   POST /act?op=fav|deep&id=...&k=...               真正触发 GitHub 上的「收藏与深挖」任务
//
// 需要在 Worker 的 Settings → Variables and Secrets 里配置：
//   GITHUB_TOKEN  细粒度令牌，只授权雷达仓库，Contents: Read and write
//   GITHUB_REPO   例如 mark/ai-radar
//   ACTION_KEY    和 GitHub 仓库 secrets 里的 ACTION_KEY 一样
//   SITE_URL      网站地址，例如 https://mark.github.io/ai-radar/
//
// 可选：绑定一个 KV 命名空间，变量名 RADAR_KV，已读状态就能在手机和电脑之间同步：
//   GET  /state?k=口令                  返回 {read: {日期: {v, t}}}
//   POST /read?date=2026-10-15&v=1&k=口令  标记已读（v=0 为未读）

const ID = /^\d{4}-\d{2}-\d{2}-[NGSB]\d{2}$/;
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function same(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS },
  });
}

function page(title, text, site, autoPost) {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const link = site ? `<a href="${esc(site)}?tab=fav">打开收藏夹</a>` : "";
  const script = autoPost
    ? `<script>
fetch(location.href, { method: "POST" }).then(r => r.json()).then(d => {
  document.getElementById("t").textContent = d.ok ? d.title : "没成功";
  document.getElementById("m").textContent = d.message;
}).catch(() => { document.getElementById("t").textContent = "网络出错"; document.getElementById("m").textContent = "稍后再点一次。"; });
</script>`
    : "";
  return new Response(
    `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>AI 机会雷达</title>
<style>
:root{--bg:#f3f5f2;--ink:#15201c;--muted:#5b6a64;--accent:#0f6b5c}
@media (prefers-color-scheme:dark){:root{--bg:#111815;--ink:#e6ece8;--muted:#9aa8a1;--accent:#5cc2ab;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,"PingFang SC","Noto Sans SC",sans-serif;display:grid;place-items:center;min-height:100vh;padding:0 20px}
main{max-width:420px}h1{font-size:22px;margin:0 0 8px}p{color:var(--muted);margin:0 0 20px}a{color:var(--accent);font-weight:600}
</style></head><body><main><h1 id="t">${esc(title)}</h1><p id="m">${esc(text)}</p>${link}</main>${script}</body></html>`,
    { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } },
  );
}

async function dispatch(env, op, id) {
  const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ai-radar-worker",
    },
    body: JSON.stringify({ event_type: op === "deep" ? "deepdive" : "favorite", client_payload: { id } }),
  });
  return r.status === 204;
}

async function readState(request, env, url) {
  if (!env.ACTION_KEY || !same(url.searchParams.get("k") || "", env.ACTION_KEY)) return json({ ok: false, message: "口令不对。" }, 403);
  if (!env.RADAR_KV) return json({ ok: true, kv: false, read: {} });
  const read = JSON.parse((await env.RADAR_KV.get("read")) || "{}");
  if (url.pathname === "/state") return json({ ok: true, kv: true, read });
  if (request.method !== "POST") return json({ ok: false, message: "要用 POST。" }, 405);
  const date = url.searchParams.get("date") || "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return json({ ok: false, message: "日期不对。" }, 400);
  read[date] = { v: url.searchParams.get("v") === "0" ? 0 : 1, t: Date.now() };
  const keep = Object.keys(read).sort().slice(-120); // 只留最近 120 天
  const trimmed = Object.fromEntries(keep.map((d) => [d, read[d]]));
  await env.RADAR_KV.put("read", JSON.stringify(trimmed));
  return json({ ok: true, kv: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/state" || url.pathname === "/read") return readState(request, env, url);
    if (url.pathname !== "/act") return new Response("AI 机会雷达收藏接口", { headers: CORS });

    const op = url.searchParams.get("op");
    const id = url.searchParams.get("id") || "";
    const key = url.searchParams.get("k") || "";
    const isPost = request.method === "POST";

    if (!env.ACTION_KEY || !same(key, env.ACTION_KEY)) {
      return isPost ? json({ ok: false, message: "口令不对。" }, 403) : page("口令不对", "请从飞书卡片里的按钮进入。", env.SITE_URL, false);
    }
    if (!["fav", "deep"].includes(op) || !ID.test(id)) {
      return isPost ? json({ ok: false, message: "参数不对。" }, 400) : page("参数不对", "这个按钮的链接不完整。", env.SITE_URL, false);
    }
    if (!isPost) return page("正在提交…", id, env.SITE_URL, true);

    const ok = await dispatch(env, op, id).catch(() => false);
    if (!ok) return json({ ok: false, message: "GitHub 没有接受请求，检查 Worker 里的 GITHUB_TOKEN 和 GITHUB_REPO。" }, 502);
    return json(
      op === "deep"
        ? { ok: true, title: "已收藏，开始深挖", message: `${id} 已进收藏夹。Claude 正在研究，写好后飞书会通知你。` }
        : { ok: true, title: "已收藏", message: `${id} 已进收藏夹，网站一两分钟后更新。` },
    );
  },
};
