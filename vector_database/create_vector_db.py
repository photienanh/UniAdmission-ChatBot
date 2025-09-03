import json
from pathlib import Path
from typing import List, Dict, Optional
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings

def load_university_mapping(mapping_file: str = "university_mapping.json") -> Dict:
    """Load university mapping"""
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"✅ Loaded {len(mapping)} universities")
        return mapping
    except Exception as e:
        print(f"❌ Error loading mapping: {e}")
        return {}

def get_university_abbr(filename: str, mapping: Dict) -> Optional[str]:
    """Get university abbreviation from filename"""
    code = filename.replace('.md', '')
    
    # Check if code exists in mapping and has valid acronym
    if code in mapping:
        acronym = mapping[code].get("acronym")
        # Only return if acronym is not null
        if acronym is not None:
            # Remove "VNU - " prefix if exists
            if acronym.startswith("VNU - "):
                acronym = acronym.replace("VNU - ","")  # Remove "VNU - " (6 characters)
            return acronym
    
    return None

def create_documents_for_university(content: str, school_id: str, university_name: str) -> List[Document]:
    documents = []
    
    # Split content into 4 sections
    sections = split_content_by_structure(content)
    
    # Create 4 documents với nội dung được phân chia rõ ràng
    section_configs = [
        {
            "section": "thong_tin_chung",
            "title": f"Thông tin chung - {university_name}",
            "content": sections["thong_tin_chung"]
        },
        {
            "section": "hoc_phi",
            "title": f"Học phí - {university_name}",
            "content": sections["hoc_phi"]
        },
        {
            "section": "diem_chuan", 
            "title": f"Điểm chuẩn - {university_name}",
            "content": sections["diem_chuan"]
        },
        {
            "section": "tuyen_sinh",
            "title": f"Thông tin tuyển sinh - {university_name}", 
            "content": sections["tuyen_sinh"]
        }
    ]
    
    for config in section_configs:
        # Ensure each section has meaningful content
        if not config["content"].strip():
            # If section is empty, create placeholder with university name
            text = f"{config['title']}:\n\n{university_name} - Thông tin {config['section']} không có sẵn"
        else:
            text = f"{config['title']}:\n\n{config['content']}"
        
        # Create document with simple metadata
        doc = Document(
            page_content=text,
            metadata={
                "school_id": school_id,
                "section": config["section"]
            }
        )
        documents.append(doc)
    
    return documents

