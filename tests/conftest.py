import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_module(name: str, relative_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
