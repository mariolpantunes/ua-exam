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


def tokenize(content):
    content = html.unescape(content)
    tokens = []
    i = 0
    n = len(content)
    escaped = False
    current_text = []

    line = 1
    col = 1

    text_start_line = 1
    text_start_col = 1

    def flush_text():
        if current_text:
            tokens.append(("TEXT", "".join(current_text), text_start_line, text_start_col))
            current_text.clear()

    while i < n:
        char = content[i]
        curr_line = line
        curr_col = col

        # Advance line and column trackers
        if char == "\n":
            line += 1
            col = 1
        else:
            col += 1

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
            if not current_text:
                text_start_line = curr_line
                text_start_col = curr_col
            escaped = True
            i += 1
            continue

        if char == "\n":
            flush_text()
            tokens.append(("NEWLINE", "\n", curr_line, curr_col))
            i += 1
            continue

        if char == ":" and i + 1 < n and content[i + 1] == ":":
            flush_text()
            tokens.append(("DBLCOLON", "::", curr_line, curr_col))
            i += 2
            col += 1
            continue

        if char in ["{", "}", "=", "~", "#", "%"]:
            flush_text()
            tokens.append((char, char, curr_line, curr_col))
            i += 1
            continue

        if not current_text:
            text_start_line = curr_line
            text_start_col = curr_col

        current_text.append(char)
        i += 1

    if escaped:
        current_text.append("\\")

    flush_text()
    return tokens


def parse_answer_block(tokens, line, col):
    is_empty = True
    for t_type, t_val, _, _ in tokens:
        if t_type == "NEWLINE":
            continue
        if t_type == "TEXT" and t_val.strip() == "":
            continue
        is_empty = False
        break

    if is_empty:
        return "essay", None, []

    full_text = "".join(t[1] for t in tokens).strip().upper()
    m_tf = re.match(r"^(T|TRUE|F|FALSE)(?:#(.*))?$", full_text, re.DOTALL)
    if m_tf:
        correct_val = m_tf.group(1) in ["T", "TRUE"]
        return "true_false", correct_val, []

    has_options = any(t[0] in ["=", "~"] for t in tokens)
    if has_options:
        options_tokens = []
        current_opt = []
        for t in tokens:
            t_type = t[0]
            if t_type in ["=", "~"]:
                if current_opt:
                    options_tokens.append(current_opt)
                current_opt = [t]
            else:
                if current_opt:
                    current_opt.append(t)
        if current_opt:
            options_tokens.append(current_opt)

        options = []
        for opt in options_tokens:
            if not opt:
                continue

            is_correct = opt[0][0] == "="
            weight = None
            idx_opt = 1

            if idx_opt < len(opt) and opt[idx_opt][0] == "%":
                idx_opt += 1
                weight_parts = []
                while idx_opt < len(opt) and opt[idx_opt][0] != "%":
                    weight_parts.append(opt[idx_opt][1])
                    idx_opt += 1
                if idx_opt < len(opt) and opt[idx_opt][0] == "%":
                    idx_opt += 1
                    try:
                        weight = float("".join(weight_parts).strip())
                    except ValueError:
                        pass

            if weight is not None:
                is_correct = weight > 0

            text_parts = []
            feedback_parts = []
            in_feedback = False

            while idx_opt < len(opt):
                t_type, t_val = opt[idx_opt][0], opt[idx_opt][1]
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

        return "multiple_choice", None, options

    return "essay", None, []


def parse_gift_file(filepath):
    """
    Reads a GIFT file and returns a list of question dictionaries.
    """
    try:
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


def is_blank_line(tokens, start_idx):
    idx = start_idx + 1
    while idx < len(tokens):
        t_type, t_val, _, _ = tokens[idx]
        if t_type == "NEWLINE":
            return True
        elif t_type == "TEXT" and t_val.strip() == "":
            idx += 1
        else:
            return False
    return False


def is_at_start_of_line(tokens, idx):
    i = idx - 1
    while i >= 0:
        t_type, t_val, _, _ = tokens[i]
        if t_type == "NEWLINE":
            return True
        elif t_type == "TEXT":
            if t_val.strip() != "":
                return False
            i -= 1
        else:
            return False
    return True


