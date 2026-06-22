import yaml
from shared.utils.enums import TrafficVehicleType
from typing import Dict, List

class YAML_ClassMapper:
    """
    Cầu nối dịch (Mapper) giữa các Class ID (0, 1, 2...) của YOLO 
    và các Enum chuẩn của Hệ thống Core.
    """
    def __init__(self, yaml_path: str):
        self.yaml_data: Dict[int, str] = self._load_yaml_names(yaml_path)
        
        self.mapping_rules: Dict[TrafficVehicleType, List[str]] = {
            TrafficVehicleType.BUS:        ['bus'],
            TrafficVehicleType.CONTAINER:  ['container'],
            TrafficVehicleType.SPECIAL:    ['firetruck'],  
            TrafficVehicleType.BICYCLE:    ['bicycle'],
            TrafficVehicleType.CAR:        ['car', 'van'], 
            TrafficVehicleType.MOTORCYCLE: ['motorcycle'],
            TrafficVehicleType.TRUCK:      ['truck']
        }

    def _load_yaml_names(self, yaml_path: str) -> Dict[int, str]:
        """Đọc an toàn tệp YAML bằng thư viện chuẩn"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

                return {int(k): v for k, v in data.get('names', {}).items()}
        except Exception as e:
            print(f"Lỗi đọc file YAML tại Mapper: {e}")
            return {}

    def get_vehicle_type(self, object_id: int) -> TrafficVehicleType:
        """
        Dịch Class ID (trả về từ YOLO) thành TrafficVehicleType.
        """
        class_name_str = self.yaml_data.get(int(object_id), "").lower()
        
        if not class_name_str:
            return TrafficVehicleType.UNKNOWN

        for vehicle_category, accepted_names in self.mapping_rules.items():
            if class_name_str in accepted_names:
                return vehicle_category
                
        return TrafficVehicleType.UNKNOWN
