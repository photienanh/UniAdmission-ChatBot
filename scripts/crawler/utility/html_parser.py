import re
from bs4 import BeautifulSoup
def extract_text(text: str):
    result = []
    elements: list[str] = re.findall(r'>(.*?)<', text)
    for element in elements:
        element = element.replace("\xa0", " ").replace(".", " ").replace(",", " ").strip()
        if element in "" :
            continue
        elif ">" not in element and "<" not in element:
            result.append(element)
        else:
            result.extend(extract_text(element))
    return result
def _parse_single_table(table: str):
    table_text = "<x_table>$$Start Table$$\n"
    table = table.partition(">")[-1]
    rows = re.findall(r'<tr>(.*?)</tr>', table)
    for row in rows:
        parsed_row = []
        columns: str = re.findall(r'<td(.*?)</td>', row)
        for column in columns:
            column = column.partition(">")[-1]
            parsed_column = extract_text(column)
            parsed_column = " ".join(parsed_column)
            parsed_row.append(parsed_column)
        if len(parsed_row) > 0:
            table_text += ", ".join(parsed_row) + "\n"
    table_text += "$$End Table$$</x_table>\n"
    return table_text if table_text !="<x_table>$$Start Table$$\n$$End Table$$</x_table>\n" else ""
def convert_to_table(text: str):
    pattern = r'<table\s(.*?)</table>'
    table = re.search(pattern, text, flags=re.DOTALL)
    while table:
        table = table.group()
        parsed_table = _parse_single_table(table)
        text = re.sub(pattern, parsed_table, text, count=1, flags=re.DOTALL)
        table = re.search(pattern, text, flags=re.DOTALL)

    return text
def parse_text(text: str) -> str:
    text = convert_to_table(text)
    target_tags = [
        "p", "x_table", "a" #, "h1", "h2", "h3", "h4", "h5", "h6"
    ]
    soup = BeautifulSoup(text, "html.parser")
    elements = soup.find_all(target_tags)
    text: list[str] = []
    for element in elements:
        element_text = element.get_text()
        if element_text != "":
            text.append(element_text)
    return "\n".join(text)

if __name__ == "__main__":
    # file_path = "data\school_raw\\724\\fepn_uet_vnu_edu_vn_dao-tao_sau-dai-hoc_thac-si-chuyen-nganh-vat-lieu-va-linh-kien-nano2_noi-dung-chuong-trinh-dao-tao.html"
    # with open(file_path, 'r', encoding='utf-8') as file:
    #     text = file.read()
        
    # print(parse_text(text))
    pass