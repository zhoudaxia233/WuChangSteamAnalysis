#!/usr/bin/env python3
"""
评论分析报告生成器 - 基于分析结果生成可视化报告
"""

import pandas as pd
import json
import os
import argparse
import base64
import io
from typing import Dict, List
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class ReportGenerator:
    """分析报告生成器"""

    def __init__(self):
        # 配置matplotlib中文字体
        plt.rcParams["font.sans-serif"] = [
            "Arial Unicode MS",  # macOS
            "PingFang SC",  # macOS 系统字体
            "SimHei",  # Windows
            "DejaVu Sans",  # 备用
        ]
        plt.rcParams["axes.unicode_minus"] = False

        # 从环境变量读取配置
        self.max_representative_reviews = int(
            os.getenv("MAX_REPRESENTATIVE_REVIEWS", "5")
        )

        # 定义分类体系（与AI分析器保持一致）
        self.categories = {
            "positive": {
                "剧情故事": "游戏的历史背景、故事情节、文学性、叙事等方面",
                "美术音效": "画面、音乐、视觉效果、音响效果等艺术表现",
                "游戏性": "玩法创新、操作体验、游戏设计等机制层面",
                "情感共鸣": "感动、情怀、对国产游戏的支持等情感因素",
                "其他": "无具体理由的好评",
            },
            "negative": {
                "游戏质量": "优化问题、bug、卡顿、闪退、性能等技术问题",
                "游戏内容": "不好玩、太难、地图设计、boss设计、操作手感、UI等玩法体验问题",
                "历史争议": "满清缺席、历史考据、敏感内容、史实准确性等历史相关争议",
                "宣发问题": "营销炒作、505发行、定价策略、试玩偷跑、预购等宣传发行问题",
                "后续公关": "豪华版补偿、优化效率、官方态度等发售后服务问题",
                "其他": "无具体理由的单纯谩骂或情绪发泄",
            },
        }

    def load_analysis_data(
        self, progress_file: str, reviews_file: str = None
    ) -> pd.DataFrame:
        """
        加载分析数据

        Args:
            progress_file: 分类进度文件路径
            reviews_file: 原始评论文件路径（可选，用于获取完整信息）

        Returns:
            包含分类结果的DataFrame
        """
        # 读取分类进度
        with open(progress_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)

        # 如果有原始评论文件，合并数据
        if reviews_file and os.path.exists(reviews_file):
            reviews_df = pd.read_csv(reviews_file)
            print(f"✅ 成功加载原始评论文件，共 {len(reviews_df)} 条评论")

            # 创建结果DataFrame
            classified_data = []
            for item in progress_data["progress_data"]:
                try:
                    idx = item["index"]
                    # 确保索引在DataFrame范围内
                    if idx < len(reviews_df):
                        # 获取原始评论数据
                        original_row = reviews_df.iloc[idx]

                        # 创建新的行数据
                        row = {
                            "index": idx,
                            "ai_categories": item["categories"],
                            "voted_up": item.get("is_positive", True),
                            "analysis_is_positive": item.get("is_positive", True),
                            "review_text": original_row.get(
                                "review_text", "无评论内容"
                            ),
                            "votes_up": original_row.get("votes_up", 0),
                            "author_playtime_hours": original_row.get(
                                "author_playtime_hours", 0
                            ),
                            "created_date": original_row.get("created_date", ""),
                            "author_steamid": original_row.get("author_steamid", ""),
                            "language": original_row.get("language", ""),
                        }
                        classified_data.append(row)
                    else:
                        print(f"⚠️ 警告: 索引 {idx} 超出原始数据范围，跳过")
                except Exception as e:
                    print(f"⚠️ 处理索引 {item.get('index', '未知')} 时出错: {e}")
                    continue

            result_df = pd.DataFrame(classified_data)
            print(f"✅ 成功合并数据，共 {len(result_df)} 条有效记录")
            return result_df
        else:
            print("⚠️ 未提供原始评论文件或文件不存在，使用简化模式")
            # 仅基于进度数据创建简化DataFrame
            classified_data = []
            for item in progress_data["progress_data"]:
                row = {
                    "index": item["index"],
                    "ai_categories": item["categories"],
                    "voted_up": item.get("is_positive", True),
                    "analysis_is_positive": item.get("is_positive", True),
                    "review_text": f"评论{item['index']}（原始内容不可用）",
                    "votes_up": 0,
                    "author_playtime_hours": 0,
                    "created_date": "",
                    "author_steamid": "",
                    "language": "",
                }
                classified_data.append(row)

            return pd.DataFrame(classified_data)

    def generate_statistics(self, classified_df: pd.DataFrame) -> Dict:
        """生成统计数据"""
        stats = {
            "total_reviews": len(classified_df),
            "positive_reviews": len(classified_df[classified_df["voted_up"] == True]),
            "negative_reviews": len(classified_df[classified_df["voted_up"] == False]),
            "positive_categories": {},
            "negative_categories": {},
            "multi_category_stats": {},
            "uncategorized": 0,
        }

        # 分别统计好评和差评
        positive_df = classified_df[classified_df["voted_up"] == True]
        negative_df = classified_df[classified_df["voted_up"] == False]

        # 统计好评类别
        all_positive_cats = []
        for categories in positive_df["ai_categories"]:
            if categories:
                all_positive_cats.extend(categories)

        positive_counter = Counter(all_positive_cats)
        for cat_name, count in positive_counter.items():
            stats["positive_categories"][cat_name] = {
                "count": count,
                "percentage": (
                    count / stats["positive_reviews"] * 100
                    if stats["positive_reviews"] > 0
                    else 0
                ),
            }

        # 统计差评类别
        all_negative_cats = []
        for categories in negative_df["ai_categories"]:
            if categories:
                all_negative_cats.extend(categories)

        negative_counter = Counter(all_negative_cats)
        for cat_name, count in negative_counter.items():
            stats["negative_categories"][cat_name] = {
                "count": count,
                "percentage": (
                    count / stats["negative_reviews"] * 100
                    if stats["negative_reviews"] > 0
                    else 0
                ),
            }

        # 多类别统计
        multi_cat_counts = defaultdict(int)
        uncategorized_count = 0

        for _, row in classified_df.iterrows():
            cat_count = len(row["ai_categories"])
            if cat_count == 0:
                uncategorized_count += 1
            elif cat_count > 1:
                multi_cat_counts[cat_count] += 1

        stats["multi_category_stats"] = dict(multi_cat_counts)
        stats["uncategorized"] = uncategorized_count

        return stats

    def get_representative_reviews(self, classified_df: pd.DataFrame) -> Dict:
        """获取每个类别的代表性评论"""
        representative = {}

        # 收集所有类别
        all_categories = set()
        for categories in classified_df["ai_categories"]:
            all_categories.update(categories)

        for category_name in all_categories:
            category_reviews = []

            for idx, row in classified_df.iterrows():
                if category_name in row["ai_categories"]:
                    category_reviews.append(
                        {
                            "review_text": row.get("review_text", f"评论{idx}"),
                            "votes_up": row.get("votes_up", 0),
                            "voted_up": row.get("voted_up", True),
                            "created_date": row.get("created_date", ""),
                            "author_playtime_hours": row.get(
                                "author_playtime_hours", 0
                            ),
                            "language": row.get("language", ""),
                        }
                    )

            # 按点赞数排序，取前N条
            category_reviews.sort(key=lambda x: x["votes_up"], reverse=True)
            representative[category_name] = category_reviews[
                : self.max_representative_reviews
            ]

        return representative

    def create_visualizations(self, stats: Dict) -> Dict[str, str]:
        """创建可视化图表并返回base64编码"""
        charts = {}

        # 1. 好评类别分布
        if stats["positive_categories"]:
            plt.figure(figsize=(12, 8))
            labels = list(stats["positive_categories"].keys())
            counts = [cat["count"] for cat in stats["positive_categories"].values()]

            bars = plt.bar(range(len(labels)), counts, color="#2ecc71", alpha=0.8)

            for bar, count in zip(bars, counts):
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + height * 0.01,
                    f"{count}",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                )

            plt.title("好评类别分布 (AI分析)", fontsize=16, fontweight="bold")
            plt.xlabel("类别", fontsize=12)
            plt.ylabel("评论数量", fontsize=12)
            plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
            plt.tight_layout()

            # 转换为base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            charts["positive_categories"] = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()

        # 2. 差评类别分布
        if stats["negative_categories"]:
            plt.figure(figsize=(12, 8))
            labels = list(stats["negative_categories"].keys())
            counts = [cat["count"] for cat in stats["negative_categories"].values()]

            bars = plt.bar(range(len(labels)), counts, color="#e74c3c", alpha=0.8)

            for bar, count in zip(bars, counts):
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + height * 0.01,
                    f"{count}",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                )

            plt.title("差评类别分布 (AI分析)", fontsize=16, fontweight="bold")
            plt.xlabel("类别", fontsize=12)
            plt.ylabel("评论数量", fontsize=12)
            plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
            plt.tight_layout()

            # 转换为base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            charts["negative_categories"] = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()

        print(f"✅ 生成了 {len(charts)} 个可视化图表")
        return charts

    def generate_html_report(
        self,
        stats: Dict,
        representative: Dict,
        charts: Dict[str, str],
        output_path: str,
    ):
        """生成HTML报告"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI评论分析报告 - 明末渊虚之羽</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .category-section {{ margin-bottom: 40px; }}
        .category-title {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .category-item {{ background: white; border-left: 4px solid #3498db; padding: 15px; margin: 10px 0; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .positive {{ border-left-color: #27ae60; }}
        .negative {{ border-left-color: #e74c3c; }}
        .review-text {{ background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0; font-style: italic; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .representative-review {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; }}
        .review-meta {{ color: #666; font-size: 0.9em; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>《明末渊虚之羽》Steam评论AI分析报告</h1>
        <p>基于DeepSeek AI深度语义分析</p>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>总体概况</h2>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{stats['total_reviews']}</div>
                <div>总分析数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['positive_reviews']}</div>
                <div>好评数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['negative_reviews']}</div>
                <div>差评数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['positive_reviews']/(stats['total_reviews'])*100:.1f}%</div>
                <div>好评率</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['uncategorized']}</div>
                <div>无法分类</div>
            </div>
        </div>
    </div>
"""

        # 嵌入图表
        if charts:
            html += """
    <div class="category-section">
        <h2>可视化分析</h2>
"""
            if "positive_categories" in charts:
                html += f"""
        <div style="text-align: center; margin: 20px 0;">
            <img src="data:image/png;base64,{charts['positive_categories']}" 
                 alt="好评类别分布" style="max-width: 100%; height: auto;">
        </div>
"""
            if "negative_categories" in charts:
                html += f"""
        <div style="text-align: center; margin: 20px 0;">
            <img src="data:image/png;base64,{charts['negative_categories']}" 
                 alt="差评类别分布" style="max-width: 100%; height: auto;">
        </div>
"""
            html += "</div>"

        # 好评类别
        if stats["positive_categories"]:
            html += """
    <div class="category-section">
        <h2 class="category-title positive">好评类别分析</h2>
        <p><em>AI深度语义分析，准确理解评论意图</em></p>
"""
            for cat_name, cat_data in stats["positive_categories"].items():
                display_name = f"{cat_name}（好评）" if cat_name == "其他" else cat_name
                html += f"""
        <div class="category-item positive">
            <h3>{display_name}</h3>
            <p><strong>{cat_data['count']}</strong> 条评论 ({cat_data['percentage']:.1f}%)</p>
"""
                if cat_name in representative and representative[cat_name]:
                    html += f"<h4>代表性评论（前{len(representative[cat_name])}条，按点赞数排序）:</h4>"
                    for i, review in enumerate(representative[cat_name], 1):
                        review_text = review["review_text"]
                        # 确保评论内容不是占位符
                        if (
                            not review_text
                            or review_text.startswith("评论")
                            and "不可用" in review_text
                        ):
                            review_text = "（评论内容不可用）"

                        html += f"""
                    <div class="representative-review">
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">#{i}</div>
                        <div class="review-text">"{review_text[:300]}{'...' if len(review_text) > 300 else ''}"</div>
                        <div class="review-meta">
                            👍 {review['votes_up']} 点赞 | 
                            ⏱️ 游戏时长: {review.get('author_playtime_hours', 0):.1f}小时 |
                            📅 {review.get('created_date', '未知日期')}
                        </div>
                    </div>
"""
                html += "</div>"
            html += "</div>"

        # 差评类别
        if stats["negative_categories"]:
            html += """
    <div class="category-section">
        <h2 class="category-title negative">差评类别分析</h2>
        <p><em>AI深度语义分析，准确理解评论意图</em></p>
"""
            for cat_name, cat_data in stats["negative_categories"].items():
                display_name = f"{cat_name}（差评）" if cat_name == "其他" else cat_name
                html += f"""
        <div class="category-item negative">
            <h3>{display_name}</h3>
            <p><strong>{cat_data['count']}</strong> 条评论 ({cat_data['percentage']:.1f}%)</p>
"""
                if cat_name in representative and representative[cat_name]:
                    html += f"<h4>代表性评论（前{len(representative[cat_name])}条，按点赞数排序）:</h4>"
                    for i, review in enumerate(representative[cat_name], 1):
                        review_text = review["review_text"]
                        # 确保评论内容不是占位符
                        if (
                            not review_text
                            or review_text.startswith("评论")
                            and "不可用" in review_text
                        ):
                            review_text = "（评论内容不可用）"

                        html += f"""
                    <div class="representative-review">
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">#{i}</div>
                        <div class="review-text">"{review_text[:300]}{'...' if len(review_text) > 300 else ''}"</div>
                        <div class="review-meta">
                            👍 {review['votes_up']} 点赞 | 
                            ⏱️ 游戏时长: {review.get('author_playtime_hours', 0):.1f}小时 |
                            📅 {review.get('created_date', '未知日期')}
                        </div>
                    </div>
"""
                html += "</div>"
            html += "</div>"

        # 多类别统计
        if stats["multi_category_stats"]:
            html += """
    <div class="category-section">
        <h2>多类别评论统计</h2>
        <p>AI识别出的包含多个问题/优点的复合评论:</p>
"""
            for cat_count, review_count in sorted(
                stats["multi_category_stats"].items()
            ):
                html += (
                    f"<p><strong>{cat_count}个类别</strong>: {review_count} 条评论</p>"
                )

        html += f"""
    </div>
    
    <div class="category-section">
        <h2>分析说明</h2>
        <div style="background: #f0f8ff; padding: 15px; border-radius: 6px; margin: 15px 0;">
            <p><strong>🤖 AI分析优势:</strong></p>
            <ul>
                <li><strong>语义理解</strong>: 能理解上下文和隐含意思，不仅仅是关键词匹配</li>
                <li><strong>反讽识别</strong>: 识别阴阳怪气和反话，准确判断真实情感</li>
                <li><strong>多标签分类</strong>: 一条评论可以同时归属多个类别</li>
                <li><strong>情感分析</strong>: 准确区分好评差评中的"其他"类别</li>
            </ul>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 6px; margin: 15px 0;">
            <p><strong>📊 统计说明:</strong></p>
            <ul>
                <li>每个类别的百分比是相对于该情感倾向（好评/差评）总数计算</li>
                <li>由于支持多标签分类，所有类别百分比相加可能超过100%</li>
                <li>代表性评论按点赞数排序，显示前{self.max_representative_reviews}条</li>
                <li>评论内容截取前300字符以保持页面整洁</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def generate_report(
        self,
        progress_file: str,
        reviews_file: str = None,
        output_dir: str = "report_output",
    ) -> str:
        """
        生成完整报告

        Args:
            progress_file: 分类进度文件路径
            reviews_file: 原始评论文件路径（可选）
            output_dir: 输出目录

        Returns:
            HTML报告路径
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print("📊 正在加载分析数据...")
        classified_df = self.load_analysis_data(progress_file, reviews_file)

        print("📈 正在生成统计数据...")
        stats = self.generate_statistics(classified_df)

        print("⭐ 正在收集代表性评论...")
        representative = self.get_representative_reviews(classified_df)

        print("📊 正在创建可视化图表...")
        charts = self.create_visualizations(stats)

        print("📄 正在生成HTML报告...")
        report_path = f"{output_dir}/analysis_report.html"
        self.generate_html_report(stats, representative, charts, report_path)

        # 保存统计数据
        stats_path = f"{output_dir}/analysis_statistics.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "statistics": stats,
                    "representative_reviews": representative,
                    "generation_time": datetime.now().isoformat(),
                    "source_data": {
                        "progress_file": progress_file,
                        "reviews_file": reviews_file,
                        "total_analyzed": len(classified_df),
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        # 保存分类结果CSV
        csv_path = f"{output_dir}/classified_reviews.csv"
        classified_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ 报告生成完成:")
        print(f"  📄 HTML报告: {report_path}")
        print(f"  📊 统计数据: {stats_path}")
        print(f"  📋 分类结果: {csv_path}")
        print(f"  🎯 代表性评论数量: {self.max_representative_reviews} (来自环境变量)")

        return report_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Steam评论分析报告生成器")
    parser.add_argument("progress_file", help="分类进度JSON文件路径")
    parser.add_argument("--reviews", help="原始评论CSV文件路径（可选，自动检测）")
    parser.add_argument(
        "--output", default="report_output", help="输出目录（默认: report_output）"
    )

    args = parser.parse_args()

    if not os.path.exists(args.progress_file):
        print(f"❌ 错误: 进度文件 {args.progress_file} 不存在")
        return

    # 如果没有指定reviews文件，自动查找常见的CSV文件
    if not args.reviews:
        print("🔍 未指定原始评论文件，正在自动检测...")
        # 查找常见的CSV文件名
        possible_files = [
            "all-comments.csv",
            "all-comments-by-Aug10.csv",
            "complete_reviews.csv",
            "reviews.csv",
            "steam_reviews.csv",
        ]

        for filename in possible_files:
            if os.path.exists(filename):
                args.reviews = filename
                print(f"✅ 自动检测到评论文件: {filename}")
                break

        if not args.reviews:
            print("⚠️  未找到评论文件，将使用简化模式")

    if args.reviews and not os.path.exists(args.reviews):
        print(f"⚠️  警告: 指定的评论文件 {args.reviews} 不存在，将使用简化模式")
        args.reviews = None

    print("=== Steam评论分析报告生成器 ===")
    print(f"进度文件: {args.progress_file}")
    print(f"原始文件: {args.reviews or '(简化模式)'}")
    print(f"输出目录: {args.output}")
    print("-" * 50)

    generator = ReportGenerator()
    try:
        report_path = generator.generate_report(
            args.progress_file, args.reviews, args.output
        )
        print(f"\n🎉 报告已生成: {report_path}")
        print("可以用浏览器打开HTML报告查看详细结果！")
    except Exception as e:
        print(f"❌ 生成报告时发生错误: {e}")


if __name__ == "__main__":
    main()
