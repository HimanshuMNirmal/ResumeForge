from helpers import load_profile
from resume_builder.textutil import (
    SkillIndex, date_range, fmt_date, numbers_in, slugify, term_in_text,
)


def test_dates():
    assert fmt_date("2021-06") == "Jun 2021"
    assert fmt_date(None) == "Present"
    assert fmt_date("2019") == "2019"
    assert date_range("2021-06", None) == "Jun 2021 – Present"
    assert date_range("2019-07", "2021-05") == "Jul 2019 – May 2021"


def test_term_matching_handles_symbols_and_ambiguous_words():
    assert term_in_text("C++", "wrote C++ services")
    assert term_in_text("CI/CD", "built CI/CD pipelines")
    assert term_in_text("Go", "services in Go and Python")
    assert not term_in_text("Go", "we go to market fast")
    assert not term_in_text("Java", "JavaScript developer")
    assert not term_in_text("Git", "GitHub Actions")


def test_numbers():
    assert numbers_in("cut 900 ms to 250 ms, 1,200 tests, 70%") == {"900", "250", "1200", "70"}


def test_alias_normalisation():
    idx = SkillIndex(load_profile())
    assert idx.canon("AWS") == "Amazon Web Services"
    assert idx.canon("postgres") == "PostgreSQL"
    assert idx.is_supported("REST API")
    assert idx.is_blocked("Kubernetes") and not idx.is_supported("Kubernetes")
    assert idx.text_has("AWS", "deployed on Amazon Web Services")


def test_slug():
    assert slugify("Senior Backend Engineer!") == "senior-backend-engineer"
    assert slugify("", "x") == "x"
