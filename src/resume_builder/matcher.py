"""Step 3: deterministic scoring + selection. Explainable: every pick has a score, every gap a reason."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import JD, Bullet, Experience, Profile, Project, Skill, SkillGroup
from .textutil import SkillIndex, numbers_in, term_in_text

W_MUST, W_NICE, W_KEYWORD, W_THEME = 3.0, 1.5, 1.0, 1.0
W_QUANT = 0.5          # bonus for bullets that carry a number (recruiters and ATS checkers like metrics)
W_VERB_REPEAT = 0.75   # penalty per earlier bullet that opens with the same verb
_LEVEL_RANK = {"strong": 0, "working": 1, "familiar": 2}


@dataclass
class Selection:
    experience: list[tuple[Experience, list[Bullet]]]
    projects: list[tuple[Project, list[Bullet]]]
    skill_groups: list[SkillGroup]
    matched_must: list[str] = field(default_factory=list)
    matched_nice: list[str] = field(default_factory=list)
    gaps_must: list[str] = field(default_factory=list)
    gaps_nice: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)  # JD asks for it but it is in never_claim
    scores: dict[str, float] = field(default_factory=dict)
    unused_bullets: list[str] = field(default_factory=list)

    def selected_ids(self) -> set[str]:
        ids = {b.id for _, bs in self.experience for b in bs}
        ids |= {b.id for _, bs in self.projects for b in bs}
        return ids


def display_skill(skill: Skill) -> str:
    """'Amazon Web Services (AWS)': add the acronym once, but only when it really is the name's initials
    (so 'JavaScript' never becomes 'JavaScript (JS)')."""
    initials = "".join(w[0] for w in re.split(r"[\s\-]+", skill.name) if w).lower()
    for a in skill.aliases:
        if a.isalpha() and a.isupper() and 2 <= len(a) <= 6 and a.lower() == initials:
            return f"{skill.name} ({a})"
    return skill.name


def score_bullet(bullet: Bullet, jd: JD, idx: SkillIndex, exp_rank: int = 0) -> float:
    blob = " ".join([bullet.text, *bullet.skills])
    jd_context = " ".join([jd.title, jd.domain, *jd.keywords, *jd.responsibilities]).lower()
    score = 0.0
    for t in jd.must_have:
        if not idx.is_blocked(t) and idx.text_has(t, blob):
            score += W_MUST
    for t in jd.nice_to_have:
        if not idx.is_blocked(t) and idx.text_has(t, blob):
            score += W_NICE
    for t in jd.keywords:
        if term_in_text(t, blob):
            score += W_KEYWORD
    for th in bullet.themes:
        if th.lower() in jd_context:
            score += W_THEME
    if bullet.metrics or numbers_in(bullet.text):
        score += W_QUANT
    score += max(0.0, 1.0 - 0.5 * exp_rank)  # recency bonus
    return round(score, 3)


def _quota(rank: int, pages: int) -> int:
    base = [5, 4, 3]
    q = base[rank] if rank < len(base) else 3
    return q + (1 if pages > 1 and rank < 2 else 0)


def opening_verb(text: str) -> str:
    m = re.match(r"[A-Za-z]+", text.strip())
    return m.group(0).lower() if m else ""


def _pick(cands: list[Bullet], quota: int, scores: dict[str, float], used: dict[str, int]) -> list[Bullet]:
    """Greedy top-`quota` by score, penalising openings that repeat a verb already used elsewhere."""
    pool = list(cands)
    chosen: list[Bullet] = []
    while pool and len(chosen) < quota:
        best = max(pool, key=lambda b: (scores[b.id] - W_VERB_REPEAT * used.get(opening_verb(b.text), 0), -cands.index(b)))
        pool.remove(best)
        chosen.append(best)
        v = opening_verb(best.text)
        used[v] = used.get(v, 0) + 1
    return chosen


def unquantified_bullets(profile: Profile) -> list[Bullet]:
    return [b for b in profile.all_bullets().values() if not b.metrics and not numbers_in(b.text)]


def select(profile: Profile, jd: JD) -> Selection:
    idx = SkillIndex(profile)
    pages = max(1, profile.preferences.max_pages)
    scores: dict[str, float] = {}

    used_verbs: dict[str, int] = {}

    # ---- experience
    exp_sel: list[tuple[Experience, list[Bullet]]] = []
    for rank, exp in enumerate(profile.experience):
        for b in exp.bullets:
            scores[b.id] = score_bullet(b, jd, idx, rank)
        exp_sel.append((exp, _pick(exp.bullets, _quota(rank, pages), scores, used_verbs)))

    # ---- projects (rank projects by total relevance, then pick bullets with verb diversity)
    proj_scored: list[tuple[float, Project]] = []
    for proj in profile.projects:
        for b in proj.bullets:
            scores[b.id] = score_bullet(b, jd, idx, exp_rank=2)
        total = sum(scores[b.id] for b in proj.bullets) / max(1, len(proj.bullets)) * min(len(proj.bullets), 3) + sum(
            W_MUST for t in jd.must_have if idx.text_has(t, " ".join(proj.skills)) and not idx.is_blocked(t)
        )
        proj_scored.append((total, proj))
    proj_scored.sort(key=lambda t: -t[0])
    max_proj = 2 if pages == 1 else 3
    per_proj = 2 if pages == 1 else 3
    early = profile.preferences.career_stage == "early_career"
    proj_sel = [
        (p, _pick(p.bullets, per_proj, scores, used_verbs))
        for total, p in proj_scored[:max_proj]
        if p.bullets and (early or total > 0)  # skip projects with no relevance signal
    ]

    # ---- trim to page budget (bullets), oldest roles first, keep >= 2 per role
    cap = 15 * pages
    def total() -> int:
        return sum(len(b) for _, b in exp_sel) + sum(len(b) for _, b in proj_sel)
    while total() > cap:
        victim = next(((i, bs) for i, (e, bs) in reversed(list(enumerate(exp_sel))) if len(bs) > 2), None)
        if victim:
            victim[1].pop()
            continue
        pv = next((bs for _, bs in reversed(proj_sel) if len(bs) > 1), None)
        if pv:
            pv.pop()
            continue
        break

    # ---- skills
    def jd_terms() -> list[str]:
        return [*jd.must_have, *jd.nice_to_have, *jd.keywords]

    shown: list[tuple[bool, Skill]] = []
    for s in profile.skills:
        if idx.is_blocked(s.name):
            continue
        forms = idx.variants(s.name)
        matched = any(any(term_in_text(f, t) or term_in_text(t, f) for f in forms) for t in jd_terms() if t)
        if matched or s.level != "familiar":
            shown.append((matched, s))
    shown.sort(key=lambda ms: (not ms[0], _LEVEL_RANK.get(ms[1].level, 1), -(ms[1].years or 0)))
    shown = shown[: 20 * pages]

    order: dict[str, list[tuple[bool, Skill]]] = {}
    first_seen: dict[str, int] = {}
    for i, (m, s) in enumerate(shown):
        order.setdefault(s.category, []).append((m, s))
        first_seen.setdefault(s.category, i)
    cats = sorted(order, key=lambda c: (-sum(1 for m, _ in order[c] if m), first_seen[c]))
    groups = [SkillGroup(category=c, skills=[display_skill(s) for _, s in order[c]]) for c in cats]

    # ---- matches and gaps
    profile_text = profile.full_text()
    sel = Selection(experience=exp_sel, projects=proj_sel, skill_groups=groups, scores=scores)
    for t in jd.must_have:
        _classify(t, idx, profile_text, sel.matched_must, sel.gaps_must, sel.blocked)
    for t in jd.nice_to_have:
        _classify(t, idx, profile_text, sel.matched_nice, sel.gaps_nice, sel.blocked)
    sel.unused_bullets = sorted(set(profile.all_bullets()) - sel.selected_ids())
    return sel


def _classify(term, idx, profile_text, matched, gaps, blocked) -> None:
    if idx.is_blocked(term):
        blocked.append(term)
        gaps.append(term)
    elif idx.is_supported(term) or idx.text_has(term, profile_text):
        matched.append(term)
    else:
        gaps.append(term)
