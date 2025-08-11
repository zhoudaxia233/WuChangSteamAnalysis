#!/usr/bin/env python3
from typing import Dict, List, Optional
import sys
import json
import time
import argparse
import signal
from datetime import datetime
import requests
import pandas as pd


class SteamChineseReviewCollector:
    def __init__(self, delay: float = 1.0, auto_save_interval: int = 1000):
        """
        Args:
            delay: 请求间隔时间（秒），避免频率限制
            auto_save_interval: 自动保存间隔（每多少条评论保存一次）
        """
        self.delay = delay
        self.auto_save_interval = auto_save_interval
        self.base_url = "https://store.steampowered.com/appreviews"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

        self.chinese_languages = ["schinese", "tchinese"]

        self.temp_file_path = None
        self.all_reviews = []

        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理Ctrl+C信号，保存已获取的数据"""
        print(f"\n\n⚠️  检测到中断信号，正在保存已获取的数据...")
        if self.all_reviews:
            if not self.temp_file_path:
                # 如果没有设置临时文件路径，生成一个
                self.temp_file_path = f"interrupted_reviews_{int(time.time())}.csv"
            self._save_incremental()
            print(f"✅ 已保存 {len(self.all_reviews)} 条评论到: {self.temp_file_path}")
        else:
            print(f"⚠️  没有数据需要保存")
        print(f"🔄 安全退出")
        sys.exit(0)

    def _save_incremental(self):
        """增量保存已获取的评论"""
        if self.all_reviews and self.temp_file_path:
            df = pd.DataFrame(self.all_reviews)
            df.to_csv(self.temp_file_path, index=False, encoding="utf-8")

    def get_chinese_reviews(
        self, app_id: int, max_reviews: int = 0, review_type: str = "all"
    ) -> List[Dict]:
        """
        获取中文游戏评论（包括简体和繁体）

        默认获取全部可用评论，直到Steam API没有更多数据为止

        Args:
            app_id: Steam游戏ID
            max_reviews: 每种语言的最大评论数量（0=获取全部，>0=限制数量）
            review_type: 评论类型 ('all', 'positive', 'negative')

        Returns:
            中文评论数据列表
        """
        self.all_reviews = []

        print(f"🚀 开始获取游戏 {app_id} 的中文评论数据...")

        # 获取各种评论统计
        all_lang_info = self._get_game_info(app_id)
        all_lang_total = all_lang_info.get("total_reviews", 0)
        print(f"📊 游戏总评论数: {all_lang_total} (所有语言)")

        # 获取各中文语言的评论统计
        schinese_info = self._get_language_info(app_id, "schinese")
        schinese_total = schinese_info.get("total_reviews", 0)

        tchinese_info = self._get_language_info(app_id, "tchinese")
        tchinese_total = tchinese_info.get("total_reviews", 0)

        # 计算安全上限
        expected_chinese_total = schinese_total + tchinese_total
        safety_limit = (
            min(all_lang_total, expected_chinese_total)
            if all_lang_total > 0
            else expected_chinese_total
        )

        print(
            f"🛡️ 预期中文评论总数: {expected_chinese_total} (简体: {schinese_total}, 繁体: {tchinese_total})"
        )
        if safety_limit > 0:
            print(f"🛡️ 安全上限设置为: {safety_limit}")

        for lang in self.chinese_languages:
            lang_name = "简体中文" if lang == "schinese" else "繁体中文"
            print(f"\n🔄 正在获取{lang_name}评论...")

            # 为这个语言设置合理的上限
            expected_lang_total = (
                schinese_total if lang == "schinese" else tchinese_total
            )
            lang_max = (
                expected_lang_total
                if max_reviews == 0
                else min(max_reviews, expected_lang_total)
            )

            if lang_max > 0:
                print(f"  📋 预期获取 {lang_max} 条{lang_name}评论")

            lang_reviews = self._get_reviews_by_language(
                app_id, lang, lang_max, review_type
            )
            self.all_reviews.extend(lang_reviews)

            print(
                f"✅ {lang_name}评论获取完成，本语言 {len(lang_reviews)} 条，累计 {len(self.all_reviews)} 条"
            )

            # 检查是否超过安全上限
            if safety_limit > 0 and len(self.all_reviews) >= safety_limit:
                print(f"🛑 已达到安全上限 ({safety_limit})，停止获取更多语言")
                break

            # 每个语言获取完后保存一次
            if self.temp_file_path:
                self._save_incremental()
                print(f"💾 已保存到: {self.temp_file_path}")

        print(f"\n🎉 所有中文评论获取完成，总计 {len(self.all_reviews)} 条")
        return self.all_reviews

    def _get_game_info(self, app_id: int) -> dict:
        """获取游戏基本信息，包括总评论数（所有语言）"""
        try:
            params = {
                "json": 1,
                "cursor": "*",
                "language": "all",
                "filter": "all",
                "review_type": "all",
                "purchase_type": "all",
                "num_per_page": 1,  # 只要1条，我们只需要summary
            }

            response = self.session.get(f"{self.base_url}/{app_id}", params=params)
            response.raise_for_status()
            data = response.json()

            query_summary = data.get("query_summary", {})
            print(f"🔍 所有语言评论统计(language=all): {query_summary}")
            return query_summary
        except Exception as e:
            print(f"⚠️  获取游戏信息失败: {e}")
            return {}

    def _get_language_info(self, app_id: int, language: str) -> dict:
        """获取特定语言的评论统计"""
        try:
            params = {
                "json": 1,
                "cursor": "*",
                "language": language,
                "filter": "all",
                "review_type": "all",
                "purchase_type": "all",
                "num_per_page": 1,
            }

            response = self.session.get(f"{self.base_url}/{app_id}", params=params)
            response.raise_for_status()
            data = response.json()

            query_summary = data.get("query_summary", {})
            lang_name = "简体中文" if language == "schinese" else "繁体中文"
            print(f"🔍 {lang_name}评论统计: {query_summary}")
            return query_summary
        except Exception as e:
            print(f"⚠️  获取{language}评论统计失败: {e}")
            return {}

    def _get_reviews_by_language(
        self, app_id: int, language: str, max_reviews: int, review_type: str
    ) -> List[Dict]:
        """
        获取特定语言的评论

        Args:
            app_id: Steam游戏ID
            language: 语言代码
            max_reviews: 最大评论数量
            review_type: 评论类型

        Returns:
            评论数据列表
        """
        reviews = []
        cursor = "*"  # Steam API的分页标识
        request_count = 0  # 请求计数，用于统计

        print(
            f"  📋 开始获取 {language} 评论，目标: {'全部' if max_reviews == 0 else f'{max_reviews}条'}"
        )

        while True:
            # 检查数量限制（仅在用户指定时才生效）
            if max_reviews > 0 and len(reviews) >= max_reviews:
                print(f"  ✋ 已达到指定限制 ({max_reviews})，停止获取")
                break

            # 智能停止：如果获取的数据已经接近或超过合理范围，显示警告
            if len(reviews) > 0 and len(reviews) % 10000 == 0:
                print(f"  📊 已获取 {len(reviews)} 条 {language} 评论")
                if len(reviews) >= 100000:  # 如果超过10万条，询问是否继续
                    print(f"  ⚠️  警告：已获取超过10万条评论，这可能超出预期")

            request_count += 1
            # 构建请求参数
            params = {
                "json": 1,
                "cursor": cursor,
                "language": language,
                "filter": "all",  # recent, updated, all - 改为all获取全部评论
                "review_type": review_type,
                "purchase_type": "all",  # 尝试获取所有购买类型的评论
                "num_per_page": (
                    100 if max_reviews == 0 else min(100, max_reviews - len(reviews))
                ),  # 每页最多100条
            }

            try:
                response = self.session.get(f"{self.base_url}/{app_id}", params=params)
                response.raise_for_status()

                data = response.json()

                # 检查是否有评论数据
                if not data.get("reviews"):
                    break

                # 处理评论数据
                batch_reviews = self._process_reviews(data["reviews"], language)
                reviews.extend(batch_reviews)

                print(
                    f"  已获取 {len(reviews)} 条评论... (本次请求: {len(batch_reviews)} 条, 请求#{request_count})"
                )

                # 每1000条保存一次
                if len(reviews) % 1000 == 0 and len(reviews) > 0:
                    print(f"    💾 已获取 {len(reviews)} 条 {language} 评论")

                # 更新游标，用于下一页
                new_cursor = data.get("cursor", "")

                # 详细调试信息
                if request_count % 100 == 0:  # 每100次请求输出详细调试信息
                    print(
                        f"  🔍 [DEBUG #{request_count}] cursor: {cursor[:30]}... -> {new_cursor[:30] if new_cursor else 'None'}..."
                    )
                    print(
                        f"      本次返回: {len(batch_reviews)} 条，累计: {len(reviews)} 条"
                    )

                # 检查Steam API的自然终止条件
                if not new_cursor:
                    print(f"  🏁 API返回空cursor，已获取全部数据，停止获取")
                    break

                if new_cursor == cursor:
                    print(f"  🏁 cursor未变化，已获取全部数据，停止获取")
                    break

                # 检查本次请求是否获取到新数据
                if len(batch_reviews) == 0:
                    print(f"  🏁 本次请求无新数据，已获取全部数据，停止获取")
                    break

                cursor = new_cursor

                # 请求间隔
                time.sleep(self.delay)

            except requests.RequestException as e:
                print(f"  请求失败: {e}")
                break
            except json.JSONDecodeError as e:
                print(f"  JSON解析失败: {e}")
                break

        return reviews

    def _process_reviews(self, raw_reviews: List[Dict], language: str) -> List[Dict]:
        """
        处理原始评论数据

        Args:
            raw_reviews: 原始评论数据
            language: 语言代码

        Returns:
            处理后的评论数据
        """
        processed = []

        for review in raw_reviews:
            try:
                # 基本评论信息
                processed_review = {
                    "recommendationid": review.get("recommendationid"),
                    "language": language,
                    "language_name": (
                        "简体中文" if language == "schinese" else "繁体中文"
                    ),
                    "review_text": review.get("review", "").strip(),
                    "timestamp_created": review.get("timestamp_created"),
                    "timestamp_updated": review.get("timestamp_updated"),
                    "voted_up": review.get("voted_up"),  # True=推荐, False=不推荐
                    "votes_up": review.get("votes_up", 0),
                    "votes_funny": review.get("votes_funny", 0),
                    "weighted_vote_score": review.get("weighted_vote_score", 0),
                    "comment_count": review.get("comment_count", 0),
                    "steam_purchase": review.get("steam_purchase"),
                    "received_for_free": review.get("received_for_free"),
                    "written_during_early_access": review.get(
                        "written_during_early_access"
                    ),
                }

                # 作者信息
                author = review.get("author", {})
                processed_review.update(
                    {
                        "author_steamid": author.get("steamid"),
                        "author_num_games_owned": author.get("num_games_owned"),
                        "author_num_reviews": author.get("num_reviews"),
                        "author_playtime_forever": author.get(
                            "playtime_forever"
                        ),  # 总游戏时长（分钟）
                        "author_playtime_at_review": author.get(
                            "playtime_at_review"
                        ),  # 写评论时的游戏时长（分钟）
                        "author_last_played": author.get("last_played"),
                    }
                )

                # 转换时间戳为可读格式
                if processed_review["timestamp_created"]:
                    processed_review["created_date"] = datetime.fromtimestamp(
                        processed_review["timestamp_created"]
                    ).strftime("%Y-%m-%d %H:%M:%S")

                # 计算游戏时长（小时）
                if processed_review["author_playtime_forever"]:
                    processed_review["author_playtime_hours"] = round(
                        processed_review["author_playtime_forever"] / 60, 1
                    )

                if processed_review["author_playtime_at_review"]:
                    processed_review["author_playtime_at_review_hours"] = round(
                        processed_review["author_playtime_at_review"] / 60, 1
                    )

                # 只保留有内容的评论
                if processed_review["review_text"]:
                    processed.append(processed_review)

            except Exception as e:
                print(f"  处理评论时出错: {e}")
                continue

        return processed

    def save_to_csv(self, reviews: List[Dict], filename: str):
        """
        保存评论数据到CSV文件

        Args:
            reviews: 评论数据
            filename: 文件名
        """
        if not reviews:
            print("没有数据可保存")
            return

        df = pd.DataFrame(reviews)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n数据已保存到: {filename}")

        # 打印数据概览
        print(f"\n=== 数据概览 ===")
        print(f"总评论数: {len(df)}")
        print(f"推荐评论: {df['voted_up'].sum()} ({df['voted_up'].mean()*100:.1f}%)")
        print(
            f"不推荐评论: {(~df['voted_up']).sum()} ({(~df['voted_up']).mean()*100:.1f}%)"
        )

        print(f"\n=== 语言分布 ===")
        lang_dist = df["language_name"].value_counts()
        for lang, count in lang_dist.items():
            print(f"{lang}: {count} 条")

        # 游戏时长统计
        if "author_playtime_hours" in df.columns:
            playtime_stats = df["author_playtime_hours"].describe()
            print(f"\n=== 游戏时长统计（小时） ===")
            print(f"平均时长: {playtime_stats['mean']:.1f}")
            print(f"中位数: {playtime_stats['50%']:.1f}")
            print(f"最长时长: {playtime_stats['max']:.1f}")

        # 评论长度统计
        df["review_length"] = df["review_text"].str.len()
        length_stats = df["review_length"].describe()
        print(f"\n=== 评论长度统计（字符数） ===")
        print(f"平均长度: {length_stats['mean']:.0f}")
        print(f"中位数: {length_stats['50%']:.0f}")
        print(f"最长评论: {length_stats['max']:.0f}")

    def get_game_info(self, app_id: int) -> Optional[Dict]:
        """
        获取游戏基本信息

        Args:
            app_id: Steam游戏ID

        Returns:
            游戏信息字典
        """
        url = f"https://store.steampowered.com/api/appdetails"
        params = {"appids": app_id, "l": "schinese"}  # 使用中文获取游戏信息

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            game_data = data.get(str(app_id), {})

            if game_data.get("success"):
                game_info = game_data["data"]
                return {
                    "app_id": app_id,
                    "name": game_info.get("name"),
                    "type": game_info.get("type"),
                    "short_description": game_info.get("short_description"),
                    "developers": game_info.get("developers", []),
                    "publishers": game_info.get("publishers", []),
                    "release_date": game_info.get("release_date", {}).get("date"),
                    "genres": [g["description"] for g in game_info.get("genres", [])],
                    "categories": [
                        c["description"] for c in game_info.get("categories", [])
                    ],
                    "price_overview": game_info.get("price_overview", {}),
                }
        except Exception as e:
            print(f"获取游戏信息失败: {e}")

        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Steam中文游戏评论数据获取工具")
    parser.add_argument("app_id", type=int, help="Steam游戏ID")
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=0,
        help="每种中文语言的最大评论数量（0=获取全部，>0=具体限制数量）",
    )
    parser.add_argument(
        "--review-type",
        default="all",
        choices=["all", "positive", "negative"],
        help="评论类型筛选",
    )
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔(秒)")
    parser.add_argument("--output", help="输出文件名")

    args = parser.parse_args()

    # 生成输出文件名
    if args.output:
        output_filename = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"steam_chinese_reviews_{args.app_id}_{timestamp}.csv"

    # 创建收集器，设置临时文件路径
    collector = SteamChineseReviewCollector(delay=args.delay)
    collector.temp_file_path = output_filename

    # 获取游戏信息
    print("=== 获取游戏信息 ===")
    game_info = collector.get_game_info(args.app_id)
    if game_info:
        print(f"游戏名称: {game_info['name']}")
        print(f"开发商: {', '.join(game_info['developers'])}")
        print(f"发行商: {', '.join(game_info['publishers'])}")
        print(f"类型: {', '.join(game_info['genres'])}")
        print(f"发布日期: {game_info['release_date']}")
        if game_info.get("price_overview"):
            price_info = game_info["price_overview"]
            if price_info.get("final_formatted"):
                print(f"价格: {price_info['final_formatted']}")
        print()

    # 获取中文评论数据
    print("=== 开始获取中文评论 ===")
    print("⚠️  按 Ctrl+C 可以随时安全中断并保存已获取的数据")
    print("-" * 60)

    reviews = collector.get_chinese_reviews(
        app_id=args.app_id, max_reviews=args.max_reviews, review_type=args.review_type
    )

    # 最终保存数据
    if reviews:
        collector.save_to_csv(reviews, output_filename)

        print(f"\n=== 完成 ===")
        print(f"数据文件: {output_filename}")
        print(f"可以使用 Excel 或其他工具打开分析")
    else:
        print("未获取到任何中文评论数据")


if __name__ == "__main__":
    main()
