from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from pop_cockpit.schemas import DailyExtractionRequest, DailyPersonaSnapshotDraft

STOPWORDS = {
    "about",
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "you",
    "your",
}

TRAIT_RULES: list[tuple[str, list[str], str]] = [
    ("local_first", ["local-first", "local first"], "prefers local-first systems"),
    ("simple", ["simple", "simplicity"], "leans toward simple implementations"),
    ("readable", ["readable", "clarity", "clear"], "cares about readable outputs"),
    ("test", ["test", "verify", "validated", "deterministic"], "shows verification-oriented behavior"),
    ("practical", ["practical", "useful", "ship"], "optimizes for practical outcomes"),
]

EMOTION_RULES: list[tuple[str, list[str]]] = [
    ("urgency", ["urgent", "asap", "immediately"]),
    ("confidence", ["confident", "clear", "certain"]),
    ("concern", ["worried", "concerned", "anxious", "stress", "stressed"]),
    ("frustration", ["frustrated", "annoyed", "blocked"]),
    ("motivation", ["excited", "motivated", "energized"]),
    ("calm", ["calm", "steady", "stable"]),
]

DECISION_KEYWORDS = ["decide", "decision", "choose", "chosen", "will", "plan", "must", "should"]
FOCUS_KEYWORDS = ["focus", "working on", "building", "priority", "goal", "today", "now"]


class DailyExtractionProvider:
    name = "provider"

    def extract_daily(self, request: DailyExtractionRequest) -> DailyPersonaSnapshotDraft:
        raise NotImplementedError


@dataclass(slots=True)
class MockDailyExtractionProvider(DailyExtractionProvider):
    response: DailyPersonaSnapshotDraft
    name: str = "mock"

    def extract_daily(self, request: DailyExtractionRequest) -> DailyPersonaSnapshotDraft:
        return self.response.model_copy(deep=True)


class LocalFallbackDailyExtractionProvider(DailyExtractionProvider):
    name = "local_fallback"

    def extract_daily(self, request: DailyExtractionRequest) -> DailyPersonaSnapshotDraft:
        records = request.records
        source_record_ids = [record.id for record in records]
        combined_text = "\n".join(record.content for record in records)
        normalized_lines = self._extract_lines(combined_text)
        keyword_counts = self._keyword_counts(combined_text)

        recurring_topics = self._top_keywords(keyword_counts, limit=5)
        goal_priority = self._goal_priority(normalized_lines, recurring_topics)
        current_focus = self._current_focus(normalized_lines, recurring_topics)
        decision_style = self._decision_style(combined_text)
        risk_profile = self._risk_profile(combined_text)
        stable_biases = self._stable_biases(combined_text)
        emotional_signals = self._emotional_signals(combined_text)
        new_traits = self._new_traits(combined_text)
        important_decisions = self._important_decisions(normalized_lines)
        confidence_notes = [
            f"Local heuristic snapshot derived from {len(records)} imported records.",
            "No external model was used; repeated keywords and explicit intent phrases drove the extraction.",
        ]

        return DailyPersonaSnapshotDraft(
            date_range=request.date_range,
            source_record_ids=source_record_ids,
            goal_priority=goal_priority,
            current_focus=current_focus,
            decision_style=decision_style,
            risk_profile=risk_profile,
            recurring_topics=recurring_topics,
            stable_biases=stable_biases,
            emotional_signals=emotional_signals,
            new_traits=new_traits,
            important_decisions=important_decisions,
            confidence_notes=confidence_notes,
            provider_name=self.name,
            metadata={"record_count": len(records)},
        )

    def _extract_lines(self, combined_text: str) -> list[str]:
        lines = [line.strip() for line in combined_text.splitlines()]
        return [line for line in lines if line]

    def _keyword_counts(self, combined_text: str) -> Counter[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z\\-]{2,}", combined_text.lower())
        filtered_tokens = [token for token in tokens if token not in STOPWORDS]
        return Counter(filtered_tokens)

    def _top_keywords(self, keyword_counts: Counter[str], limit: int) -> list[str]:
        repeated = {keyword: count for keyword, count in keyword_counts.items() if count > 1}
        selected_counts = repeated or keyword_counts
        ordered = sorted(selected_counts.items(), key=lambda item: (-item[1], item[0]))
        return [keyword for keyword, _ in ordered[:limit]]

    def _goal_priority(self, lines: list[str], recurring_topics: list[str]) -> list[str]:
        explicit_goals = self._match_lines(lines, ["priority", "goal", "must", "need to", "should"])
        if explicit_goals:
            return explicit_goals[:3]
        return [f"Advance work related to {topic}" for topic in recurring_topics[:3]]

    def _current_focus(self, lines: list[str], recurring_topics: list[str]) -> list[str]:
        focus_lines = self._match_lines(lines, FOCUS_KEYWORDS)
        if focus_lines:
            return focus_lines[:3]
        return recurring_topics[:3]

    def _decision_style(self, combined_text: str) -> str:
        lowered = combined_text.lower()
        if any(keyword in lowered for keyword in ("compare", "evaluate", "analyze", "tradeoff")):
            return "analytical and comparison-driven"
        if any(keyword in lowered for keyword in ("test", "iterate", "prototype", "experiment")):
            return "iterative and experiment-driven"
        if any(keyword in lowered for keyword in ("must", "ship", "execute", "deadline")):
            return "execution-focused and decisive"
        return "structured, based on explicit written priorities"

    def _risk_profile(self, combined_text: str) -> str:
        lowered = combined_text.lower()
        cautious_score = sum(lowered.count(keyword) for keyword in ("risk", "safe", "careful", "validate"))
        bold_score = sum(lowered.count(keyword) for keyword in ("bold", "bet", "aggressive", "move fast"))
        if cautious_score > bold_score:
            return "cautious and validation-oriented"
        if bold_score > cautious_score:
            return "more willing to take directional bets"
        return "balanced with limited explicit risk signals"

    def _stable_biases(self, combined_text: str) -> list[str]:
        lowered = combined_text.lower()
        biases: list[str] = []
        if "local-first" in lowered or "local first" in lowered:
            biases.append("local-first preference")
        if "simple" in lowered or "readable" in lowered:
            biases.append("preference for simple, readable systems")
        if "verify" in lowered or "test" in lowered or "deterministic" in lowered:
            biases.append("bias toward verification and determinism")
        return biases[:3]

    def _emotional_signals(self, combined_text: str) -> list[str]:
        lowered = combined_text.lower()
        signals = [label for label, keywords in EMOTION_RULES if any(keyword in lowered for keyword in keywords)]
        return signals[:5]

    def _new_traits(self, combined_text: str) -> list[str]:
        lowered = combined_text.lower()
        traits = [label for _, keywords, label in TRAIT_RULES if any(keyword in lowered for keyword in keywords)]
        return traits[:4]

    def _important_decisions(self, lines: list[str]) -> list[str]:
        decisions = self._match_lines(lines, DECISION_KEYWORDS)
        return decisions[:5]

    def _match_lines(self, lines: list[str], keywords: list[str]) -> list[str]:
        matched: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if self._looks_like_json_property(line):
                continue
            lowered = line.lower()
            if any(keyword in lowered for keyword in keywords):
                if line not in seen:
                    seen.add(line)
                    matched.append(line)
        return matched

    def _looks_like_json_property(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith('"') and '":' in stripped
