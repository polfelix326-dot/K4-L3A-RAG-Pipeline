"""Import policy files from k4-day8-data.zip without network access."""
from src.import_archive import import_branch


def download_documents():
    """Legacy entry point: copies archive bytes without downloading."""
    import_branch('legal')


if __name__ == '__main__':
    download_documents()
