import unittest

from ua_exam import gift_parser


class TestGiftParser(unittest.TestCase):
    def test_parse_category(self):
        content = "$CATEGORY: exam/networking\n"
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(questions, [])  # $CATEGORY alone does not produce questions, but sets category

    def test_essay_question(self):
        content = """
        ::Essay:: Describe the TCP 3-way handshake. {}
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["title"], "Essay")
        self.assertEqual(q["text"], "Describe the TCP 3-way handshake.")
        self.assertEqual(q["type"], "essay")
        self.assertEqual(q["options"], [])
        self.assertIsNone(q["correct"])

    def test_true_false_question(self):
        content = """
        ::TF1:: Is IPv6 128-bit? {T}

        ::TF2:: Is UDP connection-oriented? {F#Incorrect, UDP is connectionless}
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 2)

        q1 = questions[0]
        self.assertEqual(q1["title"], "TF1")
        self.assertEqual(q1["text"], "Is IPv6 128-bit?")
        self.assertEqual(q1["type"], "true_false")
        self.assertTrue(q1["correct"])

        q2 = questions[1]
        self.assertEqual(q2["title"], "TF2")
        self.assertEqual(q2["text"], "Is UDP connection-oriented?")
        self.assertEqual(q2["type"], "true_false")
        self.assertFalse(q2["correct"])

    def test_multiple_choice_question(self):
        content = """
        ::MC:: What is the subnet mask of a /26 network? {
            =255.255.255.192
            ~255.255.255.128
            ~255.255.255.0
        }
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["title"], "MC")
        self.assertEqual(q["text"], "What is the subnet mask of a /26 network?")
        self.assertEqual(q["type"], "multiple_choice")
        self.assertEqual(len(q["options"]), 3)
        self.assertTrue(q["options"][0]["is_correct"])
        self.assertEqual(q["options"][0]["text"], "255.255.255.192")
        self.assertFalse(q["options"][1]["is_correct"])
        self.assertEqual(q["options"][1]["text"], "255.255.255.128")
        self.assertFalse(q["options"][2]["is_correct"])
        self.assertEqual(q["options"][2]["text"], "255.255.255.0")

    def test_escaped_characters(self):
        content = r"""
        ::Escaped Braces:: When querying, how is relation represented? {
            =db.User.find(\{ "relation": "PUBLICOU", "target": "Post" \})
            ~MATCH (User) JOIN (Post) ON User.id \=\= Post.id
        }
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["title"], "Escaped Braces")
        self.assertEqual(q["text"], "When querying, how is relation represented?")
        self.assertEqual(q["type"], "multiple_choice")
        self.assertEqual(len(q["options"]), 2)
        # Option texts should be unescaped
        self.assertEqual(q["options"][0]["text"], 'db.User.find({ "relation": "PUBLICOU", "target": "Post" })')
        self.assertEqual(q["options"][1]["text"], "MATCH (User) JOIN (Post) ON User.id == Post.id")

    def test_weights_and_feedback(self):
        content = """
        ::MR:: Select correct options {
            ~%-50% Negative weight
            =%50% Positive weight 1
            =%50% Positive weight 2#Feedback for positive 2
        }
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["type"], "multiple_choice")
        self.assertEqual(len(q["options"]), 3)
        self.assertFalse(q["options"][0]["is_correct"])
        self.assertEqual(q["options"][0]["text"], "Negative weight")
        self.assertTrue(q["options"][1]["is_correct"])
        self.assertEqual(q["options"][1]["text"], "Positive weight 1")
        self.assertTrue(q["options"][2]["is_correct"])
        self.assertEqual(q["options"][2]["text"], "Positive weight 2")

    def test_multiple_blocks_and_categories(self):
        content = """
        // Section 1
        $CATEGORY: cat1

        ::Q1:: Question 1 {=A ~B}

        // Section 2
        $CATEGORY: cat2

        ::Q2:: Question 2 {=C ~D}
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["category"], "cat1")
        self.assertEqual(questions[0]["title"], "Q1")
        self.assertEqual(questions[1]["category"], "cat2")
        self.assertEqual(questions[1]["title"], "Q2")

    def test_html_entities(self):
        content = """
        ::HTML Entities:: Is a &lt; b? {
            =Yes, because a &lt; b is True.
            ~No, &gt; is greater.
        }
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["text"], "Is a < b?")
        self.assertEqual(q["options"][0]["text"], "Yes, because a < b is True.")
        self.assertEqual(q["options"][1]["text"], "No, > is greater.")

    def test_no_blank_lines_separation(self):
        content = """
        $CATEGORY: cat1
        ::Q1:: Question 1 {=Ans A ~Ans B}
        ::Q2:: Question 2 {=Ans C}
        $CATEGORY: cat2
        ::Q3:: Question 3 {=Ans D}
        """
        questions = gift_parser.parse_gift_content(content)
        self.assertEqual(len(questions), 3)
        self.assertEqual(questions[0]["category"], "cat1")
        self.assertEqual(questions[0]["title"], "Q1")
        self.assertEqual(questions[1]["category"], "cat1")
        self.assertEqual(questions[1]["title"], "Q2")
        self.assertEqual(questions[2]["category"], "cat2")
        self.assertEqual(questions[2]["title"], "Q3")

    def test_malformed_gift_files(self):
        # Missing closing brace
        content1 = "::Q1:: Question stem { =Correct "
        with self.assertRaises(ValueError):
            gift_parser.parse_gift_content(content1)

        # Option control character outside braces (at start of line)
        content2 = "::Q1:: Question stem \n =Correct { ~Incorrect }"
        with self.assertRaises(ValueError):
            gift_parser.parse_gift_content(content2)

        # Question without answer block
        content3 = "::Q1:: Question stem without block"
        with self.assertRaises(ValueError):
            gift_parser.parse_gift_content(content3)



if __name__ == "__main__":
    unittest.main()
