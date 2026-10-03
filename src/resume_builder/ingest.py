"""Step 1: get clean job-description text from a file, pasted text, stdin, or a URL."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_URL = re.compile(r"^https?://\S+$", re.IGNORECASE)

# Lines that are page furniture rather than job content.
_BOILERPLATE = re.compile(
    r"^(apply( now| for this job)?|share( this job)?|save( job)?|sign in|log in|cookie|accept (all )?cookies|"
    r"privacy policy|terms of (use|service)|follow us|report this job|back to (jobs|search)|"
    r"equal opportunity employer.*|skip to (main )?content)\W*$",
    re.IGNORECASE,
)


class IngestError(RuntimeError):
    pass


def looks_like_url(value: str) -> bool:
    return bool(_URL.match(value.strip()))


def fetch_url(url: str, timeout: float = 20.0) -> str:
    """Fetch a posting and extract its main text. Many job sites block scraping: fall back to pasting."""
    try:
        import httpx
        import trafilatura
    except ImportError as e:  # pragma: no cover
        raise IngestError("URL fetching needs 'httpx' and 'trafilatura' installed") from e
    try:
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (personal resume tool)"},
        )
        resp.raise_for_status()
    except Exception as e:
        raise IngestError(
            f"Could not fetch {url} ({e}). Many job sites block scraping: paste the text into a .txt file instead."
        ) from e
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    if not text or len(text.split()) < 40:
        raise IngestError(
            "The page did not contain readable job text (it may need JavaScript or a login). "
            "Paste the posting into a .txt file and pass that instead."
        )
    return text


def clean_text(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    out: list[str] = []
    blank = 0
    for line in raw.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line and _BOILERPLATE.match(line):
            continue
        if not line:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(line)
    return "\n".join(out).strip()


def load_jd_text(source: str | None) -> str:
    """`source` may be a file path, a URL, '-' (stdin), or raw pasted text."""
    if source is None or source == "-":
        if sys.stdin.isatty():
            raise IngestError("No job description given. Pass --jd FILE|URL|TEXT or pipe text via stdin.")
        text = sys.stdin.read()
    elif looks_like_url(source):
        text = fetch_url(source.strip())
    else:
        p = Path(source)
        try:
            is_file = p.exists() and p.is_file()
        except OSError:
            is_file = False
        text = p.read_text(encoding="utf-8") if is_file else source
    text = clean_text(text)
    if len(text.split()) < 15:
        raise IngestError("The job description looks too short to be a real posting.")
    return text
