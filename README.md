# WuChangSteamAnalysis

## 项目简介

这是一个Steam游戏评论分析工具，主要用于收集和分析《明末渊虚之羽》的中文评论数据，同时也支持对其他Steam游戏的多语言评论进行分析。项目使用DeepSeek AI进行智能语义分析，提供完整的从数据收集到可视化报告的工作流程。

## 主要功能

### 1. Steam评论收集 (`steam_reviews_collector.py`)
- 🎮 **中文评论收集**: 自动收集指定游戏的中文评论（简体中文和繁体中文）
- 📊 **数据导出**: 将评论数据导出为CSV格式，便于后续分析
- 🔄 **增量保存**: 支持数据收集过程中的增量保存，避免数据丢失
- 🛡️ **安全中断**: 支持Ctrl+C安全中断，自动保存已收集的数据
- ⚙️ **灵活配置**: 支持自定义请求间隔、评论数量限制等参数
- 📋 **游戏信息**: 自动获取游戏基本信息（名称、开发商、价格等）

### 2. AI智能分析 (`review_analyzer.py`)
- 🤖 **DeepSeek专用**: 专门针对DeepSeek API优化的高效处理
- 🚀 **并行处理**: 支持多线程并行API调用，大幅提升处理速度
- 🏷️ **多标签分类**: 一条评论可同时属于多个类别，准确反映复杂观点  
- 💾 **断点续传**: 支持中断恢复，大数据分析安全无忧
- 🔄 **自动保存**: 每处理一定数量自动保存进度
- ⚡ **智能调度**: 动态任务分配，线程安全的进度管理
- 📊 **实时进度**: 显示处理进度和预计剩余时间

### 3. 可视化报告 (`report_generator.py`)
- 📈 **交互式报告**: 生成包含图表的HTML可视化报告
- 📊 **统计分析**: 详细的类别分布和代表性评论
- 🎨 **图表嵌入**: 中文字体支持，图表直接嵌入HTML
- 📄 **多格式输出**: HTML、JSON、CSV多种格式数据导出
- 🔍 **自动检测**: 智能检测CSV文件，简化使用流程

## 环境要求

- Python 3.12+
- Poetry (依赖管理)
- DeepSeek API密钥

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

# 编辑 .env 文件，配置DeepSeek API和并行处理参数
```

**.env 文件配置**:
```bash
# DeepSeek API配置（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 并行处理配置
PARALLEL_WORKERS=5          # 并行worker数量（建议3-8）
REQUEST_DELAY=0.1           # 请求间隔秒数（避免API限制）

# 分析配置
AUTO_SAVE_INTERVAL=10       # 每N条评论保存进度
MAX_REPRESENTATIVE_REVIEWS=5 # 报告中每类别的代表性评论数量
```

## 使用方法

### 完整工作流程

#### 第一步：收集评论数据

**基本用法 - 收集《明末渊虚之羽》的评论**:
```bash
poetry run python steam_reviews_collector.py 2277560
```

**带参数的收集**:
```bash
# 限制收集数量
poetry run python steam_reviews_collector.py 2277560 --max-reviews 1000

# 指定输出文件
poetry run python steam_reviews_collector.py 2277560 --output my_reviews.csv

# 完整参数示例
poetry run python steam_reviews_collector.py 2277560 \
    --max-reviews 1000 \
    --review-type all \
    --delay 1.0 \
    --output wuchang_reviews.csv
```

**参数说明**:
- `app_id`: Steam游戏ID（必需）
- `--max-reviews`: 每种语言的最大评论数量（0=获取全部，默认为0）
- `--review-type`: 评论类型筛选（all/positive/negative，默认为all）
- `--delay`: 请求间隔时间（秒，默认为1.0）
- `--output`: 输出文件名（可选，默认自动生成时间戳文件名）

#### 第二步：AI分析评论

```bash
# 基本用法
poetry run python review_analyzer.py your_reviews.csv

# 指定输出目录
poetry run python review_analyzer.py your_reviews.csv --output analysis_results
```

**参数说明**:
- `input_file`: 输入的评论CSV文件（必需）
- `--output`: 输出目录（默认为当前目录）

**分析特点**:
- ✅ **API连接测试**: 开始前自动测试DeepSeek API连接
- 🔄 **断点续传**: 中断后重新运行会自动检测进度文件并询问是否继续
- 📊 **实时进度**: 显示处理进度、预计剩余时间
- 💾 **自动保存**: 定期保存进度，避免数据丢失

#### 第三步：生成可视化报告

```bash
# 基本用法（自动检测CSV文件）
poetry run python report_generator.py analysis_results/classification_progress.json

