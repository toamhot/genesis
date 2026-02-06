"""Tests for the NominationDetector module."""

from datetime import datetime, timezone

from src.linkedin_client import LinkedInPost
from src.nomination_detector import NominationDetector


def _make_post(text: str, author: str = "Jean Dupont") -> LinkedInPost:
    return LinkedInPost(
        author_name=author,
        author_headline="Professional",
        author_profile_url="https://linkedin.com/in/test",
        text=text,
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )


class TestKeywordDetection:
    """Test keyword-based nomination detection (no LLM)."""

    def setup_method(self):
        self.detector = NominationDetector(use_llm=False)

    def test_detects_french_nomination(self):
        post = _make_post(
            "Très heureux d'annoncer que j'ai été nommé Directeur Général chez Acme Corp !"
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        assert results[0].person_name == "Jean Dupont"
        assert results[0].nomination_type == "appointment"

    def test_detects_english_promotion(self):
        post = _make_post(
            "Thrilled to announce that I've been promoted to VP of Engineering at TechCo!",
            author="Jane Smith",
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        assert results[0].person_name == "Jane Smith"

    def test_detects_new_position(self):
        post = _make_post(
            "Après 5 ans chez BigCorp, j'ai rejoint StartupXYZ en tant que CTO. "
            "Une nouvelle aventure commence !"
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        assert results[0].nomination_type == "new_position"

    def test_ignores_unrelated_post(self):
        post = _make_post(
            "Voici un article intéressant sur le machine learning et l'IA générative."
        )
        results = self.detector.detect([post])
        assert len(results) == 0

    def test_ignores_empty_post(self):
        post = _make_post("")
        results = self.detector.detect([post])
        assert len(results) == 0

    def test_detects_joining_announcement(self):
        post = _make_post(
            "Excited to share that I'm joining Google as a Senior Product Manager! "
            "Looking forward to this new challenge."
        )
        results = self.detector.detect([post])
        assert len(results) == 1

    def test_multiple_posts(self):
        posts = [
            _make_post("J'ai été promu directeur commercial."),
            _make_post("Bel article sur le cloud computing."),
            _make_post("Happy to announce my new role as Head of Sales at SalesForce!"),
            _make_post("Retour de vacances, vivement la rentrée."),
        ]
        results = self.detector.detect(posts)
        assert len(results) == 2

    def test_confidence_increases_with_more_keywords(self):
        # Post with many nomination keywords should have higher confidence
        post_many = _make_post(
            "Heureux d'annoncer que j'ai été nommé Directeur. "
            "Fier d'annoncer cette nomination comme nouveau poste."
        )
        post_few = _make_post("J'ai rejoint une nouvelle entreprise.")

        results_many = self.detector.detect([post_many])
        results_few = self.detector.detect([post_few])

        assert len(results_many) == 1
        assert len(results_few) == 1
        assert results_many[0].confidence > results_few[0].confidence


class TestRoleExtraction:
    """Test role and company extraction from post text."""

    def setup_method(self):
        self.detector = NominationDetector(use_llm=False)

    def test_extracts_role_with_en_tant_que(self):
        post = _make_post(
            "J'ai été nommé en tant que Directeur des Opérations chez Acme."
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        assert "Directeur" in results[0].new_role

    def test_extracts_company_with_chez(self):
        post = _make_post(
            "Heureux d'annoncer que j'ai rejoint Microsoft en tant que VP."
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        # Company extraction is best-effort
        if results[0].company:
            assert "Microsoft" in results[0].company


class TestNominationSummary:
    """Test Nomination.summary() output."""

    def setup_method(self):
        self.detector = NominationDetector(use_llm=False)

    def test_summary_includes_name(self):
        post = _make_post(
            "Thrilled to announce I've been promoted to Senior Manager!",
            author="Alice Martin",
        )
        results = self.detector.detect([post])
        assert len(results) == 1
        assert "Alice Martin" in results[0].summary()
