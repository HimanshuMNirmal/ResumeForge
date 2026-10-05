"""Step 6b: Resume -> Markdown. Formats Resume model into clean, professional Markdown."""
from __future__ import annotations

from ..models import Resume
from ..textutil import clean_display_url, normalize_url


def resume_to_markdown(resume: Resume, target_title: str | None = None, target_company: str | None = None) -> str:
    """Format the Resume model into clean, professional Markdown for preview, copy, & export."""
    lines: list[str] = []
    # Header
    name = getattr(resume.basics, "name", "") or "Resume Candidate"
    lines.append(f"# {name}\n")

    contacts: list[str] = []
    if getattr(resume.basics, "email", None):
        contacts.append(resume.basics.email)
    if getattr(resume.basics, "phone", None):
        contacts.append(resume.basics.phone)
    if getattr(resume.basics, "location", None):
        contacts.append(resume.basics.location)
    for link in getattr(resume.basics, "links", []):
        url = getattr(link, "url", "") if hasattr(link, "url") else link.get("url", "")
        if url:
            disp = clean_display_url(url)
            href = normalize_url(url)
            contacts.append(f"[{disp}]({href})")
    if contacts:
        lines.append(" | ".join(contacts))
        lines.append("")

    # Summary
    if getattr(resume, "summary", None):
        lines.append("## Professional Summary")
        lines.append(resume.summary.strip())
        lines.append("")

    # Skills
    if getattr(resume, "skills", None):
        lines.append("## Skills")
        for group in resume.skills:
            g_skills = getattr(group, "skills", [])
            g_cat = getattr(group, "category", "Skills")
            if g_skills:
                lines.append(f"- **{g_cat}**: {', '.join(g_skills)}")
        lines.append("")

    # Experience
    if getattr(resume, "experience", None):
        lines.append("## Work Experience")
        for exp in resume.experience:
            dates = f"{exp.start} – {exp.end or 'Present'}"
            loc = f" · {exp.location}" if exp.location else ""
            lines.append(f"### {exp.title} | {exp.company}{loc}")
            lines.append(f"*{dates}*\n")
            for b in exp.bullets:
                lines.append(f"- {b.text}")
            lines.append("")

    # Projects
    if getattr(resume, "projects", None):
        lines.append("## Key Projects")
        for proj in resume.projects:
            url_part = ""
            if proj.url:
                import re
                raw_urls = [u.strip() for u in re.split(r"[,|]", proj.url) if u.strip()]
                if raw_urls:
                    formatted_links = [
                        f"[{clean_display_url(u)}]({normalize_url(u)})" for u in raw_urls
                    ]
                    url_part = f" — {' | '.join(formatted_links)}"
            lines.append(f"### {proj.name}{url_part}")
            for b in proj.bullets:
                lines.append(f"- {b.text}")
            lines.append("")

    # Education
    if getattr(resume, "education", None):
        lines.append("## Education")
        for edu in resume.education:
            dates = f"{edu.start} – {edu.end or 'Present'}" if edu.start or edu.end else ""
            lines.append(f"### {edu.degree} · {edu.institution}")
            if dates:
                lines.append(f"*{dates}*\n")
            for d in getattr(edu, "details", []):
                lines.append(f"- {d}")
            lines.append("")

    # Certifications
    if getattr(resume, "certifications", None):
        lines.append("## Certifications")
        for cert in resume.certifications:
            issuer = f" ({cert.issuer})" if cert.issuer else ""
            date_str = f" · {cert.date}" if cert.date else ""
            lines.append(f"- **{cert.name}**{issuer}{date_str}")
        lines.append("")

    return "\n".join(lines).strip()
