import json
import os

def check_data_files():
    """Kiểm tra các file dữ liệu có sẵn"""
    files_to_check = ['data/uni_data.json']
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f'File: {file_path}')
            print(f'Số trường: {len(data)}')
            
            # Kiểm tra cấu trúc dữ liệu
            if data:
                first_item = data[0]
                print(f'Keys: {list(first_item.keys())}')
                name = first_item.get("name", "N/A")
                code = first_item.get("universityCode", "N/A") 
                acronym = first_item.get("acronym", "N/A")
                print(f'Sample: {name} - {code} - {acronym}')
            print('-' * 50)
        else:
            print(f'File không tồn tại: {file_path}')

def create_university_mapping():
    """Tạo file university_mapping.json từ dữ liệu crawler"""
    
    # Tìm file dữ liệu tốt nhất
    data_file = None
    for file_path in ['data/uni_data.json']:
        if os.path.exists(file_path):
            data_file = file_path
            break
    
    if not data_file:
        print("Không tìm thấy file dữ liệu nào!")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mapping = {}
    
    for item in data:
        university_code = item.get('universityCode', '').strip()
        acronym = item.get('acronym', '').strip()
        name = item.get('name', '').strip()
        
        if university_code:
            # Nếu có acronym riêng (khác mã trường) thì dùng, không thì để null
            display_name = acronym if acronym and acronym != university_code else None
            
            mapping[university_code] = {
                "name": name,
                "acronym": display_name
            }
    
    # Sắp xếp theo mã trường
    sorted_mapping = dict(sorted(mapping.items()))
    
    # Lưu vào file university_mapping.json
    output_path = "../university_mapping.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)
    
    print(f"Đã tạo file {output_path}")
    print(f"Tổng số trường {len(sorted_mapping)}")
    
    # Hiển thị thống kê
    has_acronym = sum(1 for info in sorted_mapping.values() if info['acronym'] is not None)
    no_acronym = len(sorted_mapping) - has_acronym
    
    print(f"Có tên viết tắt: {has_acronym}")
    print(f"Không có tên viết tắt: {no_acronym}")

if __name__ == "__main__":
    check_data_files()
    create_university_mapping()
