"""CLI Script to trigger the ETL Pipeline locally or in AWS."""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.pipeline import main

if __name__ == "__main__":
    main()
