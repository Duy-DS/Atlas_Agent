from agents.base_agent import BaseAgent
from typing import Dict, Any

class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt=(
                "Bạn là Agent Kiểm Duyệt Dữ Liệu (Validator Agent) của Tập đoàn khách sạn The Anam. "
                "Nhiệm vụ của bạn là nhận dữ liệu hoạt động khách sạn thô (JSON/CSV), kiểm tra xem các trường chỉ số có đầy đủ không "
                "và phát hiện các giá trị bất hợp lý (ví dụ: công suất phòng > 100% hoặc âm, ADR âm hoặc quá cao). "
                "Hãy trả về kết quả dưới dạng JSON chứa các khóa: "
                "'is_valid' (True/False), 'missing_fields' (danh sách trường bị thiếu), "
                "'outliers' (danh sách các chỉ số bất hợp lý phát hiện)."
            )
        )

    def validate_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Performs programmatic baseline validation on daily hotel metrics before sending to LLM."""
        missing = []
        outliers = []
        
        required_fields = ["occupancy", "adr", "revenue", "bookings_today", "cancellations_today"]
        
        # Programmatic check for hotel branches data
        properties = data.get("properties", {})
        if not properties:
            missing.append("properties")
        else:
            for prop_name, metrics in properties.items():
                for field in required_fields:
                    if field not in metrics:
                        missing.append(f"{prop_name}.{field}")
                    else:
                        val = metrics[field]
                        if field == "occupancy" and (val < 0 or val > 1.0):
                            outliers.append(f"{prop_name}.occupancy is out of range [0, 1] ({val})")
                        elif field in ["adr", "revenue", "bookings_today", "cancellations_today"] and val < 0:
                            outliers.append(f"{prop_name}.{field} cannot be negative ({val})")

        return {
            "is_valid": len(missing) == 0 and len(outliers) == 0,
            "missing_fields": missing,
            "outliers": outliers
        }
