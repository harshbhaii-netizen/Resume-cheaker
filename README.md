# ResumeFit

A local, privacy-conscious MVP for comparing a resume with a job description. It extracts a small structured profile, identifies known skills and gaps, and explains a weighted fit score.

## Run locally

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. To run the tests:

```powershell
python -m unittest discover -s tests -v
```

## Customize the app name

Edit the `application-name` meta tag in `static/index.html`. The header and browser tab name update automatically.

## What it supports

- PDF, DOCX, and TXT resume uploads (up to 10 MB).
- Ready-to-use fictional examples: [sample resume](./samples/sample_resume.txt) and [sample job description](./samples/sample_job_description.txt).
- Basic extraction of contact details, education, experience dates, and skills.
- A transparent score weighted across skills (40%), experience (30%), education (20%), and TF-IDF text similarity (10%).
- A small editable-in-code skill alias list, including common abbreviations and related tools.
- Temporary in-memory processing: the app does not save resumes or results; the API redacts names and contact details, and only returns education level (not school or graduation year).

## Important limitations

This is a screening aid, not a hiring decision. Scoring and extraction are heuristic, the skill list is intentionally limited, and TF-IDF measures word overlap rather than deep semantic meaning. Scanned PDFs and image resumes need OCR and are not supported. This MVP does not include a trained NER model, external skill graph, database, authentication, batch processing, or cloud deployment. Names and contact details are redacted from API results and are not used in scoring. Review scores for bias before using them in hiring decisions.
