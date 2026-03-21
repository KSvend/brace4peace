"""Fetch full text from URLs — web pages and PDFs."""
import logging

logger = logging.getLogger(__name__)


def fetch_url(url: str) -> dict:
    """Fetch and extract readable text from a URL.
    Returns: {"text": str, "status": "FETCHED"|"FAILED"|"PAYWALLED", "error": str|None}
    """
    try:
        from trafilatura import fetch_url as tf_fetch, extract
        downloaded = tf_fetch(url)
        if downloaded is None:
            return {"text": "", "status": "FAILED", "error": "Could not download"}
        text = extract(downloaded, include_links=True, include_tables=True)
        if not text or len(text) < 100:
            return {"text": text or "", "status": "PAYWALLED", "error": "Insufficient content"}
        return {"text": text, "status": "FETCHED", "error": None}
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return {"text": "", "status": "FAILED", "error": str(e)}


def fetch_pdf(url: str) -> dict:
    """Fetch and extract text from a PDF URL."""
    try:
        import urllib.request
        import tempfile
        import fitz
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            urllib.request.urlretrieve(url, f.name)
            doc = fitz.open(f.name)
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
        if not text.strip():
            return {"text": "", "status": "FAILED", "error": "Empty PDF"}
        return {"text": text, "status": "FETCHED", "error": None}
    except Exception as e:
        logger.warning(f"Failed to fetch PDF {url}: {e}")
        return {"text": "", "status": "FAILED", "error": str(e)}
