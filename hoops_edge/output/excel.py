"""Excel writer implemented with minimal XLSX generation."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZipFile

from hoops_edge.config import OUTPUT_DIR


PICKS_HEADERS = [
    "Tip (ET)",
    "Matchup (AWAY @ HOME)",
    "Market",
    "Side/Player",
    "Book",
    "Line/Price",
    "Fair (Model)",
    "Book (De-vig)",
    "Diff% / ΔLine",
    "Edge %",
    "Kelly %",
    "Risk",
    "Notes",
    "Pulled At",
]

PROPS_HEADERS = PICKS_HEADERS

GAME_SUMMARY_HEADERS = [
    "Tip (ET)",
    "Matchup",
    "Conference",
    "Projected Score",
    "Fair ML (Home)",
    "Fair ML (Away)",
    "Fair Spread",
    "Fair Total",
    "Home Card",
    "Away Card",
]

AUDIT_HEADERS = [
    "Game ID",
    "Market",
    "Side",
    "Book",
    "Line",
    "Price A",
    "Price B",
    "Implied A",
    "Implied B",
    "De-vig A",
    "De-vig B",
    "Timestamp",
    "Source",
    "Books",
    "Conference",
]


def _column_letter(idx: int) -> str:
    result = ""
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _auto_width(rows: List[Sequence]) -> List[float]:
    widths: List[float] = []
    for row in rows:
        for idx, value in enumerate(row, start=1):
            text = "" if value is None else str(value)
            width = min(45, len(text) + 2)
            if idx > len(widths):
                widths.append(width)
            else:
                widths[idx - 1] = max(widths[idx - 1], width)
    return widths


def _build_sheet_xml(title: str, rows: List[Sequence], add_risk_rules: bool, add_diff_scale: bool) -> bytes:
    sheet = Element(
        "worksheet",
        {
            "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        },
    )

    sheet_views = SubElement(sheet, "sheetViews")
    sheet_view = SubElement(sheet_views, "sheetView", {"workbookViewId": "0"})
    SubElement(
        sheet_view,
        "pane",
        {
            "state": "frozen",
            "ySplit": "1",
            "topLeftCell": "A2",
            "activePane": "bottomLeft",
        },
    )

    widths = _auto_width(rows)
    if widths:
        cols = SubElement(sheet, "cols")
        for idx, width in enumerate(widths, start=1):
            SubElement(
                cols,
                "col",
                {
                    "min": str(idx),
                    "max": str(idx),
                    "width": f"{width:.2f}",
                    "customWidth": "1",
                },
            )

    sheet_data = SubElement(sheet, "sheetData")
    for row_idx, row_values in enumerate(rows, start=1):
        row = SubElement(sheet_data, "row", {"r": str(row_idx)})
        for col_idx, value in enumerate(row_values, start=1):
            cell_ref = f"{_column_letter(col_idx)}{row_idx}"
            cell = SubElement(row, "c", {"r": cell_ref, "t": "inlineStr"})
            is_elem = SubElement(cell, "is")
            t_elem = SubElement(is_elem, "t")
            text = "" if value is None else str(value)
            t_elem.text = text

    last_col = _column_letter(len(rows[0]) if rows else 1)
    SubElement(sheet, "autoFilter", {"ref": f"A1:{last_col}1"})

    if add_risk_rules:
        cf = SubElement(sheet, "conditionalFormatting", {"sqref": "L2:L1048576"})
        for idx, key in enumerate(("Low", "Med", "High")):
            SubElement(
                cf,
                "cfRule",
                {
                    "type": "containsText",
                    "operator": "containsText",
                    "text": key,
                    "dxfId": str(idx),
                    "priority": str(idx + 1),
                },
            )
            formula = SubElement(cf[-1], "formula")
            formula.text = f'NOT(ISERROR(SEARCH("{key}",$L2)))'

    if add_diff_scale:
        cf = SubElement(sheet, "conditionalFormatting", {"sqref": "I2:I1048576"})
        rule = SubElement(cf, "cfRule", {"type": "colorScale", "priority": "4"})
        color_scale = SubElement(rule, "colorScale")
        for value in ("10", "50", "90"):
            SubElement(color_scale, "cfvo", {"type": "percentile", "val": value})
        for color in ("FFFFFFFF", "FFFFF2CC", "FFFFC000"):
            SubElement(color_scale, "color", {"rgb": color})

    dimension = "A1"
    if rows:
        last_row = len(rows)
        last_col_letter = _column_letter(len(rows[0]))
        dimension = f"A1:{last_col_letter}{last_row}"
    sheet.set("dimension", dimension)

    return tostring(sheet, encoding="utf-8", xml_declaration=True)


def _content_types_xml(sheet_count: int) -> bytes:
    types = Element(
        "Types",
        {"xmlns": "http://schemas.openxmlformats.org/package/2006/content-types"},
    )
    SubElement(types, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    SubElement(types, "Default", {"Extension": "xml", "ContentType": "application/xml"})
    SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/workbook.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        },
    )
    SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/styles.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
        },
    )
    SubElement(
        types,
        "Override",
        {
            "PartName": "/docProps/core.xml",
            "ContentType": "application/vnd.openxmlformats-package.core-properties+xml",
        },
    )
    SubElement(
        types,
        "Override",
        {
            "PartName": "/docProps/app.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.extended-properties+xml",
        },
    )
    SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/theme/theme1.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.theme+xml",
        },
    )
    for idx in range(1, sheet_count + 1):
        SubElement(
            types,
            "Override",
            {
                "PartName": f"/xl/worksheets/sheet{idx}.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            },
        )
    return tostring(types, encoding="utf-8", xml_declaration=True)


def _rels_xml() -> bytes:
    rels = Element(
        "Relationships",
        {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"},
    )
    SubElement(
        rels,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    SubElement(
        rels,
        "Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
            "Target": "docProps/core.xml",
        },
    )
    SubElement(
        rels,
        "Relationship",
        {
            "Id": "rId3",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
            "Target": "docProps/app.xml",
        },
    )
    return tostring(rels, encoding="utf-8", xml_declaration=True)


def _workbook_xml(sheet_titles: Sequence[str]) -> bytes:
    workbook = Element(
        "workbook",
        {
            "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        },
    )
    sheets = SubElement(workbook, "sheets")
    for idx, title in enumerate(sheet_titles, start=1):
        SubElement(
            sheets,
            "sheet",
            {
                "name": title,
                "sheetId": str(idx),
                "r:id": f"rId{idx}",
            },
        )
    return tostring(workbook, encoding="utf-8", xml_declaration=True)


def _workbook_rels_xml(sheet_count: int) -> bytes:
    rels = Element(
        "Relationships",
        {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"},
    )
    for idx in range(1, sheet_count + 1):
        SubElement(
            rels,
            "Relationship",
            {
                "Id": f"rId{idx}",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": f"worksheets/sheet{idx}.xml",
            },
        )
    SubElement(
        rels,
        "Relationship",
        {
            "Id": f"rId{sheet_count + 1}",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )
    SubElement(
        rels,
        "Relationship",
        {
            "Id": f"rId{sheet_count + 2}",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
            "Target": "theme/theme1.xml",
        },
    )
    return tostring(rels, encoding="utf-8", xml_declaration=True)


def _styles_xml() -> bytes:
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<styleSheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
  <fonts count='1'>
    <font>
      <sz val='11'/>
      <color theme='1'/>
      <name val='Calibri'/>
      <family val='2'/>
    </font>
  </fonts>
  <fills count='2'>
    <fill><patternFill patternType='none'/></fill>
    <fill><patternFill patternType='gray125'/></fill>
  </fills>
  <borders count='1'>
    <border>
      <left/><right/><top/><bottom/><diagonal/>
    </border>
  </borders>
  <cellStyleXfs count='1'>
    <xf numFmtId='0' fontId='0' fillId='0' borderId='0'/>
  </cellStyleXfs>
  <cellXfs count='1'>
    <xf numFmtId='0' fontId='0' fillId='0' borderId='0' xfId='0'/>
  </cellXfs>
  <cellStyles count='1'>
    <cellStyle name='Normal' xfId='0' builtinId='0'/>
  </cellStyles>
  <dxfs count='3'>
    <dxf><fill><patternFill patternType='solid'><fgColor rgb='FFC6EFCE'/><bgColor rgb='FFC6EFCE'/></patternFill></fill></dxf>
    <dxf><fill><patternFill patternType='solid'><fgColor rgb='FFFFEB9C'/><bgColor rgb='FFFFEB9C'/></patternFill></fill></dxf>
    <dxf><fill><patternFill patternType='solid'><fgColor rgb='FFFFC7CE'/><bgColor rgb='FFFFC7CE'/></patternFill></fill></dxf>
  </dxfs>
  <tableStyles count='0' defaultTableStyle='TableStyleMedium9' defaultPivotStyle='PivotStyleLight16'/>
</styleSheet>"""
    return xml.encode("utf-8")


