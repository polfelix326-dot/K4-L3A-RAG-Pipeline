"""Offline regression coverage for indexing and both independent searches."""
from copy import deepcopy
import numpy as np
import pytest
from src import task4_chunking_indexing as indexer
from src import task5_semantic_search as dense
from src import task6_lexical_search as lexical
from src.contracts import validate_search_results


def chunks():
    return [{'id': f'doc::chunk-{i}', 'content': text, 'metadata': {
        'source': 'legal/doc.md', 'title': 'Policy', 'doc_type': 'legal',
        'url': None, 'chunk_index': i, 'date_crawled': None,
        'source_file': 'data/landing/legal/doc.pdf'}}
        for i, text in enumerate(['học bổng khuyến khích', 'học phí miễn giảm', 'ngoại ngữ IELTS'])]


@pytest.fixture
def local_index(tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, 'CHROMA_DIR', tmp_path / 'chroma')
    monkeypatch.setattr(indexer, 'EMBEDDING_DIM', 3)
    corpus = [{**c, 'embedding': v.tolist()} for c, v in zip(chunks(), np.eye(3))]
    indexer.index_to_vectorstore(corpus)
    return corpus


def test_upsert_rerun_and_removed_chunks(local_index):
    before = indexer.indexed_chunks()
    indexer.index_to_vectorstore(local_index)
    assert indexer.get_collection().count() == 3
    assert indexer.indexed_chunks() == before
    indexer.index_to_vectorstore(local_index[:2])
    assert indexer.get_collection().count() == 2
    assert [c['id'] for c in indexer.indexed_chunks()] == ['doc::chunk-0', 'doc::chunk-1']
    assert indexer.indexed_chunks()[0]['metadata']['url'] is None
    with pytest.raises(ValueError, match='empty'):
        indexer.index_to_vectorstore([])
    assert indexer.get_collection().count() == 2


def test_dense_and_bm25_share_persisted_corpus(local_index, monkeypatch):
    monkeypatch.setattr(dense, 'embed_texts', lambda texts: [[1, 0, 0]])
    results = dense.semantic_search('học bổng', 100)
    validate_search_results(results, top_k=100, expected_method='dense')
    assert len(results) == 3
    assert results[0]['id'] == local_index[0]['id']
    assert results[0]['score'] == pytest.approx(1)
    assert results[0]['metadata'] == local_index[0]['metadata']
    sparse = lexical.lexical_search('HỌC BỔNG', 3)
    validate_search_results(sparse, top_k=3, expected_method='bm25')
    assert sparse[0]['id'] == results[0]['id']
    assert sparse[0]['metadata'] == results[0]['metadata']
    assert lexical.lexical_search('zzzzzzzz') == []


def test_failed_index_not_served(local_index, monkeypatch):
    collection = indexer.get_collection()
    collection.modify(metadata={**collection.metadata, 'index_ready': False})
    with pytest.raises(ValueError, match='incomplete'):
        dense.semantic_search('học bổng')
    with pytest.raises(ValueError, match='incomplete'):
        lexical.lexical_search('học bổng')


def test_configuration_mismatch_rejected(local_index, monkeypatch):
    monkeypatch.setattr(indexer, 'EMBEDDING_MODEL', 'another-model')
    with pytest.raises(ValueError, match='configuration differs'):
        indexer.get_collection()


def test_document_front_matter_is_metadata_not_embedding_content():
    documents = indexer.load_documents()
    assert len(documents) == 9
    by_id = {d['id']: d for d in documents}
    output = indexer.chunk_documents(documents)
    assert output == indexer.chunk_documents(documents)
    for chunk in output:
        meta = chunk['metadata']
        source = by_id[meta['document_id']]
        assert source['content'][meta['start_char']:meta['end_char']] == chunk['content']
        assert meta['source_file'].startswith('data/landing/')
        assert meta['url'].startswith('https://')
        assert 'archive_sha256:' not in chunk['content']
        assert len(chunk['content']) <= indexer.CHUNK_SIZE
        assert any(char.isalnum() for char in chunk['content'])


def test_embedding_validation_and_non_mutation(monkeypatch):
    original = chunks()
    before = deepcopy(original)
    monkeypatch.setattr(indexer, 'EMBEDDING_DIM', 3)
    received = []
    def embed(texts):
        received.extend(texts)
        return np.eye(3).tolist()
    monkeypatch.setattr(indexer, 'embed_texts', embed)
    output = indexer.embed_chunks(original)
    assert received == ['passage: ' + c['content'] for c in original]
    assert original == before
    assert len(output) == 3
    monkeypatch.setattr(indexer, 'embed_texts', lambda texts: [[float('nan')] * 3] * 3)
    with pytest.raises(ValueError, match='finite'):
        indexer.embed_chunks(original)


@pytest.mark.parametrize('query,top_k', [('', 3), ('x', 0), ('x', -1)])
def test_empty_search_never_loads_model_or_collection(query, top_k, monkeypatch):
    def unexpected():
        raise AssertionError('must not open index')
    monkeypatch.setattr(dense, 'get_collection', unexpected)
    monkeypatch.setattr(lexical, 'indexed_chunks', unexpected)
    assert dense.semantic_search(query, top_k) == []
    assert lexical.lexical_search(query, top_k) == []
