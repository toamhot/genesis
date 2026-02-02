#!/usr/bin/env python3
"""
Script to convert PowerPoint files to PDF.

This can improve text extraction when uploading to Claude Projects.
Requires LibreOffice to be installed on the system.

Usage:
    python scripts/convert_ppt_to_pdf.py data/documents/
    python scripts/convert_ppt_to_pdf.py path/to/presentation.pptx
"""

import subprocess
import sys
from pathlib import Path


def convert_ppt_to_pdf(input_path: Path, output_dir: Path | None = None) -> Path | None:
    """
    Convert a PowerPoint file to PDF using LibreOffice.

    Args:
        input_path: Path to the .ppt or .pptx file
        output_dir: Output directory (defaults to same as input)

    Returns:
        Path to the created PDF, or None if conversion failed
    """
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return None

    if input_path.suffix.lower() not in [".ppt", ".pptx"]:
        print(f"Skipping non-PowerPoint file: {input_path}")
        return None

    output_dir = output_dir or input_path.parent

    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(input_path),
            ],
            check=True,
            capture_output=True,
        )

        pdf_path = output_dir / f"{input_path.stem}.pdf"
        if pdf_path.exists():
            print(f"Converted: {input_path.name} -> {pdf_path.name}")
            return pdf_path
        else:
            print(f"Error: PDF not created for {input_path}")
            return None

    except FileNotFoundError:
        print("Error: LibreOffice not found. Please install it:")
        print("  Ubuntu/Debian: sudo apt install libreoffice")
        print("  macOS: brew install --cask libreoffice")
        print("  Windows: Download from libreoffice.org")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_path}: {e}")
        return None


def process_directory(directory: Path) -> list[Path]:
    """
    Convert all PowerPoint files in a directory to PDF.

    Args:
        directory: Directory containing PowerPoint files

    Returns:
        List of created PDF paths
    """
    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}")
        return []

    ppt_files = list(directory.glob("*.ppt")) + list(directory.glob("*.pptx"))

    if not ppt_files:
        print(f"No PowerPoint files found in {directory}")
        return []

    print(f"Found {len(ppt_files)} PowerPoint file(s)")

    converted = []
    for ppt_file in ppt_files:
        pdf_path = convert_ppt_to_pdf(ppt_file)
        if pdf_path:
            converted.append(pdf_path)

    print(f"\nConverted {len(converted)}/{len(ppt_files)} files")
    return converted


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_dir():
        process_directory(path)
    else:
        convert_ppt_to_pdf(path)


if __name__ == "__main__":
    main()
