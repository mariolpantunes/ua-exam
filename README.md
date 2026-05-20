# ua-exam: Moodle to Paper Exam Generator

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Pandoc Required](https://img.shields.io/badge/dependency-Pandoc-maroon)
![LaTeX Required](https://img.shields.io/badge/dependency-LaTeX-lightgrey)

**ua-exam** is a Python CLI tool designed to automate the creation of physical paper exams from Moodle question banks (GIFT format). It allows instructors to define complex exam structures via a JSON configuration, randomly select questions from hierarchical categories, and generate professional LaTeX-ready documents.

## Key Features

* **Advanced GIFT Parsing:** 
    * Support for `.gift` and `.txt` files.
    * Handles **Multiple Choice**, **True/False**, and **Open Answer** (Essay).
    * Support for **Multiple Response** (partial credits) with multi-answer solution keys.
    * Robust handling of questions containing internal blank lines and complex formatting.
* **Hierarchical Question Bank:**
    * Recursive scanning of the `questions_folder`.
    * Automatic indexing by the GIFT `$CATEGORY` directive.
    * Flexible category matching using a global `category_prefix`.
* **Smart Randomization & Deduplication:**
    * **Option Shuffling:** Choices are randomized for every question to ensure variety.
    * **Global Deduplication:** Prevents the same question from appearing twice in the same exam.
    * **Reproducibility:** Use the `-s` (seed) flag to generate the exact same exam order.
* **Professional LaTeX Layout:**
    * Native support for **LaTeX Math** (`$...$`) and **Code Blocks** (`` `code` ``).
    * Automated university branding (Logo and Header).
    * Pre-configured identifying fields (Name, Number, Classification).
    * Solutions generated as a CSV file, perfectly mapped to the shuffled choices.

## Project Structure

```text
.
├── ua-exam.py           # Main execution script
├── gift_parser.py       # GIFT parsing module
├── config.json          # Exam configuration file
├── logo/
│   └── logo_ua_cropped.pdf  # University logo for the header
└── gift/                # Question bank directory (scanned recursively)
```

## Configuration (`config.json`)

The `config.json` file controls the exam generation logic.

| Field | Description | Default |
| :--- | :--- | :--- |
| `class` | The name of the course or exam. | `"Exam"` |
| `date` | Date string to appear on the header. | Current Date |
| `lang` | Language for fixed labels (`pt` or `en`). | `"pt"` |
| `exam` | Exam type (e.g., "Normal", "Recurso", "Teste 01"). | `"Normal"` |
| `logo` | Path to the university logo PDF. | `"logo/logo_ua_cropped.pdf"` |
| `questions_folder` | Root directory of your GIFT/TXT files. | `"."` |
| `category_prefix` | Common prefix for all categories. | `""` |
| `target_score` | Total expected score for validation. | `20.0` |
| `duration` | Exam duration string. | `"60 minutos"` |
| `instructions` | General instructions for the exam. | (Generic) |
| `parts` | Array of sections (see example). | Required |

### Example Configuration

```json
{
  "class": "Laboratórios de Sistemas e Serviços",
  "lang": "pt",
  "exam": "Teste 01",
  "category_prefix": "lss/test01/exam",
  "questions_folder": "gift/test01",
  "parts": [
    {
      "part": "Escolha Múltipla",
      "classification": 10,
      "questions": [
        { "topic": "01-terminal", "quantity": 3 },
        { "topic": "02-virtualizacao", "quantity": 4 }
      ]
    },
    {
      "part": "Resposta Aberta",
      "classification": 10,
      "questions": [
        { "topic": "open-questions", "quantity": 4 }
      ]
    }
  ]
}
```

## Usage

### 1. Structure GIFT Files

Questions are selected based on the `$CATEGORY` directive. A single file can contain multiple categories.

```gift
$CATEGORY: lss/test01/exam/01-terminal

::Q1:: What is the command to list files? {
    =ls
    ~dir
    ~list
}
```

### 2. Generate Exam

```bash
python3 ua-exam.py -c config.json -s 42 -o my_exam.md
```

**Outputs:**
* `my_exam.md`: The generated exam.
* `my_exam_solutions.csv`: The randomized answer key.

### 3. Convert to PDF

Use **Pandoc** with the `lualatex` engine for best font and math support:

```bash
pandoc my_exam.md -o my_exam.pdf --pdf-engine=lualatex
```

## Authors

* **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
