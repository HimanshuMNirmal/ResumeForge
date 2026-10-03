from helpers import load_jd, load_profile
from resume_builder.matcher import select
from resume_builder.models import ResumeBullet, SkillGroup
from resume_builder.validator import validate
from resume_builder.writer import base_resume


def _setup():
    p, jd = load_profile(), load_jd()
    sel = select(p, jd)
    return p, jd, sel, base_resume(p, jd, sel)


def _has(errors, needle):
    return any(needle in e for e in errors)


def test_baseline_passes():
    p, jd, sel, r = _setup()
    assert validate(r, p, jd, sel) == []


def test_rejects_injected_fake_skill():
    p, jd, sel, r = _setup()
    r.experience[0].bullets[0].text += " using Kafka streams"
    assert _has(validate(r, p, jd, sel), "Kafka")


def test_rejects_skill_in_never_claim_even_if_jd_wants_it():
    p, jd, sel, r = _setup()
    r.experience[0].bullets[0].text += " on Kubernetes"
    errs = validate(r, p, jd, sel)
    assert _has(errs, "never_claim") and _has(errs, "Kubernetes")


def test_rejects_altered_metric():
    p, jd, sel, r = _setup()
    b = next(b for b in r.experience[0].bullets if b.source_id == "exp_acme_01")
    b.text = b.text.replace("250 ms", "150 ms")
    errs = validate(r, p, jd, sel)
    assert _has(errs, "numbers not in source") or _has(errs, "dropped metric")


def test_rejects_new_number():
    p, jd, sel, r = _setup()
    r.experience[0].bullets[0].text += " for 5 million users"
    assert _has(validate(r, p, jd, sel), "numbers not in source")


def test_rejects_changed_dates_company_title():
    p, jd, sel, r = _setup()
    r.experience[0].start = "2018-01"
    r.experience[0].company = "Google"
    r.experience[0].title = "Principal Engineer"
    errs = validate(r, p, jd, sel)
    assert _has(errs, "start changed") and _has(errs, "company changed") and _has(errs, "title")


def test_allows_real_title_alias():
    p, jd, sel, r = _setup()
    r.experience[0].title = "Software Engineer (Backend)"
    assert validate(r, p, jd, sel) == []
    r.experience[0].title = "Backend Engineer"
    assert validate(r, p, jd, sel) == []


def test_rejects_unknown_source_and_cross_entry_source():
    p, jd, sel, r = _setup()
    r.experience[0].bullets.append(ResumeBullet(source_id="nope", text="Did a thing"))
    assert _has(validate(r, p, jd, sel), "not in profile")
    p, jd, sel, r = _setup()
    r.experience[0].bullets[0] = ResumeBullet(source_id="exp_zenith_01", text=p.all_bullets()["exp_zenith_01"].text)
    assert _has(validate(r, p, jd, sel), "different entry")


def test_rejects_seniority_upgrade():
    p, jd, sel, r = _setup()
    p.all_bullets()["exp_zenith_01"].text = "Assisted with 15 REST API endpoints in FastAPI serving 20,000 daily requests"
    sel = select(p, jd)
    r = base_resume(p, jd, sel)
    zen = next(e for e in r.experience if e.id == "exp_zenith")
    zen.bullets[0].text = "Led 15 REST API endpoints in FastAPI serving 20,000 daily requests"
    assert _has(validate(r, p, jd, sel), "upgrades seniority")


def test_rejects_summary_claims():
    p, jd, sel, r = _setup()
    r.summary = "Engineer with 12 years of Kubernetes and Kafka experience."
    errs = validate(r, p, jd, sel)
    assert _has(errs, "never_claim") and _has(errs, "numbers") and _has(errs, "Kafka")


def test_rejects_skill_not_in_profile():
    p, jd, sel, r = _setup()
    r.skills.append(SkillGroup(category="Extra", skills=["Terraform"]))
    assert _has(validate(r, p, jd, sel), "Terraform")


def test_rejects_overlong_resume():
    p, jd, sel, r = _setup()
    for e in r.experience:
        e.bullets = e.bullets * 8
    assert _has(validate(r, p, jd, sel), "estimated length")
