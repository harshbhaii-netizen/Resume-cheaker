from io import BytesIO
from pathlib import Path
import re
import zipfile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.analyzer import analyze_match, parse_resume


BASE_DIR = Path(__file__).resolve().parent.parent
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

app = FastAPI(title="ResumeFit", version="1.0.0")


def _anonymized_profile(profile: dict) -> dict:
    education_terms = re.findall(r"[a-z]+", (profile.get("education") or "").casefold())
    paired_terms = {
        f"{left} {right}" for left, right in zip(education_terms, education_terms[1:])
    }
    if "doctorate" in education_terms or "phd" in education_terms or "ph d" in paired_terms:
        degree_level = "Doctorate"
    elif (
        any(term in education_terms for term in ("master", "masters", "mba", "msc", "ms"))
        or {"m s", "m sc"}.intersection(paired_terms)
    ):
        degree_level = "Master's"
    elif (
        any(term in education_terms for term in ("bachelor", "bachelors", "bsc", "ba", "bs"))
        or {"b s", "b sc", "b a"}.intersection(paired_terms)
    ):
        degree_level = "Bachelor's"
    elif "associate" in education_terms or "associates" in education_terms:
        degree_level = "Associate's"
    else:
        degree_level = None

    public_profile = {
        **profile,
        "name": None,
        "email": None,
        "phone": None,
        "education": degree_level,
    }
    public_profile.pop("sections")
    return public_profile


def extract_resume_text(data: bytes, filename: str) -> str:
    extension = Path(filename).suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT resume.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise HTTPException(
                    status_code=422,
                    detail="This PDF is password-protected. Upload an unlocked PDF.",
                )
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as error:
            raise HTTPException(
                status_code=422,
                detail="This PDF could not be read. Try exporting it again as a text PDF.",
            ) from error

    if extension == ".docx":
        try:
            document = Document(BytesIO(data))
        except (PackageNotFoundError, zipfile.BadZipFile) as error:
            raise HTTPException(
                status_code=422, detail="This DOCX file is invalid or damaged."
            ) from error
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        tables = [
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        ]
        return "\n".join(paragraphs + tables)

    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


@app.post("/api/analyze")
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
) -> dict:
    filename = Path(resume_file.filename or "").name
    if Path(filename).suffix.casefold() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT resume.",
        )
    if not job_description.strip() or len(job_description) > 20_000:
        raise HTTPException(
            status_code=400,
            detail="Enter a job description between 1 and 20,000 characters.",
        )

    data = await resume_file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="Resume exceeds the 10 MB upload limit."
        )

    text = extract_resume_text(data, filename)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found. Scanned/image-only resumes need OCR.",
        )

    profile = parse_resume(text)
    match = analyze_match(profile, text, job_description)
    return {
        "filename": f"Resume ({Path(filename).suffix[1:].upper()})",
        "profile": _anonymized_profile(profile),
        "match": match,
        "notice": (
            "This is a screening aid, not a hiring decision. Scores are heuristic; "
            "personal contact details are not used in matching."
        ),
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
