#!/usr/bin/env python3
"""
评论区引流脚本
支持：知乎、小红书、抖音、B站、微博评论区挂短链
使用浏览器自动化（Playwright/Selenium）或 API（如有）
"""

import asyncio
import random
import json
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# 配置区 -----------------------------------------------------------
# 目标平台关键词
PLATFORMS = {
    'zhihu': {
        'name': '知乎',
        'search_url': 'https://www.zhihu.com/search?type=content&q={keyword}',
        'comment_selector': '.CommentItem .ContentItem-action button:has-text("评论")',
        'input_selector': '.CommentEditor .Editor-wrapper textarea',
        'submit_selector': '.CommentEditor .Button--primary',
    },
    'xiaohongshu': {
        'name': '小红书',
        'search_url': 'https://www.xiaohongshu.com/search_result?keyword={keyword}',
        'comment_selector': '.comment-item .comment-btn',
        'input_selector': '.comment-input textarea',
        'submit_selector': '.submit-btn',
    },
    'bilibili': {
        'name': 'B站',
        'search_url': 'https://search.bilibili.com/all?keyword={keyword}',
        'comment_selector': '.reply-btn',
        'input_selector': '.reply-box .input-area',
        'submit_selector': '.reply-submit',
    },
}

# 引流话术模板
COMMENT_TEMPLATES = [
    "同求！楼主可以看看这个 {service} 共享池 {url} 亲测能用",
    "我也在找 {service} 账号，发现这个 {url} 还不错，分享给大佬们",
    "刚搞到一批 {service} 现成号，含 {details}，需要的自取 {url}",
    "{service} 免费共享账号池 {url} 亲测稳定，手慢无",
    "楼上问的 {service} 这边有现成的 {url} 无需验证直连",
]

SERVICE_CONFIGS = {
    'chatgpt': {'details': 'GPT-4o/Plus/Team 全模型', 'url': 'https://phish.yourdomain.xyz/site/chatgpt/'},
    'claude': {'details': 'Claude-3.5-Sonnet/Opus', 'url': 'https://phish.yourdomain.xyz/site/claude/'},
    'aws': {'details': 'AWS $100 赠送金', 'url': 'https://phish.yourdomain.xyz/site/aws/'},
    'azure': {'details': 'Azure $200 额度', 'url': 'https://phish.yourdomain.xyz/site/azure/'},
    'gcp': {'details': 'GCP $300 试用金', 'url': 'https://phish.yourdomain.xyz/site/gcp/'},
    'binance': {'details': '币安实名认证号', 'url': 'https://phish.yourdomain.xyz/site/binance/'},
}

# 关键词库（针对不同平台）
KEYWORDS = {
    'zhihu': ['ChatGPT Plus 共享', 'Claude 3.5 免费', 'AWS 账号 注册', 'Azure 学生认证', 'GCP 试用金', 'Binance 实名', 'ChatGPT 账号 购买', 'OpenAI API Key'],
    'xiaohongshu': ['ChatGPT 共享号', 'Claude 免费用', '云服务器 免费', 'AWS 账号', 'Azure 注册', 'GCP 白嫖', 'Binance KYC'],
    'bilibili': ['ChatGPT Plus 拼车', 'Claude 3.5 共享', 'AWS 免费额度', 'Azure 学生包', 'GCP 300美元', '币安 实名号'],
}

# 评论间隔（秒）
COMMENT_INTERVAL = (60, 300)  # 1-5 分钟随机
# -----------------------------------------------------------

