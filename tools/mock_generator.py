import json
from pathlib import Path

def generate_mock_hotel_data(output_path: Path):
    """Generates mock performance metrics data for 3 Anam properties as specified in the PDF."""
    data = {
        "date": "2026-06-30",
        "data_source": "mock",
        "properties": {
            "property_a_hanoi": {
                "occupancy": 0.78,
                "adr": 150.0,
                "revenue": 17550.0,
                "bookings_today": 12,
                "cancellations_today": 2,
                "lead_time_days": 14.5,
                "booking_pace": 1.05
            },
            "property_b_danang": {
                "occupancy": 0.96, # Outlier check: very high occupancy
                "adr": 180.0,
                "revenue": 30600.0,
                "bookings_today": 25,
                "cancellations_today": 8, # Anomaly check: high cancellations
                "lead_time_days": 28.0,
                "booking_pace": 0.88 # Pace drop risk
            },
            "property_c_hcmc": {
                "occupancy": 0.62,
                "adr": -10.0, # Outlier check: negative ADR
                "revenue": 6820.0,
                "bookings_today": 8,
                "cancellations_today": 1,
                "lead_time_days": 6.2,
                "booking_pace": 1.02
            }
        },
        "budget_targets": {
            "occupancy_target": 0.80,
            "adr_target": 145.0,
            "revenue_target": 50000.0
        },
        "last_year_benchmarks": {
            "occupancy": 0.74,
            "adr": 138.0,
            "revenue": 45000.0
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CI Mock Generator] Mock hotel performance metrics saved at: {output_path}")

if __name__ == "__main__":
    generate_mock_hotel_data(Path("data/sample_hotel_metrics.json"))
