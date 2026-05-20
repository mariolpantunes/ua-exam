import argparse
import csv
import datetime
import json
import logging
import os
import random
import re
import sys

import gift_parser

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def clean_latex_text(text):
    """
    Escapes special LaTeX characters in normal text, but preserves:
    1. Code blocks enclosed in backticks (`code`) -> Converts to fully escaped \texttt{}
    2. Math formulas enclosed in dollar signs ($math$) -> Preserves as is
    """
    if not text:
        return ""

    # Helper function to escape strict text
    def escape_chars(s):
        # Escape backslash FIRST to avoid double-escaping
        s = s.replace("\\", "\\textbackslash ")
        s = s.replace("{", "\\{").replace("}", "\\}")
        s = s.replace("%", "\\%").replace("#", "\\#")
        s = s.replace("&", "\\&").replace("_", "\\_")
        s = s.replace("^", "\\textasciicircum ")
        s = s.replace("~", "\\textasciitilde ")
        return s

    # 1. Split by backticks to handle `code`
    parts = text.split("`")
    processed_parts = []

    for i, part in enumerate(parts):
        if i % 2 == 1:
            # --- CODE BLOCK (Inside backticks) ---
            # Use escape_chars for consistency, then wrap in \texttt{}
            # But we also need to escape $ in code to avoid math mode
            escaped_code = escape_chars(part).replace("$", "\\$")
            processed_parts.append(f"\\texttt{{{escaped_code}}}")
        else:
            # --- NORMAL TEXT (May contain $math$) ---
            # Split this segment by '$' to find math formulas
            # Use a regex that captures the $...$ block to avoid splitting it
            # We use () to keep the delimiter in the result list
            math_parts = re.split(r"(\$.*?\$)", part)
            for subpart in math_parts:
                if subpart.startswith("$") and subpart.endswith("$"):
                    # Inside $...$ -> This is Math. Preserve it exactly.
                    processed_parts.append(subpart)
                else:
                    # Outside $...$ -> This is Text. Escape it.
                    processed_parts.append(escape_chars(subpart))

    return "".join(processed_parts)


translations = {
    "pt": {
        "date": "Data",
        "student_name": "Nome do Estudante",
        "student_number": "N.º de Estudante",
        "classification": "Classificação",
        "exam_instructions": "Instruções do Exame",
        "duration": "Duração",
        "duration_default": "60 minutos",
        "instructions": "Instruções",
        "instructions_default": "Por favor, responda a todas as questões. Leia atentamente as instruções de cada part.",
        "exam": "Exame",
        "exam_default": "Normal",
    },
    "en": {
        "date": "Date",
        "student_name": "Student Name",
        "student_number": "Student No.",
        "classification": "Classification",
        "exam_instructions": "Exam Instructions",
        "duration": "Duration",
        "duration_default": "60 minutes",
        "instructions": "Instructions",
        "instructions_default": "Please answer all questions. Read the instructions for each part carefully.",
        "exam": "Exame",
        "exam_default": "Normal",
    },
}


