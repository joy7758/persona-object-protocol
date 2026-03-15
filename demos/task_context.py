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
        self.stage_progress: dict[str, str] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.stage_results: dict[str, dict[str, Any]] = {}
        self.final_deliverable: dict[str, Any] = {}

    def update_progress(
        self,
        persona_name: str,
        stage: str,
        stage_name: str | None = None,
    ) -> None:
        self.progress[persona_name] = stage
        if stage_name is not None:
            self.stage_progress[stage_name] = stage

    def set_result(
        self,
        persona_name: str,
        result: dict[str, Any],
        stage_name: str | None = None,
    ) -> None:
        self.results[persona_name] = result
        if stage_name is not None:
            self.stage_results[stage_name] = result

    def get_result(self, persona_name: str) -> dict[str, Any]:
        return self.results.get(persona_name, {})

    def get_stage_result(self, stage_name: str) -> dict[str, Any]:
        return self.stage_results.get(stage_name, {})

    def get_progress(self, persona_name: str) -> str:
        return self.progress.get(persona_name, "Not started")

    def set_final_deliverable(self, deliverable: dict[str, Any]) -> None:
        self.final_deliverable = deliverable

    def show_summary(self) -> None:
        print(f"Task: {self.task_name}")
        print(f"Task Type: {self.task_type}")
        print("Progress:")
        if self.stage_progress:
            for stage_name, stage in self.stage_progress.items():
                result = self.stage_results.get(stage_name, {})
                persona_name = result.get("persona_name", "Unknown persona")
                print(f"  {stage_name}: {stage} ({persona_name})")
        else:
            for persona, stage in self.progress.items():
                print(f"  {persona}: {stage}")
        print("Results:")
        results = self.stage_results if self.stage_results else self.results
        for key, result in results.items():
            task_output = result.get("task_output", {})
            if isinstance(task_output, dict):
                summary = task_output.get("summary", task_output)
            else:
                summary = task_output
            label = result.get("persona_name", key)
            if self.stage_results:
                label = f"{key} ({label})"
            print(f"  {label}: {summary}")

    def get_task_output(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            "task_input": self.task_input,
            "progress": self.progress,
            "stage_progress": self.stage_progress,
            "persona_outputs": self.results,
            "stage_outputs": self.stage_results,
            "final_deliverable": self.final_deliverable,
        }
