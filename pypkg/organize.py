import torch
from sentence_transformers import SentenceTransformer, util

from .parser import ParsedTopic


class ReplyOrganizer:
    trans: SentenceTransformer

    def __init__(self, model: str = "paraphrase-multilingual-mpnet-base-v2"):
        self.trans = SentenceTransformer(model)

    def organize(self, topic: ParsedTopic):
        candidates = [topic.content] + [post.text_in for post in topic.posts]
        query_dict = {}
        queries: list[str] = []
        for i, post in enumerate(topic.posts):
            if not post.quote_reply_to:
                continue
            query_dict[len(queries)] = i
            queries.append(post.quote_reply_to.raw)

        if len(queries) == 0:
            return

        query_embeddings = self.trans.encode(queries, convert_to_tensor=True)
        cand_embeddings = self.trans.encode(candidates, convert_to_tensor=True)
        top_k = 2
        cos_scores = util.cos_sim(query_embeddings, cand_embeddings)
        for i in range(len(queries)):
            top_results = torch.topk(cos_scores[i][: i + 1], k=min(i + 1, top_k))
            indices = top_results[1]
            topic.posts[query_dict[i]].reply_to_id = (indices[0] - 1).item()