class CommentSpammer:
    def __init__(self):
        self.posted = 0
        self.failed = 0
        self.browser = None
        self.context = None
        
    async def init_browser(self):
        """初始化浏览器（Playwright）"""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            # 使用已登录的用户数据目录（需手动登录一次）
            user_data_dir = os.path.expanduser('~/AppData/Local/CommentSpammerProfile')
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,  # 必须有头模式以便处理验证码/登录
                args=['--disable-blink-features=AutomationControlled']
            )
            print(f"[{datetime.now()}] ✅ 浏览器已启动，请确保已登录目标平台")
        except ImportError:
            print("❌ 未安装 playwright，请运行: pip install playwright && playwright install chromium")
            return False
        return True
        
    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
    def build_comment(self, platform: str) -> tuple:
        """构建评论内容"""
        service = random.choice(list(SERVICE_CONFIGS.keys()))
        config = SERVICE_CONFIGS[service]
        template = random.choice(COMMENT_TEMPLATES)
        comment = template.format(
            service=service,
            details=config['details'],
            url=config['url']
        )
        # 添加零宽字符防屏蔽
        zwsp = '\u200b'
        comment = zwsp.join(comment) + zwsp * random.randint(1, 3)
        return service, comment
        
    async def post_comment_zhihu(self, keyword: str, comment: str) -> bool:
        """知乎评论（简化版，实际需处理登录、验证码、展开评论区等）"""
        page = await self.browser.new_page()
        try:
            # 搜索
            search_url = f'https://www.zhihu.com/search?type=content&q={keyword}'
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(2, 5))
            
            # 点击第一个回答的评论按钮
            comment_btns = await page.query_selector_all('.CommentItem .ContentItem-action button:has-text("评论")')
            if not comment_btns:
                print(f"  ⚠️ 知乎未找到评论按钮: {keyword}")
                return False
                
            await comment_btns[0].click()
            await asyncio.sleep(1)
            
            # 输入评论
            textarea = await page.query_selector('.CommentEditor .Editor-wrapper textarea')
            if not textarea:
                print(f"  ⚠️ 知乎未找到输入框")
                return False
                
            await textarea.fill(comment)
            await asyncio.sleep(random.uniform(1, 2))
            
            # 发布
            submit_btn = await page.query_selector('.CommentEditor .Button--primary')
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(2)
                print(f"  ✅ 知乎评论成功: {keyword[:20]}...")
                return True
            return False
            
        except Exception as e:
            print(f"  ❌ 知乎评论异常: {e}")
            return False
        finally:
            await page.close()
            
    async def post_comment_xiaohongshu(self, keyword: str, comment: str) -> bool:
        """小红书评论"""
        page = await self.browser.new_page()
        try:
            search_url = f'https://www.xiaohongshu.com/search_result?keyword={keyword}'
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(3, 6))
            
            # 点击第一个笔记
            note_links = await page.query_selector_all('.note-item a.cover')
            if not note_links:
                return False
            await note_links[0].click()
            await asyncio.sleep(2)
            
            # 评论
            comment_btn = await page.query_selector('.comment-item .comment-btn')
            if comment_btn:
                await comment_btn.click()
                await asyncio.sleep(1)
                
                textarea = await page.query_selector('.comment-input textarea')
                if textarea:
                    await textarea.fill(comment)
                    await asyncio.sleep(1)
                    submit = await page.query_selector('.submit-btn')
                    if submit:
                        await submit.click()
                        await asyncio.sleep(2)
                        print(f"  ✅ 小红书评论成功: {keyword[:20]}...")
                        return True
            return False
        except Exception as e:
            print(f"  ❌ 小红书评论异常: {e}")
            return False
        finally:
            await page.close()
            
    async def post_comment_bilibili(self, keyword: str, comment: str) -> bool:
        """B站评论"""
        page = await self.browser.new_page()
        try:
            search_url = f'https://search.bilibili.com/all?keyword={keyword}'
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(2, 4))
            
            # 点击第一个视频
            video_links = await page.query_selector_all('.bili-video-card a')
            if not video_links:
                return False
            await video_links[0].click()
            await asyncio.sleep(3)
            
            # 评论
            reply_box = await page.query_selector('.reply-box .input-area')
            if reply_box:
                await reply_box.fill(comment)
                await asyncio.sleep(1)
                submit = await page.query_selector('.reply-submit')
                if submit:
                    await submit.click()
                    await asyncio.sleep(2)
                    print(f"  ✅ B站评论成功: {keyword[:20]}...")
                    return True
            return False
        except Exception as e:
            print(f"  ❌ B站评论异常: {e}")
            return False
        finally:
            await page.close()
            
    async def run_platform(self, platform: str):
        """运行单平台引流"""
        keywords = KEYWORDS.get(platform, [])
        if not keywords:
            return
            
        print(f"\n[{datetime.now()}] 🚀 开始 {PLATFORMS[platform]['name']} 引流，关键词 {len(keywords)} 个")
        
        post_func = getattr(self, f'post_comment_{platform}', None)
        if not post_func:
            print(f"  ⚠️ 平台 {platform} 暂未实现")
            return
            
        for keyword in keywords:
            service, comment = self.build_comment(platform)
            print(f"  📝 {keyword} -> {service}")
            
            ok = await post_func(keyword, comment)
            if ok:
                self.posted += 1
            else:
                self.failed += 1
                
            # 随机间隔
            interval = random.uniform(*COMMENT_INTERVAL)
            print(f"  ⏱ 等待 {interval:.0f} 秒...")
            await asyncio.sleep(interval)
            
    async def run_all(self):
        """运行所有平台"""
        if not await self.init_browser():
            return
            
        try:
            for platform in PLATFORMS.keys():
                await self.run_platform(platform)
                await asyncio.sleep(random.uniform(60, 180))  # 平台间隔
        finally:
            await self.close()
            
        print(f"\n📊 引流完成: 成功 {self.posted} | 失败 {self.failed}")

async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║           评论区引流器 v1.0 (Playwright)                    ║
║  平台: 知乎 / 小红书 / B站                                  ║
║  需求: pip install playwright && playwright install chromium ║
║  首次运行会打开浏览器，请手动登录各平台，后续自动复用会话      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    spammer = CommentSpammer()
    await spammer.run_all()

if __name__ == '__main__':
    asyncio.run(main())