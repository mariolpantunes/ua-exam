import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def check_pandoc_available() -> bool:
    """Checks if pandoc is installed and available in the system PATH."""
    return shutil.which("pandoc") is not None


def compile_pdf(md_path: str, pdf_path: str, pdf_engine: str = "lualatex") -> bool:
    """Compiles a Markdown file into a PDF using pandoc via subprocess.

    Args:
        md_path: Path to the input markdown file.
        pdf_path: Path to the output PDF file.
        pdf_engine: The PDF engine to pass to pandoc (default: lualatex).

    Returns:
        True if compilation succeeded, False otherwise.
    """
    if not check_pandoc_available():
        logger.error("Pandoc is not installed or not found in system PATH. Cannot compile PDF.")
        return False

    cmd = [
        "pandoc",
        md_path,
        "-o",
        pdf_path,
        f"--pdf-engine={pdf_engine}",
    ]

    logger.info(f"Compiling PDF: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully generated PDF: {pdf_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc compilation failed (exit code {e.returncode}):")
        if e.stderr:
            logger.error(e.stderr)
        return False
