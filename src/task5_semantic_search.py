"""Cosine search using the same embedding function and index as Task 4."""
from .task4_chunking_indexing import (
    embed_texts, get_collection, restore_metadata, require_ready, prepare_texts,
)
from .contracts import validate_search_results


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    if top_k <= 0 or not query.strip():
        return []
    collection = get_collection()
    if hasattr(collection, 'metadata'):
        require_ready(collection)
    count = collection.count() if hasattr(collection, 'count') else top_k
    if not count:
        return []
    response = collection.query(query_embeddings=embed_texts(prepare_texts([query], 'query')),
        n_results=min(top_k, count), include=['documents', 'metadatas', 'distances'])
    unique = {}
    for key, content, meta, distance in zip(response['ids'][0], response['documents'][0],
                                           response['metadatas'][0], response['distances'][0]):
        result = {'id': key, 'content': content, 'metadata': restore_metadata(meta),
                  'score': float(1.0 - distance), 'retrieval_method': 'dense'}
        if key not in unique or result['score'] > unique[key]['score']:
            unique[key] = result
    results = sorted(unique.values(), key=lambda c: (-c['score'], c['id']))[:top_k]
    validate_search_results(results, top_k=top_k, expected_method='dense')
    return results


if __name__ == '__main__':
    for item in semantic_search('Điều kiện nhận học bổng khuyến khích học tập', top_k=3):
        print(item['id'], round(item['score'], 4), item['metadata']['url'])
