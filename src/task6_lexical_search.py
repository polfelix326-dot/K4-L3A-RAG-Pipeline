"""BM25 over the exact persisted Chroma chunks, without loading an embedding model."""
import re
import unicodedata
from copy import deepcopy

from rank_bm25 import BM25Okapi
import numpy as np
from .contracts import validate_document, validate_search_results
from .task4_chunking_indexing import indexed_chunks

CORPUS: list[dict] = []


def tokenize(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


def build_bm25_index(corpus: list[dict]):
    if not corpus:
        return None
    if len({c['id'] for c in corpus}) != len(corpus):
        raise ValueError('BM25 corpus IDs must be unique')
    for chunk in corpus:
        validate_document(chunk, require_chunk=True)
    tokenized = [tokenize(c['content']) for c in corpus]
    if not any(tokenized):
        return None
    index = BM25Okapi(tokenized)
    # Positive Robertson/Lucene IDF avoids zero scores for a term in half of
    # a tiny corpus (including the two-document contract fixture).
    df = {}
    for tokens in tokenized:
        for token in set(tokens):
            df[token] = df.get(token, 0) + 1
    index.idf = {token: float(np.log1p((len(corpus) - n + 0.5) / (n + 0.5)))
                 for token, n in df.items()}
    return index


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    tokens = tokenize(query)
    if top_k <= 0 or not tokens:
        return []
    corpus = CORPUS if CORPUS else indexed_chunks()
    bm25 = build_bm25_index(corpus)
    if bm25 is None:
        return []
    scores = bm25.get_scores(tokens)
    results = [{'id': item['id'], 'content': item['content'], 'metadata': deepcopy(item['metadata']),
                'score': float(score), 'retrieval_method': 'bm25'}
               for item, score in zip(corpus, scores) if score > 0]
    results.sort(key=lambda item: (-item['score'], item['id']))
    results = results[:top_k]
    validate_search_results(results, top_k=top_k, expected_method='bm25')
    return results


if __name__ == '__main__':
    for item in lexical_search('học bổng khuyến khích học tập', top_k=3):
        print(item['id'], round(item['score'], 4), item['metadata']['url'])
