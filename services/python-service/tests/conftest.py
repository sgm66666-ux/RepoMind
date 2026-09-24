from pathlib import Path
import sys

SERVICE_ROOT = Path(__file__).parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