def _theme_xml() -> bytes:
    return """<?xml version='1.0' encoding='UTF-8'?>
<a:theme xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' name='Office Theme'>
  <a:themeElements>
    <a:clrScheme name='Office'>
      <a:dk1><a:sysClr val='windowText' lastClr='000000'/></a:dk1>
      <a:lt1><a:sysClr val='window' lastClr='FFFFFF'/></a:lt1>
      <a:dk2><a:srgbClr val='1F497D'/></a:dk2>
      <a:lt2><a:srgbClr val='EEECE1'/></a:lt2>
      <a:accent1><a:srgbClr val='4F81BD'/></a:accent1>
      <a:accent2><a:srgbClr val='C0504D'/></a:accent2>
      <a:accent3><a:srgbClr val='9BBB59'/></a:accent3>
      <a:accent4><a:srgbClr val='8064A2'/></a:accent4>
      <a:accent5><a:srgbClr val='4BACC6'/></a:accent5>
      <a:accent6><a:srgbClr val='F79646'/></a:accent6>
      <a:hlink><a:srgbClr val='0000FF'/></a:hlink>
      <a:folHlink><a:srgbClr val='800080'/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name='Office'>
      <a:majorFont>
        <a:latin typeface='Calibri Light'/>
        <a:ea typeface=''/>
        <a:cs typeface=''/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface='Calibri'/>
        <a:ea typeface=''/>
        <a:cs typeface=''/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name='Office'>
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val='phClr'/></a:solidFill>
        <a:gradFill flip='med' rotWithShape='1'>
          <a:gsLst>
            <a:gs pos='0'><a:schemeClr val='phClr'><a:lumMod val='110000'/><a:satMod val='105000'/><a:tint val='67000'/></a:schemeClr></a:gs>
            <a:gs pos='50000'><a:schemeClr val='phClr'><a:lumMod val='105000'/><a:satMod val='103000'/><a:tint val='73000'/></a:schemeClr></a:gs>
            <a:gs pos='100000'><a:schemeClr val='phClr'><a:lumMod val='105000'/><a:satMod val='109000'/><a:tint val='81000'/></a:schemeClr></a:gs>
          </a:gsLst>
        </a:gradFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w='9525' cap='flat' cmpd='sng' algn='ctr'>
          <a:solidFill><a:schemeClr val='phClr'/></a:solidFill>
          <a:prstDash val='solid'/>
        </a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val='phClr'/></a:solidFill>
        <a:gradFill rotWithShape='1'>
          <a:gsLst>
            <a:gs pos='0'><a:schemeClr val='phClr'><a:tint val='93000'/><a:satMod val='90000'/><a:lumMod val='99000'/></a:schemeClr></a:gs>
            <a:gs pos='100000'><a:schemeClr val='phClr'><a:lumMod val='120000'/><a:satMod val='120000'/></a:schemeClr></a:gs>
          </a:gsLst>
        </a:gradFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>""".encode("utf-8")


