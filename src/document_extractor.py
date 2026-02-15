"""Extract and download documents attached to LinkedIn posts."""

import logging
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import DOCUMENTS_DIR

logger = logging.getLogger(__name__)

# Document file extensions we look for
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".csv", ".txt", ".rtf",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

ALL_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS


@dataclass
class Attachment:
    """Represents a downloaded attachment from a LinkedIn post."""

    filename: str
    file_path: str
    file_type: str  # "document", "image", "other"
    mime_type: str
    url: str
    size_bytes: int = 0


class DocumentExtractor:
    """Extract and download documents and images from LinkedIn posts."""

    def __init__(self, output_dir: Path = DOCUMENTS_DIR):
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_url(self, post_url: str) -> list[Attachment]:
        """Fetch a LinkedIn post page and extract all downloadable attachments."""
        logger.info("Extracting documents from: %s", post_url)
        attachments = []

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            resp = requests.get(post_url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Extract og:image (post preview image / document thumbnail)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img_url = og_image["content"]
                attachment = self._download(img_url, "image")
                if attachment:
                    attachments.append(attachment)

            # 2. Look for document links in the page
            media_urls = self._find_media_urls(soup, resp.text)
            for url in media_urls:
                attachment = self._download(url, self._classify_url(url))
                if attachment:
                    attachments.append(attachment)

        except Exception:
            logger.warning("Failed to extract documents from %s", post_url, exc_info=True)

        logger.info("Extracted %d attachment(s) from %s", len(attachments), post_url)
        return attachments

    def extract_from_api_post(self, post_data: dict) -> list[Attachment]:
        """Extract documents from a LinkedIn API post response."""
        attachments = []

        # LinkedIn API: documents are in content.contentEntities
        content = post_data.get("content", {})
        entities = content.get("contentEntities", [])

        for entity in entities:
            entity_url = entity.get("entityLocation", "")
            if not entity_url:
                continue

            file_type = self._classify_url(entity_url)
            attachment = self._download(entity_url, file_type)
            if attachment:
                attachments.append(attachment)

        # Also check for images in the post
        images = post_data.get("images", [])
        for img in images:
            img_url = img.get("url", "")
            if img_url:
                attachment = self._download(img_url, "image")
                if attachment:
                    attachments.append(attachment)

        return attachments

    def _find_media_urls(self, soup: BeautifulSoup, raw_html: str) -> list[str]:
        """Find media/document URLs in the page HTML."""
        urls = set()

        # Look for links to documents
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if self._is_media_url(href):
                urls.add(href)

        # Look for embedded document viewers (LinkedIn uses these for PDFs)
        for tag in soup.find_all("iframe", src=True):
            src = tag["src"]
            if "document" in src or "media" in src:
                urls.add(src)

        # Regex: find media URLs in the raw HTML / JSON-LD data
        media_patterns = [
            r'"(https://media\.licdn\.com/[^"]+\.pdf[^"]*)"',
            r'"(https://media\.licdn\.com/dms/document/[^"]+)"',
            r'"(https://media\.licdn\.com/dms/image/[^"]+)"',
        ]
        for pattern in media_patterns:
            for match in re.finditer(pattern, raw_html):
                url = match.group(1).replace("\\u0026", "&")
                urls.add(url)

        return list(urls)

    def _download(self, url: str, file_type: str) -> Attachment | None:
        """Download a file from a URL and save it locally."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            resp = requests.get(url, headers=headers, timeout=30, stream=True)
            resp.raise_for_status()

            # Determine filename
            filename = self._filename_from_response(resp, url)
            file_path = self._output_dir / filename

            # Avoid overwriting: add suffix if file exists
            counter = 1
            stem = file_path.stem
            suffix = file_path.suffix
            while file_path.exists():
                file_path = self._output_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            # Write file
            size = 0
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    size += len(chunk)

            mime_type = resp.headers.get("Content-Type", "application/octet-stream")

            logger.info("Downloaded: %s (%d bytes)", file_path.name, size)
            return Attachment(
                filename=file_path.name,
                file_path=str(file_path),
                file_type=file_type,
                mime_type=mime_type.split(";")[0],
                url=url,
                size_bytes=size,
            )

        except Exception:
            logger.debug("Failed to download %s", url, exc_info=True)
            return None

    def _filename_from_response(self, resp: requests.Response, url: str) -> str:
        """Derive a filename from the response headers or URL."""
        # Check Content-Disposition header
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            parts = cd.split("filename=")
            if len(parts) > 1:
                return parts[1].strip('" ')

        # Derive from URL path
        parsed = urlparse(url)
        path = unquote(parsed.path)
        name = Path(path).name
        if name and "." in name:
            return name

        # Fallback: use content type to determine extension
        content_type = resp.headers.get("Content-Type", "")
        ext = mimetypes.guess_extension(content_type.split(";")[0]) or ".bin"
        return f"attachment{ext}"

    @staticmethod
    def _classify_url(url: str) -> str:
        """Classify a URL as document, image, or other."""
        parsed = urlparse(url)
        path_lower = parsed.path.lower()

        for ext in DOCUMENT_EXTENSIONS:
            if path_lower.endswith(ext):
                return "document"
        for ext in IMAGE_EXTENSIONS:
            if path_lower.endswith(ext):
                return "image"

        if "document" in path_lower:
            return "document"
        if "image" in path_lower:
            return "image"

        return "other"

    @staticmethod
    def _is_media_url(url: str) -> bool:
        """Check if a URL points to a downloadable media file."""
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        return any(path_lower.endswith(ext) for ext in ALL_EXTENSIONS)
