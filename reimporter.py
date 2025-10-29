import click
import pymongo
from sqlalchemy.orm import Session
from tqdm import tqdm

from pypkg.config import load_config
from pypkg.models.mongo import MongoPost
from pypkg.models.postgres import Author, Board, Post, Topic, make_session
from pypkg.parser import MetadataPassError, ParsedTopic, RegroupPassError, make_parser


def docgen(collection, reid_list: str | None = None):
    if not reid_list:
        for doc in collection.find({}, {"_id": False}):
            yield doc
    else:
        with open(reid_list, "r") as f:
            for line in f.readlines():
                yield collection.find_one({"reid": line.strip()}, {"_id": False})


def get_count(collection, reid_list: str | None = None):
    if not reid_list:
        return collection.count_documents({})
    else:
        with open(reid_list, "r") as f:
            count = 0
            for _ in f.readlines():
                count += 1
            return count


def parse_all_topics(
    mongo_addr: str,
    board: str,
    reid_list: str | None = None,
) -> list[ParsedTopic]:
    topics: list[ParsedTopic] = []
    with pymongo.MongoClient(mongo_addr) as client:
        db = client.get_database("sjtubbs")
        collection = db.get_collection(board)
        count = get_count(collection, reid_list)
        with tqdm(total=count) as pbar:
            for doc in docgen(collection, reid_list):
                if parser := make_parser(MongoPost(**doc)):
                    try:
                        topic = parser.parse()
                        topics.append(topic)
                    except (MetadataPassError, RegroupPassError):
                        pass
                    except Exception:
                        print(post.reid)
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


@click.command()
@click.option("--board", "-b", help="The board that needs to be reimported")
@click.option(
    "--reid_list", "-r", help="The reid list that is interested", default=None
)
@click.option(
    "--dryrun",
    "-d",
    help="Do not import the topics",
    is_flag=True,
    default=False,
)
def reimporter(board: str, reid_list: str | None, dryrun: bool):
    config = load_config()
    topics = parse_all_topics(config.mongo, board, reid_list)
    session = make_session(config.postgres)
    if not dryrun:
        import_parsed_topics(session, topics)
    else:
        # for topic in topics:
        #     print(topic.content)
        #     for post in topic.posts:
        #         print(post.content)
        pass


if __name__ == "__main__":
    reimporter()
