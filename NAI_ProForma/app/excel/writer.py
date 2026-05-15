from openpyxl import Workbook
from app.models.session import ProFormaSession
from app.excel.inputs_sheet import write_inputs_sheet
from app.excel.proforma_sheet import write_proforma_sheet


def write_workbook(session: ProFormaSession, output_path: str) -> None:
    wb = Workbook()
    write_inputs_sheet(wb.active, session)
    write_proforma_sheet(wb.create_sheet("ProForma"), session)
    wb.save(output_path)
