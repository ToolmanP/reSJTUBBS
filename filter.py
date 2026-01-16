import asyncio
import itertools
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime

import redis.asyncio as redis
import yaml
from openai import AsyncOpenAI
from tqdm import tqdm

with open("./config.yml", "r") as f:
    config = yaml.safe_load(f)

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_filename = f"logs/filter-{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_filename,
    filemode="a",
)


@dataclass
class Reid:
    reid: str
    title: str
    author: str
    section: str

    def __str__(self):
        return f"Reid(reid={self.reid}, title={self.title}, author={self.author}, section={self.section})"


class ReidFilter:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        llm_api_key: str | None = None,
        llm_base_url: str | None = None,
        llm_model: str = "qwen-plus",
    ):
        self.redis_url: str = redis_url
        self.llm_api_key: str | None = llm_api_key
        self.llm_base_url: str | None = llm_base_url
        self.llm_model: str = llm_model
        self.redis_client: redis.Redis | None = None

    async def connect_redis(self):
        """连接Redis数据库"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(self.redis_url)
        return self.redis_client

    async def close_redis(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None

    async def get_single_reid(self, reid: str) -> Reid | None:
        """获取单个Reid对象"""
        client = await self.connect_redis()
        reid_str = await client.get(f"reid:{reid}")
        if reid_str:
            data = json.loads(reid_str.decode())
            return Reid(
                reid=data.get("reid", ""),
                title=data.get("title", ""),
                author=data.get("author", ""),
                section=data.get("section", ""),
            )
        return None

    async def get_batch_reids(self, board: str) -> list[Reid]:
        """批量获取reid对象"""
        client = await self.connect_redis()
        reids = await client.smembers(f"workset:reid:{board}")

        reid_objects: list[Reid] = []
        count = 0
        for reid_bytes in reids:
            reid = reid_bytes.decode()
            reid_obj = await self.get_single_reid(reid)
            if reid_obj:
                reid_obj.section = board
                reid_objects.append(reid_obj)
                count += 1

        return reid_objects

    def group_reids_by_section(self, reids: list[Reid]) -> dict[str, list[Reid]]:
        """按section对reid进行分组"""
        groups: dict[str, list[Reid]] = {}
        for reid in reids:
            section = reid.section
            if section not in groups:
                groups[section] = []
            groups[section].append(reid)
        return groups

    def save_llm_results(
        self,
        board: str,
        reids: list[Reid],
        results: list[str],
        filtered_reids: list[Reid],
    ):
        """保存LLM请求和响应结果到文本文件以供人工检查"""
        # 创建日志目录
        log_dir = "llm_filter_logs"
        os.makedirs(log_dir, exist_ok=True)

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_dir}/filter_log_{board}_{timestamp}.txt"

        with open(log_file, "w", encoding="utf-8") as f:
            # 写入标题
            f.write("校园论坛内容筛选日志\n")
            f.write(f"版块: {board}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计: {len(reids)} 个帖子，保留: {len(filtered_reids)} 个\n")
            f.write("=" * 80 + "\n\n")

            # 写入原始请求内容
            f.write("原始请求内容:\n")
            prompt = self.create_batch_filter_prompt(reids)
            f.write(prompt)
            f.write("\n" + "=" * 80 + "\n\n")

            # 写入LLM响应结果
            f.write("LLM响应结果:\n")
            for i, result in enumerate(results, 1):
                f.write(f"{i}. {result}\n")
            f.write("\n" + "=" * 80 + "\n\n")

            # 写入详细分析
            f.write("详细分析结果:\n")
            for i, (reid, result) in enumerate(zip(reids, results)):
                status = "✓ 保留" if "KEEP" in result.upper() else "✗ 丢弃"
                f.write(f"{i + 1}. [{status}] {reid.title}\n")
                f.write(
                    f"   作者: {reid.author} | 版块: {reid.section} | ID: {reid.reid}\n"
                )
                f.write(f"   理由: {result}\n\n")

            # 写入统计信息
            f.write("统计汇总:\n")
            kept_count = len([r for r in results if "KEEP" in r.upper()])
            discarded_count = len([r for r in results if "DISCARD" in r.upper()])
            f.write(f"保留: {kept_count} 个\n")
            f.write(f"丢弃: {discarded_count} 个\n")
            f.write(f"默认保留: {len(results) - kept_count - discarded_count} 个\n")

        print(f"LLM筛选结果已保存到: {log_file}")
        return log_file

    def create_batch_filter_prompt(self, reids: list[Reid]) -> str:
        """创建批量筛选论坛内容的LLM提示"""
        content_list = []
        for i, reid in enumerate(reids, 1):
            content_list.append(
                f"{i}. 标题：{reid.title} | 作者：{reid.author} | 版块：{reid.section} | ID：{reid.reid}"
            )

        content_text = "\n".join(content_list)

        return f"""你是一个校园论坛内容筛选专家。我需要从古老的校园论坛中批量筛选出有价值的讨论内容。

请先分析以下论坛帖子标题，判断每个帖子是否包含有价值的学术、技术、生活经验或校园相关信息，是否值得保存和进一步处理，对于你认为模棱两可的信息请使用MAYBE来进行恢复。

帖子列表：
{content_text}

