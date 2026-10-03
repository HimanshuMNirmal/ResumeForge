import json

from helpers import JD_PATH, PROFILE_PATH, FakeLLM, load_profile
from resume_builder import pipeline
from resume_builder.ingest import IngestError, clean_text, load_jd_text, looks_like_url
from resume_builder.pipeline import ProfileError, load_profile as load_profile_file


def test_end_to_end_without_llm(tmp_path):
    res = pipeline.build(PROFILE_PATH, str(JD_PATH), use_llm=False, out_root=tmp_path)
    names = {p.name for p in res.folder.iterdir()}
    assert {"resume.docx", "resume.json", "jd.json", "report.md", "jd_raw.txt", "resume.txt"} <= names
    assert any(n.startswith("Asha_Verma_Northwind") and n.endswith(".docx") for n in names)
    report = (res.folder / "report.md").read_text()
    assert "Kubernetes" in report and "never_claim" in report
    assert "Kubernetes" not in (res.folder / "resume.txt").read_text()
    data = json.loads((res.folder / "resume.json").read_text())
    assert all("source_id" in b for e in data["experience"] for b in e["bullets"])
    assert res.folder.name.endswith("northwind-payments_senior-backend-engineer")


GOOD_WRITER = lambda user: {
    "summary": "Backend engineer with 5 years building backend services. Led migration of a monolith to services. Strong in Python and PostgreSQL.",
    "experience": [
        {"id": "exp_acme", "title": "Software Engineer (Backend)", "bullets": [
            {"source_id": "exp_acme_02", "text": "Led migration of a monolith to 6 microservices on Amazon Web Services (AWS), cutting deploy time from 45 minutes to 8 minutes"},
            {"source_id": "exp_acme_04", "text": "Designed PostgreSQL schemas and indexes that cut slow-query volume by 70%"},
        ]},
    ],
}


def test_llm_path_accepts_valid_rewrite(tmp_path):
    fake = FakeLLM(record_job=lambda u: {"company": "Northwind Payments", "title": "Senior Backend Engineer",
                                          "must_have": ["Python", "PostgreSQL", "AWS", "Kubernetes"], "nice_to_have": ["Kafka"]},
                   write_resume=GOOD_WRITER)
    res = pipeline.build(PROFILE_PATH, str(JD_PATH), client=fake, out_root=tmp_path)
    assert [t for t, _ in fake.calls] == ["record_job", "write_resume"]
    acme = next(e for e in res.resume.experience if e.id == "exp_acme")
    assert acme.title == "Software Engineer (Backend)"
    assert "Amazon Web Services (AWS)" in acme.bullets[0].text
    assert not any(n.startswith("validator:") for n in res.notes)


def test_llm_hallucination_is_rejected_and_falls_back(tmp_path):
    def bad(user):
        d = GOOD_WRITER(user)
        d["experience"][0]["bullets"][1]["text"] += " and streamed events through Kafka"
        return d

    fake = FakeLLM(record_job=lambda u: {"title": "Senior Backend Engineer", "must_have": ["Python"], "nice_to_have": ["Kafka"]},
                   write_resume=bad)
    res = pipeline.build(PROFILE_PATH, str(JD_PATH), client=fake, out_root=tmp_path)
    writer_calls = [c for c in fake.calls if c[0] == "write_resume"]
    assert len(writer_calls) == 3  # first try + 2 retries
    assert "REJECTED" in writer_calls[1][1] and "Kafka" in writer_calls[1][1]  # errors fed back
    assert any("fell back" in n for n in res.notes)
    assert "Kafka" not in (res.folder / "resume.txt").read_text()


def test_llm_crash_falls_back_gracefully(tmp_path):
    def boom(user):
        raise RuntimeError("api down")

    fake = FakeLLM(record_job=boom, write_resume=boom)
    res = pipeline.build(PROFILE_PATH, str(JD_PATH), client=fake, out_root=tmp_path)
    assert res.jd.title and any("fell back" in n for n in res.notes)


def test_profile_errors_are_helpful(tmp_path):
    bad = tmp_path / "p.json"
    bad.write_text("{not json")
    for content, needle in (("{not json", "not valid JSON"), ('{"basics": {"name": "x"}}', "schema validation")):
        bad.write_text(content)
        try:
            load_profile_file(bad)
        except ProfileError as e:
            assert needle in str(e)
        else:
            raise AssertionError("expected ProfileError")
    data = json.loads(PROFILE_PATH.read_text())
    data["experience"][0]["bullets"][0]["skills"].append("Cobol")
    bad.write_text(json.dumps(data))
    try:
        load_profile_file(bad)
    except ProfileError as e:
        assert "Cobol" in str(e)
    else:
        raise AssertionError("expected ProfileError")


def test_ingest_helpers(tmp_path):
    assert looks_like_url("https://example.com/job/1") and not looks_like_url("Senior Engineer at X")
    assert "Apply now" not in clean_text("Engineer\nApply now\n\n\n\nWe build things")
    f = tmp_path / "jd.txt"
    f.write_text("word " * 30)
    assert load_jd_text(str(f)).startswith("word")
    try:
        load_jd_text("too short")
    except IngestError:
        pass
    else:
        raise AssertionError("expected IngestError")


def test_fit_to_pages_trims_when_pdf_too_long(tmp_path):
    import shutil
    from resume_builder.render.pdf import find_soffice

    if not find_soffice():
        return
    data = json.loads(PROFILE_PATH.read_text())
    data["preferences"]["max_pages"] = 1
    for e in data["experience"]:
        e["bullets"] = e["bullets"] * 1
    p = tmp_path / "p.json"
    p.write_text(json.dumps(data))
    res = pipeline.build(p, str(JD_PATH), use_llm=False, out_root=tmp_path)
    assert res.ats.pages == 1
