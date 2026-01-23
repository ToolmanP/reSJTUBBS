import os

import click
import pymongo
import requests
from sqlalchemy.orm import Session
from tqdm import tqdm

from pypkg.config import load_config
from pypkg.models.mongo import MongoPost
from pypkg.models.postgres import Author, Board, Post, Topic, make_session
from pypkg.organize import ReplyOrganizer
from pypkg.parser import MetadataPassError, ParsedTopic, RegroupPassError, make_parser

config = load_config()

BASE_FILE_DIRECTORY: str = os.getenv("ROOT") + "/files"

def docgen(collection, poi: str | list[str] | None = None):
    if not poi:
        for doc in collection.find({}, {"_id": False}):
            yield doc
    elif isinstance(poi, str):
        with open(poi, "r") as f:
            for line in f.readlines():
                yield collection.find_one({"reid": line.strip()}, {"_id": False})
    else:
        for reid in poi:
            yield collection.find_one({"reid": reid}, {"_id": False})


def get_count(collection, poi: str | list[str] | None = None):
    if not poi:
        return int(collection.count_documents({}))
    elif isinstance(poi, str):
        with open(poi, "r") as f:
            count = 0
            for _ in f.readlines():
                count += 1
            return count
    else:
        return len(poi)


def download_all_assets(topic: ParsedTopic):
    for url in topic.assets:
        print("Downloading", url)
        r = requests.get(url)
        p = BASE_FILE_DIRECTORY + "/" + url.split("/")[-1]
        with open(p, "wb") as f:
            f.write(r.content)


def parse_all_topics(
    board: str,
    poi: str | list[str] | None = None,
) -> list[ParsedTopic]:
    topics: list[ParsedTopic] = []
    reply_organizer = ReplyOrganizer()
    with pymongo.MongoClient(config.mongo) as client:
        db = client.get_database("sjtubbs")
        collection = db.get_collection(board)
        count = get_count(collection, poi)
        with tqdm(total=count, desc=board) as pbar:
            for doc in docgen(collection, poi):
                if parser := make_parser(MongoPost(**doc)):
                    try:
                        topic = parser.parse()
                        reply_organizer.organize(topic)
                        download_all_assets(topic)
                        topics.append(topic)
                    except (MetadataPassError, RegroupPassError):
                        pass
                    except Exception:
                        print(doc["reid"])
                        raise
                pbar.update()
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
        posts = []
        for p_post in p_topic.posts:
            post_author = get_or_create_author(session, p_post.author.username)
            post = Post(
                content=p_post.content if p_post.quote_embedded else p_post.text_in,
                topic=topic,
                author=post_author,
                created_at=p_post.created_at,
                reply_to_id=posts[p_post.reply_to_id].id
                if p_post.reply_to_id != -1
                else None,
            )
            posts.append(post)
            session.add(post)
            session.flush()

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            raise e


@click.command()
@click.option("--board", "-b", help="The board that needs to be reimported.")
@click.option(
    "--poi",
    help="The topic list that you are interested in. The reid must be correlated to the board you've assigned. Should be a file path or comma-seperated integer list",
    default=None,
)
@click.option(
    "--dryrun",
    "-d",
    help="Do not import the topics to the postgres database. Only process the parsing.",
    is_flag=True,
    default=False,
)
def reimporter(board: str, poi: str | list[str] | None, dryrun: bool):
    if poi:
        assert isinstance(poi, str) or isinstance(poi, list)
        if poi[0].isnumeric():
            poi = poi.split(",")
    global BASE_FILE_DIRECTORY
    BASE_FILE_DIRECTORY += "/" + board
    os.makedirs(BASE_FILE_DIRECTORY, exist_ok=True)
    topics = parse_all_topics(board, poi)
    session = make_session(config.postgres)
    if not dryrun:
        import_parsed_topics(session, topics)
    else:
        for post in topics[0].posts:
            print(post.reply_to_id, post.content)
            if post.reply_to_id != -1:
                print(topics[0].posts[post.reply_to_id])


if __name__ == "__main__":
    reimporter()
