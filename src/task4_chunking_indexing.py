"""Stable source-aware chunks and a persistent cosine index shared by retrieval."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import numpy as np
from src.contracts import validate_document

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
STANDARDIZED_DIR = ROOT / 'data/standardized'
CHROMA_DIR = ROOT / 'chroma_db'
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = 'recursive'
EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'sentence_transformers')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')
EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', '384'))
EMBEDDING_REVISION = os.getenv('EMBEDDING_REVISION', '614241f622f53c4eeff9890bdc4f31cfecc418b3')
COLLECTION_NAME = 'rag_documents'


@lru_cache(maxsize=1)
def _model():
    if EMBEDDING_PROVIDER != 'sentence_transformers':
        raise ValueError('This pipeline supports EMBEDDING_PROVIDER=sentence_transformers')
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL, revision=EMBEDDING_REVISION,
                               cache_folder=str(ROOT / '.cache/huggingface'), local_files_only=True)
    if model.get_sentence_embedding_dimension() != EMBEDDING_DIM:
        raise ValueError('EMBEDDING_DIM does not match model; configure it and rebuild the index')
    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError('Embedding inputs must be non-empty strings')
    vectors = _model().encode(texts, batch_size=16, normalize_embeddings=True,
                              show_progress_bar=False, convert_to_numpy=True)
    return _validate_vectors(vectors, len(texts)).tolist()


def prepare_texts(texts, kind):
    # E5 requires these English prefixes even for Vietnamese input.
    prefix = f'{kind}: ' if 'e5' in EMBEDDING_MODEL.lower() else ''
    return [prefix + text for text in texts]


def _validate_vectors(vectors, count):
    values = np.asarray(vectors, dtype=np.float32)
    if values.shape != (count, EMBEDDING_DIM) or not np.isfinite(values).all():
        raise ValueError('Embedding count, dimension or finite values invalid')
    if np.any(np.linalg.norm(values, axis=1) == 0):
        raise ValueError('Zero embedding cannot be used for cosine retrieval')
    return values


def index_config():
    return {'distance_metric': 'cosine', 'embedding_provider': EMBEDDING_PROVIDER,
            'embedding_model': EMBEDDING_MODEL, 'embedding_dim': EMBEDDING_DIM,
            'embedding_revision': EMBEDDING_REVISION,
            'chunk_size': CHUNK_SIZE, 'chunk_overlap': CHUNK_OVERLAP,
            'chunking_method': CHUNKING_METHOD, 'embedding_input_version': 'e5-prefix-v1'}


def get_collection():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, configuration={'hnsw': {'space': 'cosine'}},
        metadata={**index_config(), 'index_ready': False})
    if collection.configuration['hnsw']['space'] != 'cosine':
        raise ValueError('Index must use cosine distance')
    if any(collection.metadata.get(k) != v for k, v in index_config().items()):
        raise ValueError('Index configuration differs; use a new CHROMA_DIR/collection and rebuild')
    return collection


def load_documents() -> list[dict]:
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob('*.md')):
        relative = path.relative_to(STANDARDIZED_DIR)
        if relative.parts[0] not in {'legal', 'news'}:
            raise ValueError(f'Unknown document branch: {path}')
        text = path.read_text(encoding='utf-8')
        if not text.startswith('---\n'):
            raise ValueError(f'Missing source front matter: {path}')
        front, content = text.split('---\n', 2)[1:]
        meta = {k: json.loads(v) for k, v in
                (line.split(': ', 1) for line in front.strip().splitlines())}
        meta.update(source=relative.as_posix(), doc_type=relative.parts[0],
                    standardized_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        document = {'id': relative.as_posix(), 'content': content.strip(), 'metadata': meta}
        validate_document(document)
        documents.append(document)
    if not documents:
        raise ValueError('No standardized documents to index')
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=['\n\n', '\n', '. ', ' ', ''], add_start_index=True)
    chunks = []
    seen = set()
    for document in documents:
        validate_document(document)
        if document['id'] in seen:
            raise ValueError('Document IDs must be unique')
        seen.add(document['id'])
        parts = [part for part in splitter.create_documents([document['content']])
                 if any(char.isalnum() for char in part.page_content)]
        for index, part in enumerate(parts):
            start = part.metadata['start_index']
            chunk = {'id': f"{document['id']}::chunk-{index}", 'content': part.page_content,
                'metadata': {**document['metadata'], 'document_id': document['id'],
                             'chunk_index': index, 'start_char': start,
                             'end_char': start + len(part.page_content)}}
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
    vectors = _validate_vectors(embed_texts(prepare_texts([c['content'] for c in chunks], 'passage')), len(chunks))
    return [{**c, 'metadata': dict(c['metadata']), 'embedding': v.tolist()}
            for c, v in zip(chunks, vectors)]


def stored_metadata(meta):
    # Chroma scalar metadata cannot store null; JSON retains the exact contract.
    return {**{k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))},
            '_metadata_json': json.dumps(meta, ensure_ascii=False, sort_keys=True)}


def restore_metadata(meta):
    return json.loads(meta['_metadata_json']) if '_metadata_json' in meta else dict(meta)


def chunk_digest(chunks):
    return hashlib.sha256(json.dumps(
        [{k: c[k] for k in ('id', 'content', 'metadata')} for c in chunks],
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Replace the complete corpus via upsert, then remove obsolete chunk IDs."""
    if not chunks:
        raise ValueError('Refusing to replace the index with an empty corpus')
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
    ids = [c['id'] for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError('Chunk IDs must be unique')
    _validate_vectors([c['embedding'] for c in chunks], len(chunks))
    collection = get_collection()
    old_ids = set(collection.get(include=[])['ids'])
    collection.modify(metadata={**index_config(), 'index_ready': False})
    for offset in range(0, len(chunks), 128):
        batch = chunks[offset:offset + 128]
        collection.upsert(ids=[c['id'] for c in batch], documents=[c['content'] for c in batch],
            embeddings=[c['embedding'] for c in batch],
            metadatas=[stored_metadata(c['metadata']) for c in batch])
    obsolete = sorted(old_ids - set(ids))
    if obsolete:
        collection.delete(ids=obsolete)
    collection.modify(metadata={**index_config(), 'index_ready': True,
                                'chunk_count': len(chunks), 'chunk_sha256': chunk_digest(chunks)})


def require_ready(collection):
    if not collection.metadata.get('index_ready'):
        raise ValueError('Index is empty or incomplete; run Task 4 successfully first')


def indexed_chunks():
    collection = get_collection()
    require_ready(collection)
    response = collection.get(include=['documents', 'metadatas'])
    return sorted([{'id': key, 'content': text, 'metadata': restore_metadata(meta)}
        for key, text, meta in zip(response['ids'], response['documents'], response['metadatas'])],
        key=lambda c: c['id'])


def run_pipeline() -> None:
    chunks = chunk_documents(load_documents())
    index_to_vectorstore(embed_chunks(chunks))
    print(f'Indexed {len(chunks)} chunks; Chroma count={get_collection().count()}')
    print(f'Chunk corpus SHA-256: {chunk_digest(chunks)}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-model', action='store_true', help='Download the pinned model before indexing')
    args = parser.parse_args()
    if args.download_model:
        from huggingface_hub import snapshot_download
        snapshot_download(EMBEDDING_MODEL, revision=EMBEDDING_REVISION,
                          cache_dir=str(ROOT / '.cache/huggingface'),
                          allow_patterns=['*.json', '*.safetensors', '*.txt', 'sentencepiece.bpe.model'],
                          ignore_patterns=['onnx/*', 'openvino/*'])
    run_pipeline()