def generate_header(config, lang: str = "pt"):
    t = translations[lang]

    course_name = config.get("class", "Exam")
    date_str = config.get("date", datetime.datetime.now().strftime("%B %d, %Y"))

    duration = config.get("duration", t["duration_default"])
    instructions = config.get("instructions", t["instructions_default"])

    exam_type = config.get("exam", t["exam_default"])

    logo_path = config.get("logo", "logo/logo_ua_cropped.pdf")

    return f"""---
geometry: a4paper, top=2cm, bottom=2cm, left=2cm, right=2cm
mainfont: NotoSans
mainfontfallback:
  - "NotoColorEmoji:mode=harf"
header-includes:
 - \\usepackage{{longtable,booktabs}}
 - \\usepackage{{etoolbox}}
 - \\usepackage{{graphicx}}
 - \\usepackage{{array}}
 - \\usepackage{{fancyhdr}}
 - \\AtBeginEnvironment{{longtable}}{{\\normalsize}}
 - \\AtBeginEnvironment{{cslreferences}}{{\\tiny}}
 - \\AtBeginEnvironment{{Shaded}}{{\\normalsize}}
 - \\AtBeginEnvironment{{verbatim}}{{\\normalsize}}
 - \\setmonofont[Contextuals={{Alternate}}]{{FiraCodeNerdFontMono-Retina}}
 - \\pagestyle{{fancy}}
 - \\fancyhf{{}}
 - \\renewcommand{{\\headrulewidth}}{{0pt}}
 - \\fancyfoot[C]{{\\thepage}}
---

\\noindent
\\begin{{minipage}}[t]{{0.3\\textwidth}}
    \\vspace{{0pt}}
    \\includegraphics[width=\\linewidth]{{{logo_path}}}
\\end{{minipage}}
\\begin{{minipage}}[t]{{0.65\\textwidth}}
    \\vspace{{0pt}}
    \\raggedleft
    {{\\Large \\textbf{{Universidade de Aveiro}}}} \\\\
    {{\\large {course_name}}} \\\\
    \\vspace{{0.25cm}}
    {{\\large {t["exam"]}: {exam_type}}} \\\\
    {{\\small {t["date"]}: {date_str}}}
\\end{{minipage}}

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}

**{t["student_name"]}:**

**{t["student_number"]}:**

**{t["classification"]}:**

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}

# {t["exam_instructions"]}

**{t["duration"]}:** {duration}

**{t["instructions"]}:** {instructions}

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}
"""


def render_multiple_choice(index, q, points):
    q_text = clean_latex_text(q["text"])

    md = f"**{index}. ({points:.2g} pts) {q_text}**\n\n"
    md += "\\noindent\n"
    md += "\\begin{tabular}{|p{14cm}|p{1cm}|}\n\\hline\n"

    for i, opt in enumerate(q["options"]):
        label = chr(65 + i)  # 65 is ASCII for 'A'. 0->A, 1->B, etc.
        clean_opt = clean_latex_text(opt["text"])
        md += f" \\textbf{{{label}.}} {clean_opt} & \\\\ \\hline\n"

    md += "\\end{tabular}\n\\vspace{0.5cm}\n\n"
    return md


def render_true_false(index, q, points):
    q_text = clean_latex_text(q["text"])

    md = f"**{index}. ({points:.2g} pts) {q_text}**\n\n"
    md += "\\noindent\n"
    md += "\\begin{tabular}{|p{14cm}|p{1cm}|}\n\\hline\n"
    md += " \\textbf{A.} True & \\\\ \\hline\n"
    md += " \\textbf{B.} False & \\\\ \\hline\n"
    md += "\\end{tabular}\n\\vspace{0.5cm}\n\n"
    return md


def render_essay(index, q, points):
    q_text = clean_latex_text(q["text"])
    md = f"**{index}. ({points:.2g} pts) {q_text}**\n\n"
    md += "\\vspace{7cm}\n\n"
    return md


def dispatch_renderer(index, q, points):
    q_type = q.get("type", "unknown")

    if q_type == "multiple_choice":
        return render_multiple_choice(index, q, points)
    elif q_type == "true_false":
        return render_true_false(index, q, points)
    elif q_type == "essay":
        return render_essay(index, q, points)
    else:
        logger.warning(
            f"Unknown question type '{q_type}' for question '{q.get('title')}'. Defaulting to Open Answer."
        )
        return render_essay(index, q, points)


def get_answer_key(q):
    """
    Returns the correct label(s) (A, B...) for objective questions,
    or a placeholder for open-ended questions.
    Handles multiple correct answers.
    """
    if q["type"] == "multiple_choice":
        labels = [chr(65 + i) for i in range(len(q["options"]))]
        correct_labels = []
        for i, opt in enumerate(q["options"]):
            if opt.get("is_correct"):
                correct_labels.append(labels[i])
        
        if not correct_labels:
            return "?"
        return ", ".join(correct_labels)

    elif q["type"] == "true_false":
        return "A" if q.get("correct") else "B"

    elif q["type"] == "essay":
        return "--- (Open Answer)"

    return "---"


def validate_scoring(config, target_score=20.0):
    total_score = sum(part.get("classification", 0) for part in config["parts"])
    if abs(total_score - target_score) > 0.01:
        logger.warning(
            f"Scoring Mismatch: Total classification is {total_score}, expected {target_score}."
        )
    else:
        logger.info(f"Scoring Validation: Total classification is {target_score}.")


