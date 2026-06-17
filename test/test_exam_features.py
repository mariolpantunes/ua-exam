import os
import shutil
import tempfile
import unittest

from ua_exam import converters, exam_generator, gift_escaper, pdf_renderer


class TestConvertersRegistry(unittest.TestCase):
    def test_registry_empty_by_default(self):
        formats = converters.get_available_formats()
        self.assertIsInstance(formats, list)

    def test_register_and_get_converter(self):

        @converters.register_converter("dummy")
        class DummyConverter(converters.BaseConverter):
            def convert(self, input_path: str, output_path: str) -> bool:
                return True

        self.assertIn("dummy", converters.get_available_formats())
        conv = converters.get_converter("dummy")
        self.assertIsInstance(conv, DummyConverter)
        self.assertTrue(conv.convert("in", "out"))


class TestGiftEscaper(unittest.TestCase):
    def test_escape_gift_naive(self):
        text = "This has ~ and = and { and } and : and \\."
        escaped = gift_escaper.escape_gift_naive(text)
        self.assertIn("\\~", escaped)
        self.assertIn("\\=", escaped)
        self.assertIn("\\{", escaped)
        self.assertIn("\\}", escaped)
        self.assertIn("\\:", escaped)
        self.assertIn("\\\\", escaped)

    def test_escape_gift_naive_markdown(self):
        text = "This is `code` and **bold** and $math$."
        escaped = gift_escaper.escape_gift_naive(text)
        self.assertIn("<code>code</code>", escaped)
        self.assertIn("<b>bold</b>", escaped)
        self.assertIn("\\\\\\\\(math\\\\\\\\)", escaped)


class TestPdfRenderer(unittest.TestCase):
    def test_pandoc_check_returns_bool(self):
        is_avail = pdf_renderer.check_pandoc_available()
        self.assertIsInstance(is_avail, bool)


class TestExamGenerator(unittest.TestCase):
    temp_dir: str = ""
    q_bank_dir: str = ""
    gift_file: str = ""
    config: dict[str, object] = {}

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create a dummy question bank directory
        self.q_bank_dir = os.path.join(self.temp_dir, "questions")
        os.makedirs(self.q_bank_dir)

        # Write some dummy gift files
        self.gift_file = os.path.join(self.q_bank_dir, "q1.gift")
        with open(self.gift_file, "w", encoding="utf-8") as f:
            f.write("""
$CATEGORY: lss/test/01-terminal
::Q1:: Question 1 { =Ans A ~Ans B ~Ans C }
::Q2:: Question 2 { =Ans X ~Ans Y }

$CATEGORY: lss/test/open
::Q3:: Describe this. {}
""")

        # Create configuration dictionary
        self.config = {
            "class": "Test Class",
            "lang": "pt",
            "copies": 2,
            "questions_folder": self.q_bank_dir,
            "category_prefix": "lss/test",
            "parts": [
                {
                    "part": "Section A",
                    "classification": 10,
                    "questions": [{"topic": "01-terminal", "quantity": 2}],
                },
                {
                    "part": "Section B",
                    "classification": 10,
                    "questions": [{"topic": "open", "quantity": 1}],
                },
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_clean_latex_text(self):
        self.assertEqual(exam_generator.clean_latex_text("hello"), "hello")
        self.assertEqual(exam_generator.clean_latex_text("`code`"), "\\texttt{code}")
        self.assertEqual(exam_generator.clean_latex_text("$x + y$"), "$x + y$")

    def test_generate_multiple_copies(self):
        output_base = os.path.join(self.temp_dir, "exam")

        # Generate 2 copies
        exam_generator.generate_exams_from_config(self.config, base_seed=42, output_base=output_base, compile_pdf_flag=False)

        # Check that files were created
        self.assertTrue(os.path.exists(output_base + "_v1.md"))
        self.assertTrue(os.path.exists(output_base + "_v1_solutions.csv"))
        self.assertTrue(os.path.exists(output_base + "_v2.md"))
        self.assertTrue(os.path.exists(output_base + "_v2_solutions.csv"))

        # Verify reproducibility by regenerating copy 1
        with open(output_base + "_v1.md", "r", encoding="utf-8") as f:
            content_v1_run1 = f.read()

        # Verify content of the generated files
        self.assertIn("Question 1", content_v1_run1)
        self.assertIn("Question 2", content_v1_run1)
        self.assertIn("Describe this.", content_v1_run1)

        import csv
        with open(output_base + "_v1_solutions.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        self.assertEqual(rows[0], ["Part", "Question ID", "Answer"])
        self.assertEqual(len(rows), 4)  # header + 3 questions
        
        # Row 1 (Section A, Q1): Part=1, QID=1, Answer should be A, B, or C
        self.assertEqual(rows[1][0], "1")
        self.assertEqual(rows[1][1], "1")
        self.assertIn(rows[1][2], ["A", "B", "C"])

        # Row 2 (Section A, Q2): Part=1, QID=2, Answer should be A or B
        self.assertEqual(rows[2][0], "1")
        self.assertEqual(rows[2][1], "2")
        self.assertIn(rows[2][2], ["A", "B"])

        # Row 3 (Section B, Q1): Part=2, QID=1, Answer should be --- (Open Answer)
        self.assertEqual(rows[3][0], "2")
        self.assertEqual(rows[3][1], "1")
        self.assertEqual(rows[3][2], "--- (Open Answer)")

        # Delete files
        os.remove(output_base + "_v1.md")
        os.remove(output_base + "_v1_solutions.csv")
        os.remove(output_base + "_v2.md")
        os.remove(output_base + "_v2_solutions.csv")

        # Generate copy 1 again with same seed
        single_config = self.config.copy()
        single_config["copies"] = 1
        exam_generator.generate_exams_from_config(single_config, base_seed=42, output_base=output_base, compile_pdf_flag=False)

        self.assertTrue(os.path.exists(output_base + ".md"))
        with open(output_base + ".md", "r", encoding="utf-8") as f:
            content_v1_run2 = f.read()

        # Check identical content (reproducibility)
        idx_run1 = content_v1_run1.find("# Section A")
        idx_run2 = content_v1_run2.find("# Section A")
        self.assertEqual(content_v1_run1[idx_run1:], content_v1_run2[idx_run2:])


if __name__ == "__main__":
    unittest.main()
