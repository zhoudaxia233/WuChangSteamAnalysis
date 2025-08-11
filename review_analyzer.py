#!/usr/bin/env python3
from typing import Dict, List
import json
import time
import os
import sys
import signal
import argparse
from datetime import datetime
from collections import Counter, defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ReviewAnalyzer:
    def __init__(self, api_key: str = None):
        """
        初始化AI分类器

        Args:
            api_key: DeepSeek API密钥，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DeepSeek API密钥未找到！请在.env文件中设置DEEPSEEK_API_KEY"
            )

        # 初始化OpenAI客户端，使用DeepSeek的base_url
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

        # 进度保存相关
        self.checkpoint_file = None
        self.auto_save_interval = int(
            os.getenv("AUTO_SAVE_INTERVAL", "10")
        )  # 每10条保存一次

        # Token统计
        self.total_tokens = 0

        # API错误计数
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 定义分类体系
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

    def test_api_connection(self) -> bool:
        """测试API连接"""
        print("🔍 正在测试API连接...")

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "请回复'连接成功'"},
                ],
                max_tokens=10,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            print("✅ API连接测试成功")
            print(f"响应内容: {content}")
            return True

        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False

    def _signal_handler(self, signum, frame):
        """处理中断信号，保存进度"""
        print(f"\n\n⚠️  检测到中断信号 ({signum})，正在保存进度...")
        if hasattr(self, "current_progress") and self.checkpoint_file:
            self._save_checkpoint()
            print(f"✅ 进度已保存到: {self.checkpoint_file}")
        print("🔄 安全退出")
        sys.exit(0)

    def _save_checkpoint(self):
        """保存当前进度"""
        if not hasattr(self, "current_progress") or not self.checkpoint_file:
            return

        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "processed_count": len(self.current_progress),
            "progress_data": self.current_progress,
            "total_count": getattr(self, "total_count", 0),
            "sample_size": getattr(self, "sample_size", None),
        }

        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

    def _load_checkpoint(self, checkpoint_file: str) -> Dict:
        """加载进度文件"""
        try:
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载进度文件 {checkpoint_file}: {e}")
        return {}

    def _call_deepseek_api(self, prompt: str, max_retries: int = 3) -> str:
        """调用DeepSeek API"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )

                # 统计token使用量
                if hasattr(response, "usage") and response.usage:
                    self.total_tokens += response.usage.total_tokens

                # 重置失败计数
                self.consecutive_failures = 0
                return response.choices[0].message.content.strip()

            except Exception as e:
                self.consecutive_failures += 1
                if self.consecutive_failures == 1:  # 只在第一次失败时显示详细错误
                    print(f"\n❌ API调用失败: {e}")

                if self.consecutive_failures >= self.max_consecutive_failures:
                    print(
                        f"\n🚫 连续 {self.max_consecutive_failures} 次API调用失败，停止分析"
                    )
                    print("请检查：")
                    print("1. DEEPSEEK_API_KEY 是否正确设置")
                    print("2. API密钥是否有效")
                    print("3. 网络连接是否正常")
                    print("4. DeepSeek服务是否可用")
                    raise Exception("API调用连续失败")

                if attempt < max_retries - 1:
                    time.sleep(2)

        return None

    def classify_single_review(self, review_text: str, is_positive: bool) -> List[str]:
        """
        对单条评论进行AI分类

        Args:
            review_text: 评论文本
            is_positive: 是否为好评

        Returns:
            分类结果列表
        """
        if not review_text:
            return []

        sentiment = "好评" if is_positive else "差评"
        categories = self.categories["positive" if is_positive else "negative"]

        category_list = "\n".join(
            [f"- {name}: {desc}" for name, desc in categories.items()]
        )

        prompt = f"""你是专业的游戏评论分析师。请分析以下《明末渊虚之羽》Steam评论，判断它属于哪些类别。

评论内容: "{review_text}"
评论类型: {sentiment}

可选类别:
{category_list}

要求:
1. 仔细理解评论的语义和情感倾向
2. 注意识别反讽、阴阳怪气等表达方式
3. 一条评论可以属于多个类别
4. 只返回适用的类别名称，用逗号分隔
5. 如果没有明确的类别，返回"无明确类别"
6. 必须从上述类别中选择，不要自创类别

示例输出格式: "剧情故事,美术音效" 或 "游戏质量" 或 "无明确类别"

输出:"""

        ai_response = self._call_deepseek_api(prompt)

        if not ai_response or ai_response == "无明确类别":
            return []

        # 解析AI响应
        result_categories = []
        raw_categories = ai_response.replace("、", ",").replace("，", ",").split(",")

        for cat in raw_categories:
            cat = cat.strip()
            if cat and cat != "无明确类别" and cat in categories:
                result_categories.append(cat)

        return result_categories

    def classify_batch(
        self,
        reviews_df: pd.DataFrame,
        sample_size: int = None,
        output_dir: str = "ai_analysis",
    ) -> pd.DataFrame:
        """
        批量分类评论（支持断点续传）

        Args:
            reviews_df: 评论数据
            sample_size: 样本大小，None表示全部处理
            output_dir: 输出目录，用于生成checkpoint文件名

        Returns:
            添加了分类结果的DataFrame
        """
        print("开始纯AI分类分析...")

        # 选择处理范围
        if sample_size and sample_size < len(reviews_df):
            df_to_process = reviews_df.sample(n=sample_size, random_state=42).copy()
            print(f"随机抽样 {sample_size} 条评论进行分析（共 {len(reviews_df)} 条）")
        else:
            df_to_process = reviews_df.copy()
            print(f"处理全部 {len(df_to_process)} 条评论")

        # 设置checkpoint文件
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.checkpoint_file = os.path.join(output_dir, "classification_progress.json")

        # 存储进度相关变量
        self.total_count = len(df_to_process)
        self.sample_size = sample_size
        self.current_progress = []

        # 检查是否有断点文件
        checkpoint_data = self._load_checkpoint(self.checkpoint_file)
        start_idx = 0

        if checkpoint_data and checkpoint_data.get("progress_data"):
            print(f"🔄 发现断点文件，已处理 {checkpoint_data['processed_count']} 条")
            print("选择操作：")
            print("1. 继续AI分析 (Y)")
            print("2. 基于现有数据生成报告 (R)")
            print("3. 重新开始分析 (N)")
            choice = input("请选择 (Y/r/n): ").lower().strip()

            if choice == "r":
                print("🎯 基于现有数据生成报告...")
                # 构建简化的DataFrame用于报告生成
                classified_data = []
                for item in checkpoint_data["progress_data"]:
                    row = {
                        "index": item["index"],
                        "ai_categories": item["categories"],
                        "voted_up": item.get("is_positive", True),
                        "analysis_is_positive": item.get("is_positive", True),
                        "review_text": f"评论{item['index']}",
                        "votes_up": 0,
                        "author_playtime_hours": 0,
                    }
                    if item["index"] < len(df_to_process):
                        original_row = df_to_process.iloc[item["index"]]
                        row.update(
                            {
                                "review_text": original_row.get(
                                    "review_text", f"评论{item['index']}"
                                ),
                                "votes_up": original_row.get("votes_up", 0),
                                "author_playtime_hours": original_row.get(
                                    "author_playtime_hours", 0
                                ),
                            }
                        )
                    classified_data.append(row)

                return pd.DataFrame(classified_data)
            elif choice != "n":
                self.current_progress = checkpoint_data["progress_data"]
                start_idx = len(self.current_progress)
                print(f"✅ 从第 {start_idx + 1} 条开始继续分析")
            else:
                print("🔄 重新开始分析")
                if os.path.exists(self.checkpoint_file):
                    os.remove(self.checkpoint_file)

        total_reviews = len(df_to_process)
        start_time = time.time()

        if start_idx > 0:
            print(
                f"📊 续传进度: 已完成 {start_idx}/{total_reviews} ({start_idx/total_reviews*100:.1f}%)"
            )

        # 处理评论（从断点开始）
        for idx, (df_idx, row) in enumerate(df_to_process.iterrows()):
            if idx < start_idx:
                continue

            if idx % 10 == 0 and idx >= start_idx:
                elapsed = time.time() - start_time
                if idx > start_idx:
                    estimated_total = (elapsed / (idx - start_idx)) * (
                        total_reviews - start_idx
                    )
                    remaining = estimated_total - elapsed
                else:
                    remaining = 0

                # 格式化Token显示
                if self.total_tokens >= 1000000:
                    token_display = f"{self.total_tokens/1000000:.1f}M"
                elif self.total_tokens >= 1000:
                    token_display = f"{self.total_tokens/1000:.1f}K"
                else:
                    token_display = str(self.total_tokens)

                print(
                    f"AI分析进度: {idx + 1}/{total_reviews} ({(idx + 1)/total_reviews*100:.1f}%) "
                    f"预计剩余: {remaining/60:.1f}分钟 | 已用Tokens: {token_display}"
                )

            review_text = str(row.get("review_text", ""))
            is_positive = bool(row.get("voted_up", True))

            try:
                categories = self.classify_single_review(review_text, is_positive)
            except Exception as e:
                if "API调用连续失败" in str(e):
                    print(f"\n💾 已保存前 {idx} 条评论的分析结果")
                    self._save_checkpoint()
                    raise e
                else:
                    print(f"警告: 第{idx + 1}条评论分析失败: {e}")
                    categories = []

            review_result = {
                "index": df_idx,
                "categories": categories,
                "is_positive": is_positive,
            }
            self.current_progress.append(review_result)

            # 定期保存进度
            if (idx + 1) % self.auto_save_interval == 0:
                self._save_checkpoint()

            # 控制请求频率，避免触发API限制
            time.sleep(0.2)

        # 最终保存
        self._save_checkpoint()

        # 将结果应用到DataFrame
        ai_categories = [[] for _ in range(len(df_to_process))]

        for result in self.current_progress:
            df_idx = result["index"]
            categories = result["categories"]
            result_is_positive = result.get("is_positive", True)  # 兼容旧格式

            try:
                position = df_to_process.index.get_loc(df_idx)
                # 验证分类是否与情感倾向匹配
                actual_is_positive = bool(df_to_process.iloc[position]["voted_up"])

                if result_is_positive == actual_is_positive:
                    ai_categories[position] = categories
                else:
                    # 如果情感倾向不匹配，重新分类这条评论
                    print(f"警告: 第{position + 1}条评论情感倾向不匹配，跳过")
                    ai_categories[position] = []

            except KeyError:
                continue

        df_to_process["ai_categories"] = ai_categories

        # 格式化最终Token显示
        if self.total_tokens >= 1000000:
            final_token_display = f"{self.total_tokens/1000000:.2f}M"
        elif self.total_tokens >= 1000:
            final_token_display = f"{self.total_tokens/1000:.1f}K"
        else:
            final_token_display = str(self.total_tokens)

        print(
            f"AI分类完成！处理了 {len(self.current_progress)} 条评论，耗时 {(time.time() - start_time)/60:.1f} 分钟"
        )
        print(f"总计使用Tokens: {final_token_display}")

        # 询问是否删除checkpoint文件
        choice = input("分析完成，是否删除进度文件？(Y/n): ").lower().strip()
        if choice != "n" and os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            print("✅ 进度文件已删除")

        return df_to_process

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

    def get_representative_reviews(
        self, classified_df: pd.DataFrame, max_per_category: int = None
    ) -> Dict:
        """获取每个类别的代表性评论"""
        if max_per_category is None:
            max_per_category = int(os.getenv("MAX_REPRESENTATIVE_REVIEWS", "5"))

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
                            "review_text": row["review_text"],
                            "votes_up": row.get("votes_up", 0),
                            "voted_up": row.get("voted_up", True),
                            "created_date": row.get("created_date", ""),
                            "author_playtime_hours": row.get(
                                "author_playtime_hours", 0
                            ),
                        }
                    )

            # 按点赞数排序
            category_reviews.sort(key=lambda x: x["votes_up"], reverse=True)
            representative[category_name] = category_reviews[:max_per_category]

        return representative

    def create_visualizations(self, stats: Dict, output_dir: str):
        """创建可视化图表"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

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
            plt.savefig(
                f"{output_dir}/positive_categories_ai.png", dpi=300, bbox_inches="tight"
            )
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
            plt.savefig(
                f"{output_dir}/negative_categories_ai.png", dpi=300, bbox_inches="tight"
            )
            plt.close()

        # 3. 总体好差评比例
        plt.figure(figsize=(8, 6))
        labels = ["好评", "差评"]
        sizes = [stats["positive_reviews"], stats["negative_reviews"]]
        colors = ["#2ecc71", "#e74c3c"]

        plt.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)
        plt.title("好评差评比例", fontsize=16, fontweight="bold")
        plt.savefig(
            f"{output_dir}/overall_sentiment_ai.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

        print(f"可视化图表已保存到 {output_dir} 目录")

    def generate_report(
        self, classified_df: pd.DataFrame, output_dir: str = "ai_analysis"
    ) -> str:
        """生成完整的AI分析报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成统计数据
        stats = self.generate_statistics(classified_df)

        # 获取代表性评论
        representative = self.get_representative_reviews(classified_df)

        # 创建可视化
        self.create_visualizations(stats, output_dir)

        # 生成HTML报告
        report_path = f"{output_dir}/ai_analysis_report.html"
        html_content = self._generate_html_report(stats, representative)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 保存数据
        json_path = f"{output_dir}/ai_analysis_data.json"
        analysis_data = {
            "statistics": stats,
            "representative_reviews": representative,
            "generation_time": datetime.now().isoformat(),
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)

        # 保存分类结果
        csv_path = f"{output_dir}/ai_classified_reviews.csv"
        classified_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        print(f"\nAI分析报告已生成:")
        print(f"  HTML报告: {report_path}")
        print(f"  数据文件: {json_path}")
        print(f"  分类结果: {csv_path}")

        return report_path

    def _generate_html_report(self, stats: Dict, representative: Dict) -> str:
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
    
    <div class="category-section">
        <h2 class="category-title positive">好评类别分析</h2>
        <p><em>AI深度语义分析，准确理解评论意图</em></p>
        """

        # 好评类别
        for cat_name, cat_data in stats["positive_categories"].items():
            display_name = f"{cat_name}（好评）" if cat_name == "其他" else cat_name
            html += f"""
        <div class="category-item positive">
            <h3>{display_name}</h3>
            <p><strong>{cat_data['count']}</strong> 条评论 ({cat_data['percentage']:.1f}%)</p>
            """

            if cat_name in representative:
                html += "<h4>代表性评论:</h4>"
                for review in representative[cat_name][:3]:
                    html += f"""
                    <div class="representative-review">
                        <div class="review-text">"{review['review_text'][:200]}{'...' if len(review['review_text']) > 200 else ''}"</div>
                        <div class="review-meta">
                            👍 {review['votes_up']} 点赞 | 
                            ⏱️ 游戏时长: {review.get('author_playtime_hours', 0):.1f}小时
                        </div>
                    </div>
                    """

            html += "</div>"

        html += """
    </div>
    
    <div class="category-section">
        <h2 class="category-title negative">差评类别分析</h2>
        <p><em>AI深度语义分析，准确理解评论意图</em></p>
        """

        # 差评类别
        for cat_name, cat_data in stats["negative_categories"].items():
            display_name = f"{cat_name}（差评）" if cat_name == "其他" else cat_name
            html += f"""
        <div class="category-item negative">
            <h3>{display_name}</h3>
            <p><strong>{cat_data['count']}</strong> 条评论 ({cat_data['percentage']:.1f}%)</p>
            """

            if cat_name in representative:
                html += "<h4>代表性评论:</h4>"
                for review in representative[cat_name][:3]:
                    html += f"""
                    <div class="representative-review">
                        <div class="review-text">"{review['review_text'][:200]}{'...' if len(review['review_text']) > 200 else ''}"</div>
                        <div class="review-meta">
                            👍 {review['votes_up']} 点赞 | 
                            ⏱️ 游戏时长: {review.get('author_playtime_hours', 0):.1f}小时
                        </div>
                    </div>
                    """

            html += "</div>"

        if stats["multi_category_stats"]:
            html += """
    </div>
    
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

        html += """
    </div>
    
    <div class="category-section">
        <h2>AI分析优势</h2>
        <ul>
            <li><strong>语义理解</strong>: 能理解上下文和隐含意思</li>
            <li><strong>反讽识别</strong>: 识别阴阳怪气和反话</li>
            <li><strong>复合分析</strong>: 一条评论多个问题准确识别</li>
            <li><strong>情感分析</strong>: 准确判断真实情感倾向</li>
        </ul>
    </div>
</body>
</html>
        """

        return html


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="纯AI Steam评论分类工具")
    parser.add_argument("input_file", help="输入的评论CSV文件")
    parser.add_argument("--output", default=".", help="输出目录（默认当前目录）")

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件 {args.input_file} 不存在")
        return

    output_dir = args.output

    print("=== 纯AI Steam评论分类工具 ===")
    print(f"输入文件: {args.input_file}")
    print(f"输出目录: {output_dir}")
    print("-" * 50)

    # 加载数据
    try:
        reviews_df = pd.read_csv(args.input_file)
        print(f"加载了 {len(reviews_df)} 条评论")

    except Exception as e:
        print(f"错误: 无法加载CSV文件 - {e}")
        return

    # 检查必要字段
    required_fields = ["review_text", "voted_up"]
    missing_fields = [
        field for field in required_fields if field not in reviews_df.columns
    ]
    if missing_fields:
        print(f"错误: CSV文件缺少必要字段: {missing_fields}")
        return

    # 初始化AI分类器
    try:
        classifier = ReviewAnalyzer()
    except ValueError as e:
        print(f"错误: {e}")
        print("请确保已设置DEEPSEEK_API_KEY环境变量")
        return

    # API连接测试
    if not classifier.test_api_connection():
        print("\n🚫 API连接测试失败，请检查配置后重试")
        print("\n常见问题排查：")
        print("1. 检查 .env 文件是否存在且包含正确的 DEEPSEEK_API_KEY")
        print("2. 确认API密钥格式正确（以 sk- 开头）")
        print("3. 验证API密钥是否有效且有足够余额")
        print("4. 检查网络连接是否正常")
        return

    print("-" * 50)

    # 进行AI分类
    classified_df = classifier.classify_batch(reviews_df, None, output_dir)

    # 生成报告
    report_path = classifier.generate_report(classified_df, output_dir)

    print("\n=== AI分析完成 ===")
    print(f"报告已生成: {report_path}")
    print("可以用浏览器打开HTML报告查看详细结果！")


if __name__ == "__main__":
    main()
