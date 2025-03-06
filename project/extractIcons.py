import os
import fitz  # PyMuPDF
import json
import re

ICON_OUTPUT_DIR = "./icons"


def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)


def is_icon_candidate(char: str, font_name: str, font_size: float) -> bool:
    if "symb" in font_name.lower() or "icon" in font_name.lower():
        return True
    cp = ord(char)
    if 0xE000 <= cp <= 0xF8FF:
        return True
    if char.isalnum() or char.isspace() or char in ".,!?()[]{}:;\"'–-_=+…":
        return False
    if font_size > 10:
        return True
    return False


def extract_and_map_icons(pdf_path: str, icon_mapping: dict) -> None:
    doc = fitz.open(pdf_path)
    zoom = 3.0
    matrix = fitz.Matrix(zoom, zoom)

    for page_index, page in enumerate(doc):
        text_dict = page.get_text("rawdict")

        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_name = span["font"]
                        font_size = span["size"]

                        for char in span["chars"]:
                            c = char["c"]
                            bbox = fitz.Rect(char["bbox"])

                            if is_icon_candidate(c, font_name, font_size):
                                key = f"{c}||{font_name}"
                                if key not in icon_mapping:
                                    clip_rect = bbox
                                    pix = page.get_pixmap(matrix=matrix, clip=clip_rect)

                                    safe_char = sanitize_filename(c)
                                    safe_font = sanitize_filename(font_name)
                                    filename = f"icon_{safe_char}_{safe_font}_{page_index}.png"
                                    out_path = os.path.join(ICON_OUTPUT_DIR, filename)
                                    pix.save(out_path)

                                    icon_mapping[key] = {
                                        "glyph": c,
                                        "font": font_name,
                                        "image": filename,
                                    }


def main():
    pdf_files = [
        "./pdfs/mercedes-eqs-sedan-manual_1.pdf",
        "./pdfs/mercedes-eqs-sedan-manual_2.pdf",
        "./pdfs/mercedes-eqs-sedan-manual_3.pdf",
        "./pdfs/mercedes-eqs-sedan-manual_4.pdf",
        "./pdfs/mercedes-eqs-sedan-manual_5.pdf",
    ]

    os.makedirs(ICON_OUTPUT_DIR, exist_ok=True)
    icon_mapping = {}

    for pdf in pdf_files:
        extract_and_map_icons(pdf, icon_mapping)

    with open("icon_mapping.json", "w", encoding="utf-8") as f:
        json.dump(icon_mapping, f, ensure_ascii=False, indent=4)

    print("아이콘 매핑이 완료되었습니다.")
    print("icon_mapping.json 및 ./icons 폴더를 확인하세요.")


if __name__ == "__main__":
    main()
