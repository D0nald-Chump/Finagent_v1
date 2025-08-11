from __future__ import annotations

import json
from pathlib import Path

from finagent.config import MODEL_NAME, PRICING
from finagent.costing import COST_LOG, summarize_cost
from finagent.graph import build_parent_graph
from finagent.state import State


def run_pipeline(initial_state: State | None = None) -> State:
    parent = build_parent_graph()
    app = parent.compile()

    # Optional: visualize mermaid if desired (skipped in CLI run)
    # _ = app.get_graph(xray=True).draw_mermaid_png()

    state: State = initial_state or {}
    final_state = app.invoke(state)
    return final_state


def print_report(state: State) -> None:
    print("\n=== Final Report (markdown) ===\n")
    print(state.get("final_report", "<no report>"))

    print("\n=== Cost Items ===")
    for item in COST_LOG:
        print(
            item["node"],
            item["role"],
            "→",
            f"in={item['input_tokens']}, out={item['output_tokens']},",
            f"cost=${item['total_cost']:.4f}",
        )

    print("\n=== Total Cost Summary ===")
    print(json.dumps(summarize_cost(), indent=2))


def export_run_as_notebook(ipynb_path: Path) -> None:
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    cells = []
    cells.append(
        nbf.v4.new_markdown_cell(
            """# Finagent Main Run\n\n此 notebook 由 `main.py` 自动生成，复现一次完整运行。"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """
from finagent.graph import build_parent_graph
from finagent.state import State
from finagent.costing import COST_LOG, summarize_cost

parent = build_parent_graph()
app = parent.compile()
initial_state: State = {}
final_state = app.invoke(initial_state)

print("\n=== Final Report (markdown) ===\n")
print(final_state.get("final_report","<no report>"))

print("\n=== Cost Items ===")
for item in COST_LOG:
    print(item["node"], item["role"], "→",
          f"in={item['input_tokens']}, out={item['output_tokens']},",
          f"cost=${item['total_cost']:.4f}")

print("\n=== Total Cost Summary ===")
print(summarize_cost())
""".strip()
        )
    )

    nb["cells"] = cells
    ipynb_path.write_text(nbf.writes(nb), encoding="utf-8")


def main() -> None:
    final_state = run_pipeline({})
    print_report(final_state)
    export_run_as_notebook(Path("main.ipynb"))


if __name__ == "__main__":
    main()


