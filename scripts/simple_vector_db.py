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
    
    # Find abbreviation by code
    for abbr, data in mapping.items():
        if data.get("ma_truong") == code:
            return abbr
    
    return None

def create_documents_for_university(content: str, school_id: str, university_name: str) -> List[Document]:
    documents = []
    
    # Split content into sections với regex pattern matching
    sections = split_content_by_structure(content)
    
    # Create 3 documents với nội dung được phân chia rõ ràng
    section_configs = [
        {
            "section": "thong_tin_chung",
            "title": f"Thông tin chung - {university_name}",
            "content": sections["thong_tin_chung"]
        },
        {
            "section": "diem_chuan", 
            "title": f"Điểm chuẩn - {university_name}",
            "content": sections["diem_chuan"]
        },
        {
            "section": "tuyen_sinh",
            "title": f"Tuyển sinh - {university_name}", 
            "content": sections["tuyen_sinh"]
        }
    ]
    
    for config in section_configs:
        # Ensure each section has meaningful content
        if not config["content"].strip():
            # If section is empty, create placeholder with university name
            text = f"{config['title']}:\n\n{university_name} - Thông tin {config['section']}"
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
        "diem_chuan": "",
        "tuyen_sinh": ""
    }
    
    # Define split markers
    diem_chuan_marker = "Ngành đào tạo và điểm chuẩn"
    tuyen_sinh_marker1 = "### **II. Các ngành tuyển sinh"
    tuyen_sinh_marker2 = "Đối tượng tuyển sinh"
    
    # Find positions of markers
    diem_chuan_pos = content.find(diem_chuan_marker)
    tuyen_sinh_pos1 = content.find(tuyen_sinh_marker1)
    tuyen_sinh_pos2 = content.find(tuyen_sinh_marker2)
    
    # Logic quyết định marker tuyển sinh:
    # - Ưu tiên "### **II. Các ngành tuyển sinh" nếu có
    # - CHỈ dùng "Đối tượng tuyển sinh" khi KHÔNG có marker1
    if tuyen_sinh_pos1 != -1:
        tuyen_sinh_pos = tuyen_sinh_pos1
    elif tuyen_sinh_pos2 != -1:
        tuyen_sinh_pos = tuyen_sinh_pos2
    else:
        tuyen_sinh_pos = -1
    
    if diem_chuan_pos == -1:
        # No "Ngành đào tạo và điểm chuẩn" found - put everything in thông tin chung
        if tuyen_sinh_pos != -1:
            sections["thong_tin_chung"] = content[:tuyen_sinh_pos].strip()
            sections["tuyen_sinh"] = content[tuyen_sinh_pos:].strip()
        else:
            sections["thong_tin_chung"] = content.strip()
    else:
        # Found "Ngành đào tạo và điểm chuẩn"
        # Section 1: Thông tin chung (from start to điểm chuẩn marker)
        sections["thong_tin_chung"] = content[:diem_chuan_pos].strip()
        
        if tuyen_sinh_pos == -1:
            # No tuyển sinh marker - everything after điểm chuẩn is điểm chuẩn
            sections["diem_chuan"] = content[diem_chuan_pos:].strip()
        else:
            # Section 2: Điểm chuẩn (from điểm chuẩn marker to tuyển sinh marker)  
            sections["diem_chuan"] = content[diem_chuan_pos:tuyen_sinh_pos].strip()
            # Section 3: Tuyển sinh (from tuyển sinh marker to end)
            sections["tuyen_sinh"] = content[tuyen_sinh_pos:].strip()
    
    # Clean up empty sections - ensure each has some content
    for section_name, section_content in sections.items():
        if not section_content.strip():
            sections[section_name] = f"Thông tin {section_name} không có sẵn."
    
    return sections

def build_vectorstore(data_dir: str = "../uni_data/output", 
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
            # Get university abbreviation
            abbr = get_university_abbr(file_path.name, mapping)
            if not abbr:
                print(f"Skipping {file_path.name}: No abbreviation found")
                continue
            
            # Get university name
            university_name = mapping[abbr]["ten_truong"]
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create 3 documents
            docs = create_documents_for_university(content, abbr, university_name)
            all_documents.extend(docs)
            processed_count += 1
            
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"Total documents: {len(all_documents)} from {processed_count} universities")
    
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
        data_dir="../uni_data/output",
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
