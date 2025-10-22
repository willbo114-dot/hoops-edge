import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile


NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _sheet_rows(path):
    with ZipFile(path) as zf:
        sheet_xml = zf.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(sheet_xml)
    return list(root.find("main:sheetData", NS).findall("main:row", NS))


def test_cli_replay(tmp_path):
    output_path = Path("outputs/NBA_2024-02-24_East.xlsx")
    if output_path.exists():
        output_path.unlink()

    result = subprocess.run(
        [
            "python",
            "-m",
            "hoops_edge",
            "scan",
            "--date",
            "2024-02-24",
            "--conf",
            "east",
            "--replay",
            "odds=tests/fixtures/odds/2024-02-24_bos_at_nyk.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "✅" in result.stdout
    assert output_path.exists()

    rows = _sheet_rows(output_path)
    assert len(rows) >= 2
