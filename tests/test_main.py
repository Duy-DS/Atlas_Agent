import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from agents.web_search import StaticWebSearch


class MainOutputTest(unittest.TestCase):
    def test_build_predictions_keeps_valid_answers_and_marks_invalid_or_missing_na(self):
        questions = "qid,question,A,B,C,D\n1,one,a,b,c,d\n2,two,a,b,c,d\n3,three,a,b,c,d\n"
        model_output = "qid,answer\n1,A\n2,E\n"

        rows = main.build_predictions(questions, model_output)

        self.assertEqual(
            rows,
            [
                {"qid": "1", "answer": "A"},
                {"qid": "2", "answer": "N/A"},
                {"qid": "3", "answer": "N/A"},
            ],
        )

    def test_run_batches_questions_and_writes_pred_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,one,a,b,c,d\n"
                "2,two,a,b,c,d\n"
                "3,three,a,b,c,d\n",
                encoding="utf-8",
            )
            calls = []

            def fake_agent(prompt):
                calls.append(prompt)
                if "3,three" in prompt:
                    return "qid,answer\n3,C\n"
                return "qid,answer\n1,A\n2,B\n"

            with patch.object(main, "agent", fake_agent):
                result_path = main.run(input_path=input_path, output_path=output_path, batch_size=2)

            self.assertEqual(result_path, output_path)
            self.assertEqual(len(calls), 2)
            self.assertIn("1,one", calls[0])
            self.assertIn("2,two", calls[0])
            self.assertIn("3,three", calls[1])
            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [
                        {"qid": "1", "answer": "A"},
                        {"qid": "2", "answer": "B"},
                        {"qid": "3", "answer": "C"},
                    ],
                )
            audit_path = output_path.with_name("pred_audit.csv")
            with audit_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [
                        {"qid": "1", "answer": "A", "confidence": "0.90", "needs_search": "false", "search_used": "false"},
                        {"qid": "2", "answer": "B", "confidence": "0.90", "needs_search": "false", "search_used": "false"},
                        {"qid": "3", "answer": "C", "confidence": "0.90", "needs_search": "false", "search_used": "false"},
                    ],
                )

    def test_run_retries_missing_or_invalid_rows_one_by_one_with_one_retry_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,one,a,b,c,d\n"
                "2,two,a,b,c,d\n"
                "3,three,a,b,c,d\n",
                encoding="utf-8",
            )
            calls = []

            def fake_agent(prompt):
                calls.append(prompt)
                if len(calls) == 1:
                    return "qid,answer\n1,A\n2,E\n"
                if "2,two" in prompt:
                    return "qid,answer\n2,B\n"
                return "qid,answer\n3,C\n"

            with patch.object(main, "agent", fake_agent):
                main.run(input_path=input_path, output_path=output_path, batch_size=3)

            self.assertEqual(len(calls), 3)
            self.assertIn("Chi tra ve dung 2 dong CSV", calls[1])
            self.assertIn("Chi tra ve dung 2 dong CSV", calls[2])
            self.assertNotIn("1,one", calls[1])
            self.assertIn("2,two", calls[1])
            self.assertNotIn("3,three", calls[1])
            self.assertIn("3,three", calls[2])
            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [
                        {"qid": "1", "answer": "A"},
                        {"qid": "2", "answer": "B"},
                        {"qid": "3", "answer": "C"},
                    ],
                )


    def test_parse_model_answers_handles_preamble_and_colon_rows(self):
        output = "dau ra:\nqid,answer  \n5:A\n6, B\n"

        self.assertEqual(main.parse_model_answers(output), {"5": "A", "6": "B"})


    def test_predict_single_retry_uses_one_forced_call(self):
        row = {"qid": "4", "question": "one", "A": "a", "B": "b", "C": "c", "D": "d"}
        calls = []

        def fake_agent(prompt):
            calls.append(prompt)
            return "dau ra:\nqid,answer\n1,B"

        with patch.object(main, "agent", fake_agent):
            self.assertEqual(main.predict_single_retry(row), "B")

        self.assertEqual(len(calls), 1)
        self.assertIn("Chi tra ve dung 2 dong CSV", calls[0])

    def test_predict_batch_single_row_uses_only_valid_answer_when_qid_is_wrong(self):
        row = {"qid": "4", "question": "one", "A": "a", "B": "b", "C": "c", "D": "d"}
        model_output = "dau ra:\nqid,answer\n1,B"

        with patch.object(main, "agent", return_value=model_output):
            self.assertEqual(main.predict_batch([row]), {"4": "B"})

    def test_predict_batch_extracts_single_prose_answer_when_model_ignores_csv(self):
        row = {"qid": "1", "question": "one", "A": "a", "B": "b", "C": "c", "D": "d"}
        prose_output = "**KẾT LUẬN**:\nĐáp án đúng là **C**."

        with patch.object(main, "agent", return_value=prose_output):
            self.assertEqual(main.predict_batch([row]), {"1": "C"})


    def test_audit_marks_current_questions_as_needing_search(self):
        row = {"qid": "9", "question": "CEO hiện nay là ai?", "A": "a", "B": "b", "C": "c", "D": "d"}

        audit = main.build_audit_rows([row], {"9": "A"})

        self.assertEqual(audit, [{"qid": "9", "answer": "A", "confidence": "0.40", "needs_search": "true", "search_used": "false"}])


    def test_audit_marks_search_used_qids(self):
        row = {"qid": "9", "question": "CEO hiện nay là ai?", "A": "a", "B": "b", "C": "c", "D": "d"}

        audit = main.build_audit_rows([row], {"9": "A"}, {"9"})

        self.assertEqual(audit, [{"qid": "9", "answer": "A", "confidence": "0.40", "needs_search": "true", "search_used": "true"}])


    def test_run_searches_rows_marked_needs_search_when_search_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,CEO hiện nay là ai?,a,b,c,d\n",
                encoding="utf-8",
            )
            search = StaticWebSearch({"CEO hiện nay là ai?": "Nguồn web: đáp án là C."})
            calls = []

            def fake_agent(prompt):
                calls.append(prompt)
                if "Nguon canh web" in prompt or "Ngu canh web" in prompt:
                    return "qid,answer\n1,C\n"
                return "qid,answer\n1,A\n"

            with patch.object(main, "agent", fake_agent):
                main.run(input_path=input_path, output_path=output_path, batch_size=1, search_client=search)

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "C"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "C", "confidence": "0.40", "needs_search": "true", "search_used": "true"}],
                )


    def test_run_reads_utf8_sig_csv_with_bom_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "\ufeffqid,question,A,B,C,D\n"
                "1,one,a,b,c,d\n",
                encoding="utf-8",
            )

            with patch.object(main, "agent", return_value="qid,answer\n1,A\n"):
                main.run(input_path=input_path, output_path=output_path, batch_size=1)

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "A"}])



if __name__ == "__main__":
    unittest.main()
