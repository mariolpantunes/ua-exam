# <img src="assets/logo.svg" alt="logo" width="128" height="128" align="middle"> ua-exam

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)](https://mariolpantunes.github.io/ua-exam)
[![License](https://img.shields.io/badge/license-MIT-green)](https://mariolpantunes.github.io/ua-exam)
[![Pandoc Required](https://img.shields.io/badge/dependency-Pandoc-maroon)](https://mariolpantunes.github.io/ua-exam)
[![LaTeX Required](https://img.shields.io/badge/dependency-LaTeX-lightgrey)](https://mariolpantunes.github.io/ua-exam)

**ua-exam** is a Python CLI tool designed to automate the creation of physical paper exams from Moodle question banks (GIFT format). It allows instructors to define complex exam structures via a JSON configuration, randomly select questions from hierarchical categories, generate professional LaTeX-ready documents, and support multiple randomized exam copies.

Detailed documentation is available on the [GitHub Pages](https://mariolpantunes.github.io/ua-exam).

## Key Features

* **Advanced GIFT Parsing:**
    * Support for `.gift` and `.txt` files.
    * Handles Multiple Choice, True/False, and Open Answer (Essay).
    * Support for Multiple Response (partial credits) with multi-answer solution keys.
    * Robust handling of questions containing internal blank lines and complex formatting.
* **Hierarchical Question Bank:**
    * Recursive scanning of questions folders.
    * Automatic indexing by the GIFT `$CATEGORY` directive.
    * Flexible category matching using a global `category_prefix`.
* **Smart Randomization & Deduplication:**
    * Option Shuffling: Choices are randomized for every question to ensure variety.
    * Global Deduplication: Prevents the same question from appearing twice in the same exam.
    * Reproducibility: Use the seed flag to generate the exact same exam order.
* **Multiple Exam Versions (Copies):**
    * Automatically generate multiple randomized copies of the same exam structure (e.g. Version A, Version B) with sequential seeds.
* **Professional LaTeX Layout:**
    * Native support for LaTeX Math ($...$) and Code Blocks (`code`).
    * Automated university branding (Logo and Header).
    * Pre-configured identifying fields (Name, Number, Classification).
    * Solutions generated as a CSV file, perfectly mapped to the shuffled choices.
* **Modular Question Conversion:**
    * Extensible converter registry to transform GIFT files into other Moodle or LMS formats.

## Project Structure

```text
.
├── src/
│   └── ua_exam/
│       ├── __init__.py         # Package initialization
│       ├── cli.py              # CLI entry point
│       ├── exam_generator.py   # Exam generation engine
│       ├── gift_parser.py      # GIFT parsing module
│       ├── gift_escaper.py     # GIFT escaping/markdown translation module
│       ├── pdf_renderer.py     # PDF compilation module
│       ├── converters/         # Modular question format converters
│       └── assets/
│           └── logo_ua_cropped.pdf  # Packaged default university logo
├── test/                       # Test suite
├── examples/                   # Configuration examples
└── assets/
    └── logo.svg                # Project logo
```

## Installation

Install directly from source or via PyPI using pip or uv:

```bash
pip install .
```

## Usage

The `ua-exam` command-line tool provides three primary subcommands: `generate`, `escape`, and `convert`.

### 1. Generating Exams (`generate`)

Generates randomized exam copies from a JSON configuration file.

```bash
ua-exam generate -c config.json -s 42 -o out/exam.md --pdf
```

* `-c`, `--config`: Path to the JSON configuration file (required).
* `-s`, `--seed`: Base random seed (default: 42).
* `-o`, `--output`: Base output file path (default: exam.md).
* `--pdf`: Automatically compile the generated Markdown file into a PDF.

#### Configuration (`config.json`)

The config file controls the exam generation logic.

| Field | Description | Default |
| :--- | :--- | :--- |
| `class` | The name of the course or exam. | `"Exam"` |
| `date` | Date string to appear on the header. | Current Date |
| `lang` | Language for fixed labels (`pt` or `en`). | `"pt"` |
| `exam` | Exam type (e.g., "Normal", "Recurso", "Teste 01"). | `"Normal"` |
| `logo` | Path to the university logo PDF. | Packaged Logo |
| `questions_folder` | Root directory of your GIFT/TXT files (used if `questions_folders` is omitted). | `"."` |
| `questions_folders`| Alternative array of question source folders. Each element can be a string path or an object with `path` and `category_prefix`. | Optional |
| `category_prefix` | Common prefix for all categories (used globally with `questions_folder`). | `""` |
| `target_score` | Total expected score for validation. | `20.0` |
| `duration` | Exam duration string. | `"60 minutos"` |
| `instructions` | General instructions for the exam. | (Generic) |
| `copies` | Number of randomized copies of the exam to generate. | `1` |
| `parts` | Array of sections. | Required |

#### Example Configurations

##### Example 1: Single Question Folder
```json
{
  "class": "Laboratórios de Sistemas e Serviços",
  "lang": "pt",
  "exam": "Teste 01",
  "copies": 3,
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

##### Example 2: Multiple Question Folders (with prefixes)
```json
{
  "class": "Laboratórios de Sistemas e Serviços",
  "lang": "en",
  "exam": "Exam",
  "copies": 2,
  "questions_folders": [
    {"path": "gift/test01/en", "category_prefix": "lss/test01/exam"},
    {"path": "gift/test02/en", "category_prefix": "lss/test02/exam"}
  ],
  "parts": [
    {
      "part": "Multiple Choice",
      "classification": 10,
      "questions": [
        { "topic": "01-terminal", "quantity": 2 },
        { "topic": "02-virtualizacao", "quantity": 2 }
      ]
    }
  ]
}
```

### 2. Escaping and Converting MD to GIFT (`escape`)

Converts a formatted Markdown file into a Moodle-compatible GIFT file, handling necessary special character escaping.

```bash
ua-exam escape -i input.md -o output.gift
```

### 3. Modular Question Format Conversion (`convert`)

Converts GIFT question banks to other question formats (e.g. Moodle XML).

```bash
ua-exam convert -i input.gift -f xml -o output.xml
```

## Authors

* **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