判断标准：
1. 学术价值：讨论学术问题、学习方法、课程经验、研究分享，但请不要包含对于出版书籍的转载。
2. 技术价值：技术讨论、编程问题、项目经验、工具分享，但请不要包含过时技术，已经可能过时经验的内容。
3. 生活价值：校园生活经验、实用信息、有参考价值的故事分享，可以包含哲学思考，对生活的见解，以及爱情故事等。
4. 历史价值：反映特定时期的校园文化、主流文化、亚文化变迁以及其他重大历史事件讨论。
5. 讨论质量：可能会导向具有一定深度的讨论，而不是简单的水贴，一般以【合集】为标题的帖子可以考虑保留。
6. 时效性：内容仍具有参考价值，不是过时信息，请直接丢弃过时的校内通知，天气预报，放假安排，比赛通知，比赛结果等新闻，
以及去除针对某个非历史影响的事件的人物的吐槽等，但可以包含人事变动，政策规划以及相关分析等信息。
7. 文艺价值：讨论文学、电影、音乐、艺术、游戏、动画，动漫，二次元等内容以及周边。

严格导向：讨论版相关：请尽可能根据讨论版本身的主题(section)来确定其价值，可以对上述的标准进行调整。

请严格按以下格式回复，每行一个结果，并附带理由：
1. KEEP/DISCARD/MAYBE 理由：xxx
2. KEEP/DISCARD/MAYBE 理由：xxx
3. KEEP/DISCARD/MAYBE 理由: xxx
...

示例回复格式：
1. KEEP
2. DISCARD
3. MAYBE
...

回复："""

    async def filter_with_llm(self, reids: list[Reid]) -> tuple[list[Reid], list[Reid]]:
        """使用LLM批量筛选有价值的reid"""
        if not reids:
            return [], []

        client = AsyncOpenAI(api_key=self.llm_api_key, base_url=self.llm_base_url)
        try:
            prompt = self.create_batch_filter_prompt(reids)
            response = await client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100 * len(reids),  # 为每个结果预留足够tokens
                temperature=0.1,
            )
            result_text = response.choices[0].message.content
            if result_text is None:
                logging.info(f"警告：LLM返回空内容，将保留所有内容 reids: {reids}")
                return reids, []

            results = result_text.strip().split("\n")
            valuable_reids = []
            sus_reids = []
            for i, reid in enumerate(reids):
                if i < len(results):
                    result_line = results[i].strip().upper()
                    if "KEEP" in result_line:
                        valuable_reids.append(reid)
                        logging.info(f"保留: {reid}")
                    elif "DISCARD" in result_line:
                        logging.info(f"丢弃: {reid}")
                    else:
                        sus_reids.append(reid)
                        logging.info(f"可能：{reid}")
                else:
                    valuable_reids.append(reid)
                    logging.info(f"保留(默认): {reid}")

            return valuable_reids, sus_reids

        except Exception as e:
            logging.error(f"批量筛选时出错: {e} {reids}")
            return reids, []

    async def save_filtered_workset(
        self, board: str, filtered_reids: list[Reid], workset_name: str = "filtered"
    ):
        """保存筛选后的结果到新的workset"""
        client = await self.connect_redis()
        new_workset_key = f"workset:reid:{board}:{workset_name}"
        await client.delete(new_workset_key)  # type: ignore
        for reid in filtered_reids:
            await client.sadd(new_workset_key, reid.reid)

        print(f"已保存 {len(filtered_reids)} 个筛选后的reid到 {new_workset_key}")


async def main():
    # 初始化筛选器
    filter = ReidFilter(
        llm_api_key=config["api_key"],  # 请替换为您的API密钥
        llm_base_url=config[
            "api_endpoint"
        ],  # 如果使用OpenAI官方API，保持None；如果使用兼容API，请设置URL
        llm_model=config["api_model"],
    )

    semaphore = asyncio.Semaphore(3)  # 限制并发数量

    async def process_one_board(filter: ReidFilter, board: str, limit=20):
        reids = await filter.get_batch_reids(board)  # 限制数量用于测试
        filtered_reids = []
        sus_reids = []
        total_batches = (len(reids) + limit - 1) // limit
        async with semaphore:
            for reid_list in tqdm(
                itertools.batched(reids, limit),
                total=total_batches,
                desc=board,
                unit="batch",
                disable=not sys.stdout.isatty(),
            ):
                filtered_reids_list, sus_reid_list = await filter.filter_with_llm(
                    list(reid_list)
                )
                filtered_reids.extend(filtered_reids_list)
                sus_reids.extend(sus_reid_list)
            await filter.save_filtered_workset(board, filtered_reids, "valuable")
            await filter.save_filtered_workset(board, sus_reids, "suspicious")
        return filtered_reids, sus_reids

    try:
        # 获取所有版块
        await filter.connect_redis()
        client = await filter.connect_redis()
        boards = await client.smembers("BoardStorage")
        boards = ["SJTUNews", "forum"]

        if not boards:
            print("没有找到任何版块")
            return

        logging.info(f"找到版块: {boards}")

        async def f(board: str):
            filter_reids, sus_reids = await process_one_board(filter, board, 200)
            logging.info(
                f"board: 筛选出的话题共{len(filter_reids)}个，可能的话题共{len(sus_reids)}个"
            )

        _ = await asyncio.gather(*[f(board) for board in boards])
    finally:
        await filter.close_redis()


async def count_reids():
    client = await redis.from_url("redis://localhost:6379")
    boards = await client.smembers("BoardStorage")
    for board in boards:
        print(
            board.decode(),
            await client.scard("workset:reid:" + board.decode()),
        )
    await client.aclose()
    pass


if __name__ == "__main__":
    asyncio.run(count_reids())
