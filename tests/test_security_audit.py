"""Unit test for DevSecOps secret leak audit."""
import unittest
from scripts.check_secrets import scan_for_secrets


class TestSecurityAudit(unittest.TestCase):
    """Test suite ensuring zero hardcoded secrets exist before git commits."""

    def test_no_credentials_leaked_in_codebase(self) -> None:
        """Verify that secret scan finds zero leaked credentials in repository."""
        is_clean = scan_for_secrets()
        self.assertTrue(is_clean, "Security audit failed! Check scripts/check_secrets.py output.")


if __name__ == "__main__":
    unittest.main()
