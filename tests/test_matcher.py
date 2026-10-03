from helpers import load_jd, load_profile
from resume_builder.matcher import display_skill, select, score_bullet
from resume_builder.textutil import SkillIndex


def test_jd_heuristics_find_requirements_and_nice_to_have():
    jd = load_jd()
    assert "Python" in jd.must_have and "PostgreSQL" in jd.must_have and "Kubernetes" in jd.must_have
    assert "Kafka" in jd.nice_to_have and "Terraform" in jd.nice_to_have
    assert jd.seniority == "senior"
    assert jd.company == "Northwind Payments"


def test_gaps_and_blocked():
    p, jd = load_profile(), load_jd()
    sel = select(p, jd)
    assert "Kubernetes" in sel.gaps_must and "Kubernetes" in sel.blocked
    assert {"Kafka", "Terraform"} <= set(sel.gaps_nice)
    assert {"Python", "PostgreSQL", "Amazon Web Services", "Docker"} <= set(sel.matched_must)
    assert "Redis" in sel.matched_nice


def test_selection_is_explainable_and_prefers_relevant_bullets():
    p, jd = load_profile(), load_jd()
    sel = select(p, jd)
    acme_ids = [b.id for b in dict((e.id, bs) for e, bs in sel.experience)["exp_acme"]]
    assert acme_ids[0] in {"exp_acme_02", "exp_acme_04", "exp_acme_01"}
    assert "exp_acme_05" in acme_ids or len(acme_ids) <= 5
    total = sum(len(bs) for _, bs in sel.experience) + sum(len(bs) for _, bs in sel.projects)
    assert total <= 15
    assert set(sel.unused_bullets).isdisjoint(sel.selected_ids())


def test_never_claim_skills_never_shown_and_matched_skills_first():
    p, jd = load_profile(), load_jd()
    sel = select(p, jd)
    shown = [s for g in sel.skill_groups for s in g.skills]
    assert not any("Kubernetes" in s for s in shown)
    assert any(s == "Amazon Web Services (AWS)" for s in shown)


def test_display_skill_adds_acronym_once():
    p = load_profile()
    aws = next(s for s in p.skills if s.name == "Amazon Web Services")
    assert display_skill(aws) == "Amazon Web Services (AWS)"
    py = next(s for s in p.skills if s.name == "Python")
    assert display_skill(py) == "Python"


def test_score_uses_must_have_weight():
    p, jd = load_profile(), load_jd()
    idx = SkillIndex(p)
    b = p.all_bullets()["exp_acme_04"]  # PostgreSQL + SQL
    assert score_bullet(b, jd, idx) >= 3


def test_display_skill_only_uses_true_initials():
    from resume_builder.models import Skill
    assert display_skill(Skill(name="JavaScript", aliases=["JS"])) == "JavaScript"
    assert display_skill(Skill(name="HTML", aliases=["HTML5"])) == "HTML"
    assert display_skill(Skill(name="Role-Based Access Control", aliases=["RBAC"])) == "Role-Based Access Control (RBAC)"
    assert display_skill(Skill(name="Retrieval-Augmented Generation", aliases=["RAG"])) == "Retrieval-Augmented Generation (RAG)"


def test_quantified_bullets_get_a_bonus_and_openings_are_varied():
    from resume_builder.matcher import opening_verb, unquantified_bullets
    from resume_builder.models import Bullet

    p, jd = load_profile(), load_jd()
    idx = SkillIndex(p)
    with_num = Bullet(id="a", text="Built a service for 40 users", skills=[], metrics=["40"], themes=[])
    without = Bullet(id="b", text="Built a service for users", skills=[], metrics=[], themes=[])
    assert score_bullet(with_num, jd, idx) > score_bullet(without, jd, idx)
    assert unquantified_bullets(p) == [b for b in p.all_bullets().values() if not b.metrics and not any(c.isdigit() for c in b.text)]

    sel = select(p, jd)
    verbs = [opening_verb(b.text) for _, bs in sel.experience for b in bs] + [opening_verb(b.text) for _, bs in sel.projects for b in bs]
    assert max(verbs.count(v) for v in set(verbs)) <= 2


def test_verb_diversity_prefers_a_different_verb_when_scores_are_close():
    from resume_builder.matcher import _pick
    from resume_builder.models import Bullet

    bs = [Bullet(id=f"x{i}", text=t, skills=[], metrics=[], themes=[]) for i, t in
          enumerate(["Built A", "Built B", "Built C", "Designed D"])]
    scores = {"x0": 3.0, "x1": 2.9, "x2": 2.8, "x3": 2.5}
    picked = [b.id for b in _pick(bs, 3, scores, {})]
    assert "x3" in picked and picked[0] == "x0"
