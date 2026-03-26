"""Extract all text content from Anilam PDFs for reference library."""
import fitz
import os
import json

folder = r"F:\anilam\Anilam crusader m"
output = {}

for f in sorted(os.listdir(folder)):
    if f.lower().endswith(".pdf"):
        path = os.path.join(folder, f)
        doc = fitz.open(path)
        pages_text = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages_text.append(text)
        doc.close()
        if pages_text:
            output[f] = pages_text

    elif f.lower().endswith(".txt"):
        path = os.path.join(folder, f)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            output[f] = [fh.read()]

# Print everything
for filename, pages in output.items():
    print("=" * 80)
    print(f"FILE: {filename}")
    print("=" * 80)
    for i, text in enumerate(pages):
        print(f"\n--- Section {i+1} ---")
        print(text)
    print()
