import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import override

import markdownify
import requests
from bs4 import BeautifulSoup, Tag

from .models.mongo import MongoPost

LEGACY_SEPARATOR = "☆──────────────────────────────────────☆"

SYSTEM_HINT = "自动发信系统"
ANNOUNCE_HINT = "校内机关通知"
BASE_URL = "http://bbs.sjtu.edu.cn"


class Node:
    def to_markdown(self) -> str: ...


class RegularNode(Node):
    text: str

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    @override
    def to_markdown(self) -> str:
        return self.text


class IndentionNode(Node):
    children: list[Node]
    author: str | None

    def __init__(self, author: str):
        super().__init__()
        self.author = author
        self.children = list()

    def add_child(self, node: Node) -> None:
        self.children.append(node)

    @override
    def to_markdown(self) -> str:
        return f"""
[quote="{self.author}"]
{"\n".join([node.to_markdown() for node in self.children])}
[/quote]
"""


class IndentionAutomata:
    referer_re: re.Pattern[str]
    stack: list[IndentionNode]
    authors: list[str]

    def __init__(self) -> None:
        self.referer_re = re.compile("【 在 (.*) 的大作中提到: 】")
        self.stack = list()
        self.authors = list()

    def run(self, text: str) -> str:
        def parse_line(line: str) -> tuple[int, str]:
            if len(line) < 2:
                return 0, line
            pos = 0
            depth = 0
            while pos < len(line) and line[pos : pos + 2] == ": ":
                depth += 1
                pos += 2
            return depth, line[pos:]

        result = ""

        for line in text.splitlines():
            depth, line = parse_line(line)
            author_match = self.referer_re.search(line)
            if author_match:
                depth += 1
                self.authors = self.authors[:depth]
                self.authors.append(author_match[1])

            if depth < len(self.stack):
                while depth < len(self.stack):
                    node = self.stack.pop()
                    if len(self.stack) != 0:
                        self.stack[-1].add_child(node)
                    else:
                        result += node.to_markdown() + "\n"
            else:
                depth = min(len(self.authors), depth)
                while depth > len(self.stack):
                    self.stack.append(IndentionNode(self.authors[len(self.stack)]))

            if author_match:
                continue

            if depth == 0:
                result += line + "\n"
            else:
                self.stack[-1].add_child(RegularNode(text=line))

        while len(self.stack) != 0:
            node = self.stack.pop()
            if len(self.stack) != 0:
                self.stack[-1].add_child(node)
            else:
                result += node.to_markdown() + "\n"

        return result


@dataclass
class ParsedAuthor:
    username: str
    nickname: str


@dataclass
class ParsedPost:
    author: ParsedAuthor
    created_at: datetime
    content: str


@dataclass
class ParsedTopic:
    reid: int
    author: ParsedAuthor
    board: str
    created_at: datetime
    title: str
    content: str
    posts: list[ParsedPost]
    assets: list[str]


class MetadataPassError(Exception):
    pass


class RegroupPassError(Exception):
    pass


class Parser(ABC):
    _mongo_post: MongoPost

    def __init__(self, mongo_post: MongoPost):
        self._mongo_post = mongo_post

    @abstractmethod
    def parse(self) -> ParsedTopic: ...

    @staticmethod
    def strip_all_fonts(text: str) -> str:
        text = re.sub(r"<font (class|color)=.*>", "", text)
        text = re.sub(r"</font>", "", text)
        return text

    @staticmethod
    def to_raw_html(tag: Tag) -> str:
        text = "\n".join([str(c) for c in tag.children])
        return text

    @staticmethod
    def strip_assets(tag: Tag) -> list[str]:
        assets: list[str] = []
        for img in tag.find_all("img"):
            src = str(img["src"])
            url = ""

            if src.startswith("http://"):
                continue
            else:
                url = f"{BASE_URL}{str(img['src'])}"
            try:
                resp = requests.get(url, timeout=1)
                if resp.status_code != 200:
                    raise Exception("Not reached")
                assets.append(url)

            except Exception:
                img.decompose()
        return assets

    @staticmethod
    def convert_datetime(s: str) -> datetime:
        try:
            return datetime.strptime(s.split(" ")[0].strip(), "%Y年%m月%d日%H:%M:%S")
        except ValueError:
            pass
        try:
            return datetime.strptime(s, "%a %b %d %H:%M:%S %Y")
        except Exception:
            print(s)
            raise


