"""Unit tests for the Streamlit Application interface."""
import unittest
import importlib


class TestApp(unittest.TestCase):
    """Test suite ensuring app.py imports and runs cleanly."""

    def test_app_module_imports(self) -> None:
        """Verify that app.py imports without syntax errors or missing packages."""
        app_mod = importlib.import_module("app")
        self.assertIsNotNone(app_mod)
        self.assertTrue(hasattr(app_mod, "main"))
        self.assertTrue(hasattr(app_mod, "get_engine"))


if __name__ == "__main__":
    unittest.main()
