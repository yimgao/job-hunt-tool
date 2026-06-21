"""TF-IDF 去重服务单元测试。"""
from __future__ import annotations

from app.services.dedup import compute_content_hash, filter_duplicates, is_similar

JD_A = "Python backend engineer with FastAPI PostgreSQL experience required. " * 8
JD_B = "Python backend engineer with FastAPI PostgreSQL experience required. " * 8  # identical
JD_C = "We are looking for a Go developer with Kubernetes and Docker skills. " * 8  # different


class TestComputeContentHash:
    def test_same_text_same_hash(self):
        assert compute_content_hash(JD_A) == compute_content_hash(JD_A)

    def test_different_text_different_hash(self):
        assert compute_content_hash(JD_A) != compute_content_hash(JD_C)

    def test_case_insensitive(self):
        assert compute_content_hash("Hello World") == compute_content_hash("hello world")

    def test_punctuation_stripped(self):
        assert compute_content_hash("hello, world!") == compute_content_hash("hello  world")


class TestIsSimilar:
    def test_identical_text_is_similar(self):
        assert is_similar(JD_A, [JD_B]) is True

    def test_unrelated_text_not_similar(self):
        assert is_similar(JD_C, [JD_A]) is False

    def test_empty_existing_not_similar(self):
        assert is_similar(JD_A, []) is False


class TestFilterDuplicates:
    def test_exact_duplicate_rejected(self):
        job_a = {"jd_text": JD_A, "title": "Job A"}
        job_b = {"jd_text": JD_B, "title": "Job B"}  # same text

        unique, dupes = filter_duplicates([job_a, job_b], set(), [])
        assert len(unique) == 1
        assert len(dupes) == 1

    def test_hash_collision_rejected(self):
        h = compute_content_hash(JD_A)
        job = {"jd_text": JD_A, "title": "Job"}

        unique, dupes = filter_duplicates([job], {h}, [])
        assert len(unique) == 0
        assert len(dupes) == 1

    def test_different_jobs_all_unique(self):
        job_a = {"jd_text": JD_A, "title": "Python Job"}
        job_c = {"jd_text": JD_C, "title": "Go Job"}

        unique, dupes = filter_duplicates([job_a, job_c], set(), [])
        assert len(unique) == 2
        assert len(dupes) == 0

    def test_unique_jobs_get_content_hash(self):
        job = {"jd_text": JD_A, "title": "Job"}
        unique, _ = filter_duplicates([job], set(), [])
        assert "content_hash" in unique[0]
        assert len(unique[0]["content_hash"]) == 64
