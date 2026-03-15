from __future__ import annotations


class TaskContext:
    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        self.progress: dict[str, str] = {}
        self.results: dict[str, str] = {}

    def update_progress(self, persona_name: str, stage: str) -> None:
        self.progress[persona_name] = stage

    def set_result(self, persona_name: str, result: str) -> None:
        self.results[persona_name] = result

    def get_result(self, persona_name: str) -> str:
        return self.results.get(persona_name, "No result yet")

    def get_progress(self, persona_name: str) -> str:
        return self.progress.get(persona_name, "Not started")

    def show_summary(self) -> None:
        print(f"Task: {self.task_name}")
        print("Progress:")
        for persona, stage in self.progress.items():
            print(f"  {persona}: {stage}")
        print("Results:")
        for persona, result in self.results.items():
            print(f"  {persona}: {result}")