def parse_gift_content(content, filename="string"):
    # Remove single-line comments
    content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)

    tokens = tokenize(content)

    questions = []
    current_category = filename
    state = "INITIAL"

    # Question builder state variables
    q_title = "Question"
    q_stem_parts = []
    q_post_stem_parts = []
    q_answer_tokens = []
    q_line = 1
    q_col = 1

    idx = 0
    n = len(tokens)

    def add_question(line, col):
        nonlocal q_title, q_stem_parts, q_post_stem_parts, q_answer_tokens
        stem_text = "".join(q_stem_parts).strip()
        post_stem_text = "".join(q_post_stem_parts).strip()

        question_text = stem_text
        if post_stem_text:
            question_text = (stem_text + " " + post_stem_text).strip()

        q_type, correct_answer, options = parse_answer_block(q_answer_tokens, line, col)

        questions.append(
            {
                "category": current_category,
                "title": q_title,
                "text": question_text,
                "type": q_type,
                "options": options,
                "correct": correct_answer,
            }
        )

        # Reset temp vars
        q_title = "Question"
        q_stem_parts.clear()
        q_post_stem_parts.clear()
        q_answer_tokens.clear()

    while idx < n:
        token = tokens[idx]
        t_type, t_val, t_line, t_col = token

        if state == "INITIAL":
            if t_type == "NEWLINE":
                idx += 1
                continue
            elif t_type == "DBLCOLON":
                q_line, q_col = t_line, t_col
                state = "TITLE"
                idx += 1
                continue
            elif t_type == "TEXT":
                trimmed = t_val.strip()
                if not trimmed:
                    idx += 1
                    continue
                match = re.match(r"^\$CATEGORY:\s*(.*)", trimmed, re.IGNORECASE)
                if match:
                    current_category = match.group(1).strip()
                    idx += 1
                    continue
                # Start stem
                q_line, q_col = t_line, t_col
                q_stem_parts.append(t_val)
                state = "STEM"
                idx += 1
                continue
            elif t_type == "{":
                q_line, q_col = t_line, t_col
                state = "ANSWER"
                idx += 1
                continue
            elif t_type in ["=", "~", "#"]:
                if is_at_start_of_line(tokens, idx):
                    raise ValueError(
                        f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' at start of line outside answer block."
                    )
                q_line, q_col = t_line, t_col
                q_stem_parts.append(t_val)
                state = "STEM"
                idx += 1
                continue
            elif t_type == "%":
                q_line, q_col = t_line, t_col
                q_stem_parts.append(t_val)
                state = "STEM"
                idx += 1
                continue
            else:
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' outside answer block."
                )

        elif state == "TITLE":
            if t_type == "TEXT":
                q_title = t_val.strip()
                idx += 1
                continue
            elif t_type == "DBLCOLON":
                state = "STEM"
                idx += 1
                continue
            elif t_type in ["=", "~", "#", "%"]:
                q_title += t_val
                idx += 1
                continue
            elif t_type == "NEWLINE":
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Title cannot span multiple lines."
                )
            else:
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Title must be followed by ::."
                )

        elif state == "STEM":
            if t_type == "{":
                state = "ANSWER"
                idx += 1
                continue
            elif t_type in ["TEXT", "NEWLINE", "DBLCOLON"]:
                # Check if we are starting a new question/directive without closing the current one
                if t_type == "DBLCOLON":
                    raise ValueError(
                        f"Line {t_line}, Col {t_col}: Question must have an answer block."
                    )
                if t_type == "TEXT":
                    trimmed = t_val.strip()
                    if trimmed.lower().startswith("$category:"):
                        raise ValueError(
                            f"Line {t_line}, Col {t_col}: Question must have an answer block."
                        )
                q_stem_parts.append(t_val)
                idx += 1
                continue
            elif t_type in ["=", "~", "#"]:
                if is_at_start_of_line(tokens, idx):
                    raise ValueError(
                        f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' at start of line outside answer block."
                    )
                q_stem_parts.append(t_val)
                idx += 1
                continue
            elif t_type == "%":
                q_stem_parts.append(t_val)
                idx += 1
                continue
            else:
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' outside answer block."
                )

        elif state == "ANSWER":
            if t_type == "}":
                state = "POST_ANSWER"
                idx += 1
                continue
            elif t_type == "{":
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Unescaped '{t_val}' inside answer block."
                )
            q_answer_tokens.append(token)
            idx += 1
            continue

        elif state == "POST_ANSWER":
            # Check for block separation boundary
            if t_type == "NEWLINE":
                if is_blank_line(tokens, idx):
                    add_question(q_line, q_col)
                    state = "INITIAL"
                    # Skip to second newline
                    idx += 1
                    while idx < n:
                        if tokens[idx][0] == "NEWLINE":
                            break
                        idx += 1
                    idx += 1
                    continue
                else:
                    q_post_stem_parts.append(t_val)
                    idx += 1
                    continue
            elif t_type == "DBLCOLON":
                add_question(q_line, q_col)
                q_line, q_col = t_line, t_col
                state = "TITLE"
                idx += 1
                continue
            elif t_type == "TEXT":
                trimmed = t_val.strip()
                if trimmed.lower().startswith("$category:"):
                    add_question(q_line, q_col)
                    state = "INITIAL"
                    # Let the INITIAL state handle this token
                    continue
                q_post_stem_parts.append(t_val)
                idx += 1
                continue
            elif t_type == "{":
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Multiple answer blocks in a single question are not allowed."
                )
            elif t_type in ["=", "~", "#"]:
                if is_at_start_of_line(tokens, idx):
                    raise ValueError(
                        f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' at start of line outside answer block."
                    )
                q_post_stem_parts.append(t_val)
                idx += 1
                continue
            elif t_type == "%":
                q_post_stem_parts.append(t_val)
                idx += 1
                continue
            else:
                raise ValueError(
                    f"Line {t_line}, Col {t_col}: Unescaped control character '{t_val}' outside answer block."
                )

    # End of tokens loop
    if state == "ANSWER":
        raise ValueError(
            f"Line {q_line}, Col {q_col}: Missing closing brace '}}' at end of file."
        )
    elif state == "STEM":
        raise ValueError(
            f"Line {q_line}, Col {q_col}: Question must have an answer block."
        )
    elif state == "TITLE":
        raise ValueError(
            f"Line {q_line}, Col {q_col}: Title must be followed by ::."
        )
    elif state == "POST_ANSWER":
        add_question(q_line, q_col)

    return questions
