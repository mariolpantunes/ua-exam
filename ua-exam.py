import argparse
import csv
import json
import logging
import os
import random
import re
import sys
from datetime import datetime

import gift_parser

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def clean_latex_text(text):
    """
    Escapes special LaTeX characters and handles basic Markdown code blocks correctly.
    Splits by backticks first to avoid double-escaping the LaTeX commands generated for code.
    """
    if not text:
        return ""

    # Split by backticks to separate normal text from code blocks
    # Example: "Use `cron` now" -> ['Use ', 'cron', ' now']
    parts = text.split("`")

    processed_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # NORMAL TEXT: Escape all LaTeX special chars
            # We must escape backslash first to avoid escaping the escapes
            part = part.replace("\\", "\\textbackslash ")
            part = part.replace("{", "\\{").replace("}", "\\}")
            part = part.replace("%", "\\%").replace("#", "\\#")
            part = part.replace("&", "\\&").replace("_", "\\_")
            part = part.replace("$", "\\$").replace("^", "\\textasciicircum ")
            part = part.replace("~", "\\textasciitilde ")
            processed_parts.append(part)
        else:
            # CODE BLOCK (Inside backticks):
            # We wrap this in \texttt{}, but we must still escape characters
            # INSIDE the code that would break LaTeX (like } or \),
            # but NOT the \texttt wrapper itself.
            part = part.replace("\\", "\\textbackslash ")
            part = part.replace("{", "\\{").replace("}", "\\}")
            part = part.replace("%", "\\%").replace("#", "\\#")
            part = part.replace("&", "\\&").replace("_", "\\_")
            part = part.replace("$", "\\$").replace("^", "\\textasciicircum ")
            part = part.replace("~", "\\textasciitilde ")

            processed_parts.append(f"\\texttt{{{part}}}")

    return "".join(processed_parts)


def generate_header(config):
    course_name = config.get("class", "Exam")
    date_str = config.get("date", datetime.now().strftime("%B %d, %Y"))

    duration = config.get("duration", "90 Minutes")
    instructions = config.get(
        "instructions",
        "Please answer all questions. Read the instructions for each section carefully.",
    )

    logo_path = "logo/logo_ua_cropped.pdf"

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
    {{\\small Date: {date_str}}}
\\end{{minipage}}

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}

**Student Name:**

**Student No.:**

**Classification:**

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}

# Exam Instructions

**Duration:** {duration}

**Instructions:** {instructions}

\\vspace{{0.5cm}}
\\hrule
\\vspace{{0.5cm}}
"""


def render_multiple_choice(index, q, points):
    q_text = clean_latex_text(q["text"])

    md = f"**{index}. ({points:.2g} pts) {q_text}**\n\n"
    md += "\\noindent\n"
    md += "\\begin{tabular}{|p{14cm}|p{1cm}|}\n\\hline\n"

    labels = ["A", "B", "C", "D", "E", "F"]
    for i, opt in enumerate(q["options"]):
        if i >= len(labels):
            break
        label = labels[i]
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
    """Returns the correct label (A, B, C...) for objective questions."""
    if q["type"] == "multiple_choice":
        labels = ["A", "B", "C", "D", "E", "F"]
        for i, opt in enumerate(q["options"]):
            if opt["is_correct"]:
                return labels[i] if i < len(labels) else "?"
        return "?"
    elif q["type"] == "true_false":
        return "A" if q["correct"] else "B"
    return None


def validate_scoring(config):
    total_score = sum(part.get("classification", 0) for part in config["parts"])
    if abs(total_score - 20.0) > 0.01:
        logger.warning(
            f"Scoring Mismatch: Total classification is {total_score}, expected 20."
        )
    else:
        logger.info("Scoring Validation: Total classification is 20.")


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
    validate_scoring(config)

    base_folder = config.get("questions_folder", ".")

    full_markdown = generate_header(config)
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

            filename = os.path.join(base_folder, f"{topic}.gift")

            if not os.path.exists(filename):
                logger.error(f"GIFT file not found: {filename}")
                continue

            pool = gift_parser.parse_gift_file(filename)

            if len(pool) < qty:
                logger.warning(
                    f"File {filename}: Requested {qty} questions, but only found {len(pool)}. Using all available."
                )
                selected = pool
            else:
                selected = random.sample(pool, qty)
                source_name = selected[0].get("category") if selected else filename
                logger.info(
                    f"  - Selected {len(selected)} questions from {source_name}"
                )

            for q in selected:
                full_markdown += dispatch_renderer(question_counter, q, points_per_q)

                ans = get_answer_key(q)
                if ans:
                    csv_rows.append([part_idx, question_counter, ans])

                question_counter += 1

        # full_markdown += "---\n\n"

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
