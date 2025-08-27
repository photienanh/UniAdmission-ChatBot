import json
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator

# Load dữ liệu từ Selenium crawler
try:
    with open("data/uni_data.json", 'r', encoding='utf-8') as file:
        data = json.loads(file.read())
except FileNotFoundError:
    print("File uni_data.json không tồn tại. Hãy chạy selenium_crawler.py trước.")
    exit(1)

FORMAT = """
Tên trường: {name}
Mã trường: {universityCode}
Tên viết tắt: {acronym}
Loại hình: {type}
Địa chỉ: {address}
Số điện thoại: {phone}
Website: {website}
Tỉnh thành: {city}

HỌC PHÍ:
{fee}

NGÀNH ĐÀO TẠO VÀ ĐIỂM CHUẨN:
{majors}

THÔNG TIN TUYỂN SINH:

Phương thức xét tuyển:
{method}

Hồ sơ xét tuyển:
{profile}

Đối tượng tuyển sinh:
{target}

Phạm vi tuyển sinh:
{region}

Các ngành tuyển sinh:
{admission_majors}
"""

generator = DefaultMarkdownGenerator(
    content_filter=None,
    options={
        "ignore_links": False,
        "escape_html": True,
        "ignore_images": False,
        "skip_internal_links": False,
        "include_sup_sub": False,
    }
)

def split_fee_content(fee_content: str):
    """Tách nội dung học phí và thông tin ngành tuyển sinh"""
    if not fee_content:
        return "", ""
    
    # Tìm điểm tách dựa trên "## **II. Các ngành tuyển sinh**" hoặc tương tự
    split_markers = [
        "### **II. Các ngành tuyển sinh**",
        "## **II. Các ngành tuyển sinh**", 
        "# **II. Các ngành tuyển sinh**",
        "**II. Các ngành tuyển sinh**",
        "II. Các ngành tuyển sinh"
    ]
    
    for marker in split_markers:
        if marker in fee_content:
            parts = fee_content.split(marker, 1)
            fee_only = parts[0].strip()
            admission_majors = marker + parts[1].strip() if len(parts) > 1 else ""
            return fee_only, admission_majors
    
    # Nếu không tìm thấy marker, trả về toàn bộ nội dung cho fee
    return fee_content, ""

def parser(html: str, url: str = "") -> str:
    if not html or html.strip() == "":
        return ""
    try:
        parsed: MarkdownGenerationResult = generator.generate_markdown(
            input_html=html,
            base_url=url
        )
        text: str = parsed.raw_markdown #type:ignore
        return text
    except:
        return html  # Trả về HTML gốc nếu không parse được

def process_single(data: dict):
    extracted_data: dict = {}
    
    # Thông tin cơ bản
    extracted_data["name"] = data.get("name", "")
    extracted_data["universityCode"] = data.get("universityCode", "")
    extracted_data["acronym"] = data.get("acronym", "")
    extracted_data["type"] = data.get("type", "")
    extracted_data["address"] = data.get("address", "")
    extracted_data["phone"] = data.get("phone", "")
    extracted_data["website"] = data.get("website", "")
    extracted_data["city"] = ", ".join(data.get("city", []))
    
    # Tạo bảng điểm chuẩn
    years = [str(2025), str(2024), str(2023), str(2022), str(2021), str(2020)]
    major_header = ["**Mã ngành**", "**Tên ngành**", *[f"**{y}**" for y in years]]
    major_lines = [" | "+ " | ".join(major_header) + " | "]
    major_lines.append(" | " + "|".join("-" for _ in major_header) + " | ")
    
    for major_info in data.get("universityMajors", []):
        major_line = [major_info.get("code", ""), major_info.get("name", "")]
        for year in years:
            score = major_info.get("scores", {}).get(year, "-")
            major_line.append(str(score) if score != "-" else "-")
        major_lines.append("| " + " | ".join(major_line) + " |")
    
    extracted_data["majors"] = "\n".join(major_lines) if len(major_lines) > 2 else "Chưa có thông tin điểm chuẩn"
    
    # Parse thông tin tuyển sinh từ HTML sang Markdown
    extracted_data["method"] = parser(data.get("method", ""))
    extracted_data["profile"] = parser(data.get("profile", ""))
    extracted_data["target"] = parser(data.get("target", ""))
    extracted_data["region"] = parser(data.get("region", ""))
    
    # Xử lý riêng phần fee để tách học phí và thông tin ngành tuyển sinh
    fee_raw = parser(data.get("fee", ""))
    
    # Chỉ tách khi có marker "II. Các ngành tuyển sinh"
    has_admission_section = any(marker in fee_raw for marker in [
        "### **II. Các ngành tuyển sinh**",
        "## **II. Các ngành tuyển sinh**", 
        "# **II. Các ngành tuyển sinh**",
        "**II. Các ngành tuyển sinh**",
        "II. Các ngành tuyển sinh"
    ])
    
    if has_admission_section:
        fee_only, admission_majors = split_fee_content(fee_raw)
        extracted_data["fee"] = fee_only
        extracted_data["admission_majors"] = admission_majors
    else:
        # Không tách, để nguyên toàn bộ nội dung cho học phí
        extracted_data["fee"] = fee_raw
        extracted_data["admission_majors"] = ""
    
    return extracted_data, FORMAT.format(**extracted_data)

def main():
    all_data: list[dict] = []
    import os
    os.makedirs("data/output", exist_ok=True)
    
    print(f"Đang xử lý {len(data)} trường đại học...")
    
    for i, item in enumerate(data):
        try:
            university_code = item.get('universityCode', f'UNI_{i}')
            print(f"Xử lý {i+1}/{len(data)}: {item.get('name', 'Unknown')} ({university_code})")
            
            item_data, text = process_single(item)
            
            # Lưu file markdown cho từng trường
            with open(f"data/output/{university_code}.md", 'w', encoding='utf-8') as file:
                file.write(text)
            
            all_data.append(item_data)
            
        except Exception as e:
            print(f"Lỗi khi xử lý trường {item.get('name', 'Unknown')}: {e}")
            continue
    
    # Lưu tất cả dữ liệu đã format
    with open(f"data/all_uni_formatted.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(all_data, ensure_ascii=False, indent=2))
    
    print(f"Đã xử lý {len(all_data)} trường")
    print(f"File markdown đã được tạo trong thư mục data/output/")
    print(f"Dữ liệu tổng hợp: data/all_uni_formatted.json")
    
if __name__ == "__main__":
    main()
