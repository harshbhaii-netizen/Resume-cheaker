import unittest
from io import BytesIO

from app.analyzer import analyze_match, extract_skills, parse_resume
from app.main import _anonymized_profile, extract_resume_text
from docx import Document


class SkillExtractionTests(unittest.TestCase):
    def test_normalizes_common_aliases(self):
        self.assertEqual(
            extract_skills("Built UI with React.js and JS; deployed on AWS."),
            ["AWS", "JavaScript", "React"],
        )

    def test_does_not_match_skill_inside_larger_word(self):
        self.assertNotIn("Java", extract_skills("Experience with JavaScript only."))


class ResumeParsingTests(unittest.TestCase):
    def test_extracts_profile_and_infers_related_skill(self):
        text = """Jordan Lee
jordan@example.com
+1 415 555 0134

Skills
Pandas, NumPy, Scikit-learn

Experience
Data Analyst | Acme
2020 - 2023

Education
B.S. Computer Science
"""
        profile = parse_resume(text)
        self.assertEqual(profile["name"], "Jordan Lee")
        self.assertEqual(profile["email"], "jordan@example.com")
        self.assertIn("Python", profile["inferred_skills"])
        self.assertEqual(profile["experience_years"], 3)
        self.assertIn("B.S. Computer Science", profile["education"])

    def test_extracts_docx_paragraphs_and_tables(self):
        document = Document()
        document.add_paragraph("Skills")
        document.add_paragraph("Python")
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "Education"
        stream = BytesIO()
        document.save(stream)

        text = extract_resume_text(stream.getvalue(), "resume.docx")
        self.assertIn("Python", text)
        self.assertIn("Education", text)

    def test_api_profile_redacts_identifiers_and_school_details(self):
        profile = parse_resume(
            "Jordan Lee\njordan@example.com\n"
            "Education\nB.S. Computer Science, Example University, 2021"
        )
        public = _anonymized_profile(profile)
        self.assertIsNone(public["name"])
        self.assertIsNone(public["email"])
        self.assertEqual(public["education"], "Bachelor's")
        self.assertNotIn("sections", public)


class MatchScoringTests(unittest.TestCase):
    def test_calculates_weighted_fit_and_skill_gaps(self):
        resume_text = """Software Engineer
Skills
Python, SQL, AWS
Experience
2020 - 2024
Education
B.S. Computer Science
"""
        profile = parse_resume(resume_text)
        jd = (
            "We need a bachelor's degree and 3 years of experience. "
            "Must use Python, SQL, and Docker to build reliable software."
        )
        result = analyze_match(profile, resume_text, jd)
        self.assertEqual(result["matched_skills"], ["Python", "SQL"])
        self.assertEqual(result["missing_skills"], ["Docker"])
        self.assertEqual(
            sum(item["weight"] for item in result["components"]),
            100,
        )
        self.assertEqual(result["fit_score"], 79)

    def test_contact_details_do_not_change_scoring(self):
        resume_text = "Python developer\nSkills\nPython\nExperience\n2022 - 2025"
        jd = "Python developer with at least 2 years experience building software."
        without_contact = parse_resume(resume_text)
        with_contact = parse_resume(
            "Alex Candidate\nalex@example.com\n+1 415 555 0134\n" + resume_text
        )
        first = analyze_match(without_contact, resume_text, jd)
        second = analyze_match(with_contact, resume_text, jd)
        self.assertEqual(first["fit_score"], second["fit_score"])
        self.assertEqual(first["components"], second["components"])

    def test_related_tools_can_support_an_inferred_skill_match(self):
        resume_text = "Skills\nPandas, NumPy, Scikit-learn"
        profile = parse_resume(resume_text)
        result = analyze_match(profile, resume_text, "Python developer")
        self.assertEqual(result["matched_skills"], ["Python"])
        self.assertEqual(result["missing_skills"], [])


if __name__ == "__main__":
    unittest.main()