def split_content_by_structure(content: str) -> Dict[str, str]:
    sections = {
        "thong_tin_chung": "",
        "hoc_phi": "",
        "diem_chuan": "",
        "tuyen_sinh": ""
    }
    
    # Define split markers theo thứ tự
    hoc_phi_marker = "HỌC PHÍ:"
    diem_chuan_marker = "NGÀNH ĐÀO TẠO VÀ ĐIỂM CHUẨN:"
    tuyen_sinh_marker = "THÔNG TIN TUYỂN SINH:"
    
    # Find positions
    hoc_phi_pos = content.find(hoc_phi_marker)
    diem_chuan_pos = content.find(diem_chuan_marker)
    tuyen_sinh_pos = content.find(tuyen_sinh_marker)
    
    # Chia theo thứ tự: thong_tin_chung -> hoc_phi -> diem_chuan -> tuyen_sinh
    
    # 1. Thông tin chung: từ đầu đến "HỌC PHÍ:"
    if hoc_phi_pos != -1:
        sections["thong_tin_chung"] = content[:hoc_phi_pos].strip()
    else:
        # Nếu không có HỌC PHÍ, thì từ đầu đến NGÀNH ĐÀO TẠO
        if diem_chuan_pos != -1:
            sections["thong_tin_chung"] = content[:diem_chuan_pos].strip()
        else:
            # Nếu không có cả hai, thì từ đầu đến THÔNG TIN TUYỂN SINH
            if tuyen_sinh_pos != -1:
                sections["thong_tin_chung"] = content[:tuyen_sinh_pos].strip()
            else:
                # Nếu không có marker nào, đưa tất cả vào thông tin chung
                sections["thong_tin_chung"] = content.strip()
                return sections
    
    # 2. Học phí: từ "HỌC PHÍ:" đến "NGÀNH ĐÀO TẠO VÀ ĐIỂM CHUẨN:"
    if hoc_phi_pos != -1:
        if diem_chuan_pos != -1:
            sections["hoc_phi"] = content[hoc_phi_pos:diem_chuan_pos].strip()
        else:
            # Nếu không có NGÀNH ĐÀO TẠO, thì đến THÔNG TIN TUYỂN SINH
            if tuyen_sinh_pos != -1:
                sections["hoc_phi"] = content[hoc_phi_pos:tuyen_sinh_pos].strip()
            else:
                # Nếu không có marker sau, lấy đến hết
                sections["hoc_phi"] = content[hoc_phi_pos:].strip()
    
    # 3. Điểm chuẩn: từ "NGÀNH ĐÀO TẠO VÀ ĐIỂM CHUẨN:" đến "THÔNG TIN TUYỂN SINH:"
    if diem_chuan_pos != -1:
        if tuyen_sinh_pos != -1:
            sections["diem_chuan"] = content[diem_chuan_pos:tuyen_sinh_pos].strip()
        else:
            # Nếu không có THÔNG TIN TUYỂN SINH, lấy đến hết
            sections["diem_chuan"] = content[diem_chuan_pos:].strip()
    
    # 4. Thông tin tuyển sinh: từ "THÔNG TIN TUYỂN SINH:" đến hết
    if tuyen_sinh_pos != -1:
        sections["tuyen_sinh"] = content[tuyen_sinh_pos:].strip()
    
    # Clean up empty sections
    for section_name, section_content in sections.items():
        if not section_content.strip():
            sections[section_name] = f"Thông tin {section_name} không có sẵn."
    
    return sections

def build_vectorstore(data_dir: str = "crawl/data/output", 
                     mapping_file: str = "university_mapping.json",
                     model_name: str = "intfloat/multilingual-e5-small") -> FAISS:
    """
    Build vectorstore from university files
    """
    
    # Load mapping
    mapping = load_university_mapping(mapping_file)
    if not mapping:
        return None
    
    # Initialize embeddings
    print(f"Loading embeddings: {model_name}")
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Process files
    data_path = Path(data_dir)
    md_files = list(data_path.glob("*.md"))
    print(f"Found {len(md_files)} .md files")
    
    all_documents = []
    processed_count = 0
    
    for file_path in md_files:
        try:
            # Get university code from filename
            university_code = file_path.name.replace('.md', '')
            
            # Get university abbreviation 
            abbr = get_university_abbr(file_path.name, mapping)
            if not abbr:
                print(f"Skipping {file_path.name}: No abbreviation found")
                continue
            
            # Get university name from mapping using university code
            university_name = mapping[university_code]["name"]
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create 4 documents using abbr as school_id
            docs = create_documents_for_university(content, abbr, university_name)
            all_documents.extend(docs)
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print(f"Total documents: {len(all_documents)} from {processed_count} universities")
    print(f"Average documents per university: {len(all_documents)/processed_count:.1f}" if processed_count > 0 else "")
    
    if not all_documents:
        print("No documents created!")
        return None
    
    # Create vectorstore
    print("Creating FAISS vectorstore...")
    vectorstore = FAISS.from_documents(all_documents, embeddings)
    
    print("Vectorstore created successfully!")
    return vectorstore

def main():
    # Build vectorstore
    vectorstore = build_vectorstore(
        data_dir="crawl/data/output",
        mapping_file="university_mapping.json"
    )
    
    if vectorstore:
        # Save vectorstore
        vectorstore.save_local("vectordb")
        print("Vectorstore saved to 'vectordb'")
    else:
        print("Failed to create vectorstore!")

if __name__ == "__main__":
    main()