import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any


SKILL_ALIASES = {
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "C": ("c", "c language"),
    "C++": ("c++", "cpp"),
    "CSS": ("css", "css3"),
    "Docker": ("docker",),
    "Excel": ("excel", "microsoft excel"),
    "FastAPI": ("fastapi",),
    "GCP": ("gcp", "google cloud platform"),
    "Git": ("git", "github", "gitlab"),
    "HTML": ("html", "html5"),
    "Java": ("java",),
    "JavaScript": ("javascript", "js", "ecmascript"),
    "Kubernetes": ("kubernetes", "k8s"),
    "Linux": ("linux",),
    "MongoDB": ("mongodb", "mongo"),
    "MySQL": ("mysql",),
    "Node.js": ("node.js", "nodejs"),
    "NumPy": ("numpy",),
    "Pandas": ("pandas",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Power BI": ("power bi", "powerbi"),
    "Python": ("python",),
    "PyTorch": ("pytorch",),
    "R": ("r programming", "r language"),
    "React": ("react", "react.js", "reactjs"),
    "Redis": ("redis",),
    "Scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "Sass": ("sass", "scss"),
    "SQL": ("sql", "structured query language"),
    "Tableau": ("tableau",),
    "TensorFlow": ("tensorflow",),
    "TypeScript": ("typescript", "ts"),
    "Vue": ("vue", "vue.js", "vuejs"),
}

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "candidate", "for",
    "from", "have", "in", "into", "is", "it", "job", "of", "on", "or",
    "our", "the", "their", "this", "to", "we", "with", "you", "your",
    "years", "year", "work", "working", "experience", "role", "team",
    "skills", "including", "required", "preferred", "responsibilities",
}

SECTION_HEADERS = {
    "skills": ("skills", "technical skills", "core skills", "technologies"),
    "experience": (
        "experience", "work experience", "professional experience",
        "employment history", "work history",
    ),
    "education": ("education", "academic background", "qualifications"),
    "projects": ("projects", "personal projects", "selected projects"),
}


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def extract_skills(text: str) -> list[str]:
    normalized = _normalized(text)
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = rf"(?<![\w+#]){re.escape(alias.casefold())}(?![\w+#])"
            if re.search(pattern, normalized):
                found.append(canonical)
                break
    return sorted(found)


def _sections(text: str) -> dict[str, str]:
    content = {name: [] for name in SECTION_HEADERS}
    current = None
    for line in text.splitlines():
        heading = re.sub(r"[:\s]+$", "", _normalized(line.strip()))
        match = next(
            (
                section
                for section, headers in SECTION_HEADERS.items()
                if heading in headers
            ),
            None,
        )
        if match:
            current = match
        elif current:
            content[current].append(line.strip())
    return {name: "\n".join(lines) for name, lines in content.items()}


def _years_of_experience(text: str) -> float:
    current_year = datetime.now().year
    intervals: list[tuple[int, int]] = []
    date_range = re.compile(
        r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*"
        r"((?:19|20)\d{2}|present|current|now)\b",
        re.IGNORECASE,
    )
    for match in date_range.finditer(text):
        start = int(match.group(1))
        end = current_year if match.group(2).casefold() in {
            "present", "current", "now",
        } else int(match.group(2))
        if start <= end <= current_year + 1 and end - start <= 60:
            intervals.append((start, end))
    if not intervals:
        return 0.0

    intervals.sort()
    total = 0
    start, end = intervals[0]
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    total += end - start
    return round(min(total, 60), 1)


def _candidate_name(text: str) -> str | None:
    for line in text.splitlines()[:12]:
        value = line.strip()
        if (
            2 <= len(value) <= 70
            and not re.search(r"[@\d]|https?://|www\.", value, re.IGNORECASE)
            and not re.search(
                r"\b(resume|curriculum vitae|skills|experience|education)\b",
                value,
                re.IGNORECASE,
            )
            and len(value.split()) <= 6
        ):
            return value
    return None


def parse_resume(text: str) -> dict[str, Any]:
    normalized = unicodedata.normalize("NFKC", text)
    sections = _sections(normalized)
    email_match = re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", normalized, re.IGNORECASE
    )
    phone_match = re.search(
        r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)"
        r"\d{3,4}[\s.-]?\d{3,4}(?!\w)",
        normalized,
    )
    skills = extract_skills(normalized)
    inferred_skills = []
    if {"NumPy", "Pandas", "Scikit-learn"}.intersection(skills) and "Python" not in skills:
        inferred_skills.append("Python")

    education_lines = [
        line.strip()
        for line in sections["education"].splitlines()
        if line.strip()
    ]
    degree_pattern = re.compile(
        r"\b(bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|associate'?s?|"
        r"b\.?s\.?c?\.?|b\.?a\.?|m\.?s\.?c?\.?|m\.?b\.?a\.?)\b",
        re.IGNORECASE,
    )
    education = next(
        (line[:180] for line in education_lines if degree_pattern.search(line)),
        education_lines[0][:180] if education_lines else None,
    )

    return {
        "name": _candidate_name(normalized),
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": skills,
        "inferred_skills": inferred_skills,
        "education": re.sub(r"\b(?:19|20)\d{2}\b", "", education).strip()
        if education
        else None,
        "experience_years": _years_of_experience(sections["experience"] or normalized),
        "sections": sections,
    }


