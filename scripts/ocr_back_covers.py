#!/usr/bin/env python3
"""
OCR back cover images and update markdown content files.

For each book markdown file in src/content/books/:
1. Find the corresponding back cover image in public/images/books/<slug>/back.*
2. Run tesseract OCR on it (with preprocessing for better results)
3. Clean up the OCR output
4. Write the cleaned text as the body of the markdown file (after the frontmatter)

Only processes English-language books (tesseract only has 'eng' installed).
Non-English books are skipped with a note.
"""

import os
import re
import glob
import subprocess
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

PROJECT_ROOT = Path("/Users/eivind/Documents/Sevashram/JagannathPublications")
CONTENT_DIR = PROJECT_ROOT / "src" / "content" / "books"
IMAGES_DIR = PROJECT_ROOT / "public" / "images" / "books"
TESSERACT = "/opt/homebrew/bin/tesseract"


def get_language(frontmatter: str) -> str:
    """Extract language from frontmatter."""
    m = re.search(r'language:\s*"([^"]+)"', frontmatter)
    return m.group(1) if m else "Unknown"


def find_back_image(slug: str) -> str | None:
    """Find back cover image for a book slug."""
    img_dir = IMAGES_DIR / slug
    if not img_dir.exists():
        return None
    for ext in ["jpg", "jpeg", "webp", "png"]:
        candidate = img_dir / f"back.{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def preprocess_image(image_path: str) -> str:
    """
    Preprocess image for better OCR results.
    Returns path to preprocessed temp file.
    """
    if not HAS_PILLOW:
        return image_path

    img = Image.open(image_path)

    # Convert to grayscale
    img = img.convert("L")

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Increase size for better OCR (if small)
    w, h = img.size
    if w < 1500:
        scale = 1500 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Save to temp file as PNG (lossless, good for OCR)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    return tmp.name


def run_tesseract(image_path: str) -> str:
    """Run tesseract on an image and return the text."""
    # Preprocess
    processed_path = preprocess_image(image_path)

    try:
        result = subprocess.run(
            [TESSERACT, processed_path, "-", "-l", "eng", "--psm", "6"],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout
    finally:
        # Clean up temp file if we created one
        if processed_path != image_path and os.path.exists(processed_path):
            os.unlink(processed_path)

    return text


def clean_ocr_text(raw: str) -> str:
    """Clean up OCR output text."""
    text = raw

    # Remove form feed characters
    text = text.replace("\f", "")

    # Fix common OCR errors
    text = text.replace("|", "I")  # pipe -> I (common OCR mistake)

    # Normalize whitespace: collapse multiple spaces to one
    text = re.sub(r"[ \t]+", " ", text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]

    # Remove excessive blank lines (keep max 1)
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if line == "":
            if not prev_blank:
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    # Strip leading and trailing blank lines
    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    text = "\n".join(cleaned_lines)

    # Remove lines that are just noise (single chars, only punctuation/symbols)
    lines = text.split("\n")
    filtered = []
    for line in lines:
        # Skip lines that are just 1-2 non-alpha characters
        stripped = re.sub(r"[^a-zA-Z]", "", line)
        if len(line) > 0 and len(stripped) == 0 and len(line) < 5:
            continue
        filtered.append(line)
    text = "\n".join(filtered)

    return text.strip()


def parse_markdown(content: str) -> tuple[str, str]:
    """
    Parse markdown file into frontmatter and body.
    Returns (frontmatter_block, body).
    frontmatter_block includes the --- delimiters.
    """
    # Match frontmatter between --- markers
    match = re.match(r"(---\n.*?\n---)\s*(.*)", content, re.DOTALL)
    if match:
        return match.group(1), match.group(2).strip()
    return content, ""


def main():
    md_files = sorted(CONTENT_DIR.glob("*.md"))

    updated = 0
    skipped_no_image = 0
    skipped_non_english = 0
    skipped_empty_ocr = 0
    skipped_has_body = 0
    errors = 0

    print(f"Found {len(md_files)} markdown files\n")

    for md_file in md_files:
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        frontmatter_block, existing_body = parse_markdown(content)
        language = get_language(frontmatter_block)

        # Skip non-English books
        if language != "English":
            print(f"  SKIP (non-English: {language}): {slug}")
            skipped_non_english += 1
            continue

        # Find back cover image
        image_path = find_back_image(slug)
        if not image_path:
            print(f"  SKIP (no back image): {slug}")
            skipped_no_image += 1
            continue

        # Skip if body already has substantial content
        if existing_body and len(existing_body) > 50:
            print(f"  SKIP (already has body): {slug}")
            skipped_has_body += 1
            continue

        # Run OCR
        try:
            raw_text = run_tesseract(image_path)
            cleaned = clean_ocr_text(raw_text)
        except Exception as e:
            print(f"  ERROR ({e}): {slug}")
            errors += 1
            continue

        if not cleaned or len(cleaned) < 10:
            print(f"  SKIP (OCR returned too little text): {slug}")
            skipped_empty_ocr += 1
            continue

        # Write updated markdown
        new_content = frontmatter_block + "\n\n" + cleaned + "\n"
        md_file.write_text(new_content, encoding="utf-8")
        print(f"  OK: {slug} ({len(cleaned)} chars)")
        updated += 1

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Updated:            {updated}")
    print(f"  Skipped (non-English): {skipped_non_english}")
    print(f"  Skipped (no image):    {skipped_no_image}")
    print(f"  Skipped (empty OCR):   {skipped_empty_ocr}")
    print(f"  Skipped (has body):    {skipped_has_body}")
    print(f"  Errors:                {errors}")
    print(f"  Total:                 {len(md_files)}")


if __name__ == "__main__":
    main()
