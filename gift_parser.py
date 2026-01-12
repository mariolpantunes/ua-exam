import logging
import re

logger = logging.getLogger(__name__)


def parse_gift_file(filepath):
    """
    Reads a GIFT file and returns a list of question dictionaries.
    """
    try:
        # Try reading with utf-8-sig to handle Windows BOM automatically
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
        return parse_gift_content(content, filepath)
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="cp1252") as f:
                content = f.read()
            return parse_gift_content(content, filepath)
        except Exception as e:
            logger.error(f"Encoding error reading {filepath}: {e}")
            return []
    except Exception as e:
        logger.error(f"Failed to read file {filepath}: {e}")
        return []


def parse_gift_content(content, filename="string"):
    questions = []
    current_category = filename  # Default to filename if no $CATEGORY is found

    # 1. CLEANUP
    # Remove single-line comments // ...
    content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)

    # 2. SPLIT INTO BLOCKS
    # GIFT separates questions (and directives) with at least one blank line.
    raw_blocks = re.split(r"\n\s*\n", content)

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # 3. CHECK FOR $CATEGORY DIRECTIVE
        # Pattern: $CATEGORY: category/name
        cat_match = re.match(r"^\$CATEGORY:\s*(.*)", block, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).strip()
            # This block is a directive, not a question, so we skip to the next
            continue

        # 4. EXTRACT TITLE ::Title::
        # Titles are optional and at the start.
        title = "Question"
        # Non-greedy match for title at start of string
        # We strip it so it doesn't appear in the question text
        title_match = re.match(r"^\s*::(.*?)::", block, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            # Remove title from block to get the rest
            block = block[title_match.end() :].strip()

        # 5. FIND ANSWER BLOCK { ... }
        # Capture the LAST occurrence of a { block }
        answer_match = list(re.finditer(r"\{([^{]*?)\}", block))

        if not answer_match:
            continue

        target_match = answer_match[-1]
        answer_content = target_match.group(1).strip()

        # The text is everything *before* this answer block
        question_text = block[: target_match.start()].strip()

        # 6. DETERMINE TYPE
        q_type = "unknown"
        options = []
        correct_answer = None

        # A. ESSAY: Empty bracket {}
        if answer_content == "":
            q_type = "essay"

        # B. TRUE/FALSE: {T} {F} {TRUE} {FALSE}
        elif re.match(r"^(T|TRUE|F|FALSE|#T|#F)$", answer_content, re.IGNORECASE):
            q_type = "true_false"
            clean_ans = answer_content.upper().replace("#", "")
            is_true = clean_ans in ["T", "TRUE"]
            correct_answer = is_true

        # C. MULTIPLE CHOICE
        elif "=" in answer_content or "~" in answer_content:
            q_type = "multiple_choice"
            parts = re.split(r"(?=[=~])", answer_content)

            for p in parts:
                p = p.strip()
                if not p:
                    continue
                is_correct = p.startswith("=")
                txt = p[1:].strip()

                if "#" in txt:
                    txt = txt.split("#", 1)[0].strip()

                options.append({"text": txt, "is_correct": is_correct})

        # D. FALLBACK
        if q_type == "unknown":
            q_type = "essay"

        questions.append(
            {
                "category": current_category,  # Storing the category
                "title": title,
                "text": question_text,
                "type": q_type,
                "options": options,
                "correct": correct_answer,
            }
        )

    return questions
