import os

from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize, QImage
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import QMarginsF, QUrl, QSizeF

from shared.utils import paths


class TicketGenerator:

    @staticmethod
    def _find_exact_file(folder_dir: str, time_prefix: str, suffix: str) -> str:
        if not os.path.exists(folder_dir):
            return ""

        for filename in os.listdir(folder_dir):
            if filename.startswith(time_prefix) and filename.endswith(suffix):
                return os.path.abspath(
                    os.path.join(folder_dir, filename)
                )

        return ""

    @classmethod
    def generate_pdf(
        cls,
        record_data: dict,
        evidence_dir: str,
        output_filepath: str
    ) -> bool:

        # ==================================================
        # 1. Tìm ảnh hiện trường và biển số
        # ==================================================

        time_prefix = record_data["time_str"]

        scene_path = cls._find_exact_file(
            evidence_dir,
            time_prefix,
            "_3_scene_out.jpg"
        )

        plate_path = cls._find_exact_file(
            evidence_dir,
            time_prefix,
            "_4_plate_crop.jpg"
        )

        document = QTextDocument()

        # --------------------------------------------------
        # Nạp Ảnh hiện trường, Ảnh biển số, và Logo 
        # --------------------------------------------------
        src_scene = ""
        if scene_path and os.path.exists(scene_path):
            img_scene = QImage(scene_path)
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl("scene_image"), img_scene)
            src_scene = "scene_image"

        src_plate = ""
        if plate_path and os.path.exists(plate_path):
            img_plate = QImage(plate_path)
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl("plate_image"), img_plate)
            src_plate = "plate_image"

        logo_path = os.path.join(paths.ICONS_DIR, "uth-logo.png")
        src_logo = ""
        if os.path.exists(logo_path):
            img_logo = QImage(logo_path)
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl("logo_uth"), img_logo)
            src_logo = "logo_uth"

        # ==================================================
        # 3. HTML & CSS
        # ==================================================

        logo_html = ""
        if src_logo:
            logo_html = f'<img src="{src_logo}" width="80">'

        scene_image_html = ""
        if src_scene:
            scene_image_html = f'<img src="{src_scene}" width="480" style="border:1px solid black;">'

        plate_image_html = ""
        if src_plate:
            separator = "<br><br>" if src_scene else ""
            plate_image_html = f'{separator}<img src="{src_plate}" width="200" style="border:1px solid black;">'

        html_content = f"""
        <html>
        <head>
        <style>

        body {{
            font-family: "Times New Roman", serif;
            font-size: 14pt;
            line-height: 1.5;
            color: black;
        }}

        .main-title {{
            font-size: 20pt;
            font-weight: bold;
            text-align: center;
            margin-top: 15pt;
            margin-bottom: 10pt;
        }}

        .content {{
            margin-left: 40pt;
            margin-right: 40pt;
        }}

        .info-line {{
            margin: 6pt 0;
        }}

        .bold {{
            font-weight: bold;
        }}

        .plate-number {{
            font-size: 16pt;
            font-weight: bold;
        }}

        .image-container {{
            text-align: center;
            margin-top: 15pt;
        }}

        .footer {{
            margin-top: 30pt;
            text-align: right;
            padding-right: 50pt;
        }}

        </style>
        </head>

        <body>

        <!-- ========================================= -->
        <!-- HEADER CÓ CHỨA LOGO -->
        <!-- ========================================= -->

        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr>
                <td width="20%" align="left" valign="top">
                    {logo_html}
                </td>
                <td width="60%" align="center" valign="top">
                    <span style="font-size:14pt; font-weight:bold;">
                        HỆ THỐNG GIÁM SÁT TRẬT TỰ AN TOÀN
                        <br>
                        GIAO THÔNG ĐƯỜNG BỘ BẰNG HÌNH ẢNH
                    </span>
                    <br>
                    ____________________________________
                </td>
                <td width="20%">
                    <!-- Cột đối xứng trống -->
                </td>
            </tr>
        </table>

        <!-- ========================================= -->
        <!-- TIÊU ĐỀ CHÍNH -->
        <!-- ========================================= -->

        <div class="main-title">HÌNH ẢNH PHƯƠNG TIỆN VI PHẠM</div>

        <!-- ========================================= -->
        <!-- NỘI DUNG -->
        <!-- ========================================= -->

        <div class="content">
            <p class="info-line">
                - Hành vi vi phạm:
                <span class="bold">{record_data.get('loi_vi_pham', '')}</span>
            </p>
            <p class="info-line">
                - Thời gian vi phạm:
                {record_data.get('thoi_gian_vi_pham_vn', '')}
            </p>
            <p class="info-line">
                - Địa điểm vi phạm:
                {record_data.get('dia_diem', '')}
            </p>
            <p class="info-line">
                - Biển số vi phạm:
                <span class="plate-number">{record_data.get('bien_so_xe', '')}</span>
            </p>
            <p class="info-line">
                - Đơn vị vận hành hệ thống:
                <span class="bold">Trung tâm giám sát camera giao thông Trường Đại học Giao thông vận tải</span>
            </p>
        </div>

        <!-- ========================================= -->
        <!-- HÌNH ẢNH -->
        <!-- ========================================= -->

        <div class="image-container">
            {scene_image_html}
            {plate_image_html}
        </div>

        <!-- ========================================= -->
        <!-- FOOTER -->
        <!-- ========================================= -->

        <div class="footer">
            <p><i>Ngày ..... tháng ..... năm 20...</i></p>
            <p><b>CƠ QUAN XỬ LÝ VI PHẠM</b></p>
            <p>(Ký, ghi rõ họ tên và đóng dấu)</p>
        </div>

        </body>
        </html>
        """

        # ==================================================
        # 4. Xuất PDF
        # ==================================================

        try:
            document.setHtml(html_content)

            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_filepath)

            page_layout = QPageLayout()
            page_layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            page_layout.setOrientation(QPageLayout.Orientation.Portrait)
            page_layout.setMargins(QMarginsF(15.0, 15.0, 15.0, 15.0))
            
            printer.setPageLayout(page_layout)
            
            paint_rect = printer.pageLayout().paintRectPixels(printer.resolution())
            document.setPageSize(QSizeF(paint_rect.width(), paint_rect.height()))

            document.print(printer)

            print(f"[DEBUG - PDF] Da xuat thanh cong: {output_filepath}")
            return True

        except Exception as e:
            print(f"[DEBUG - PDF] LOI FATAL KHI IN: {e}")
            return False