import unittest
from pathlib import Path


class DockerConfigTest(unittest.TestCase):
    def test_main_uses_environment_default_paths(self):
        main_source = Path("main.py").read_text(encoding="utf-8")

        self.assertIn('PUBLIC_QUESTION = Path(os.getenv("INPUT_CSV", BASE_DIR / "data" / "public_test.csv"))', main_source)
        self.assertIn('PREDICTION_OUTPUT = Path(os.getenv("OUTPUT_CSV", BASE_DIR / "output" / "pred.csv"))', main_source)
        self.assertIn('AUDIT_OUTPUT = Path(os.getenv("AUDIT_CSV", BASE_DIR / "output" / "pred_audit.csv"))', main_source)

    def test_entrypoint_uses_configured_paths_and_waits_for_ollama(self):
        entrypoint = Path("entrypoints.sh").read_text(encoding="utf-8")

        self.assertIn("${INPUT_CSV:-/data/public_test.csv}", entrypoint)
        self.assertIn("${OUTPUT_CSV:-/output/pred.csv}", entrypoint)
        self.assertIn("mkdir -p \"$(dirname \"$OUTPUT_CSV\")\"", entrypoint)
        self.assertIn("OLLAMA_BASE_URL", entrypoint)
        self.assertIn("/api/tags", entrypoint)

    def test_dockerfile_installs_curl_and_uses_entrypoint(self):
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

        self.assertIn("apt-get update", dockerfile)
        self.assertIn("apt-get install -y --no-install-recommends curl", dockerfile)
        self.assertIn('ENTRYPOINT ["/app/entrypoints.sh"]', dockerfile)

    def test_compose_defines_cpu_stack_with_healthcheck_and_outputs(self):
        compose = Path("docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("atlas-ollama", compose)
        self.assertIn("atlas-agent", compose)
        self.assertIn("healthcheck:", compose)
        self.assertIn("condition: service_healthy", compose)
        self.assertIn("./data:/data:ro", compose)
        self.assertIn("./output:/output", compose)
        self.assertIn("INPUT_CSV=${INPUT_CSV:-/data/public_test.csv}", compose)
        self.assertIn("OUTPUT_CSV=${OUTPUT_CSV:-/output/pred.csv}", compose)
        self.assertIn("AUDIT_CSV=${AUDIT_CSV:-/output/pred_audit.csv}", compose)
        self.assertIn("$${MODEL_NAME}", compose)

    def test_gpu_compose_only_overrides_ollama_gpu_runtime(self):
        gpu_compose = Path("docker-compose.gpu.yml").read_text(encoding="utf-8")

        self.assertIn("ollama:", gpu_compose)
        self.assertIn("driver: nvidia", gpu_compose)
        self.assertIn("NVIDIA_VISIBLE_DEVICES=all", gpu_compose)
        self.assertNotIn("app:", gpu_compose)

    def test_env_example_documents_compose_runtime_knobs(self):
        env_example = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("MODEL_NAME=qwen3.5:0.8b", env_example)
        self.assertIn("BATCH_SIZE=20", env_example)
        self.assertIn("OLLAMA_NUM_PREDICT=512", env_example)
        self.assertIn("INPUT_CSV=/data/public_test.csv", env_example)
        self.assertIn("OUTPUT_CSV=/output/pred.csv", env_example)
        self.assertIn("AUDIT_CSV=/output/pred_audit.csv", env_example)
        self.assertIn("WEB_SEARCH_ENABLED=false", env_example)

    def test_readme_documents_compose_cpu_gpu_and_outputs(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("docker compose up --build", readme)
        self.assertIn("docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build", readme)
        self.assertIn("data/public_test.csv", readme)
        self.assertIn("output/pred.csv", readme)
        self.assertIn("output/pred_audit.csv", readme)

    def test_docker_usage_doc_covers_required_workflow(self):
        doc = Path("docs/docker_compose_usage.md").read_text(encoding="utf-8")

        self.assertIn("# Docker Compose Usage", doc)
        self.assertIn("data/public_test.csv", doc)
        self.assertIn("docker compose up --build", doc)
        self.assertIn("docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build", doc)
        self.assertIn("output/pred.csv", doc)
        self.assertIn("output/pred_audit.csv", doc)


if __name__ == "__main__":
    unittest.main()
