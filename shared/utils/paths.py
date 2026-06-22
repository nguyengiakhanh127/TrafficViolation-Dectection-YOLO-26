import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICONS_DIR = os.path.join(PROJECT_ROOT, "shared", "gui", "assets", "icons")
CURSORS_DIR = os.path.join(PROJECT_ROOT, "shared", "gui", "assets", "cursors")

CONFIGS_DIR = os.path.join(PROJECT_ROOT, "storage", "configs")
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "storage", "violation_evidences")

LICENSE_PLATE_DETECTION_OPENVINO_MODEL = os.path.join(PROJECT_ROOT, r"model\yolo\openVINO_format\license_plate_detection\best_openvino_model")
VEHICLE_DETECTION_OPENVINO_MODEL = os.path.join(PROJECT_ROOT, r"model\yolo\openVINO_format\vehicle_detection\best_openvino_model")
YAML = os.path.join(PROJECT_ROOT, r"model\yaml\hutech.yaml") 
