import os
import argparse
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load env variables
load_dotenv()

from core.graph import create_agent_graph
from tools.data_loader import load_data
from tools.pdf_generator import markdown_to_pdf

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "AAWB Hotel Commercial Intelligence Engine"})

@app.route("/analyze", methods=["POST"])
def analyze():
    """Endpoint for web UI dashboards to submit daily metrics and get the strategic analysis."""
    raw_input = request.json
    if not raw_input:
        return jsonify({"error": "Invalid request, JSON data is required"}), 400
    
    # Compile and run graph
    graph = create_agent_graph()
    initial_state = {
        "raw_data": raw_input,
        "validation_results": {},
        "forecast_14d": {},
        "analysis": {},
        "risks": {},
        "strategy_recommendations": {},
        "report_markdown": "",
        "audit_trail": []
    }
    
    try:
        result = graph.invoke(initial_state)
        return jsonify({
            "validation_results": result.get("validation_results"),
            "forecast_14d": result.get("forecast_14d"),
            "performance_analysis": result.get("analysis"),
            "risks_and_anomalies": result.get("risks"),
            "strategy_recommendations": result.get("strategy_recommendations"),
            "report_markdown": result.get("report_markdown"),
            "audit_trail": result.get("audit_trail", [])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_cli_analysis(input_path: str, output_pdf: str):
    """CLI handler to analyze a daily data file (JSON) and compile a PDF report."""
    print(f"[CI Engine] Loading input file: {input_path}")
    
    try:
        # Load hotel metrics
        with open(input_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"[CI Engine] Failed to load JSON input: {e}")
        return
        
    print(f"[CI Engine] Running Multi-Agent Commercial Intelligence Pipeline...")
    graph = create_agent_graph()
    initial_state = {
        "raw_data": raw_data,
        "validation_results": {},
        "forecast_14d": {},
        "analysis": {},
        "risks": {},
        "strategy_recommendations": {},
        "report_markdown": "",
        "audit_trail": []
    }
    
    try:
        result = graph.invoke(initial_state)
        report_md = result.get("report_markdown", "")
        
        # Save raw markdown brief
        md_output_path = Path(output_pdf).with_suffix(".md")
        md_output_path.parent.mkdir(parents=True, exist_ok=True)
        md_output_path.write_text(report_md, encoding="utf-8")
        print(f"[CI Engine] Strategic Markdown saved at: {md_output_path}")
        
        # Save premium PDF brief
        pdf_output_path = Path(output_pdf)
        success = markdown_to_pdf(report_md, pdf_output_path, title="The Anam Commercial Brief")
        
        if success:
            print(f"[CI Engine] Analysis completed successfully! PDF output: {pdf_output_path}")
        else:
            print(f"[CI Engine] Analysis completed, but PDF compilation failed. Check log output.")
            
    except Exception as e:
        print(f"[CI Engine] Pipeline execution failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AAWB Commercial Intelligence System")
    parser.add_argument("--server", action="store_true", help="Start Flask API Server")
    parser.add_argument("--input", type=str, help="Path to input daily data JSON file")
    parser.add_argument("--output", type=str, default="output/executive_brief.pdf", help="Path to save PDF report")
    args = parser.parse_args()

    if args.server:
        port = int(os.getenv("PORT", "8000"))
        debug = os.getenv("DEBUG", "true").lower() == "true"
        print(f"Starting Flask API Server on port {port}...")
        app.run(host="0.0.0.0", port=port, debug=debug)
    elif args.input:
        run_cli_analysis(args.input, args.output)
    else:
        # Default behavior: run server
        port = int(os.getenv("PORT", "8000"))
        print(f"No arguments specified. Starting Flask API Server on port {port}...")
        app.run(host="0.0.0.0", port=port, debug=True)
