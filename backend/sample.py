import fitz

doc = fitz.open("C:/Users/divya/Downloads/Untitled document.pdf")

for page_no, page in enumerate(doc):
    print(f"\n========== PAGE {page_no} ==========")

    data = page.get_text("dict")

    for b_idx, block in enumerate(data["blocks"]):
        print(f"\nBlock {b_idx} | Type: {block['type']} | Lines: {len(block.get('lines', []))}")

        if block["type"] == 0:
            for l_idx, line in enumerate(block["lines"]):
                full_line_text = "".join(span["text"] for span in line["spans"])
                print(f"   Line {l_idx}: {full_line_text}")