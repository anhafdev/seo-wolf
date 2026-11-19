import ast
import io
import tokenize
from pathlib import Path

import pytest

__author__ = "@anhafxd"

REPOSITORY = Path(__file__).resolve().parent.parent
PYTHON_FILES = sorted(
    path
    for folder in ("seowolf", "tests")
    for path in (REPOSITORY / folder).rglob("*.py")
    if "__pycache__" not in path.parts
)
WATERMARK = '__author__ = "@anhafxd"'
MAX_LINES = 200


def short_name(path: Path) -> str:
    return str(path.relative_to(REPOSITORY))


@pytest.mark.parametrize("path", PYTHON_FILES, ids=short_name)
def test_file_carries_the_watermark(path: Path) -> None:
    assert WATERMARK in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", PYTHON_FILES, ids=short_name)
def test_file_stays_within_line_budget(path: Path) -> None:
    assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_LINES


@pytest.mark.parametrize("path", PYTHON_FILES, ids=short_name)
def test_file_has_no_comments(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    assert not [token.string for token in tokens if token.type == tokenize.COMMENT]


@pytest.mark.parametrize("path", PYTHON_FILES, ids=short_name)
def test_file_has_no_docstrings(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    documented = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    nodes = [node for node in ast.walk(tree) if isinstance(node, documented)]
    assert not [node for node in nodes if ast.get_docstring(node) is not None]


@pytest.mark.parametrize("path", PYTHON_FILES, ids=short_name)
def test_file_has_no_placeholder_bodies(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Pass)]
    assert "TO" + "DO" not in path.read_text(encoding="utf-8")