# 指定输出目录
poetry run python report_generator.py analysis_results/classification_progress.json --output report

# 手动指定原始评论文件
poetry run python report_generator.py analysis_results/classification_progress.json --reviews your_reviews.csv --output report
```

**参数说明**:
- `progress_file`: 分类进度JSON文件路径（必需）
- `--reviews`: 原始评论CSV文件路径（可选，工具会自动检测）
- `--output`: 输出目录（默认为report_output）

## 分析类别体系

### 好评类别
- **剧情故事**: 游戏的历史背景、故事情节、文学性、叙事等方面
- **美术音效**: 画面、音乐、视觉效果、音响效果等艺术表现  
- **游戏性**: 玩法创新、操作体验、游戏设计等机制层面
- **情感共鸣**: 感动、情怀、对国产游戏的支持等情感因素
- **其他**: 无具体理由的好评

### 差评类别
- **游戏质量**: 优化问题、bug、卡顿、闪退、性能等技术问题
- **游戏内容**: 不好玩、太难、地图设计、boss设计、操作手感、UI等玩法体验问题  
- **历史争议**: 满清缺席、历史考据、敏感内容、史实准确性等历史相关争议
- **宣发问题**: 营销炒作、505发行、定价策略、试玩偷跑、预购等宣传发行问题
- **后续公关**: 豪华版补偿、优化效率、官方态度等发售后服务问题
- **其他**: 无具体理由的单纯谩骂或情绪发泄

## 输出文件结构

### 评论收集器输出
```
steam_chinese_reviews_{app_id}_{timestamp}.csv
```
包含字段：
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
- 更多作者和评论详细信息...

### AI分析器输出
```
analysis_results/
├── classification_progress.json    # 分类进度和结果数据
```

### 报告生成器输出
```
report_output/
├── analysis_report.html           # 交互式可视化报告
├── analysis_statistics.json       # 详细统计数据  
└── classified_reviews.csv         # 完整分类结果
```

## 游戏ID获取

Steam游戏ID可以从游戏的Steam页面URL中获取：
- 《明末渊虚之羽》: `2277560`
- URL格式: `https://store.steampowered.com/app/{app_id}/game_name/`

## Roadmap (有时间就实现，不过大概率没时间😐)

### 🧪 测试与质量保证
- **单元测试覆盖**: 为所有核心功能添加单元测试，确保代码质量和功能稳定性
- **集成测试**: 测试完整工作流程，验证各模块间的协作
- **CI/CD集成**: 设置自动化测试流程，确保代码提交质量

### 🤖 AI模型优化与容错
- **敏感内容处理**: 实现DeepSeek API 400状态码的智能处理
- **模型切换机制**: 当遇到敏感内容时自动切换到备用模型或调整prompt策略
- **错误重试机制**: 实现智能重试策略，提高分析成功率

### 🏗️ 代码架构重构
- **ReviewAnalyzer基类设计**: 创建通用的评论分析基类

### 📊 数据与可视化
- **更多图表类型**: 添加词云、情感趋势、时间序列等可视化
- **交互式筛选**: 支持按时间、语言、评分等维度动态筛选数据
- **导出格式扩展**: 支持Excel、PDF等更多导出格式
- **数据持久化**: 实现数据库存储，支持历史数据查询和对比

---

## 常见问题

### API配置问题
如果遇到API连接失败，请检查：
1. `.env` 文件是否存在且包含正确的 `DEEPSEEK_API_KEY`
2. 确认API密钥格式正确（以 `sk-` 开头）
3. 验证API密钥是否有效且有足够余额
4. 检查网络连接是否正常

### 内存使用
- 大量评论分析时可能占用较多内存
- 建议处理超大数据集时分批进行
- 利用断点续传功能可以安全中断和恢复

### 文件权限
- 确保有足够的磁盘空间用于输出文件
- 确保对输出目录有写入权限

## 注意事项

- 🚫 请合理使用，避免对Steam服务器造成过大压力
- ⏰ 默认请求间隔为1秒，建议不要设置过小的值
- 💾 大量数据收集时建议使用增量保存功能
- 🔄 支持中断后继续，数据不会丢失
- 📊 收集完成后会自动显示数据统计概览
- 🤖 仅支持DeepSeek API，不支持其他AI服务


---

**免责声明**: 本工具仅用于学习和研究目的，请遵守Steam的使用条款和相关法律法规。