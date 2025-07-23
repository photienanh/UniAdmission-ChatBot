from .common import IProcessor, ProcessInput, ProcessedResult

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
        columns: list[str] = re.findall(r'<td(.*?)</td>', row)
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
        "p", "x_table" #, "a" #, "h1", "h2", "h3", "h4", "h5", "h6"
    ]
    soup = BeautifulSoup(text, "html.parser")
    elements = soup.find_all(target_tags)
    lines: list[str] = []
    for element in elements:
        element_text = element.get_text()
        if element_text != "":
            lines.append(element_text)
    return "\n".join(lines)
def processs_text(text: str) -> str:
    lines = text.splitlines()
    valid_lines: list[str] = []
    for line in lines:
        line = line.strip()
        if line != "":
            valid_lines.append(line)
    return "\n".join(valid_lines)
class SimpleProcessor(IProcessor):
    def process(self, data: ProcessInput) -> ProcessedResult:
        text = processs_text(parse_text(data.text))
        result = ProcessedResult(data.index, data.url, text)
        return result