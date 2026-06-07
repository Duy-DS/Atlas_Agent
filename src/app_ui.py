from pathlib import Path
import hashlib
import time

import pandas as pd
import streamlit as st


# =========================
# Config
# =========================

OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "pred.csv"

VALID_ANSWERS = ["A", "B", "C", "D"]


# =========================
# Mock AI Model
# =========================

def mock_ai_predict(qid: str, row_text: str) -> str:
    """
    Mock model để test luồng UI trước khi gắn model thật.

    Logic:
    - Dùng hash của qid + nội dung câu hỏi.
    - Sinh ra đáp án ổn định A/B/C/D.
    - Cùng một input sẽ luôn ra cùng một output.

    Đây không phải model thật. Đây là cái nạng test pipeline.
    """
    raw_text = f"{qid}|{row_text}"
    hash_value = hashlib.md5(raw_text.encode("utf-8")).hexdigest()
    answer_index = int(hash_value, 16) % 4
    return VALID_ANSWERS[answer_index]


# =========================
# Helpers
# =========================

def validate_input_csv(df: pd.DataFrame) -> list[str]:
    """
    Kiểm tra file CSV đầu vào.
    Trả về danh sách lỗi. Không có lỗi thì trả về list rỗng.
    """
    errors = []

    if df.empty:
        errors.append("File CSV đang rỗng.")

    if "qid" not in df.columns:
        errors.append("File CSV phải có cột 'qid'.")

    if "answer" in df.columns:
        errors.append(
            "File input test không nên có cột 'answer'. "
            "Cột 'answer' chỉ xuất hiện trong file output pred.csv."
        )

    if "qid" in df.columns and df["qid"].isna().any():
        errors.append("Cột 'qid' có giá trị rỗng.")

    if "qid" in df.columns and df["qid"].duplicated().any():
        errors.append("Cột 'qid' có giá trị bị trùng.")

    return errors


def row_to_text(row: pd.Series) -> str:
    """
    Gộp các cột ngoài qid thành text để đưa vào mock model.

    Vì format CSV thật chưa chốt chi tiết, hàm này xử lý linh hoạt:
    - Nếu có các cột question, A, B, C, D thì vẫn chạy.
    - Nếu có các cột khác thì vẫn gom lại được.
    """
    parts = []

    for col, value in row.items():
        if col == "qid":
            continue

        if pd.isna(value):
            continue

        parts.append(f"{col}: {value}")

    return "\n".join(parts)


def run_mock_inference(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Chạy mock inference cho toàn bộ file CSV.
    Trả về:
    - pred_df: DataFrame gồm qid, answer
    - logs: danh sách log basic
    """
    logs = []
    predictions = []

    total_rows = len(df)

    logs.append(f"[START] Nhận {total_rows} câu hỏi từ file CSV.")
    logs.append("[CHECK] Đã kiểm tra file input hợp lệ.")
    logs.append("[RUN] Bắt đầu chạy mock AI model.")

    for idx, row in df.iterrows():
        qid = str(row["qid"])
        row_text = row_to_text(row)

        answer = mock_ai_predict(qid=qid, row_text=row_text)

        predictions.append({
            "qid": qid,
            "answer": answer,
        })

        logs.append(f"[{idx + 1}/{total_rows}] qid={qid} -> answer={answer}")

        # Sleep nhẹ để UI nhìn thấy tiến trình.
        # Khi gắn model thật thì bỏ dòng này.
        time.sleep(0.03)

    pred_df = pd.DataFrame(predictions, columns=["qid", "answer"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    logs.append(f"[SAVE] Đã ghi file: {OUTPUT_FILE}")
    logs.append("[DONE] Hoàn tất sinh pred.csv.")

    return pred_df, logs


def init_session_state() -> None:
    """
    Khởi tạo session state cho Streamlit.
    """
    if "pred_df" not in st.session_state:
        st.session_state.pred_df = None

    if "logs" not in st.session_state:
        st.session_state.logs = []

    if "input_df" not in st.session_state:
        st.session_state.input_df = None


# =========================
# Streamlit UI
# =========================

def main() -> None:
    st.set_page_config(
        page_title="Local AI UI Tester",
        page_icon="🧪",
        layout="wide",
    )

    init_session_state()

    st.title("Local AI UI Tester")
    st.caption("Task 5.2 - Upload CSV, chạy mock AI, xuất pred.csv")

    st.divider()

    uploaded_file = st.file_uploader(
        label="Upload file public_test.csv hoặc private_test.csv",
        type=["csv"],
        accept_multiple_files=False,
    )

    if uploaded_file is None:
        st.info("Upload file CSV để bắt đầu test.")
        return

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Không đọc được file CSV. Lỗi: {exc}")
        return

    st.session_state.input_df = df

    st.subheader("Preview input CSV")
    st.dataframe(df.head(20), use_container_width=True)

    st.write(f"Số dòng: `{len(df)}`")
    st.write(f"Số cột: `{len(df.columns)}`")
    st.write("Danh sách cột:")
    st.code(", ".join(df.columns), language="text")

    errors = validate_input_csv(df)

    if errors:
        st.error("File CSV chưa hợp lệ.")
        for error in errors:
            st.write(f"- {error}")
        return

    st.success("File CSV hợp lệ.")

    run_button = st.button(
        "Chạy mock AI và tạo pred.csv",
        type="primary",
        use_container_width=True,
    )

    if run_button:
        log_placeholder = st.empty()
        progress_bar = st.progress(0)

        logs = []
        predictions = []

        total_rows = len(df)

        logs.append(f"[START] Nhận {total_rows} câu hỏi từ file CSV.")
        logs.append("[CHECK] Đã kiểm tra file input hợp lệ.")
        logs.append("[RUN] Bắt đầu chạy mock AI model.")

        for idx, row in df.iterrows():
            qid = str(row["qid"])
            row_text = row_to_text(row)

            answer = mock_ai_predict(qid=qid, row_text=row_text)

            predictions.append({
                "qid": qid,
                "answer": answer,
            })

            logs.append(f"[{idx + 1}/{total_rows}] qid={qid} -> answer={answer}")

            progress = int(((idx + 1) / total_rows) * 100)
            progress_bar.progress(progress)

            log_placeholder.code("\n".join(logs), language="text")

            time.sleep(0.03)

        pred_df = pd.DataFrame(predictions, columns=["qid", "answer"])

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        pred_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

        logs.append(f"[SAVE] Đã ghi file: {OUTPUT_FILE}")
        logs.append("[DONE] Hoàn tất tạo pred.csv.")

        st.session_state.pred_df = pred_df
        st.session_state.logs = logs

        log_placeholder.code("\n".join(logs), language="text")
        st.success("Đã tạo xong file output/pred.csv.")

    if st.session_state.pred_df is not None:
        st.divider()

        st.subheader("Kết quả pred.csv")
        st.dataframe(st.session_state.pred_df, use_container_width=True)

        csv_bytes = st.session_state.pred_df.to_csv(
            index=False,
            encoding="utf-8",
        ).encode("utf-8")

        st.download_button(
            label="Tải pred.csv",
            data=csv_bytes,
            file_name="pred.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.subheader("Log basic")
        st.code("\n".join(st.session_state.logs), language="text")


if __name__ == "__main__":
    main()