def _core_xml() -> bytes:
    return """<?xml version='1.0' encoding='UTF-8'?>
<cp:coreProperties xmlns:cp='http://schemas.openxmlformats.org/package/2006/metadata/core-properties' xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:dcterms='http://purl.org/dc/terms/' xmlns:dcmitype='http://purl.org/dc/dcmitype/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
  <dc:creator>hoops-edge</dc:creator>
  <cp:lastModifiedBy>hoops-edge</cp:lastModifiedBy>
  <dcterms:created xsi:type='dcterms:W3CDTF'>2024-01-01T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type='dcterms:W3CDTF'>2024-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>""".encode("utf-8")


def _app_xml(sheet_titles: Sequence[str]) -> bytes:
    props = Element(
        "Properties",
        {
            "xmlns": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
            "xmlns:vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
        },
    )
    SubElement(props, "Application").text = "Microsoft Excel"
    sheets = SubElement(props, "TitlesOfParts")
    vector = SubElement(sheets, "vt:vector", {"size": str(len(sheet_titles)), "baseType": "lpstr"})
    for title in sheet_titles:
        SubElement(vector, "vt:lpstr").text = title
    return tostring(props, encoding="utf-8", xml_declaration=True)


class ExcelWriter:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        file_date: datetime,
        conference: str,
        picks_rows: Iterable[Sequence],
        props_rows: Iterable[Sequence],
        summary_rows: Iterable[Sequence],
        audit_rows: Iterable[Sequence],
    ) -> Path:
        picks_data = [PICKS_HEADERS, *picks_rows]
        props_data = [PROPS_HEADERS, *props_rows]
        summary_data = [GAME_SUMMARY_HEADERS, *summary_rows]
        audit_data = [AUDIT_HEADERS, *audit_rows]

        sheets = [
            ("Picks", picks_data, True, True),
            ("Player Props", props_data, True, True),
            ("Game Summary", summary_data, False, False),
            ("Audit", audit_data, False, False),
        ]

        conference_suffix = conference.capitalize()
        filename = f"NBA_{file_date:%Y-%m-%d}_{conference_suffix}.xlsx"
        output_path = self.output_dir / filename

        with ZipFile(output_path, "w") as zf:
            zf.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
            zf.writestr("_rels/.rels", _rels_xml())
            zf.writestr("docProps/core.xml", _core_xml())
            zf.writestr("docProps/app.xml", _app_xml([title for title, *_ in sheets]))
            zf.writestr("xl/workbook.xml", _workbook_xml([title for title, *_ in sheets]))
            zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(len(sheets)))
            zf.writestr("xl/styles.xml", _styles_xml())
            zf.writestr("xl/theme/theme1.xml", _theme_xml())
            for idx, (title, data, risk, diff) in enumerate(sheets, start=1):
                zf.writestr(
                    f"xl/worksheets/sheet{idx}.xml",
                    _build_sheet_xml(title, data, add_risk_rules=risk, add_diff_scale=diff),
                )

        return output_path
