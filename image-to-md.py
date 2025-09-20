from marker.convert import convert_to_markdown
from marker.models import load_all_models  # Tải mô hình một lần

load_all_models()  # Tải mô hình (chạy lần đầu)
markdown_output = convert_to_markdown("ccc.png", output_format="markdown")
print(markdown_output)  # In Markdown ra console
# Lưu vào file: with open("output.md", "w") as f: f.write(markdown_output)