"""Execute the EDA notebook in place and fail on any cell error."""

from __future__ import annotations

import os
import ast
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "eda.ipynb"


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
    os.environ.setdefault("IPYTHONDIR", str(ROOT / ".ipython"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["IPYTHONDIR"]).mkdir(parents=True, exist_ok=True)
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            try:
                ast.parse(cell.source)
            except SyntaxError as exc:
                raise SyntaxError(f"Notebook code cell {index} is invalid: {exc}") from exc
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    client.execute()
    nbformat.write(notebook, NOTEBOOK)
    print(f"Executed {NOTEBOOK}")


if __name__ == "__main__":
    main()
