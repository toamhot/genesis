"""Tests for the DocumentExtractor module."""

from src.document_extractor import DocumentExtractor


class TestClassifyUrl:
    """Test URL classification."""

    def test_pdf_classified_as_document(self):
        assert DocumentExtractor._classify_url("https://example.com/file.pdf") == "document"

    def test_docx_classified_as_document(self):
        assert DocumentExtractor._classify_url("https://example.com/file.docx") == "document"

    def test_png_classified_as_image(self):
        assert DocumentExtractor._classify_url("https://example.com/photo.png") == "image"

    def test_jpg_classified_as_image(self):
        assert DocumentExtractor._classify_url("https://example.com/photo.jpg") == "image"

    def test_unknown_url_with_document_keyword(self):
        assert DocumentExtractor._classify_url("https://media.licdn.com/dms/document/abc123") == "document"

    def test_unknown_url_with_image_keyword(self):
        assert DocumentExtractor._classify_url("https://media.licdn.com/dms/image/abc123") == "image"

    def test_completely_unknown_url(self):
        assert DocumentExtractor._classify_url("https://example.com/unknown") == "other"


class TestIsMediaUrl:
    """Test media URL detection."""

    def test_pdf_is_media(self):
        assert DocumentExtractor._is_media_url("https://example.com/file.pdf") is True

    def test_png_is_media(self):
        assert DocumentExtractor._is_media_url("https://example.com/photo.png") is True

    def test_html_is_not_media(self):
        assert DocumentExtractor._is_media_url("https://example.com/page.html") is False

    def test_no_extension_is_not_media(self):
        assert DocumentExtractor._is_media_url("https://example.com/page") is False
