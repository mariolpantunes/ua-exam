import html
import logging
import re

logger = logging.getLogger(__name__)


def count_unescaped(text, char):
    count = 0
    escaped = False
    for c in text:
        if escaped:
            escaped = False
            continue
        if c == "\\":
            escaped = True
            continue
        if c == char:
            count += 1
    return count


def tokenize_block(block):
    block = html.unescape(block)
    tokens = []
    i = 0
    n = len(block)
    escaped = False
    current_text = []

    def flush_text():
        if current_text:
            tokens.append(("TEXT", "".join(current_text)))
            current_text.clear()

    while i < n:
        char = block[i]

        if escaped:
            if char in ["{", "}", "=", "~", "#", "%", ":", "\\"]:
                current_text.append(char)
            else:
                current_text.append("\\")
                current_text.append(char)
            escaped = False
            i += 1
            continue

        if char == "\\":
            escaped = True
            i += 1
            continue

        if char == ":" and i + 1 < n and block[i + 1] == ":":
            flush_text()
            tokens.append(("DBLCOLON", "::"))
            i += 2
            continue

        if char in ["{", "}", "=", "~", "#", "%"]:
            flush_text()
            tokens.append((char, char))
            i += 1
            continue

        current_text.append(char)
        i += 1

    if escaped:
        current_text.append("\\")

    flush_text()
    return tokens


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
        in_brackets += count_unescaped(line, "{") - count_unescaped(line, "}")

        # Check if line starts a new block/directive when not inside brackets
        starts_new_block = in_brackets <= 0 and (
            stripped.startswith("::") or stripped.lower().startswith("$category:")
        )

        if not stripped and in_brackets <= 0:
            if current_block:
                raw_blocks.append("\n".join(current_block))
                current_block = []
        elif starts_new_block:
            if current_block:
                raw_blocks.append("\n".join(current_block))
            current_block = [line]
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

        # 4. TOKENIZE THE BLOCK
        tokens = tokenize_block(block)
        if not tokens:
            continue

        # 5. PARSE THE TOKENS
        idx = 0
        title = "Question"

        # Parse Title ::Title::
        if idx < len(tokens) and tokens[idx][0] == "DBLCOLON":
            idx += 1
            if idx < len(tokens) and tokens[idx][0] == "TEXT":
                title = tokens[idx][1].strip()
                idx += 1
            if idx < len(tokens) and tokens[idx][0] == "DBLCOLON":
                idx += 1

        # Parse Question Stem (Text before LBRACE)
        stem_parts = []
        while idx < len(tokens) and tokens[idx][0] != "{":
            stem_parts.append(tokens[idx][1])
            idx += 1
        question_text = "".join(stem_parts).strip()

        q_type = "unknown"
        options = []
        correct_answer = None

        # Parse Answer Block
        if idx < len(tokens) and tokens[idx][0] == "{":
            idx += 1  # consume '{'

            # Read tokens in answer block
            answer_tokens = []
            brace_depth = 1
            while idx < len(tokens):
                t_type, t_val = tokens[idx]
                if t_type == "{":
                    brace_depth += 1
                elif t_type == "}":
                    brace_depth -= 1
                    if brace_depth == 0:
                        idx += 1  # consume '}'
                        break
                answer_tokens.append(tokens[idx])
                idx += 1

            # Determine type of question
            # A. ESSAY: Empty or only whitespace tokens
            is_empty = True
            for t in answer_tokens:
                if t[0] != "TEXT" or t[1].strip() != "":
                    is_empty = False
                    break

            if is_empty:
                q_type = "essay"
            else:
                # B. TRUE/FALSE
                tf_text = "".join(t[1] for t in answer_tokens).strip().upper()
                m_tf = re.match(r"^(T|TRUE|F|FALSE)(?:#(.*))?$", tf_text)
                if m_tf:
                    q_type = "true_false"
                    correct_answer = m_tf.group(1) in ["T", "TRUE"]
                else:
                    # C. MULTIPLE CHOICE / MULTIPLE RESPONSE
                    has_options = any(t[0] in ["=", "~"] for t in answer_tokens)
                    if has_options:
                        q_type = "multiple_choice"

                        # Group tokens into options
                        options_tokens = []
                        current_opt = []
                        for t in answer_tokens:
                            if t[0] in ["=", "~"]:
                                if current_opt:
                                    options_tokens.append(current_opt)
                                current_opt = [t]
                            else:
                                if current_opt:
                                    current_opt.append(t)
                        if current_opt:
                            options_tokens.append(current_opt)

                        # Parse options
                        for opt_tokens in options_tokens:
                            if not opt_tokens:
                                continue

                            is_correct = opt_tokens[0][0] == "="
                            weight = None
                            idx_opt = 1

                            # Check for weight
                            if idx_opt < len(opt_tokens) and opt_tokens[idx_opt][0] == "%":
                                idx_opt += 1
                                weight_parts = []
                                while idx_opt < len(opt_tokens) and opt_tokens[idx_opt][0] != "%":
                                    weight_parts.append(opt_tokens[idx_opt][1])
                                    idx_opt += 1
                                if idx_opt < len(opt_tokens) and opt_tokens[idx_opt][0] == "%":
                                    idx_opt += 1
                                    try:
                                        weight = float("".join(weight_parts).strip())
                                    except ValueError:
                                        pass

                            if weight is not None:
                                is_correct = weight > 0

                            # Extract option text and feedback
                            text_parts = []
                            feedback_parts = []
                            in_feedback = False
                            while idx_opt < len(opt_tokens):
                                t_type, t_val = opt_tokens[idx_opt]
                                if t_type == "#":
                                    in_feedback = True
                                    idx_opt += 1
                                    continue
                                if in_feedback:
                                    feedback_parts.append(t_val)
                                else:
                                    text_parts.append(t_val)
                                idx_opt += 1

                            opt_text = "".join(text_parts).strip()
                            options.append({"text": opt_text, "is_correct": is_correct})

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
