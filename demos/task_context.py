from __future__ import annotations

from typing import Any


class TaskContext:
    def __init__(
        self,
        task_name: str,
        task_type: str = "market_research",
        task_input: dict[str, Any] | None = None,
    ) -> None:
        self.task_name = task_name
        self.task_type = task_type
        self.task_input = task_input or {}
        self.progress: dict[str, str] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.final_deliverable: dict[str, Any] = {}

    def update_progress(self, persona_name: str, stage: str) -> None:
        self.progress[persona_name] = stage

    def set_result(self, persona_name: str, result: dict[str, Any]) -> None:
        self.results[persona_name] = result

    def get_result(self, persona_name: str) -> dict[str, Any]:
        return self.results.get(persona_name, {})

    def get_progress(self, persona_name: str) -> str:
        return self.progress.get(persona_name, "Not started")

    def set_final_deliverable(self, deliverable: dict[str, Any]) -> None:
        self.final_deliverable = deliverable

    def show_summary(self) -> None:
        print(f"Task: {self.task_name}")
        print(f"Task Type: {self.task_type}")
        print("Progress:")
        for persona, stage in self.progress.items():
            print(f"  {persona}: {stage}")
        print("Results:")
        for persona, result in self.results.items():
            task_output = result.get("task_output", {})
            if isinstance(task_output, dict):
                summary = task_output.get("summary", task_output)
            else:
                summary = task_output
            print(f"  {persona}: {summary}")

    def get_task_output(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            "task_input": self.task_input,
            "progress": self.progress,
            "persona_outputs": self.results,
            "final_deliverable": self.final_deliverable,
        }
