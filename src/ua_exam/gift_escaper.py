import os
import re


def parse_md(md_content):
    """
    Parses Markdown content to extract questions, options, and the answer key.
    """
    # 1. Parse Answer Key
    answer_key = {}
    # Look for "## Grelha de Correção" or similar
    key_section_match = re.search(
        r"##\s*(?:Grelha de Correção|Respostas|Soluções)\s*\n(.*?)$", md_content, re.DOTALL | re.IGNORECASE
    )
    if key_section_match:
        key_text = key_section_match.group(1).strip()
        for line in key_text.splitlines():
            # Match "1. B" or "1-B" or "1 B"
            m = re.match(r"(\d+)[.\s-]*([A-E])", line.strip(), re.IGNORECASE)
            if m:
                answer_key[int(m.group(1))] = m.group(2).upper()

    # 2. Parse Category
    category = ""
    cat_match = re.search(r"^#\s+(.*?)$", md_content, re.MULTILINE)
    if cat_match:
        category = cat_match.group(1).strip()

    # 3. Parse Questions
    # Split by question number at the start of a line: "1. "
    q_blocks = re.split(r"\n(?=\d+\.\s+)", "\n" + md_content)

    questions = []
    for block in q_blocks:
        block = block.strip()
        if not block or block.startswith("##") or block.startswith("# "):
            continue

        # Extract question number and text
        # Format: 1. **Question Text** or 1. Question Text
        # We try to match the question text until the first option A)
        m_q = re.match(r"(\d+)\.\s+(?:\*\*)?(.*?)(?:\*\*)?\n(.*)", block, re.DOTALL)
        if not m_q:
            continue

        q_num = int(m_q.group(1))
        q_text = m_q.group(2).strip()
        rest = m_q.group(3).strip()

        # Options
        # Match A) text, B) text ...
        opt_matches = list(re.finditer(r"^([A-E])\)\s+(.*?)(?=\n[A-E]\)\s+|$)", rest, re.MULTILINE | re.DOTALL))

        if not opt_matches:
            opt_matches = list(re.finditer(r"([A-E])\)\s+(.*?)(?=\s+[A-E]\)\s+|$)", rest, re.DOTALL))

        correct_letter = answer_key.get(q_num)

        gift_options = []
        for match in opt_matches:
            letter = match.group(1).upper()
            opt_text = match.group(2).strip()
            is_correct = letter == correct_letter
            gift_options.append((is_correct, opt_text))

        if gift_options:
            questions.append({"num": q_num, "text": q_text, "options": gift_options})

    return category, questions


def escape_gift_naive(text):
    """
    Escapes text for GIFT format using a naive approach.
    Avoids [html] prefix.
    """
    if not text:
        return ""

    # 0. Escape literal angle brackets first (to avoid breaking Moodle)
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # 1. Convert Markdown formatting to basic HTML
    # `code` -> <code>code</code>
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    # **bold** -> <b>bold</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    # 2. MathJax: $...$ -> \\( ... \\)
    # Note: we do this before escaping backslashes to avoid triple-escaping
    text = re.sub(r"(?<!\\)\$(.*?)(?<!\\)\$", r"\\\\(\1\\\\)", text)

    # 3. Escape backslashes (for any other purpose)
    # Actually, we should be careful not to escape the ones we just added.
    # But in GIFT, any \ must be \\ to be seen as \.
    # So if we want \( in Moodle, we need \\( in GIFT.
    # If we had a literal \ in MD, it should be \\ in GIFT.

    # Simplest: escape all literal \ first, then add the MathJax ones?
    # No, let's just do it in one pass or carefully.

    # Let's escape existing backslashes EXCEPT those we just added?
    # Hard. Let's just do it sequentially:
    # A. Replace literal \ with \\
    # B. Replace literal ~ with \~, etc.

    # Restarting sequence:
    text = text.replace("\\", "\\\\")
    for char in ["~", "=", "#", "{", "}", ":"]:
        text = text.replace(char, "\\" + char)

    return text


def convert_md_to_gift(md_path, gift_path):
    with open(md_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    category, questions = parse_md(content)

    if not questions:
        print(f"Warning: No questions found in {md_path}")
        return False

    output = []
    if category:
        output.append(f"$CATEGORY: {category}\n")
    elif md_path:
        # Use filename as category if no title found
        filename = os.path.basename(md_path)
        name_no_ext = os.path.splitext(filename)[0]
        output.append(f"$CATEGORY: {name_no_ext}\n")

    for q in questions:
        title = f"::Q{q['num']}::"
        q_text = escape_gift_naive(q["text"])

        output.append(f"{title} {q_text} {{")
        for is_correct, opt_text in q["options"]:
            symbol = "=" if is_correct else "~"
            opt_text = escape_gift_naive(opt_text)
            output.append(f"    {symbol} {opt_text}")
        output.append("}\n")

    with open(gift_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    return True
