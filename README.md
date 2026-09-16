# 每日产业情报晨报（云端自动运行版）

基于 Coze 智能体 + GitHub Actions + PushPlus 的全自动产业情报晨报系统，**电脑不开机也能每天早上8:30自动把晨报推送到你的微信**。

---

## 📋 前置条件

1. **GitHub 账号**（免费注册：https://github.com）
2. **Coze 智能体**（已创建，审核通过后可用）
3. **PushPlus 账号**（已注册并充会员，token 已获取）

---

## 🚀 部署步骤（5分钟搞定）

### 第1步：创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名随便填，比如 `morning-report`
3. 选择 **Public**（公开）或 **Private**（私有）都可以
4. 勾选 **Add a README file**（可选）
5. 点击 **Create repository**

### 第2步：上传3个文件

把本目录下的3个文件上传到刚创建的仓库：

```
你的仓库/
├── .github/
│   └── workflows/
│       └── morning-report.yml    ← 工作流配置
├── generate_report.py             ← Python 脚本
└── README.md                       ← 说明文档（本文件）
```

**上传方法：**
- 在仓库页面点击 **Add file** → **Upload files**
- 把文件拖进去（注意 `.github/workflows/` 目录结构要保持）
- 点击 **Commit changes**

### 第3步：配置3个密钥（Secrets）

这是最关键的一步！

1. 在仓库页面点击 **Settings**（设置）
2. 左侧菜单找到 **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，依次添加以下3个：

| 密钥名称 (Name) | 密钥值 (Secret) | 说明 |
|---|---|---|
| `COZE_PAT` | `pat_gIPrD1vEbpvHkLhpS4VTPMnkzQSxIpsmzB6MIso6HF5n0P2VfZpyiR3EE9YRSIbJ` | Coze 个人访问令牌 |
| `COZE_BOT_ID` | `7685993046869639195` | 智能体 Bot ID |
| `PUSHPLUS_TOKEN` | `8a52dd54e2e4402b8bc6494e6301ac65` | PushPlus 推送 token |

> ⚠️ **注意**：密钥值粘贴时不要有多余空格！

### 第4步：启用 GitHub Actions

1. 在仓库页面点击 **Actions** 标签
2. 如果看到提示，点击 **I understand my workflows, go ahead and enable them**
3. 完成！

---

## 🧪 测试一下（手动触发）

配置完成后，可以手动触发一次看看效果：

1. 点击仓库页面的 **Actions** 标签
2. 左侧选择 **每日产业情报晨报**
3. 点击 **Run workflow** → 选择分支（main/master）→ 点击 **Run workflow**
4. 等1-3分钟，查看运行状态
5. 如果成功，你的微信会收到晨报推送

---

## ⏰ 自动运行时间

- **每周一到周五 北京时间 8:30** 自动运行
- 周末和节假日不运行（cron 表达式 `30 0 * * 1-5`）
- 运行时长约1-3分钟（取决于 Coze 智能体生成速度）

---

## ❓ 常见问题

### Q1: 微信收不到推送怎么办？
A: 检查以下几点：
1. PushPlus token 是否正确（在 PushPlus 官网"个人中心"查看）
2. PushPlus 账号是否已关注公众号（首次使用需要扫码关注）
3. 查看 GitHub Actions 运行日志，看是否有报错

### Q2: Coze API 调用失败？
A: 检查：
1. Coze 智能体是否已**审核通过**（在 Coze 工作台查看状态）
2. COZE_PAT 令牌是否正确（注意只显示一次，丢失需要重新创建）
3. 令牌是否过期（默认30天有效，过期需要重新创建）

### Q3: 怎么修改推送时间？
A: 编辑 `.github/workflows/morning-report.yml`，修改 `cron` 表达式：
- 北京时间 = UTC + 8
- 例如北京时间 9:00 = UTC 1:00 → `0 1 * * 1-5`

### Q4: 怎么修改晨报内容/格式？
A: 直接在 Coze 平台编辑智能体的提示词即可，GitHub 端不需要修改。

### Q5: GitHub Actions 免费额度够吗？
A: 完全够！GitHub 免费账户每月有2000分钟运行时间，本任务每次运行约3分钟，每月最多22个工作日，总共约66分钟，只用了3%。

---

## 📁 文件说明

| 文件 | 作用 |
|---|---|
| `.github/workflows/morning-report.yml` | GitHub Actions 工作流配置（定时触发、运行环境） |
| `generate_report.py` | Python 脚本（调用 Coze API 生成晨报 + PushPlus 推送微信） |
| `README.md` | 使用说明（本文件） |

---

## 🔧 技术原理

```
GitHub Actions (每天8:30定时触发)
    ↓
运行 generate_report.py
    ↓
调用 Coze API (智能体生成晨报)
    ↓
获取晨报内容
    ↓
调用 PushPlus API (推送到微信)
    ↓
你在微信收到晨报 🎉
```

---

**有问题随时问我！**
