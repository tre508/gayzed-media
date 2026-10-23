import ast
import unittest
from pathlib import Path


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function not found: {name}")


def _is_self_attr_call(expr: ast.AST, attrs: list[str]) -> bool:
    if not isinstance(expr, ast.Expr):
        return False
    if not isinstance(expr.value, ast.Call):
        return False

    func = expr.value.func
    for attr in reversed(attrs):
        if not isinstance(func, ast.Attribute) or func.attr != attr:
            return False
        func = func.value
    return isinstance(func, ast.Name) and func.id == "self"


def _statement_index(func: ast.FunctionDef, attrs: list[str]) -> int:
    for idx, stmt in enumerate(func.body):
        if _is_self_attr_call(stmt, attrs):
            return idx
    return -1


class TestClearInputOnAddStatic(unittest.TestCase):
    def _assert_clears_after_add(self, file_path: Path) -> None:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        func = _find_function(tree, "add_urls_from_input")

        add_idx = _statement_index(func, ["add_urls_to_queue"])
        self.assertNotEqual(add_idx, -1, f"{file_path.name}: missing self.add_urls_to_queue(...) call")

        clear_idx = _statement_index(func, ["url_input", "clear"])
        self.assertNotEqual(clear_idx, -1, f"{file_path.name}: missing self.url_input.clear() call")

        self.assertGreater(
            clear_idx,
            add_idx,
            f"{file_path.name}: expected self.url_input.clear() after self.add_urls_to_queue(...)",
        )

    def test_app_py(self) -> None:
        self._assert_clears_after_add(Path(__file__).with_name("app.py"))

    def test_desktop_media_gui_py(self) -> None:
        self._assert_clears_after_add(Path(__file__).with_name("desktop_media_gui.py"))

    def test_updated_app_py(self) -> None:
        self._assert_clears_after_add(
            Path(__file__).with_name("updated_desktop_media_gui_no_archive_no_thumbs")
            / "app.py"
        )

    def test_updated_desktop_media_gui_py(self) -> None:
        self._assert_clears_after_add(
            Path(__file__).with_name("updated_desktop_media_gui_no_archive_no_thumbs")
            / "desktop_media_gui.py"
        )


if __name__ == "__main__":
    unittest.main()
