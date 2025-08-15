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

        for _, row in classified_df.iterrows():
            cat_count = len(row["ai_categories"])
            if cat_count > 1:
                multi_cat_counts[cat_count] += 1

        stats["multi_category_stats"] = dict(multi_cat_counts)

        return stats

    def get_representative_reviews(self, classified_df: pd.DataFrame) -> Dict:
        """获取每个类别的代表性评论"""
        representative = {}

        # 分别处理好评和差评类别
        for sentiment, categories in self.categories.items():
            is_positive = sentiment == "positive"
            # 筛选对应情感倾向的评论
            sentiment_df = classified_df[classified_df["voted_up"] == is_positive]

            for category_name in categories.keys():
                category_reviews = []
                seen_reviews = set()  # 用于去重的集合

                # 分两轮收集：第一轮只收集单一类别的评论，第二轮补充多类别评论
                single_category_reviews = []
                multi_category_reviews = []

                for idx, row in sentiment_df.iterrows():
                    if category_name in row["ai_categories"]:
                        review_text = row.get("review_text", f"评论{idx}")
                        votes_up = row.get("votes_up", 0)
                        created_date = row.get("created_date", "")
                        ai_categories = row["ai_categories"]

                        # 使用评论文本的起始片段作为去重键，对于高度相似的评论
                        # 只取前100个字符进行比较，这样能捕获大部分重复但有细微差别的评论
                        import re

                        # 去除所有标点符号和空白字符，只保留中文字符，并截取前100字符
                        cleaned_text = re.sub(r"[^\u4e00-\u9fff\w]", "", review_text)[
                            :100
                        ]
                        review_key = cleaned_text

                        if review_key not in seen_reviews:
                            seen_reviews.add(review_key)
                            review_data = {
                                "review_text": review_text,
                                "votes_up": votes_up,
                                "voted_up": row.get("voted_up", True),
                                "created_date": created_date,
                                "author_playtime_hours": row.get(
                                    "author_playtime_hours", 0
                                ),
                                "language": row.get("language", ""),
                                "category_count": len(ai_categories),
                            }

                            # 根据类别数量分类
                            if len(ai_categories) == 1:
                                single_category_reviews.append(review_data)
                            else:
                                multi_category_reviews.append(review_data)

                # 优先选择单一类别评论，按点赞数排序
                single_category_reviews.sort(
                    key=lambda x: (-x["votes_up"], x["review_text"])
                )
                multi_category_reviews.sort(
                    key=lambda x: (-x["votes_up"], x["review_text"])
                )

                # 先添加单一类别评论，如果不够再添加多类别评论
                category_reviews = single_category_reviews[
                    : self.max_representative_reviews
                ]
                if len(category_reviews) < self.max_representative_reviews:
                    remaining_slots = self.max_representative_reviews - len(
                        category_reviews
                    )
                    category_reviews.extend(multi_category_reviews[:remaining_slots])

                # 为不同情感倾向的相同类别名称创建不同的键，避免覆盖
                sentiment_suffix = "（好评）" if is_positive else "（差评）"
                unique_key = (
                    f"{category_name}{sentiment_suffix}"
                    if category_name == "其他"
                    else category_name
                )

                representative[unique_key] = category_reviews[
                    : self.max_representative_reviews
                ]

        # 添加全局高赞好评和差评
        self._add_global_top_reviews(classified_df, representative)

        return representative

    def _add_global_top_reviews(
        self, classified_df: pd.DataFrame, representative: Dict
    ):
        """添加全局高赞好评和差评"""
        import re

        # 全局高赞好评
        positive_df = classified_df[classified_df["voted_up"] == True]
        if not positive_df.empty:
            positive_reviews = []
            seen_positive = set()

            # 按点赞数排序
            positive_df_sorted = positive_df.sort_values("votes_up", ascending=False)

            for idx, row in positive_df_sorted.iterrows():
                review_text = row.get("review_text", f"评论{idx}")
                votes_up = row.get("votes_up", 0)
                created_date = row.get("created_date", "")

                # 去重逻辑
                cleaned_text = re.sub(r"[^\u4e00-\u9fff\w]", "", review_text)[:100]
                review_key = cleaned_text

                if review_key not in seen_positive:
                    seen_positive.add(review_key)
                    positive_reviews.append(
                        {
                            "review_text": review_text,
                            "votes_up": votes_up,
                            "voted_up": True,
                            "created_date": created_date,
                            "author_playtime_hours": row.get(
                                "author_playtime_hours", 0
                            ),
                            "language": row.get("language", ""),
                            "ai_categories": row["ai_categories"],
                        }
                    )

                    if len(positive_reviews) >= self.max_representative_reviews:
                        break

            representative["全局高赞好评"] = positive_reviews

        # 全局高赞差评
        negative_df = classified_df[classified_df["voted_up"] == False]
        if not negative_df.empty:
            negative_reviews = []
            seen_negative = set()

            # 按点赞数排序
            negative_df_sorted = negative_df.sort_values("votes_up", ascending=False)

            for idx, row in negative_df_sorted.iterrows():
                review_text = row.get("review_text", f"评论{idx}")
                votes_up = row.get("votes_up", 0)
                created_date = row.get("created_date", "")

                # 去重逻辑
                cleaned_text = re.sub(r"[^\u4e00-\u9fff\w]", "", review_text)[:100]
                review_key = cleaned_text

                if review_key not in seen_negative:
                    seen_negative.add(review_key)
                    negative_reviews.append(
                        {
                            "review_text": review_text,
                            "votes_up": votes_up,
                            "voted_up": False,
                            "created_date": created_date,
                            "author_playtime_hours": row.get(
                                "author_playtime_hours", 0
                            ),
                            "language": row.get("language", ""),
                            "ai_categories": row["ai_categories"],
                        }
                    )

                    if len(negative_reviews) >= self.max_representative_reviews:
                        break

            representative["全局高赞差评"] = negative_reviews

    def create_visualizations(self, stats: Dict) -> Dict[str, str]:
        """创建可视化图表并返回base64编码"""
        # 设置全局字体大小
        plt.rcParams.update({"font.size": 16})

        charts = {}

        # 1. 好评类别分布
        if stats["positive_categories"]:
            plt.figure(figsize=(18, 10))  # 增大图表尺寸
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
                    fontsize=15,  # 增大数值标签字体
                    fontweight="bold",
                )

            plt.title(
                "好评类别分布", fontsize=22, fontweight="bold", pad=20
            )  # 增大标题并去掉"AI分析"
            plt.xlabel("类别", fontsize=18)  # 增大轴标签字体
            plt.ylabel("评论数量", fontsize=18)
            plt.xticks(
                range(len(labels)), labels, rotation=45, ha="right", fontsize=16
            )  # 增大刻度字体
            plt.yticks(fontsize=16)
            plt.grid(axis="y", alpha=0.3, linewidth=0.8)  # 添加网格线
            plt.tight_layout()

            # 转换为base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=200, bbox_inches="tight")  # 增加DPI
            buffer.seek(0)
            charts["positive_categories"] = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()

        # 2. 差评类别分布
        if stats["negative_categories"]:
            plt.figure(figsize=(18, 10))  # 增大图表尺寸
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
                    fontsize=15,  # 增大数值标签字体
                    fontweight="bold",
                )

            plt.title(
                "差评类别分布", fontsize=22, fontweight="bold", pad=20
            )  # 增大标题并去掉"AI分析"
            plt.xlabel("类别", fontsize=18)  # 增大轴标签字体
            plt.ylabel("评论数量", fontsize=18)
            plt.xticks(
                range(len(labels)), labels, rotation=45, ha="right", fontsize=16
            )  # 增大刻度字体
            plt.yticks(fontsize=16)
            plt.grid(axis="y", alpha=0.3, linewidth=0.8)  # 添加网格线
            plt.tight_layout()

            # 转换为base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=200, bbox_inches="tight")  # 增加DPI
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
        html = (
            f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steam评论分析报告 - 明末渊虚之羽</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        
        .content-layout {{
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .sidebar {{
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            height: fit-content;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            position: sticky;
            top: 20px;
        }}
        
        .sidebar h2 {{
            color: #2c3e50;
            margin-bottom: 25px;
            font-size: 1.4rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 25px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-3px);
        }}
        
        .stat-number {{
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.85rem;
            opacity: 0.9;
        }}
        
        .progress-section {{
            margin-top: 25px;
        }}
        
        .progress-label {{
            color: #2c3e50;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1rem;
        }}
        
        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        
        .progress-fill {{
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            height: 100%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }}
        
        .progress-text {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: #6c757d;
        }}
        
        .main-content {{
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        
        .charts-section {{
            margin-bottom: 40px;
        }}
        
        .chart-container {{
            display: flex;
            flex-direction: column;
            gap: 30px;
            margin-top: 20px;
        }}
        
        .chart-item {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            text-align: center;
            width: 100%;
        }}
        
        .chart-item img {{
            width: 100%;
            border-radius: 10px;
        }}
        
        .section-title {{
            color: #2c3e50;
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        .categories-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        
        .category-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .category-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        
        .category-card.positive {{
            border-left-color: #28a745;
            background: linear-gradient(135deg, #ffffff 0%, #f8fff8 100%);
        }}
        
        .category-card.negative {{
            border-left-color: #dc3545;
            background: linear-gradient(135deg, #ffffff 0%, #fff8f8 100%);
        }}
        
        .category-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .category-name {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .category-stats {{
            display: flex;
            gap: 10px;
        }}
        
        .stat-badge {{
            background: #f8f9fa;
            color: #495057;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .reviews-container {{
            max-height: 350px;
            overflow-y: auto;
            padding-right: 10px;
        }}
        
        .review-item {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 12px;
            border-left: 3px solid #667eea;
            transition: all 0.2s ease;
        }}
        
        .review-item:hover {{
            background: #e9ecef;
            transform: translateX(3px);
        }}
        
        .review-number {{
            color: #6c757d;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .review-text {{
            color: #495057;
            line-height: 1.5;
            margin-bottom: 10px;
            font-style: italic;
        }}
        
        .review-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: #6c757d;
        }}
        
        .vote-info {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .playtime-info {{
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-left: 8px;
        }}
        
        .emoji {{
            font-size: 1rem;
        }}
        
        .footer {{
            background: rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            color: rgba(255,255,255,0.9);
            margin-top: 30px;
        }}
        
        .footer p {{
            margin-bottom: 8px;
        }}
        
        /* 滚动条样式 */
        .reviews-container::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .reviews-container::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 3px;
        }}
        
        .reviews-container::-webkit-scrollbar-thumb {{
            background: #667eea;
            border-radius: 3px;
        }}
        
        /* 响应式设计 */
        @media (max-width: 1200px) {{
            .content-layout {{
                grid-template-columns: 1fr;
            }}
            .sidebar {{
                position: static;
            }}
            .chart-container {{
                grid-template-columns: 1fr;
            }}
            .categories-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            .header h1 {{
                font-size: 2rem;
            }}
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🎮 《明末渊虚之羽》Steam评论分析报告</h1>
            <p>基于DeepSeek深度语义分析</p>
            <p>📊 数据来源：全部中文评论（简体+繁体），截止2025年8月10日</p>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="content-layout">
            <aside class="sidebar">
                <h2>📊 数据概览</h2>
                
                <div class="stats-grid">
            <div class="stat-card">
                        <div class="stat-number">{stats['total_reviews']:,}</div>
                        <div class="stat-label">总评论数</div>
            </div>
                    
                    <div class="stat-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                        <div class="stat-number">{stats['positive_reviews']:,}</div>
                        <div class="stat-label">好评数量</div>
            </div>
    
                    <div class="stat-card" style="background: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%);">
                        <div class="stat-number">{stats['negative_reviews']:,}</div>
                        <div class="stat-label">差评数量</div>
            </div>
                    
                    <div class="stat-card" style="background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);">
                <div class="stat-number">{stats['positive_reviews']/(stats['total_reviews'])*100:.1f}%</div>
                        <div class="stat-label">好评率</div>
            </div>
            </div>
                
                <div class="progress-section">
                    <div class="progress-label">评论情感分布</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {stats['positive_reviews']/(stats['total_reviews'])*100:.1f}%;"></div>
        </div>
                    <div class="progress-text">
                        <span>👍 好评 {stats['positive_reviews']/(stats['total_reviews'])*100:.1f}%</span>
                        <span>👎 差评 {stats['negative_reviews']/(stats['total_reviews'])*100:.1f}%</span>
    </div>
        </div>
                
                <div style="background: #e8f5e8; border-radius: 10px; padding: 15px; margin-top: 20px; border-left: 4px solid #28a745;">
                    <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 1rem;">👍 好评类别定义</h4>
                    <div style="color: #495057; line-height: 1.4; font-size: 0.85rem;">"""
            + "".join(
                [
                    f'<div style="margin-bottom: 8px;"><strong>{cat_name}：</strong>{cat_desc}</div>'
                    for cat_name, cat_desc in self.categories["positive"].items()
                ]
            )
            + """
                    </div>
                </div>
                
                <div style="background: #fce8e8; border-radius: 10px; padding: 15px; margin-top: 15px; border-left: 4px solid #dc3545;">
                    <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 1rem;">👎 差评类别定义</h4>
                    <div style="color: #495057; line-height: 1.4; font-size: 0.85rem;">"""
            + "".join(
                [
                    f'<div style="margin-bottom: 8px;"><strong>{cat_name}：</strong>{cat_desc}</div>'
                    for cat_name, cat_desc in self.categories["negative"].items()
                ]
            )
            + """
                    </div>
                </div>
            </aside>
            
            <main class="main-content">
                                <section class="charts-section">
                    <h2 class="section-title">
                        <span class="emoji">📈</span>
                        类别分布可视化
                    </h2>
                    
                    <div class="chart-container">"""
        )

        # 添加图表
        if charts:
            if "positive_categories" in charts:
                html += f"""
                        <div class="chart-item">
                            <img src="data:image/png;base64,{charts['positive_categories']}" alt="好评类别分布" style="width: 100%; height: auto;">
                        </div>"""

            if "negative_categories" in charts:
                html += f"""
                        <div class="chart-item">
                            <img src="data:image/png;base64,{charts['negative_categories']}" alt="差评类别分布" style="width: 100%; height: auto;">
                        </div>"""

        html += """
        </div>
                    
                    <div style="background: #f8f9fa; border-radius: 10px; padding: 20px; margin-top: 20px; border-left: 4px solid #667eea;">
                        <h4 style="color: #2c3e50; margin-bottom: 15px;">📋 统计说明</h4>
                        <ul style="color: #495057; line-height: 1.6; margin: 0;">
                            <li><strong>多标签分类：</strong>一条评论可能包含多个类别（如既谈论画面又谈论剧情）</li>
                            <li><strong>分类规则：</strong>短评（≤50字）只能分配单一类别，长评可以分配多个类别</li>
                            <li><strong>百分比计算：</strong>由于存在某个评论属于多个类别的情况，各类别百分比相加会超过100%，所以没有使用饼状图</li>
                            <li><strong>智能识别：</strong>基于语义理解，能识别反讽、暗示等复杂表达</li>
                        </ul>
                    </div>
                    
                                        
                </section>
            </main>
        </div>
        
        <div class="categories-section" style="background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <h2 class="section-title">
                <span class="emoji">👍</span>
                好评类别分析
            </h2>
            
            <div class="categories-grid">"""

        # 好评类别
        if stats["positive_categories"]:
            for cat_name, cat_data in stats["positive_categories"].items():
                display_name = f"{cat_name}（好评）" if cat_name == "其他" else cat_name
                html += f"""
                <div class="category-card positive">
                    <div class="category-header">
                        <h3 class="category-name">{display_name}</h3>
                        <div class="category-stats">
                            <span class="stat-badge">{cat_data['count']} 条</span>
                            <span class="stat-badge">{cat_data['percentage']:.1f}%</span>
                        </div>
                    </div>
                    
                    <div class="reviews-container">"""

                # 为"其他"类别查找正确的键名
                if cat_name == "其他":
                    lookup_key = f"{cat_name}（好评）"
                else:
                    lookup_key = cat_name

                if lookup_key in representative and representative[lookup_key]:
                    for i, review in enumerate(
                        representative[lookup_key][: self.max_representative_reviews], 1
                    ):
                        review_text = review["review_text"]
                        # 确保评论内容不是占位符
                        if (
                            not review_text
                            or review_text.startswith("评论")
                            and "不可用" in review_text
                        ):
                            review_text = "（评论内容不可用）"

                        # 获取游玩时间信息
                        playtime_hours = review.get("author_playtime_hours", 0)
                        playtime_display = (
                            f"🎮 {playtime_hours:.1f}h"
                            if playtime_hours > 0
                            else "🎮 未记录"
                        )

                        html += f"""
                        <div class="review-item">
                            <div class="review-number">#{i}</div>
                            <div class="review-text">"{review_text[:150]}{'...' if len(review_text) > 150 else ''}"</div>
                        <div class="review-meta">
                                <div class="vote-info">
                                    <span class="emoji">👍</span>
                                    <span>{review['votes_up']} 赞同</span>
                                    <span class="playtime-info">{playtime_display}</span>
                        </div>
                                <span>{review.get('created_date', '未知日期')}</span>
                    </div>
                        </div>"""

                html += """
                    </div>
                </div>"""

        html += """
            </div>
        </div>
        
        <div class="categories-section" style="background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <h2 class="section-title">
                <span class="emoji">👎</span>
                差评类别分析
            </h2>
            
            <div class="categories-grid">"""

        # 差评类别
        if stats["negative_categories"]:
            for cat_name, cat_data in stats["negative_categories"].items():
                display_name = f"{cat_name}（差评）" if cat_name == "其他" else cat_name
                html += f"""
                <div class="category-card negative">
                    <div class="category-header">
                        <h3 class="category-name">{display_name}</h3>
                        <div class="category-stats">
                            <span class="stat-badge">{cat_data['count']} 条</span>
                            <span class="stat-badge">{cat_data['percentage']:.1f}%</span>
                        </div>
                    </div>
                    
                    <div class="reviews-container">"""

                # 为"其他"类别查找正确的键名
                if cat_name == "其他":
                    lookup_key = f"{cat_name}（差评）"
                else:
                    lookup_key = cat_name

                if lookup_key in representative and representative[lookup_key]:
                    for i, review in enumerate(
                        representative[lookup_key][: self.max_representative_reviews], 1
                    ):
                        review_text = review["review_text"]
                        # 确保评论内容不是占位符
                        if (
                            not review_text
                            or review_text.startswith("评论")
                            and "不可用" in review_text
                        ):
                            review_text = "（评论内容不可用）"

                        # 获取游玩时间信息
                        playtime_hours = review.get("author_playtime_hours", 0)
                        playtime_display = (
                            f"🎮 {playtime_hours:.1f}h"
                            if playtime_hours > 0
                            else "🎮 未记录"
                        )

                        html += f"""
                        <div class="review-item">
                            <div class="review-number">#{i}</div>
                            <div class="review-text">"{review_text[:150]}{'...' if len(review_text) > 150 else ''}"</div>
                        <div class="review-meta">
                                <div class="vote-info">
                                    <span class="emoji">👎</span>
                                    <span>{review['votes_up']} 赞同</span>
                                    <span class="playtime-info">{playtime_display}</span>
                        </div>
                                <span>{review.get('created_date', '未知日期')}</span>
                    </div>
                        </div>"""

                html += """
    </div>
                </div>"""

        # 添加全局高赞部分
        html += """
        
        <div class="categories-section" style="background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <h2 class="section-title">
                <span class="emoji">🏆</span>
                全局高赞评论
            </h2>
            
            <div class="categories-grid">"""

        # 全局高赞好评
        if "全局高赞好评" in representative and representative["全局高赞好评"]:
            html += (
                """
                <div class="category-card positive">
                    <div class="category-header">
                        <h3 class="category-name">高赞好评 TOP"""
                + str(self.max_representative_reviews)
                + """</h3>
                        <div class="category-stats">
                            <span class="stat-badge">"""
                + str(len(representative["全局高赞好评"]))
                + """ 条</span>
                        </div>
                    </div>
                    
                    <div class="reviews-container">"""
            )

            for i, review in enumerate(representative["全局高赞好评"], 1):
                review_text = review["review_text"]
                if not review_text or (
                    review_text.startswith("评论") and "不可用" in review_text
                ):
                    review_text = "（评论内容不可用）"

                # 显示评论所属的类别
                categories_str = (
                    "、".join(review["ai_categories"])
                    if review["ai_categories"]
                    else "无分类"
                )

                # 获取游玩时间信息
                playtime_hours = review.get("author_playtime_hours", 0)
                playtime_display = (
                    f"🎮 {playtime_hours:.1f}h" if playtime_hours > 0 else "🎮 未记录"
                )

                html += f"""
                        <div class="review-item">
                            <div class="review-number">#{i}</div>
                            <div class="review-text">"{review_text[:150]}{'...' if len(review_text) > 150 else ''}"</div>
                            <div class="review-meta">
                                <div class="vote-info">
                                    <span class="emoji">👍</span>
                                    <span>{review['votes_up']} 赞同</span>
                                    <span class="playtime-info">{playtime_display}</span>
                                </div>
                                <span>{review.get('created_date', '未知日期')}</span>
                                <span class="category-tags" style="color: #666; font-size: 0.9em;">分类：{categories_str}</span>
                            </div>
                        </div>"""

            html += """
                    </div>
                </div>"""

        # 全局高赞差评
        if "全局高赞差评" in representative and representative["全局高赞差评"]:
            html += (
                """
                <div class="category-card negative">
                    <div class="category-header">
                        <h3 class="category-name">高赞差评 TOP"""
                + str(self.max_representative_reviews)
                + """</h3>
                        <div class="category-stats">
                            <span class="stat-badge">"""
                + str(len(representative["全局高赞差评"]))
                + """ 条</span>
                        </div>
                    </div>
                    
                    <div class="reviews-container">"""
            )

            for i, review in enumerate(representative["全局高赞差评"], 1):
                review_text = review["review_text"]
                if not review_text or (
                    review_text.startswith("评论") and "不可用" in review_text
                ):
                    review_text = "（评论内容不可用）"

                # 显示评论所属的类别
                categories_str = (
                    "、".join(review["ai_categories"])
                    if review["ai_categories"]
                    else "无分类"
                )

                # 获取游玩时间信息
                playtime_hours = review.get("author_playtime_hours", 0)
                playtime_display = (
                    f"🎮 {playtime_hours:.1f}h" if playtime_hours > 0 else "🎮 未记录"
                )

                html += f"""
                        <div class="review-item">
                            <div class="review-number">#{i}</div>
                            <div class="review-text">"{review_text[:150]}{'...' if len(review_text) > 150 else ''}"</div>
                            <div class="review-meta">
                                <div class="vote-info">
                                    <span class="emoji">👎</span>
                                    <span>{review['votes_up']} 赞同</span>
                                    <span class="playtime-info">{playtime_display}</span>
                                </div>
                                <span>{review.get('created_date', '未知日期')}</span>
                                <span class="category-tags" style="color: #666; font-size: 0.9em;">分类：{categories_str}</span>
                            </div>
                        </div>"""

            html += """
                    </div>
                </div>"""

        html += """
            </div>
        </div>"""

        html += (
            """
        
        <footer class="footer">
            <p>📊 报告生成时间: """
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + """</p>
            <p>🤖 由AI智能分析系统生成 | 基于DeepSeek模型</p>
            <p>💡 想要更详细的分析结果？可查看生成的CSV文件获取完整数据</p>
        </footer>
    </div>
</body>
</html>
"""
        )

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
