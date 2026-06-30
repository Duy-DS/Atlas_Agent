import csv
import json
from pathlib import Path
from typing import List, Dict

def load_data(file_path: Path) -> List[Dict[str, str]]:
    """Loads dataset from CSV or JSON file and returns a list of dictionaries."""
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
        
    suffix = file_path.suffix.lower()
    
    if suffix == ".json":
        with file_path.open(encoding="utf-8-sig") as f:
            data = json.load(f)
        # Handle list of items or dictionary wrapper
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "questions" in data:
            return data["questions"]
        return [data]
        
    elif suffix == ".csv":
        rows = []
        with file_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Remove Byte-Order Mark (BOM) from keys if present
                clean_row = {(k.lstrip("\ufeff") if k else ""): v for k, v in row.items()}
                if clean_row.get("qid"):
                    rows.append(clean_row)
        return rows
        
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Only JSON and CSV are supported.")

def save_predictions(predictions: List[Dict[str, str]], output_path: Path):
    """Saves predictions list containing qid and answer to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer"])
        writer.writeheader()
        writer.writerows(predictions)
