__author__ = "Mário Antunes"
__version__ = "0.1.0"
__email__ = "mario.antunes@ua.pt"
__status__ = "Development"

import argparse
import json
import logging
import os
import sys

from . import converters, exam_generator, gift_escaper, gift_parser

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_generate(args):
    """
    Generate randomized exam versions from config.
    """
    # Read config file
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        return 1

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return 1

    # Generate the exam files
    exam_generator.generate_exams_from_config(
        config=config,
        base_seed=args.seed,
        output_base=args.output,
        compile_pdf_flag=args.pdf,
    )
    return 0


def cmd_escape(args):
    """
    Escape and convert MD to Moodle GIFT format.
    """
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return 1

    logger.info(f"Converting MD: {args.input} -> GIFT: {args.output}")
    try:
        success = gift_escaper.convert_md_to_gift(args.input, args.output)
        if success:
            logger.info("Successfully converted MD to GIFT.")
            return 0
        else:
            logger.error("Failed to convert MD to GIFT.")
            return 1
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        return 1


def cmd_convert(args):
    """
    Convert GIFT questions to other formats.
    """
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return 1

    try:
        converter = converters.get_converter(args.format)
        logger.info(f"Converting {args.input} to format '{args.format}' -> {args.output}")
        success = converter.convert(args.input, args.output)
        if success:
            logger.info(f"Successfully converted to {args.format}.")
            return 0
        else:
            logger.error(f"Conversion to {args.format} failed.")
            return 1
    except ValueError as e:
        logger.error(e)
        return 1
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        return 1


def cmd_verify(args):
    """
    Verify a GIFT file for structure and proper encoding of special characters.
    """
    filepath = args.file

    # Step 1: Read the file with the same encoding attempts as in parse_gift_file
    content = None
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="cp1252") as f:
                content = f.read()
        except Exception as e:
            print(f"Error: Could not read file {filepath} with utf-8-sig or cp1252 encoding: {e}")
            return 1
    except Exception as e:
        print(f"Error: Failed to read file {filepath}: {e}")
        return 1

    if content is None:
        print(f"Error: Could not read file {filepath}")
        return 1

    # Step 2: Check structure by parsing
    try:
        questions = gift_parser.parse_gift_content(content, filepath)
        if not questions and content.strip():
            # If the file is not empty and we got no questions, then structure is bad
            print(f"Error: Failed to parse GIFT file {filepath}. No questions found or invalid format.")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    # Step 3: Check for unescaped < and >
    # Helper function to check for unescaped < or > (not part of an HTML entity)
    def has_unescaped_lt_gt(text):
        import re

        # Pattern for HTML entities: & followed by letters or # and numbers and then ;
        entity_pattern = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);")
        # Split the text by entities, returning the non-entity parts
        non_entity_parts = re.split(entity_pattern, text)
        for part in non_entity_parts:
            if "<" in part or ">" in part:
                return True
        return False

    if has_unescaped_lt_gt(content):
        print(f"Error: File {filepath} contains unescaped '<' or '>' characters. These must be HTML encoded as &lt; and &gt;.")
        return 1

    # If we get here, everything is okay
    print(f"Success: File {filepath} is a valid GIFT file with properly encoded special characters.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="UA Exam Tool: A suite of tools to parse, escape, generate, and convert exams."
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Subcommand: generate
    parser_gen = subparsers.add_parser("generate", help="Generate randomized exam versions from config")
    parser_gen.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to JSON config file",
    )
    parser_gen.add_argument(
        "-s",
        "--seed",
        type=int,
        default=42,
        help="Base random seed for reproducibility",
    )
    parser_gen.add_argument(
        "-o",
        "--output",
        type=str,
        default="exam.md",
        help="Output filename base (default: exam.md)",
    )
    parser_gen.add_argument("--pdf", action="store_true", help="Compile output markdown to PDF via Pandoc")

    # Subcommand: escape
    parser_esc = subparsers.add_parser("escape", help="Escape and convert MD to Moodle GIFT format")
    parser_esc.add_argument("-i", "--input", type=str, required=True, help="Input MD file path")
    parser_esc.add_argument("-o", "--output", type=str, required=True, help="Output GIFT file path")

    # Subcommand: convert
    parser_conv = subparsers.add_parser("convert", help="Convert GIFT questions to other formats")
    parser_conv.add_argument("-i", "--input", type=str, required=True, help="Input file path")
    parser_conv.add_argument(
        "-f",
        "--format",
        type=str,
        required=True,
        help="Destination format name.",
    )
    parser_conv.add_argument("-o", "--output", type=str, required=True, help="Output file path")

    # verify subcommand
    parser_verify = subparsers.add_parser("verify", help="Verify a GIFT file for structure and proper encoding")
    parser_verify.add_argument("file", help="Path to the GIFT file to verify")

    args = parser.parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "escape":
        sys.exit(cmd_escape(args))
    elif args.command == "convert":
        sys.exit(cmd_convert(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