def _tokens(text: str) -> Counter[str]:
    words = re.findall(r"\b[a-z][a-z0-9+#.]*\b", _normalized(text))
    return Counter(word for word in words if word not in STOP_WORDS and len(word) > 1)


def _tfidf_similarity(left: str, right: str) -> float:
    left_counts = _tokens(left)
    right_counts = _tokens(right)
    vocabulary = set(left_counts) | set(right_counts)
    if not vocabulary:
        return 0.0

    left_vector = {}
    right_vector = {}
    for term in vocabulary:
        document_frequency = int(term in left_counts) + int(term in right_counts)
        inverse_frequency = math.log(3 / (document_frequency + 1)) + 1
        left_vector[term] = left_counts[term] * inverse_frequency
        right_vector[term] = right_counts[term] * inverse_frequency

    dot = sum(left_vector[word] * right_vector[word] for word in vocabulary)
    left_norm = math.sqrt(sum(value * value for value in left_vector.values()))
    right_norm = math.sqrt(sum(value * value for value in right_vector.values()))
    if not left_norm or not right_norm:
        return 0.0
    return round(100 * dot / (left_norm * right_norm))


def _education_score(resume: dict[str, Any], job_description: str) -> tuple[int, str]:
    jd = _normalized(job_description)
    requirements = (
        ("ph.d.", ("ph.d.", "phd", "doctorate")),
        ("master's", ("master", "m.s.", "msc", "m.sc.", "mba")),
        ("bachelor's", ("bachelor", "b.s.", "b.sc.", "b.a.")),
        ("associate's", ("associate",)),
    )
    required = next(
        (
            (label, aliases)
            for label, aliases in requirements
            if any(alias in jd for alias in aliases)
        ),
        None,
    )
    if not required:
        return 100, "No specific degree requirement found."
    label, aliases = required
    education = _normalized(resume["education"] or "")
    if any(alias in education for alias in aliases):
        return 100, f"Resume education matches the {label} requirement."
    higher_degree = (
        label == "bachelor's"
        and any(term in education for term in ("master", "ph.d", "phd", "doctorate"))
    )
    if higher_degree:
        return 100, "Resume lists a higher degree than the stated requirement."
    if not resume["education"]:
        return 0, f"No education entry found for the {label} requirement."
    return 0, f"Resume education does not show the {label} requirement."


def analyze_match(resume: dict[str, Any], resume_text: str, job_description: str) -> dict[str, Any]:
    required_skills = extract_skills(job_description)
    candidate_skills = set(resume["skills"]) | set(resume["inferred_skills"])
    matched_skills = sorted(candidate_skills.intersection(required_skills))
    missing_skills = sorted(set(required_skills) - candidate_skills)
    inferred = sorted(set(resume["inferred_skills"]))

    if required_skills:
        skill_score = round(100 * len(matched_skills) / len(required_skills))
        skill_detail = (
            f"{len(matched_skills)} of {len(required_skills)} detected skills matched, "
            "including inferred skills where applicable."
        )
    else:
        skill_score = 100
        skill_detail = "No catalogued skills were detected in the job description."

    required_years_match = re.search(
        r"\b(\d{1,2})\+?\s*(?:years?|yrs?)\b", job_description, re.IGNORECASE
    )
    if required_years_match:
        required_years = int(required_years_match.group(1))
        experience_score = min(
            100, round(100 * resume["experience_years"] / required_years)
        ) if required_years else 100
        experience_detail = (
            f"{resume['experience_years']:g} years detected; "
            f"{required_years} years requested."
        )
    else:
        experience_score = 100
        experience_detail = "No minimum years requirement found."

    education_score, education_detail = _education_score(resume, job_description)
    sections = resume.get("sections", {})
    contextual_text = "\n".join(
        sections.get(section, "") for section in ("skills", "experience", "projects")
    )
    if not contextual_text.strip():
        contextual_text = resume_text
    contextual_text = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|https?://\S+|www\.\S+",
        " ",
        contextual_text,
        flags=re.IGNORECASE,
    )
    contextual_text = re.sub(
        r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)"
        r"\d{3,4}[\s.-]?\d{3,4}(?!\w)",
        " ",
        contextual_text,
    )
    if resume.get("name"):
        contextual_text = re.sub(
            re.escape(resume["name"]), " ", contextual_text, flags=re.IGNORECASE
        )
    contextual_text = re.sub(r"\b(?:19|20)\d{2}\b", " ", contextual_text)
    contextual_score = _tfidf_similarity(contextual_text, job_description)
    components = [
        {"name": "Skills", "weight": 40, "score": skill_score, "detail": skill_detail},
        {
            "name": "Experience",
            "weight": 30,
            "score": experience_score,
            "detail": experience_detail,
        },
        {
            "name": "Education",
            "weight": 20,
            "score": education_score,
            "detail": education_detail,
        },
        {
            "name": "Contextual similarity",
            "weight": 10,
            "score": contextual_score,
            "detail": "TF-IDF word similarity; it is not a trained semantic model.",
        },
    ]
    fit_score = round(sum(item["weight"] * item["score"] for item in components) / 100)
    return {
        "fit_score": fit_score,
        "components": components,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "inferred_skills": inferred,
    }
