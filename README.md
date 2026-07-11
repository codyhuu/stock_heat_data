# Stock Heat Tracker

一个自动收集 ApeWisdom 股票 ticker 热度的小工具，可在本地运行，也可通过 GitHub Actions 每天云端自动运行。

第一版功能：

- 从 ApeWisdom API 抓取股票热度榜
- 自动翻页，默认抓取 `all-stocks`
- 将每次抓取结果保存到 SQLite
- 生成每日 Markdown 热度报告
- 支持每 24 小时循环运行
- 支持 GitHub Actions 云端定时运行
- 支持飞书机器人推送

## 快速开始

```bash
python -m app.cli init-db
python -m app.cli collect --filter all-stocks --pages 1
python -m app.cli report
```

生成的文件：

- 数据库：`data/stocks_heat.db`
- 报告：`reports/daily_heat_YYYY-MM-DD.md`

## 常用命令

抓取前 3 页数据：

```bash
python -m app.cli collect --filter all-stocks --pages 3
```

抓取所有页面：

```bash
python -m app.cli collect --filter all-stocks --all-pages
```

查看某个 ticker 的历史：

```bash
python -m app.cli history NVDA
```

每 24 小时自动运行：

```bash
python -m app.cli run-scheduler
```

## GitHub Actions 云端定时

项目已包含 GitHub Actions 配置：

```text
.github/workflows/daily-stock-heat.yml
```

默认每天北京时间 `09:17` 自动运行一次，并在 `10:17` 增加一次备用触发。备用触发会先检查当天报告是否已经存在，存在就跳过，避免重复采集。流程会：

- 抓取 ApeWisdom `all-stocks` Top 100
- 更新 `data/stocks_heat.db`
- 生成 `reports/daily_heat_*.md`
- 如果配置了飞书密钥，发送飞书消息
- 将数据库和报告提交回 GitHub 仓库

首次使用需要把项目推到 GitHub：

```bash
git init
git add .
git commit -m "Initial stock heat tracker"
git branch -M main
git remote add origin 你的GitHub仓库地址
git push -u origin main
```

如果想把本地已有 SQLite 和历史报告也一起上传，需要强制加入这些被 `.gitignore` 忽略的文件：

```bash
git add -f data/stocks_heat.db reports/*.md
git commit -m "Add existing stock heat history"
git push
```

在 GitHub 网页里配置飞书密钥：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

添加：

```text
FEISHU_WEBHOOK_URL
FEISHU_SECRET
```

如果没有开启飞书签名校验，`FEISHU_SECRET` 可以不填。

也可以在 GitHub 网页手动运行一次：

```text
Actions -> Daily Stock Heat -> Run workflow
```

## 配置

默认配置在 `config.toml`。

```toml
default_filter = "all-stocks"
default_pages = 1
database_path = "data/stocks_heat.db"
reports_dir = "reports"
alert_mentions_growth_pct = 100
feishu_webhook_url = ""
feishu_secret = ""
```

## 飞书推送

在飞书群里添加「自定义机器人」，复制 webhook 地址，填到 `config.toml`：

```toml
feishu_webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/你的机器人地址"
feishu_secret = ""
```

如果机器人开启了签名校验，把签名密钥填到 `feishu_secret`。

也可以不写进配置文件，改用环境变量：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/你的机器人地址"
export FEISHU_SECRET="你的签名密钥"
```

测试推送：

```bash
python -m app.cli test-feishu
```

生成报告时，如果配置了 `feishu_webhook_url`，程序会自动发送飞书消息：

```bash
python -m app.cli report --filter all-stocks
```

## ApeWisdom 数据字段

API 返回的核心字段包括：

- `rank`
- `ticker`
- `name`
- `mentions`
- `upvotes`
- `rank_24h_ago`
- `mentions_24h_ago`