def normalize_category(cat):
    """Normalizes category paths: removes leading/trailing slashes and handles hierarchy."""
    if not cat:
        return ""
    return cat.strip().strip("/")


def load_question_bank(base_folder):
    """
    Recursively scans base_folder for .gift and .txt files and builds a bank indexed by category.
    """
    bank = {}
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".gift") or file.endswith(".txt"):
                filepath = os.path.join(root, file)
                logger.info(f"Parsing {filepath}...")
                questions = gift_parser.parse_gift_file(filepath)
                for q in questions:
                    cat = normalize_category(q.get("category", "default"))
                    if cat not in bank:
                        bank[cat] = []
                    bank[cat].append(q)
    return bank


def main():
    parser = argparse.ArgumentParser(description="UA Exam Generator")
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="Path to JSON config file"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="exam.md",
        help="Output filename (default: exam.md)",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        logger.info(f"Random seed set to: {args.seed}")
    else:
        logger.info("No seed provided. Using random selection.")

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        sys.exit(1)

    logger.info(f"Generating Exam for: {config.get('class', 'Unknown Class')}")
    
    target_score = config.get("target_score", 20.0)
    validate_scoring(config, target_score)

    base_folder = config.get("questions_folder", ".")
    bank = load_question_bank(base_folder)

    # Extract language from config, defaulting to "pt" if missing
    lang = config.get("lang", "pt")
    if lang not in translations:
        logger.warning(
            f"Language '{lang}' not found in translations. Falling back to 'pt'."
        )
        lang = "pt"

    category_prefix = normalize_category(config.get("category_prefix", ""))
    
    # Global tracking to prevent duplicates
    used_questions = set()

    # Pass the extracted language to the generator
    full_markdown = generate_header(config, lang=lang)
    csv_rows = []

    for part_idx, part in enumerate(config["parts"], 1):
        question_counter = 1
        part_name = part.get("part", "Section")
        part_total_score = part.get("classification", 0)

        total_qs_needed = sum(item.get("quantity", 0) for item in part["questions"])

        if total_qs_needed == 0:
            logger.warning(f"Part '{part_name}' has 0 questions defined. Skipping.")
            continue

        points_per_q = part_total_score / total_qs_needed
        logger.info(
            f"Processing Part {part_idx}: '{part_name}' | Total Points: {part_total_score} | Qs: {total_qs_needed}"
        )

        full_markdown += f"# {part_name} ({part.get('classification')} pts)\n\n"

        for q_req in part["questions"]:
            topic = q_req.get("topic")
            qty = q_req.get("quantity", 0)

            # Resolve category path
            full_topic = normalize_category(topic)
            if category_prefix:
                full_topic = normalize_category(f"{category_prefix}/{full_topic}")

            pool = bank.get(full_topic, [])
            
            # Filter out already used questions
            available_pool = [q for q in pool if f"{q['text']}_{q['title']}" not in used_questions]

            if len(available_pool) < qty:
                logger.warning(
                    f"Category '{full_topic}': Requested {qty} questions, but only {len(available_pool)} available (after deduplication). Using all available."
                )
                selected = available_pool
            else:
                selected = random.sample(available_pool, qty)

            for q in selected:
                # Mark as used
                used_questions.add(f"{q['text']}_{q['title']}")
                
                # SHUFFLE OPTIONS BEFORE RENDERING
                if q["type"] == "multiple_choice":
                    random.shuffle(q["options"])

                full_markdown += dispatch_renderer(question_counter, q, points_per_q)

                ans = get_answer_key(q)
                csv_rows.append([part_idx, question_counter, ans])

                question_counter += 1

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(full_markdown)
        logger.info(f"Success! Exam generated: {args.output}")
    except IOError as e:
        logger.error(f"Failed to write output file: {e}")

    try:
        csv_filename = os.path.splitext(args.output)[0] + "_solutions.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Part", "Question ID", "Answer"])
            writer.writerows(csv_rows)
        logger.info(f"Success! Solutions generated: {csv_filename}")
    except IOError as e:
        logger.error(f"Failed to write solutions file: {e}")


if __name__ == "__main__":
    main()
