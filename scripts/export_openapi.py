import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tsu.api import create_app  # noqa: E402

destination = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
destination.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
print(f"Exported {destination.name}")
