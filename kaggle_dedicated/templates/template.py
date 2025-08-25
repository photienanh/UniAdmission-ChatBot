import os
def search_query_rewrite_template(folder_path: str):
    file_path = os.path.join(folder_path, "templates", "search_query_rewrite.md")
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
    
if __name__ == "__main__":
    print(len(search_query_rewrite_template("")))