class BBSParser(Parser):
    author_re: re.Pattern[str]
    created_at_re: re.Pattern[str]

    def __init__(self, mongo_post: MongoPost):
        super().__init__(mongo_post)
        self.author_re = re.compile(r"发信人: (.*)\s*\((.*)\)?, ")
        self.created_at_re = re.compile(r"发信站: .* \((.*)\)")

    def regroup(self) -> tuple[Tag, list[Tag]]:
        pres: list[Tag] = []
        for page in self._mongo_post.pages:
            soup = BeautifulSoup(page, features="html.parser")
            for pre in soup.find_all("pre"):
                pres.append(pre)
        return pres[0], pres[1:]

    def author_pass(self, pre: Tag) -> ParsedAuthor:
        assert isinstance(pre.text, str)
        try:
            author_match = self.author_re.search(pre.text)
            assert author_match
            username = author_match[1].strip()
            assert username
            nickname = author_match[2].strip()
            return ParsedAuthor(username, nickname)
        except Exception:
            raise MetadataPassError()

    def date_pass(self, pre: Tag) -> datetime:
        assert isinstance(pre.text, str)
        m = self.created_at_re.search(pre.text)
        try:
            return self.convert_datetime(str(m[1]))
        except TypeError:
            raise MetadataPassError()

    def text_pass(self, pre: Tag) -> str:
        t = self.to_raw_html(pre)
        t = "\n".join(t.split("\n\n")[1:])
        t = t.split("--")[0]
        t = markdownify.markdownify(t, strip=["font", "img"])
        return t

    def asset_pass(self, pre: Tag) -> list[str]:
        return []

    def reference_pass(self, text: str) -> str:
        try:
            return IndentionAutomata().run(text)
        except Exception:
            print(text)
            raise

    @override
    def parse(self) -> ParsedTopic:
        try:
            topic_pre, post_pres = self.regroup()
        except Exception:
            raise RegroupPassError()
        topic_author = self.author_pass(topic_pre)
        topic_date = self.date_pass(topic_pre)

        topic_text = self.reference_pass(self.text_pass(topic_pre))
        assets = self.strip_assets(topic_pre)
        posts: list[ParsedPost] = []

        for post_pre in post_pres:
            author = self.author_pass(post_pre)
            date = self.date_pass(post_pre)
            text = self.reference_pass(self.text_pass(post_pre))
            assets.extend(self.strip_assets(post_pre))
            posts.append(ParsedPost(author=author, created_at=date, content=text))
        return ParsedTopic(
            int(self._mongo_post.reid.strip()),
            topic_author,
            self._mongo_post.section.strip(),
            topic_date,
            self._mongo_post.title.strip(),
            f"reid={self._mongo_post.reid}\n\n" + topic_text,
            posts,
            assets,
        )


class BBSLegacyParser(Parser):
    metadata_re: re.Pattern[str]

    def __init__(self, mongo_post: MongoPost):
        super().__init__(mongo_post)
        self.metadata_re = re.compile(
            r"""([a-zA-Z0-9]+) \((.+)\)?\s+于\s*(.+)\)?\s*
\s*提到：""",
            re.MULTILINE,
        )

    def metadata_pass(self, raw: str) -> tuple[ParsedAuthor, datetime]:
        try:
            metadata_match = self.metadata_re.search(raw)
            username = metadata_match[1].strip()
            nickname = metadata_match[2].strip()
            dt = self.convert_datetime(str(metadata_match[3].removesuffix(")")))
            return ParsedAuthor(username, nickname), dt
        except Exception:
            raise MetadataPassError()

    def text_pass(self, raw: str):
        try:
            text = "\n".join(raw.split("\n\n")[1:])
            text = "".join(text.split("提到：")[1:]).strip()
        except Exception:
            raise
        return text

    def reference_pass(self, text: str) -> str:
        return IndentionAutomata().run(text)

    def regroup(self) -> tuple[str, list[str], list[str]]:
        group: list[str] = []
        assets: list[str] = []
        for page in self._mongo_post.pages:
            soup = BeautifulSoup(page, features="html.parser")
            whole_page = soup.find("pre")
            assert whole_page
            assets.extend(self.strip_assets(whole_page))
            whole_page = self.to_raw_html(whole_page)
            whole_page = markdownify.markdownify(whole_page)
            whole_page = re.sub(
                r"(\s:)+☆──────────────────────────────────────☆", "", whole_page
            )
            group.extend(
                list(map(self.strip_all_fonts, whole_page.split(LEGACY_SEPARATOR)[1:]))
            )
        return group[0], group[1:], assets

    @override
    def parse(self) -> ParsedTopic:
        try:
            topic_raw, post_raws, assets = self.regroup()
        except Exception:
            raise RegroupPassError()
        topic_author, topic_date = self.metadata_pass(topic_raw)
        posts: list[ParsedPost] = []

        for post_raw in post_raws:
            author, date = self.metadata_pass(post_raw)
            post_content = self.reference_pass(self.text_pass(post_raw))
            posts.append(ParsedPost(author, date, post_content))

        return ParsedTopic(
            int(self._mongo_post.reid.strip()),
            topic_author,
            self._mongo_post.section.strip(),
            topic_date,
            self._mongo_post.title.strip(),
            f"reid={self._mongo_post.reid}\n\n"
            + self.reference_pass(self.text_pass(topic_raw)),
            posts,
            assets,
        )


def make_parser(post: MongoPost) -> Parser | None:
    if post.pages[0].find(SYSTEM_HINT) != -1:
        return None

    if post.pages[0].find(ANNOUNCE_HINT) != -1:
        return None

    if post.pages[0].find(LEGACY_SEPARATOR) != -1:
        return BBSLegacyParser(post)
    else:
        return BBSParser(post)
