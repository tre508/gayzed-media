import importlib.util
from pathlib import Path
import sys


def main() -> None:
    root = Path(__file__).resolve().parent
    target = root / "updated_desktop_media_gui_no_archive_no_thumbs" / "app.py"
    if not target.is_file():
        raise FileNotFoundError(f"Missing app entrypoint at: {target}")

    module_dir = str(target.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    spec = importlib.util.spec_from_file_location("gayzed_media_app", str(target))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for: {target}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            sys.stderr.write(
                "PySide6 is not installed in the current environment.\n\n"
                "Activate your venv, then install dependencies:\n"
                "  python3 -m pip install -r requirements.txt\n"
            )
            raise SystemExit(1) from exc
        raise

    entry = getattr(module, "main", None)
    if entry is None or not callable(entry):
        raise AttributeError(f"Entrypoint 'main' not found in: {target}")

    entry()


if __name__ == "__main__":
    main()
