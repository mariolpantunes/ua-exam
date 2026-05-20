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
    # Robust splitting: We look for blocks separated by blank lines,
    # but we must be careful not to split inside { ... }
    raw_blocks = []
    current_block = []
    in_brackets = 0

    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()

        # Count brackets to avoid splitting inside them
        in_brackets += line.count("{") - line.count("}")

        if not stripped and in_brackets <= 0:
            if current_block:
                raw_blocks.append("\n".join(current_block))
                current_block = []
        else:
            current_block.append(line)

    if current_block:
        raw_blocks.append("\n".join(current_block))

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # 3. CHECK FOR $CATEGORY DIRECTIVE
        cat_match = re.match(r"^\$CATEGORY:\s*(.*)", block, re.IGNORECASE)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        # 4. EXTRACT TITLE ::Title::
        title = "Question"
        title_match = re.match(r"^\s*::(.*?)::", block, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            block = block[title_match.end() :].strip()

        # 5. FIND ANSWER BLOCK { ... }
        # Capture the LAST occurrence of a { block }
        answer_match = list(re.finditer(r"\{([^{]*?)\}", block, re.DOTALL))

        if not answer_match:
            continue

        target_match = answer_match[-1]
        answer_content = target_match.group(1).strip()
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

        # C. MULTIPLE CHOICE / MULTIPLE RESPONSE
        elif "=" in answer_content or "~" in answer_content:
            q_type = "multiple_choice"
            # Split by = or ~ but only if they are at the start of a line or preceded by whitespace
            # This prevents splitting inside math formulas like $E=mc^2$
            parts = re.split(r"(?m)(?=[=~])", answer_content)
            
            # Re-join parts that don't actually start an option (not start of block and not preceded by space)
            # Actually, GIFT options are usually one per line or separated by space.
            # A better way is to look for delimiters that are NOT inside $...$ or `...`
            # but for simplicity, we'll look for delimiters at the start of a line or after whitespace.
            
            refined_parts = []
            for p in parts:
                if not p: continue
                if p.startswith("=") or p.startswith("~"):
                    refined_parts.append(p)
                else:
                    if refined_parts:
                        refined_parts[-1] += p
                    else:
                        refined_parts.append(p)
            
            for p in refined_parts:
                p = p.strip()
                if not p:
                    continue
                
                # Check for weights like ~%50% or ~%-50%
                weight_match = re.match(r"^[=~]%(-?\d+\.?\d*)%(.*)", p)
                
                if weight_match:
                    weight = float(weight_match.group(1))
                    txt = weight_match.group(2).strip()
                    # In GIFT, a positive weight is considered "correct" for multiple response
                    is_correct = weight > 0
                else:
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
                "category": current_category,
                "title": title,
                "text": question_text,
                "type": q_type,
                "options": options,
                "correct": correct_answer,
            }
        )

    return questions
