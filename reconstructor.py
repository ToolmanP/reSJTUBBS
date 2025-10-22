import asyncio
import sys

import pymongo
import yaml
from sqlalchemy.orm import Session

from pypkg.models.mongo import MongoPost
from pypkg.models.postgres import Author, Board, Post, Topic
from pypkg.parser import MetadataPassError, ParsedTopic, RegroupPassError, make_parser


async def parse_all_topics(mongo_addr: str, board: str) -> list[ParsedTopic]:
    topics: list[ParsedTopic] = []
    async with pymongo.AsyncMongoClient(mongo_addr) as client:
        async for doc in (
            client.get_database("sjtubbs")
            .get_collection(board)
            .find({}, {"_id": False})
        ):
            if parser := make_parser(MongoPost(**doc)):
                try:
                    topics.append(parser.parse())
                except (MetadataPassError, RegroupPassError):
                    pass
                except Exception:
                    print(post.reid)
                    raise
    print(f"Found topics: {len(topics)}")
    topics.sort(key=lambda t: t.reid)
    return topics


def get_or_create_author(session: Session, username: str) -> Author:
    """获取或创建 Author（忽略 nickname）"""
    author = session.query(Author).filter_by(username=username).one_or_none()
    if author is None:
        author = Author(username=username)
        session.add(author)
        session.flush()  # 获取 id
    return author


def get_or_create_board(session: Session, board_name: str) -> Board:
    """获取或创建 Board"""
    board = session.query(Board).filter_by(name=board_name).one_or_none()
    if board is None:
        board = Board(name=board_name)
        session.add(board)
        session.flush()
    return board


def find_topic(session: Session, reid: int) -> bool:
    return session.query(Topic).filter_by(reid=reid).one_or_none() != None


def import_parsed_topics(session: Session, parsed_topics: list["ParsedTopic"]) -> None:
    """
    将 ParsedTopic 列表导入数据库。

    - 自动去重 Author（按 username）
    - 自动去重 Board（按 name）
    - 忽略 ParsedAuthor.nickname
    - 正确建立 Topic 和 Post 的关系
    """
    # 为性能考虑，可以先收集所有唯一 username 和 board name，但这里逐条处理更清晰
    for p_topic in parsed_topics:
        if find_topic(session, p_topic.reid):
            continue
        author = get_or_create_author(session, p_topic.author.username)
        board = get_or_create_board(session, p_topic.board)
        topic = Topic(
            reid=p_topic.reid,
            title=p_topic.title,
            author=author,
            board=board,
            content=p_topic.content,
            created_at=p_topic.created_at,
        )
        session.add(topic)
        session.flush()

        first_post = Post(
            content=p_topic.content,
            topic=topic,
            author=author,
            created_at=p_topic.created_at,
        )
        session.add(first_post)

        for p_post in p_topic.posts:
            post_author = get_or_create_author(session, p_post.author.username)
            post = Post(
                content=p_post.content,
                topic=topic,
                author=post_author,
                created_at=p_post.created_at,
            )
            session.add(post)

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            raise e


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Illegal input")
    with open("./config.yml", "r") as f:
        config = yaml.safe_load(f)
        topics = asyncio.run(parse_all_topics(config["mongo"], sys.argv[1]))
        # session = make_session(config["postgres"])
        # import_parsed_topics(session, topics)
