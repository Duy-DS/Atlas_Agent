import json
from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.validator import ValidatorAgent
from agents.forecaster import ForecasterAgent
from agents.analyzer import AnalyzerAgent
from agents.risk_detector import RiskDetectorAgent
from agents.strategist import StrategistAgent

def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Initialize agents
    validator = ValidatorAgent()
    forecaster = ForecasterAgent()
    analyzer = AnalyzerAgent()
    risk_detector = RiskDetectorAgent()
    strategist = StrategistAgent()

    # --- NODE 1: Validation ---
    def validate_node(state: AgentState):
        raw = state["raw_data"]
        # 1. Programmatic validation
        prog_res = validator.validate_metrics(raw)
        
        # 2. LLM validation to wrap it in a nice format or explain issues
        user_msg = f"Dữ liệu thô đầu vào:\n{json.dumps(raw, indent=2)}\n\nKết quả kiểm tra tự động:\n{json.dumps(prog_res, indent=2)}"
        llm_res_text = validator.run(user_msg, max_tokens=256)
        
        # Parse or clean JSON
        try:
            # Simple fallback parser for JSON
            cleaned_text = llm_res_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            val_json = json.loads(cleaned_text.strip())
        except Exception:
            val_json = {"is_valid": prog_res["is_valid"], "outliers": prog_res["outliers"], "raw_llm_output": llm_res_text}
            
        state["validation_results"] = val_json
        state["audit_trail"].append("Data validation completed.")
        return state

    # --- NODE 2: Forecasting ---
    def forecast_node(state: AgentState):
        raw = state["raw_data"]
        user_msg = f"Dữ liệu hoạt động:\n{json.dumps(raw, indent=2)}"
        llm_res_text = forecaster.run(user_msg, max_tokens=300)
        
        try:
            cleaned_text = llm_res_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            fore_json = json.loads(cleaned_text.strip())
        except Exception:
            fore_json = {"raw_forecast": llm_res_text}
            
        state["forecast_14d"] = fore_json
        state["audit_trail"].append("14-day demand forecasting completed.")
        return state

    # --- NODE 3: Budget/Variance Analysis ---
    def analyze_node(state: AgentState):
        raw = state["raw_data"]
        user_msg = f"Dữ liệu hoạt động khách sạn:\n{json.dumps(raw, indent=2)}"
        llm_res_text = analyzer.run(user_msg, max_tokens=300)
        
        try:
            cleaned_text = llm_res_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            ana_json = json.loads(cleaned_text.strip())
        except Exception:
            ana_json = {"raw_analysis": llm_res_text}
            
        state["analysis"] = ana_json
        state["audit_trail"].append("Budget variance analysis completed.")
        return state

    # --- NODE 4: Risk & Anomaly Detection ---
    def risk_node(state: AgentState):
        raw = state["raw_data"]
        user_msg = f"Dữ liệu hoạt động khách sạn:\n{json.dumps(raw, indent=2)}"
        llm_res_text = risk_detector.run(user_msg, max_tokens=300)
        
        try:
            cleaned_text = llm_res_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            risk_json = json.loads(cleaned_text.strip())
        except Exception:
            risk_json = {"raw_risks": llm_res_text}
            
        state["risks"] = risk_json
        state["audit_trail"].append("Risk and anomaly detection completed.")
        return state

    # --- NODE 5: Strategy Recommendation ---
    def strategy_node(state: AgentState):
        context = {
            "validation": state.get("validation_results"),
            "forecast_14d": state.get("forecast_14d"),
            "performance_analysis": state.get("analysis"),
            "risk_alerts": state.get("risks")
        }
        
        user_msg = f"Ngữ cảnh phân tích từ các Agent trước:\n{json.dumps(context, indent=2, ensure_ascii=False)}"
        llm_res_text = strategist.run(user_msg, max_tokens=512)
        
        try:
            cleaned_text = llm_res_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            strat_json = json.loads(cleaned_text.strip())
        except Exception:
            strat_json = {"raw_strategy": llm_res_text}
            
        state["strategy_recommendations"] = strat_json
        state["audit_trail"].append("Strategy recommendations formulated.")
        return state

    # --- NODE 6: Aggregator Report Node ---
    def report_node(state: AgentState):
        raw = state["raw_data"]
        date = raw.get("date", "Hôm nay")
        
        val_res = state.get("validation_results", {})
        forecast = state.get("forecast_14d", {})
        analysis = state.get("analysis", {})
        risks = state.get("risks", {})
        strat = state.get("strategy_recommendations", {})
        
        # Format list to markdown helper
        def to_md_list(items):
            if not items:
                return "*Không có*"
            if isinstance(items, list):
                return "\n".join([f"- {i}" for i in items])
            return str(items)

        # Build Markdown content
        report = f"""# Báo cáo Trí tuệ Thương mại (Commercial Intelligence Executive Brief)
## Tập đoàn khách sạn The Anam | Ngày: {date}

---

## 1. Kết quả kiểm toán dữ liệu (Data Audit)
- **Hợp lệ:** {"Đồng ý" if val_res.get("is_valid", True) else "Cần chú ý"}
- **Các giá trị bất hợp lý phát hiện (Outliers):**
{to_md_list(val_res.get("outliers", []))}
- **Trường dữ liệu bị thiếu:**
{to_md_list(val_res.get("missing_fields", []))}

---

## 2. Phân tích kết quả so với Kế hoạch (Budget Variance & Growth)
- **Tình trạng so với Ngân sách:** {analysis.get("vs_budget_status", "N/A").upper()}
- **Tốc độ tăng trưởng so với năm ngoái:** {analysis.get("vs_last_year_status", "N/A").upper()}
- **Tỷ lệ lệch doanh thu chênh lệch (Revenue Variance %):** {analysis.get("revenue_variance_pct", "0%")}
- **Tóm tắt phân tích chênh lệch:** 
> {analysis.get("variance_analysis_brief", "Không có tóm tắt.")}

---

## 3. Dự báo nhu cầu 14 ngày tới (14-Day Demand Forecast)
- **Trạng thái dự báo:** {forecast.get("forecast_status", "N/A").upper()}
- **Công suất phòng dự kiến:** {forecast.get("occupancy_projection_14d", "N/A")}
- **Các động lực tăng trưởng chính:**
{to_md_list(forecast.get("key_drivers", []))}

---

## 4. Nhận diện rủi ro & Cảnh báo bất thường (Risk & Anomaly Alert)
- **Điểm số rủi ro hệ thống:** **{risks.get("risk_score", 0)} / 100**
- **Phát hiện dị thường:** {"CÓ" if risks.get("anomaly_detected", False) else "KHÔNG"}
- **Các yếu tố rủi ro chính cần theo dõi:**
{to_md_list(risks.get("risk_factors", []))}

---

## 5. Khuyến nghị chiến lược phòng & giá (Rate & Inventory Decisions)
### Đề xuất Thay đổi Giá bán phòng (Dynamic Pricing Rates):
{to_md_list(strat.get("rate_recommendations", []))}

### Quy tắc kiểm soát phòng trống (Inventory Control):
{to_md_list(strat.get("inventory_rules", []))}

### Chiến dịch kênh phân phối (OTAs vs Direct):
{to_md_list(strat.get("distribution_strategy", []))}

**Ước lượng tác động doanh thu:** **+{strat.get("estimated_revenue_impact_usd", 0):,} USD / tháng**
"""
        state["report_markdown"] = report
        state["audit_trail"].append("Strategic markdown report generated.")
        return state

    # Add Nodes
    workflow.add_node("validate", validate_node)
    workflow.add_node("forecast", forecast_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("strategy", strategy_node)
    workflow.add_node("report", report_node)

    # Compile Flow
    workflow.set_entry_point("validate")
    workflow.add_edge("validate", "forecast")
    workflow.add_edge("forecast", "analyze")
    workflow.add_edge("analyze", "risk")
    workflow.add_edge("risk", "strategy")
    workflow.add_edge("strategy", "report")
    workflow.add_edge("report", END)

    return workflow.compile()
