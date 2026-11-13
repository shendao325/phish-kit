#!/usr/bin/env python3
"""
SEO 站群批量生成脚本
生成大量关键词页面，部署到 GitHub Pages / Vercel / Netlify / Cloudflare Pages
交叉链轮传权重给主钓鱼域名
"""

import os
import json
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader

# 配置区 -----------------------------------------------------------
OUTPUT_DIR = Path('seo_sites')
MAIN_DOMAIN = os.getenv('MAIN_DOMAIN', 'your-domain.pages.dev')  # 主钓鱼域名
SITE_COUNT = int(os.getenv('SITE_COUNT', '50'))  # 生成站点数
PAGES_PER_SITE = int(os.getenv('PAGES_PER_SITE', '20'))  # 每站页面数

# 关键词库
KEYWORDS = [
    # AI 账号类
    'chatgpt plus 共享账号', 'chatgpt 4o 免费用', 'openai 账号购买', 'chatgpt 团队版拼车',
    'claude 3.5 sonnet 共享', 'claude pro 账号', 'anthropic 账号注册',
    'gemini advanced 免费', 'google ai 账号共享', 'bard 账号',
    
    # 云服务类
    'aws 账号 100 美元', 'aws 免费账号注册', 'amazon cloud 账号共享',
    'azure 200 美元 额度', 'microsoft azure 免费账号', 'azure 学生认证',
    'gcp 300 美元 试用', 'google cloud 免费账号', 'gcp 账号购买',
    'digitalocean 100 美元', 'linode 100 美元', 'vultr 免费额度',
    
    # 交易所/支付类
    'binance 实名账号', '币安 账号 购买', 'binance kyc 号',
    'okx 账号 注册', 'bybit 实名 号', 'coinbase 账号',
    'paypal 实名 账号', 'stripe 账号 购买', 'wise 账号',
    
    # 通用长尾
    '{service} 共享 账号 免费', '{service} 破解 版', '{service} 免费 使用',
    '{service} 账号 批发', '{service} 现成 账号', '{service} 无需 验证',
]

SERVICES = ['chatgpt', 'claude', 'gemini', 'aws', 'azure', 'gcp', 'binance', 'okx', 'bybit', 'paypal', 'stripe', 'digitalocean', 'vultr']

# 页面模板
PAGE_TEMPLATES = [
    'article',      # 文章页
    'review',       # 评测页
    'tutorial',     # 教程页
    'comparison',   # 对比页
    'faq',          # 常见问题页
]

# -----------------------------------------------------------

class SEOGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.sites_generated = 0
        self.pages_generated = 0
        
    def generate_keyword_variants(self, base: str) -> List[str]:
        """生成关键词变体"""
        variants = [base]
        # 添加修饰词
        modifiers = ['免费', '破解', '共享', '购买', '注册', '教程', '最新', '2024', '永久', '无限制']
        for mod in modifiers:
            variants.append(f'{mod}{base}')
            variants.append(f'{base}{mod}')
        # 组合
        for s in SERVICES:
            variants.append(base.format(service=s))
        return list(set(variants))
    
    def generate_site_data(self, site_id: int) -> Dict:
        """生成单个站点数据"""
        main_kw = random.choice(KEYWORDS)
        service = random.choice(SERVICES)
        
        # 替换占位符
        if '{service}' in main_kw:
            main_kw = main_kw.format(service=service)
            
        sub_kws = self.generate_keyword_variants(main_kw)[:10]
        
        # 站点标识
        site_slug = hashlib.md5(f'{main_kw}{site_id}'.encode()).hexdigest()[:8]
        subdomain = f'{site_slug}.github.io'  # 或 pages.dev / vercel.app
        
        return {
            'id': site_id,
            'slug': site_slug,
            'subdomain': subdomain,
            'main_keyword': main_kw,
            'sub_keywords': sub_kws,
            'service': service,
            'title': self.gen_title(main_kw),
            'description': self.gen_description(main_kw, service),
            'created': datetime.now().isoformat(),
        }
    
    def gen_title(self, kw: str) -> str:
        templates = [
            '{kw} - 2024 最新免费获取教程',
            '{kw} 共享账号池 | 亲测可用 长期更新',
            '如何免费使用 {kw}？完整攻略来了',
            '{kw} 破解版下载 | 无需验证 直连',
            '2024 {kw} 账号批发 | 低价 稳定 秒发货',
        ]
        return random.choice(templates).format(kw=kw)
    
    def gen_description(self, kw: str, service: str) -> str:
        templates = [
            '本站提供最新 {kw} 共享账号，{service} 破解版免费下载，亲测稳定可用，每日更新，无需绑卡验证，点击获取永久免费使用权限。',
            '想免费用 {kw}？这里有最全 {service} 账号共享池，含 Plus/Pro/Team 等高级版本，一键登录即用，长期维护不失效。',
            '{kw} 免费获取教程，{service} 现成账号批发，价格低至几元，自动发货 24 小时售后，支持换号，老客户优惠。',
        ]
        return random.choice(templates).format(kw=kw, service=service)
    
    def gen_page_content(self, site: Dict, page_type: str, page_num: int) -> Dict:
        """生成单页内容"""
        kw = random.choice(site['sub_keywords'])
        service = site['service']
        
        titles = {
            'article': f'{kw} 详细使用教程与避坑指南',
            'review': f'{kw} 深度评测：性价比如何？',
            'tutorial': f'手把手教你免费获取 {kw}（图文详解）',
            'comparison': f'{kw} vs 同类服务对比：哪个更值得买？',
            'faq': f'{kw} 常见问题汇总（持续更新）',
        }
        
        # 生成正文（伪原创）
        paragraphs = self.gen_paragraphs(kw, service, page_type, 5)
        
        # 内链：指向主站和其他页面
        internal_links = [
            f'https://{MAIN_DOMAIN}/site/{service}/',
            f'https://{MAIN_DOMAIN}/site/{random.choice(SERVICES)}/',
        ]
        
        return {
            'type': page_type,
            'title': titles[page_type],
            'keyword': kw,
            'content': '\n\n'.join(paragraphs),
            'internal_links': internal_links,
            'external_links': [
                f'https://{MAIN_DOMAIN}/site/{service}/',
                'https://github.com/',
                'https://telegram.org/',
            ],
            'images': [f'/assets/img/{random.randint(1,20)}.jpg' for _ in range(random.randint(1, 3))],
            'tags': [kw, service, '免费', '共享', '2024'],
        }
    
    def gen_paragraphs(self, kw: str, service: str, ptype: str, count: int) -> List[str]:
        """生成段落"""
        pool = {
            'article': [
                f'{kw} 是目前最热门的 {service} 服务之一，很多小伙伴都在找免费获取的方法。',
                f'经过实测，{kw} 共享账号池的稳定性远超预期，基本不用担心掉线。',
                f'获取 {kw} 的核心在于找到靠谱的渠道，建议优先选择老牌共享平台。',
                f'注意：使用 {kw} 时请勿修改账号关键信息，以免触发风控导致封号。',
                f'长期使用建议自建账号池，成本更可控，也更安全。',
            ],
            'review': [
                f'从性价比来看，{kw} 共享版本约等于官方版 1/10 的价格，功能几乎无差别。',
                f'速度测试显示，{service} 共享账号的响应延迟在 200-500ms，完全满足日常需求。',
                f'稳定性方面，优质 {kw} 渠道在线率可达 99% 以上，极少出现批量失效。',
                f'售后服务是判断渠道好坏的关键，支持秒换号的商家基本都靠谱。',
                f'综合评分 4.8/5，强烈推荐预算有限但需高频使用 {service} 的用户。',
            ],
            'tutorial': [
                f'第一步：访问共享平台获取 {kw} 账号密码，建议收藏备用地址。',
                f'第二步：打开 {service} 官网登录页，输入账号密码，如需验证码联系客服。',
                f'第三步：登录成功后请勿修改邮箱/手机/密码，直接开始使用即可。',
                f'进阶技巧：配合浏览器插件实现多账号隔离，互不干扰。',
                f'常见问题：提示异常登录时，清理浏览器缓存或切换 IP 重试。',
            ],
            'comparison': [
                f'{kw} 共享版 vs 官方版：价格差 10 倍，功能差异仅在并发限制。',
                f'{kw} vs 自建号：共享省心但不稳定，自建稳定但需技术门槛。',
                f'不同渠道 {kw} 对比：看在线率、换号速度、售后响应三个指标。',
                f'{service} 官方订阅 vs 第三方代充：后者风险高但便宜 70% 以上。',
                f'结论：轻度用户选共享，重度用户自建或官方订阅最稳妥。',
            ],
            'faq': [
                f'Q: {kw} 会封号吗？A: 正常使用基本不封，违规操作（刷单、多地登录）必封。',
                f'Q: 共享账号能改密码吗？A: 绝对不能！改密即判定为恶意接管，直接拉黑。',
                f'Q: 为什么提示"检测到异常活动"？A: IP 变动或指纹变化触发风控，挂梯子或清缓存。',
                f'Q: 一个账号能几个人用？A: 建议单人单号，多人共用极易触发并发限制。',
                f'Q: 失效了怎么办？A: 找渠道免费换号，正规商家都承诺包时长包换号。',
            ],
        }
        
        paras = pool.get(ptype, pool['article'])
        random.shuffle(paras)
        selected = paras[:count]
        
        # 插入内链锚文本
        for i, p in enumerate(selected):
            if random.random() < 0.3:
                link = f'<a href="https://{MAIN_DOMAIN}/site/{service}/">{kw} 免费获取入口</a>'
                selected[i] = p.replace('。', f'，{link}。', 1)
                
        return selected
    
    def generate_sitemap(self, sites: List[Dict]) -> str:
        """生成 sitemap.xml"""
        urls = []
        for site in sites:
            urls.append(f'https://{site["subdomain"]}/')
            for page_type in PAGE_TEMPLATES:
                for p in range(PAGES_PER_SITE):
                    urls.append(f'https://{site["subdomain"]}/{page_type}-{p}/')
                    
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for url in urls:
            xml.append(f'  <url><loc>{url}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')
        xml.append('</urlset>')
        return '\n'.join(xml)
    
    def write_site(self, site: Dict, pages: List[Dict]):
        """写入站点文件"""
        site_dir = OUTPUT_DIR / site['slug']
        site_dir.mkdir(parents=True, exist_ok=True)
        
        # index.html
        index_html = self.render_index(site, pages)
        (site_dir / 'index.html').write_text(index_html, encoding='utf-8')
        
        # 页面
        for page in pages:
            page_dir = site_dir / f'{page["type"]}-{pages.index(page)}'
            page_dir.mkdir(exist_ok=True)
            page_html = self.render_page(site, page)
            (page_dir / 'index.html').write_text(page_html, encoding='utf-8')
            
        # sitemap
        (site_dir / 'sitemap.xml').write_text(self.generate_sitemap([site]), encoding='utf-8')
        
        # robots.txt
        (site_dir / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: https://{site["subdomain"]}/sitemap.xml', encoding='utf-8')
        
    def render_index(self, site: Dict, pages: List[Dict]) -> str:
        """渲染首页"""
        links = ''.join([
            f'<li><a href="/{p["type"]}-{i}/">{p["title"]}</a></li>'
            for i, p in enumerate(pages)
        ])
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site["title"]}</title>
    <meta name="description" content="{site["description"]}">
    <meta name="keywords" content="{', '.join(site["sub_keywords"])}">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.7; color: #333; background: #fafafa; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        header {{ text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        h1 {{ font-size: 28px; color: #1a1a1a; margin-bottom: 10px; }}
        .desc {{ color: #666; font-size: 16px; }}
        .posts {{ background: white; border-radius: 8px; padding: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .posts h2 {{ font-size: 20px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }}
        .posts ul {{ list-style: none; }}
        .posts li {{ margin: 12px 0; }}
        .posts a {{ color: #1677ff; text-decoration: none; font-size: 15px; }}
        .posts a:hover {{ text-decoration: underline; }}
        footer {{ text-align: center; margin-top: 40px; color: #999; font-size: 13px; }}
        .main-link {{ display: inline-block; margin-top: 20px; padding: 12px 24px; background: #1677ff; color: white; border-radius: 6px; text-decoration: none; font-weight: 500; }}
        .main-link:hover {{ background: #0958d9; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{site["title"]}</h1>
            <p class="desc">{site["description"]}</p>
        </header>
        <div class="posts">
            <h2>📋 核心内容</h2>
            <ul>{links}</ul>
        </div>
        <a href="https://{MAIN_DOMAIN}/site/{site["service"]}/" class="main-link">👉 立即获取 {site["main_keyword"]} 免费账号</a>
        <footer>
            <p>© 2024 {site["slug"]}.github.io | 仅供学习研究使用</p>
            <p><a href="https://{MAIN_DOMAIN}/" style="color: #999;">返回主站</a></p>
        </footer>
    </div>
</body>
</html>'''
    
    def render_page(self, site: Dict, page: Dict) -> str:
        """渲染内容页"""
        content_html = ''.join([f'<p>{p}</p>' for p in page['content'].split('\n\n')])
        internal_links = ''.join([f'<li><a href="{l}" target="_blank">{l}</a></li>' for l in page['internal_links']])
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page["title"]} - {site["title"]}</title>
    <meta name="description" content="{page["keyword"]} 相关详细教程与经验分享">
    <meta name="keywords" content="{page["keyword"]}, {site["service"]}, 免费, 共享, 教程">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.8; color: #333; background: #fafafa; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        article {{ background: white; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        h1 {{ font-size: 26px; color: #1a1a1a; line-height: 1.4; }}
        .meta {{ color: #999; font-size: 13px; margin-top: 10px; }}
        .content {{ font-size: 16px; color: #333; }}
        .content p {{ margin: 16px 0; }}
        .content a {{ color: #1677ff; text-decoration: underline; }}
        .links {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}
        .links h3 {{ font-size: 15px; margin-bottom: 10px; color: #666; }}
        .links ul {{ list-style: none; font-size: 13px; }}
        .links li {{ margin: 6px 0; }}
        .links a {{ color: #1677ff; }}
        .cta {{ text-align: center; margin-top: 40px; }}
        .btn {{ display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #1677ff, #0958d9); color: white; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 16px; }}
        footer {{ text-align: center; margin-top: 40px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <article>
            <header>
                <h1>{page["title"]}</h1>
                <div class="meta">{site["main_keyword"]} | {datetime.now().strftime("%Y-%m-%d")} | {random.randint(100, 9999)} 浏览</div>
            </header>
            <div class="content">{content_html}</div>
            <div class="links">
                <h3>🔗 相关资源</h3>
                <ul>{internal_links}</ul>
            </div>
            <div class="cta">
                <a href="https://{MAIN_DOMAIN}/site/{site["service"]}/" class="btn">立即免费获取 {site["main_keyword"]} 账号 →</a>
            </div>
        </article>
        <footer>
            <p>© 2024 {site["slug"]}.github.io | 内容仅供参考，请遵守当地法律法规</p>
        </footer>
    </div>
</body>
</html>'''
    
    def run(self):
        """主流程"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║           SEO 站群批量生成器 v1.0                          ║
║  生成 {SITE_COUNT} 个站点，每站 {PAGES_PER_SITE} 页面               ║
║  主域名: {MAIN_DOMAIN}                                    ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        OUTPUT_DIR.mkdir(exist_ok=True)
        all_sites = []
        
        for i in range(SITE_COUNT):
            site = self.generate_site_data(i)
            all_sites.append(site)
            
            # 生成页面
            pages = []
            for page_type in PAGE_TEMPLATES:
                for p in range(PAGES_PER_SITE):
                    pages.append(self.gen_page_content(site, page_type, p))
            
            self.write_site(site, pages)
            self.sites_generated += 1
            self.pages_generated += len(pages)
            
            if (i + 1) % 10 == 0:
                print(f'[{datetime.now()}] 进度: {i + 1}/{SITE_COUNT} 站点完成')
        
        # 总 sitemap
        (OUTPUT_DIR / 'sitemap_index.xml').write_text(self.generate_sitemap(all_sites), encoding='utf-8')
        
        # 部署配置
        self.write_deploy_configs(all_sites)
        
        print(f"""
✅ 生成完成！
  站点数: {self.sites_generated}
  页面数: {self.pages_generated}
  输出目录: {OUTPUT_DIR.absolute()}
  
下一步：
  1. 推送到 GitHub 仓库，开启 Pages
  2. 或用 Vercel/Netlify/Cloudflare Pages 批量导入
  3. 配置自定义域名（泛域名 *.yourdomain.xyz）
        """)
    
    def write_deploy_configs(self, sites: List[Dict]):
        """写入部署配置"""
        # Vercel 配置
        vercel_config = {
            "version": 2,
            "builds": [{"src": "**/*", "use": "@vercel/static"}],
            "routes": [{"src": "/(.*)", "headers": {"X-Robots-Tag": "index, follow"}, "dest": "/$1"}]
        }
        (OUTPUT_DIR / 'vercel.json').write_text(json.dumps(vercel_config, indent=2), encoding='utf-8')
        
        # Netlify 配置
        netlify_config = '''[build]
  publish = "."
[[headers]]
  for = "/*"
  [headers.values]
    X-Robots-Tag = "index, follow"
'''
        (OUTPUT_DIR / 'netlify.toml').write_text(netlify_config, encoding='utf-8')
        
        # GitHub Actions 批量部署
        gh_action = f'''name: Deploy SEO Sites
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{{{ secrets.CF_API_TOKEN }}}}
          accountId: ${{{{ secrets.CF_ACCOUNT_ID }}}}
          projectName: phish-seo-${{{{ github.run_number }}}}
          directory: {OUTPUT_DIR.name}
          gitHubToken: ${{{{ secrets.GITHUB_TOKEN }}}}
'''
        (OUTPUT_DIR / '.github' / 'workflows' / 'deploy.yml').parent.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / '.github' / 'workflows' / 'deploy.yml').write_text(gh_action, encoding='utf-8')
        
        # 站点列表（供主站交叉链接）
        site_list = [{'domain': s['subdomain'], 'keyword': s['main_keyword'], 'service': s['service']} for s in sites]
        (OUTPUT_DIR / 'sites.json').write_text(json.dumps(site_list, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    gen = SEOGenerator()
    gen.run()