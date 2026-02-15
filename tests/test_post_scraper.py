"""Tests for the PostScraper module."""

from src.post_scraper import extract_post_id, normalize_linkedin_url


class TestExtractPostId:
    """Test extraction of post IDs from LinkedIn URLs."""

    def test_activity_url(self):
        url = "https://www.linkedin.com/feed/update/urn:li:activity:7654321098765432100"
        assert extract_post_id(url) == "7654321098765432100"

    def test_ugc_post_url(self):
        url = "https://www.linkedin.com/feed/update/urn:li:ugcPost:7654321098765432100"
        assert extract_post_id(url) == "7654321098765432100"

    def test_post_slug_url(self):
        url = "https://www.linkedin.com/posts/john-doe_excited-to-share-7654321098765432100-abcd"
        assert extract_post_id(url) == "7654321098765432100"

    def test_unrecognized_url_returns_none(self):
        url = "https://www.linkedin.com/in/john-doe"
        assert extract_post_id(url) is None

    def test_empty_string(self):
        assert extract_post_id("") is None


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_strips_whitespace(self):
        url = "  https://linkedin.com/posts/test  "
        assert normalize_linkedin_url(url) == "https://linkedin.com/posts/test"

    def test_removes_tracking_params(self):
        url = "https://linkedin.com/posts/test?utm_source=share&utm_medium=member_desktop"
        assert normalize_linkedin_url(url) == "https://linkedin.com/posts/test"

    def test_clean_url_unchanged(self):
        url = "https://linkedin.com/posts/test"
        assert normalize_linkedin_url(url) == url
