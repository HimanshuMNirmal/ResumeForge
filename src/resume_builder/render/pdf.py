"""Step 6b: DOCX -> PDF with LibreOffice headless, so the PDF matches the DOCX and has selectable text."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class PdfError(RuntimeError):
    pass


def find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def docx_to_pdf(docx_path: str | Path, out_pdf: str | Path | None = None, timeout: int = 120) -> Path:
    docx_path = Path(docx_path)
    soffice = find_soffice()
    if not soffice:
        raise PdfError("LibreOffice ('soffice') not found: install it to produce PDFs (DOCX is still written).")
    out_pdf = Path(out_pdf) if out_pdf else docx_path.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            soffice, f"-env:UserInstallation=file://{tmp}/profile", "--headless",
            "--convert-to", "pdf", "--outdir", tmp, str(docx_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise PdfError("LibreOffice timed out while converting to PDF") from e
        except subprocess.CalledProcessError as e:
            raise PdfError(f"LibreOffice failed: {e.stderr.decode(errors='replace')[:300]}") from e
        produced = Path(tmp) / (docx_path.stem + ".pdf")
        if not produced.exists():
            raise PdfError("LibreOffice did not produce a PDF")
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), out_pdf)
    return out_pdf


def page_count(pdf_path: str | Path) -> int:
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        return len(pdf.pages)
