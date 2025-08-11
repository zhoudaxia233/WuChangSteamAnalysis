# WuChangSteamAnalysis

## 项目简介

这是一个Steam游戏评论分析工具，主要用于收集和分析《明末渊虚之羽》的中文评论数据，同时也支持对其他Steam游戏的多语言评论进行分析。

## 主要功能

### 数据收集
- 🎮 **Steam评论收集**: 自动收集指定游戏的中文评论（简体中文和繁体中文）
- 📊 **数据导出**: 将评论数据导出为CSV格式，便于后续分析
- 🔄 **增量保存**: 支持数据收集过程中的增量保存，避免数据丢失
- 🛡️ **安全中断**: 支持Ctrl+C安全中断，自动保存已收集的数据
- 🌍 **多语言支持**: 可扩展支持其他语言的评论收集
- ⚙️ **灵活配置**: 支持自定义请求间隔、评论数量限制等参数

### AI智能分析
- 🤖 **DeepSeek AI分析**: 基于大语言模型的深度语义理解
- 🏷️ **多标签分类**: 一条评论可同时属于多个类别，准确反映复杂观点
- 💾 **断点续传**: 支持中断恢复，大数据分析安全无忧
- 🔄 **自动保存**: 每处理一定数量自动保存进度

### 可视化报告
- 📈 **交互式报告**: 生成包含图表的HTML可视化报告
- 📊 **统计分析**: 详细的类别分布和代表性评论
- 🎨 **图表嵌入**: 中文字体支持，图表直接嵌入HTML
- 📄 **多格式输出**: HTML、JSON、CSV多种格式数据导出

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

### 4. 配置环境变量
```bash
# 复制环境变量模板
cp sample.env .env

# 编辑 .env 文件，填入你的DeepSeek API密钥
# DEEPSEEK_API_KEY=sk-your-api-key-here
```

### 5. 激活虚拟环境
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

## 评论分析工具

项目提供了两个独立的分析工具：

### 1. AI分析器 (`review_analyzer.py`)

使用DeepSeek AI进行精准语义分析，生成分类数据：

```bash
# 开始AI分析（自动保存进度）
poetry run python review_analyzer.py your_reviews.csv --output analysis_results

# 中断后重新运行会提供三个选择：
# Y - 继续AI分析
# R - 基于现有数据生成报告  
# N - 重新开始分析
```

### 2. 报告生成器 (`report_generator.py`)

基于分析结果生成可视化报告：

```bash
# 基本用法（自动检测CSV文件）
poetry run python report_generator.py analysis_results/classification_progress.json --output report

# 手动指定原始评论文件
poetry run python report_generator.py analysis_results/classification_progress.json --reviews your_reviews.csv --output report
```

### 完整工作流程

1. **收集评论数据**:
   ```bash
   poetry run python steam_reviews_collector.py 2277560 --output my_reviews.csv
   ```

2. **AI分析评论**:
   ```bash
   poetry run python review_analyzer.py my_reviews.csv --output analysis_results
   ```

3. **生成可视化报告**:
   ```bash
   poetry run python report_generator.py analysis_results/classification_progress.json --output report
   ```


## 分析类别

**好评类别**:
- 剧情故事: 历史、故事、文学性等
- 美术音效: 画面、音乐、视觉效果等  
- 游戏性: 玩法、创新、操作体验等
- 情感共鸣: 感动、情怀、对国产游戏的支持等情感因素
- 其他: 无具体理由的好评

**差评类别**:
- 游戏质量: 优化、bug、卡顿、闪退、性能等技术问题
- 游戏内容: 不好玩、太难、地图太绕、boss变态、操作手感、UI等  
- 历史争议: 满清缺席隐身、鞑子、巴图鲁、历史考据、史实准确性等争议
- 宣发问题: 营销炒作、505发行、豪华版定价、试玩偷跑、预购诈骗等
- 后续公关: 豪华版补偿、优化效率、官方态度等发售后服务问题
- 其他: 无具体理由的单纯谩骂

## 游戏ID获取

Steam游戏ID可以从游戏的Steam页面URL中获取：
- 《明末渊虚之羽》: `2277560`

URL格式: `https://store.steampowered.com/app/{app_id}/game_name/`

## 输出数据格式

### 原始评论数据 (CSV格式)

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

### 分析结果

**AI分析器输出**：
- `classification_progress.json`: 分类进度和结果
- 包含每条评论的类别标签和情感倾向

**报告生成器输出**：
- `analysis_report.html`: 交互式可视化报告
- `analysis_statistics.json`: 详细统计数据
- `classified_reviews.csv`: 完整分类结果
- 内嵌图表，包含真实评论内容

## 注意事项

- 🚫 请合理使用，避免对Steam服务器造成过大压力
- ⏰ 默认请求间隔为1秒，建议不要设置过小的值
- 💾 大量数据收集时建议使用增量保存功能
- 🔄 支持中断后继续，数据不会丢失
- 📊 收集完成后会自动显示数据统计概览


---

**免责声明**: 本工具仅用于学习和研究目的，请遵守Steam的使用条款和相关法律法规。