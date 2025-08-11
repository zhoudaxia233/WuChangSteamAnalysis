# WuChangSteamAnalysis

## 项目简介

这是一个Steam游戏评论分析工具，主要用于收集和分析《明末渊虚之羽》的中文评论数据，同时也支持对其他Steam游戏的多语言评论进行分析。

## 主要功能

- 🎮 **Steam评论收集**: 自动收集指定游戏的中文评论（简体中文和繁体中文）
- 📊 **数据导出**: 将评论数据导出为CSV格式，便于后续分析
- 🔄 **增量保存**: 支持数据收集过程中的增量保存，避免数据丢失
- 🛡️ **安全中断**: 支持Ctrl+C安全中断，自动保存已收集的数据
- 🌍 **多语言支持**: 可扩展支持其他语言的评论收集
- ⚙️ **灵活配置**: 支持自定义请求间隔、评论数量限制等参数

## 环境要求

- Python 3.12+
- Poetry (依赖管理)

## 安装和设置

### 1. 克隆项目
```bash
git clone <repository-url>
cd WuChangSteamAnalysis
```

### 2. 安装Poetry（如果尚未安装）
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. 安装依赖
```bash
poetry install
```

### 4. 激活虚拟环境
```bash
poetry shell
```

## 使用方法

### 基本用法

**收集《明末渊虚之羽》的评论**:
```bash
poetry run python steam_reviews_collector.py 2277560
```

**限制收集数量**:
```bash
poetry run python steam_reviews_collector.py 2277560 --max-reviews 100
```

**指定输出文件**:
```bash
poetry run python steam_reviews_collector.py 2277560 --output my_reviews.csv
```

**完整参数示例**:
```bash
poetry run python steam_reviews_collector.py 2277560 \
    --max-reviews 1000 \
    --review-type all \
    --delay 1.0 \
    --output wuchang_reviews.csv
```

### 参数说明

- `app_id`: Steam游戏ID（必需）
- `--max-reviews`: 每种语言的最大评论数量（0=获取全部，默认为0）
- `--review-type`: 评论类型筛选（all/positive/negative，默认为all）
- `--delay`: 请求间隔时间（秒，默认为1.0）
- `--output`: 输出文件名（可选）

### 获取帮助信息

查看所有可用参数：
```bash
poetry run python steam_reviews_collector.py --help
```

## 游戏ID获取

Steam游戏ID可以从游戏的Steam页面URL中获取：
- 《明末渊虚之羽》: `2277560`

URL格式: `https://store.steampowered.com/app/{app_id}/game_name/`

## 输出数据格式

生成的CSV文件包含以下字段：
- `recommendationid`: 评论ID
- `language`: 语言代码（schinese/tchinese）
- `language_name`: 语言名称（简体中文/繁体中文）
- `review_text`: 评论内容
- `voted_up`: 是否推荐（True/False）
- `timestamp_created`: 创建时间戳
- `created_date`: 可读创建日期
- `author_playtime_hours`: 作者游戏时长（小时）
- `votes_up`: 点赞数
- `comment_count`: 回复数
- 更多作者和评论相关信息...

## 注意事项

- 🚫 请合理使用，避免对Steam服务器造成过大压力
- ⏰ 默认请求间隔为1秒，建议不要设置过小的值
- 💾 大量数据收集时建议使用增量保存功能
- 🔄 支持中断后继续，数据不会丢失
- 📊 收集完成后会自动显示数据统计概览


---

**免责声明**: 本工具仅用于学习和研究目的，请遵守Steam的使用条款和相关法律法规。