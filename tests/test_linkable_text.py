import os
import unittest
from io import BytesIO

from pydantic import ValidationError
from pypdf import PdfReader

from app.core.defaults import DEFAULT_LAYOUT, DEFAULT_STYLING
from app.core.render import PDFManager
from app.models.base import Resume
from app.schemas.base import LinkableText, PersonalInfo, ProjectEntry, TemplateName
from app.services.resume import create_html_string


class LinkableTextSchemaTests(unittest.TestCase):
    def test_legacy_string_becomes_plain_text(self):
        value = LinkableText.model_validate("Portfolio")

        self.assertEqual(value.text, "Portfolio")
        self.assertIsNone(value.url)

    def test_domain_without_scheme_uses_https(self):
        value = LinkableText(text="Portfolio", url="example.com/work")

        self.assertEqual(value.url, "https://example.com/work")

    def test_blank_url_becomes_none(self):
        value = LinkableText(text="San Francisco", url="  ")

        self.assertIsNone(value.url)

    def test_non_web_schemes_are_rejected(self):
        for url in (
            "javascript:alert(1)",
            "mailto:user@example.com",
            "tel:+15555555555",
            "ftp://example.com/file",
            "file:/etc/passwd",
            "blob:https://example.com/id",
            "urn:1234",
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                LinkableText(text="Unsafe", url=url)

    def test_urls_with_whitespace_are_rejected(self):
        with self.assertRaises(ValidationError):
            LinkableText(text="Broken", url="https://example.com/my work")

    def test_scheme_relative_urls_are_rejected(self):
        with self.assertRaises(ValidationError):
            LinkableText(text="Broken", url="//evil.example/path")

    def test_bare_scheme_less_hosts_are_rejected(self):
        for url in ("notaurlatall", "localhost:3000"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                LinkableText(text="Broken", url=url)

    def test_urls_with_credentials_are_rejected(self):
        for url in (
            "https://user:password@example.com",
            "https://linkedin.com@evil.example/",
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                LinkableText(text="Broken", url=url)

    def test_scheme_is_normalized_to_lowercase(self):
        value = LinkableText(text="Portfolio", url="HTTPS://Example.com/work")

        self.assertEqual(value.url, "https://Example.com/work")

    def test_existing_profile_and_project_shapes_remain_valid(self):
        personal_info = PersonalInfo.model_validate(
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "phonenumber": "555-0100",
                "extras": ["London"],
            }
        )
        project = ProjectEntry.model_validate(
            {"id": "project-1", "title": "Analytical Engine", "bullets": []}
        )

        self.assertEqual(personal_info.extras[0].text, "London")
        self.assertIsNone(personal_info.extras[0].url)
        self.assertEqual(project.title.text, "Analytical Engine")


class LinkableTextTemplateTests(unittest.TestCase):
    def make_resume(self, template: TemplateName) -> Resume:
        layout = DEFAULT_LAYOUT.model_copy(deep=True)
        layout.selected_template = template
        return Resume(
            resume_data={
                "personalInfo": {
                    "name": "Ada <Lovelace>",
                    "email": "ada@example.com",
                    "phonenumber": "555-0100",
                    "extras": [
                        {"text": "Portfolio & Notes", "url": "example.com?a=1&b=2"},
                        "London <script>alert(1)</script>",
                    ],
                },
                "summary": None,
                "jobs": None,
                "education": None,
                "projects": [
                    {
                        "id": "project-1",
                        "title": {
                            "text": "Analytical <Engine>",
                            "url": "https://example.com/engine",
                        },
                        "bullets": [],
                    },
                    {"id": "project-2", "title": "Plain Project", "bullets": []},
                ],
                "skills": None,
            },
            layout=layout.model_dump(),
            styling=DEFAULT_STYLING.model_dump(),
        )

    def test_all_layouts_render_safe_linked_and_plain_values(self):
        for template in TemplateName:
            with self.subTest(template=template):
                html = create_html_string(self.make_resume(template))

                self.assertIn(
                    'href="https://example.com?a=1&amp;b=2">Portfolio &amp; Notes</a>',
                    html,
                )
                self.assertIn(
                    'href="https://example.com/engine">Analytical &lt;Engine&gt;</a>',
                    html,
                )
                self.assertIn("London &lt;script&gt;alert(1)&lt;/script&gt;", html)
                self.assertNotIn("<script>", html)
                self.assertIn("Plain Project", html)


@unittest.skipUnless(
    os.environ.get("RUN_PDF_INTEGRATION_TESTS") == "1",
    "set RUN_PDF_INTEGRATION_TESTS=1 to run Chromium integration coverage",
)
class LinkableTextPDFTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pdf_manager = PDFManager()
        await self.pdf_manager.start()

    async def asyncTearDown(self):
        await self.pdf_manager.stop()

    async def test_pdf_contains_external_link_annotations(self):
        source = LinkableTextTemplateTests().make_resume(TemplateName.classic)
        result = await self.pdf_manager.create_pdf(create_html_string(source))
        reader = PdfReader(BytesIO(result.pdf))
        uris = []
        for page in reader.pages:
            for annotation_ref in page.get("/Annots", []):
                annotation = annotation_ref.get_object()
                action = annotation.get("/A")
                if action and action.get("/URI"):
                    uris.append(action["/URI"])

        self.assertIn("https://example.com/?a=1&b=2", uris)
        self.assertIn("https://example.com/engine", uris)


if __name__ == "__main__":
    unittest.main()
