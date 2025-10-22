from datetime import datetime
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from hoops_edge.output.excel import (
    AUDIT_HEADERS,
    GAME_SUMMARY_HEADERS,
    PICKS_HEADERS,
    ExcelWriter,
)

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _sheet_headers(zip_path, sheet_index):
    with ZipFile(zip_path) as zf:
        sheet_xml = zf.read(f"xl/worksheets/sheet{sheet_index}.xml")
    root = ET.fromstring(sheet_xml)
    row = root.find("main:sheetData", NS).find("main:row", NS)
    values = []
    for cell in row.findall("main:c", NS):
        text_node = cell.find("main:is", NS).find("main:t", NS)
        values.append(text_node.text or "")
    return values


def _sheet_names(zip_path):
    with ZipFile(zip_path) as zf:
        workbook_xml = zf.read("xl/workbook.xml")
    root = ET.fromstring(workbook_xml)
    sheets = root.find("main:sheets", NS)
    return [sheet.attrib["name"] for sheet in sheets.findall("main:sheet", NS)]


def test_excel_headers(tmp_path):
    writer = ExcelWriter(output_dir=tmp_path)
    path = writer.write(
        datetime(2024, 2, 24),
        "east",
        [],
        [],
        [],
        [],
    )
    assert _sheet_names(path) == ["Picks", "Player Props", "Game Summary", "Audit"]
    assert _sheet_headers(path, 1) == PICKS_HEADERS
    assert _sheet_headers(path, 2) == PICKS_HEADERS
    assert _sheet_headers(path, 3) == GAME_SUMMARY_HEADERS
    assert _sheet_headers(path, 4) == AUDIT_HEADERS
