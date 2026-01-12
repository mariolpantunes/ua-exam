# ua-exam: Moodle to Paper Exam Generator

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Pandoc Required](https://img.shields.io/badge/dependency-Pandoc-maroon)
![LaTeX Required](https://img.shields.io/badge/dependency-LaTeX-lightgrey)
![Maintenance](https://img.shields.io/badge/maintained-yes-brightgreen)

**ua-exam** is a Python CLI tool designed to automate the creation of physical paper exams from Moodle question banks (GIFT format). It allows instructors to define exam structures via a JSON configuration file, randomly select questions from specific topics, and generate a professional-grade LaTeX/Markdown document ready for PDF conversion.

## Key Features

* **GIFT Parsing:** Natively reads standard Moodle `.gift` files (Multiple Choice, True/False, and Open Answer/Essay).
* **Flexible Configuration:** Define exam sections, duration, instructions, and scoring logic via a simple JSON file.
* **Questions Randomization:** Randomly selects questions from specified topics/files. Supports a **seed** argument for reproducible exams.
* **Automatic Solutions:** Generates a companion CSV file (`_solutions.csv`) with the answer key for objective questions.
* **Professional Layout:** Outputs clean Markdown designed for Pandoc + LaTeX, including university branding and structured student identification fields.

## Project Structure

Ensure your directory looks like this before running the tool:

```text
.
├── ua-exam.py           # Main script
├── gift_parser.py       # GIFT parsing logic module
├── config.json          # Exam configuration
├── logo/
│   └── logo_ua_cropped.pdf  # University logo (required for header)
```

## Configuration (`config.json`)

The exam logic is controlled entirely by a JSON file.

* **`questions_folder`**: Directory where your `.gift` files are stored.
* **`parts`**: Defines the sections of the exam.
* **`topic`**: Corresponds to the filename of the GIFT file (without extension). E.g., `"topic": "t1_test"` looks for `gift/t1_test.gift`.

**Example Configuration:**

```json
{
  "class": "Introdução Engenharia Informática",
  "date": "January 13, 2026",
  "questions_folder": "gift",
  "duration": "60 minutes",
  "instructions": "Please answer all questions. Read the instructions for each section carefully.",
  "parts": [
    {
      "part": "Multiple Choice",
      "classification": 10,
      "questions": [
        { "topic": "t1_test", "quantity": 2 },
        { "topic": "t2_test", "quantity": 4 },
        { "topic": "t3_test", "quantity": 2 }
      ]
    },
    {
      "part": "Open Answer",
      "classification": 10,
      "questions": [
        { "topic": "general_test", "quantity": 5 }
      ]
    }
  ]
}

```

## Requirements

* **Python 3.8+**
* **Pandoc** (for PDF conversion)
* **LaTeX Distribution** (TeX Live, MiKTeX, or MacTeX)
* Must include `lualatex` or `xelatex` engine.

## Usage

### 1. Generate the Exam (Markdown & CSV)

Run the script passing your configuration file. You can optionally set a seed for reproducibility.

```bash
# Basic usage
python3 ua-exam.py -c config.json

# With a specific output filename and random seed
python3 ua-exam.py -c config.json -s 12345 -o final_exam.md
```

**Outputs:**

1. `final_exam.md`: The exam content in Markdown.
2. `final_exam_solutions.csv`: A CSV file containing the Answer Key (Part #, Question ID, Correct Option) for Multiple Choice and True/False questions.

### 2. Convert to PDF

Use Pandoc to compile the Markdown into a PDF.

```bash
pandoc final_exam.md -o final_exam.pdf --pdf-engine=lualatex

```

*If `lualatex` is not available, you can try `--pdf-engine=xelatex`.*

## Authors

* **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
