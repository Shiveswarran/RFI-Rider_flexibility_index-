from pathlib import Path

import nbformat
from nbclient import NotebookClient


project_dir = Path(__file__).resolve().parent
notebook_path = project_dir / "data_analysis_pattern_Classtran_two_indexes.ipynb"
notebook = nbformat.read(notebook_path, as_version=4)
client = NotebookClient(
    notebook,
    timeout=1200,
    kernel_name="python3",
    resources={"metadata": {"path": str(project_dir)}},
)
client.execute()
nbformat.write(notebook, notebook_path)
print(f"Executed and saved {notebook_path}")
