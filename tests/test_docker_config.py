"""Unit tests for Docker configuration and security practices."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDockerConfig(unittest.TestCase):
    """Test suite ensuring Dockerfile and .dockerignore adhere to cloud standards."""

    def test_dockerfile_exists_and_contains_best_practices(self) -> None:
        """Verify that Dockerfile exists and enforces non-root user and healthchecks."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        self.assertTrue(dockerfile.exists(), "Dockerfile is missing.")

        content = dockerfile.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11", content)
        self.assertIn("USER appuser", content, "Dockerfile must run as non-root user.")
        self.assertIn("EXPOSE 8501", content)
        self.assertIn("HEALTHCHECK", content, "Dockerfile should include HEALTHCHECK for cloud hosting.")
        self.assertIn("app.py", content)

    def test_dockerignore_excludes_secrets_and_caches(self) -> None:
        """Verify that .dockerignore blocks .env, venv, and cache files from entering image."""
        dockerignore = PROJECT_ROOT / ".dockerignore"
        self.assertTrue(dockerignore.exists(), ".dockerignore is missing.")

        content = dockerignore.read_text(encoding="utf-8")
        self.assertIn(".env", content, "CRITICAL: .dockerignore must ignore .env files.")
        self.assertIn("venv", content, ".dockerignore must ignore local virtual environments.")
        self.assertIn("__pycache__", content)


if __name__ == "__main__":
    unittest.main()
