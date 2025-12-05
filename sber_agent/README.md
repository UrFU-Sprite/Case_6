Sber Инвестиции — 1st-line support agent (Python)

Usage

1. Create a virtualenv and install dependencies (Windows PowerShell):

```powershell
python -m venv .venv;
.\.venv\Scripts\Activate.ps1;
pip install -r requirements.txt
```

2. Run the CLI (from workspace root):

```powershell
python -m sber_agent.cli
```

Behavior

- Answers user questions when the vector DB contains a high-confidence match.
- Escalates to L2 or L3 when confidence is insufficient.
- Marks queries as out-of-scope when no relevant information is found.

Notes

- The project uses `sentence-transformers` to compute embeddings locally.
- If `faiss` is available it will be used for faster search; otherwise, a brute-force numpy search is used.
