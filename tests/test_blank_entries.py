import unittest

from app.core.defaults import DEFAULT_LAYOUT, DEFAULT_STYLING
from app.models.base import Resume
from app.schemas.base import ResumeData, SectionName, TemplateName
from app.services.resume import create_html_string, verify_section

PERSONAL_INFO = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phonenumber": "555-0100",
    "extras": None,
}

BLANK_PROJECT = {"id": "blank", "title": "", "bullets": []}
REAL_PROJECT = {"id": "real", "title": "Analytical Engine", "bullets": ["Built it"]}


def make_resume(template: TemplateName = TemplateName.classic, **sections) -> Resume:
    layout = DEFAULT_LAYOUT.model_copy(deep=True)
    layout.selected_template = template
    resume_data = {
        "personalInfo": PERSONAL_INFO,
        "summary": None,
        "jobs": None,
        "education": None,
        "projects": None,
        "skills": None,
    }
    resume_data.update(sections)
    return Resume(
        resume_data=resume_data,
        layout=layout.model_dump(),
        styling=DEFAULT_STYLING.model_dump(),
    )


class VerifySectionTests(unittest.TestCase):
    def test_all_blank_projects_hide_the_section(self):
        data = ResumeData.model_validate(
            {**make_resume().resume_data, "projects": [BLANK_PROJECT]}
        )

        self.assertFalse(verify_section(data, SectionName.projects))

    def test_one_real_project_shows_the_section(self):
        data = ResumeData.model_validate(
            {**make_resume().resume_data, "projects": [BLANK_PROJECT, REAL_PROJECT]}
        )

        self.assertTrue(verify_section(data, SectionName.projects))

    def test_all_blank_jobs_hide_the_section(self):
        data = ResumeData.model_validate(
            {
                **make_resume().resume_data,
                "jobs": [
                    {
                        "id": "blank",
                        "company": "  ",
                        "role": "",
                        "startDate": "2020",
                        "endDate": "2021",
                        "bullets": [],
                    }
                ],
            }
        )

        self.assertFalse(verify_section(data, SectionName.jobs))

    def test_all_blank_education_hides_the_section(self):
        data = ResumeData.model_validate(
            {
                **make_resume().resume_data,
                "education": [
                    {"id": "blank", "school": "", "degree": "", "bullets": []}
                ],
            }
        )

        self.assertFalse(verify_section(data, SectionName.education))

    def test_empty_list_hides_the_section(self):
        data = ResumeData.model_validate({**make_resume().resume_data, "projects": []})

        self.assertFalse(verify_section(data, SectionName.projects))


class BlankEntryTemplateTests(unittest.TestCase):
    def test_only_blank_projects_render_no_heading(self):
        for template in TemplateName:
            with self.subTest(template=template):
                html = create_html_string(
                    make_resume(template, projects=[BLANK_PROJECT])
                )

                self.assertNotIn("Projects", html)

    def test_blank_project_is_skipped_beside_a_real_one(self):
        for template in TemplateName:
            with self.subTest(template=template):
                html = create_html_string(
                    make_resume(template, projects=[BLANK_PROJECT, REAL_PROJECT])
                )

                self.assertIn("Projects", html)
                self.assertIn("Analytical Engine", html)
                self.assertEqual(html.count('class="section-item"'), 1)

    def test_blank_bullets_are_dropped(self):
        html = create_html_string(
            make_resume(
                projects=[
                    {
                        "id": "real",
                        "title": "Analytical Engine",
                        "bullets": ["Built it", "", "   "],
                    }
                ]
            )
        )

        self.assertEqual(html.count("<li>"), 1)
        self.assertIn("<li>Built it</li>", html)

    def test_legacy_string_title_still_renders(self):
        html = create_html_string(
            make_resume(projects=[{"id": "p", "title": "Plain Project", "bullets": []}])
        )

        self.assertIn("Plain Project", html)

    def test_job_without_company_has_no_dangling_dash(self):
        html = create_html_string(
            make_resume(
                jobs=[
                    {
                        "id": "job-1",
                        "company": "",
                        "role": "Engineer",
                        "startDate": "2020",
                        "endDate": "2021",
                        "location": None,
                        "bullets": ["Shipped things"],
                    }
                ]
            )
        )

        headline = html.split('<span class="section-item-primary">')[1].split(
            "</span>"
        )[0]

        self.assertEqual(headline.strip(), "Engineer")


if __name__ == "__main__":
    unittest.main()
