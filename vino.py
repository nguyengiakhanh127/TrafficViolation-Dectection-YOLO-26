from ultralytics import YOLO

# 1. Tải mô hình YOLO gốc (.pt)
model = YOLO("best.pt")

# 2. Xuất mô hình sang định dạng OpenVINO
model.export(format="openvino")
