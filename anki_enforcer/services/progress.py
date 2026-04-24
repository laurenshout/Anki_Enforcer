from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ProgressStatus:
    complete: bool
    reason: str
    remaining_cards: int = 0


class ProgressTracker:
    def get_status(self, mw: Any, config: dict[str, Any]) -> ProgressStatus:
        if not config.get("enabled", False):
            return ProgressStatus(True, "Add-on is disabled.")

        required_decks = config.get("required_deck_ids") or []
        if not required_decks:
            return ProgressStatus(True, "No required decks selected.")

        if not getattr(mw, "col", None):
            return ProgressStatus(False, "Collection is not ready yet.")

        remaining_by_deck = self._remaining_cards_by_selected_deck(mw, required_decks)
        if remaining_by_deck is None:
            return ProgressStatus(False, "Could not determine remaining cards yet.")

        total_remaining = sum(max(0, count) for count in remaining_by_deck.values())
        if total_remaining <= 0:
            return ProgressStatus(
                True,
                "No more cards left to do today in the required deck(s).",
                remaining_cards=0,
            )

        details = self._format_remaining_details(mw, remaining_by_deck)
        reason = f"{total_remaining} card(s) left to do today in required deck(s)."
        if details:
            reason = f"{reason} {details}"
        return ProgressStatus(False, reason, remaining_cards=total_remaining)

    def _remaining_cards_by_selected_deck(
        self, mw: Any, required_decks: list[int]
    ) -> Optional[dict[int, int]]:
        selected_ids = [int(deck_id) for deck_id in required_decks]

        # Prefer scheduler/deck-browser counts because they match Anki's "New/Learn/Due"
        # daily availability semantics (search `is:new` overcounts all unseen new cards).
        from_sched = self._remaining_from_scheduler_tree(mw, selected_ids)
        if from_sched is not None:
            return from_sched

        return self._remaining_from_search(mw, selected_ids)

    def _remaining_from_scheduler_tree(
        self, mw: Any, selected_ids: list[int]
    ) -> Optional[dict[int, int]]:
        col = getattr(mw, "col", None)
        sched = getattr(col, "sched", None)
        if sched is None:
            return None

        tree = None
        for name in ("deck_due_tree", "deckDueTree", "due_tree"):
            fn = getattr(sched, name, None)
            if callable(fn):
                try:
                    tree = fn()
                    break
                except Exception:
                    continue

        if tree is None:
            return None

        counts_by_deck: dict[int, int] = {}
        self._walk_due_tree(tree, counts_by_deck)
        if not counts_by_deck:
            return None

        return {deck_id: max(0, int(counts_by_deck.get(deck_id, 0))) for deck_id in selected_ids}

    def _walk_due_tree(self, node: Any, counts_by_deck: dict[int, int]) -> None:
        if node is None:
            return

        if self._is_node_iterable(node):
            for item in node:
                self._walk_due_tree(item, counts_by_deck)
            return

        if isinstance(node, dict):
            deck_id = self._first_int(
                node.get("deck_id"),
                node.get("deckId"),
                node.get("id"),
            )
            if deck_id is not None:
                counts_by_deck[deck_id] = self._node_remaining_count(node)

            for key in ("children", "child_nodes", "items", "nodes"):
                children = node.get(key)
                if self._is_node_iterable(children):
                    self._walk_due_tree(children, counts_by_deck)
            return

        deck_id = self._first_int(
            getattr(node, "deck_id", None),
            getattr(node, "deckId", None),
            getattr(node, "id", None),
        )
        if deck_id is not None:
            counts_by_deck[deck_id] = self._node_remaining_count(node)

        for attr in ("children", "child_nodes", "items", "nodes"):
            children = getattr(node, attr, None)
            if self._is_node_iterable(children):
                self._walk_due_tree(children, counts_by_deck)

    def _node_remaining_count(self, node: Any) -> int:
        return (
            self._coerce_nonnegative_int(self._get(node, "new_count", "newCount", "new"))
            + self._coerce_nonnegative_int(
                self._get(
                    node,
                    "learn_count",
                    "learnCount",
                    "learning_count",
                    "learningCount",
                    "learn",
                )
            )
            + self._coerce_nonnegative_int(
                self._get(node, "review_count", "reviewCount", "review")
            )
        )

    def _remaining_from_search(self, mw: Any, selected_ids: list[int]) -> Optional[dict[int, int]]:
        col = getattr(mw, "col", None)
        if col is None:
            return None

        find_cards = getattr(col, "find_cards", None)
        if not callable(find_cards):
            find_cards = getattr(col, "findCards", None)
        if not callable(find_cards):
            return None

        result: dict[int, int] = {}
        for deck_id in selected_ids:
            deck_name = self._deck_name(mw, deck_id)
            if not deck_name:
                result[deck_id] = 0
                continue

            # Fallback approximation when scheduler due-tree APIs are unavailable.
            # `is:due` avoids overcounting all unseen new cards (which can happen with `is:new`).
            escaped_name = deck_name.replace('"', '\\"')
            query = f'deck:"{escaped_name}" is:due'
            try:
                cards = find_cards(query) or []
            except Exception:
                return None
            result[deck_id] = len(cards)

        return result

    def _deck_name(self, mw: Any, deck_id: int) -> Optional[str]:
        col = getattr(mw, "col", None)
        decks = getattr(col, "decks", None)
        if decks is None:
            return None

        for getter in ("name", "name_if_exists"):
            fn = getattr(decks, getter, None)
            if callable(fn):
                try:
                    name = fn(int(deck_id))
                    if name:
                        return str(name)
                except Exception:
                    pass

        get_fn = getattr(decks, "get", None)
        if callable(get_fn):
            try:
                deck = get_fn(int(deck_id))
            except Exception:
                deck = None
            if isinstance(deck, dict):
                name = deck.get("name")
                if name:
                    return str(name)

        return None

    def _format_remaining_details(self, mw: Any, remaining_by_deck: dict[int, int]) -> str:
        nonzero = [(deck_id, count) for deck_id, count in remaining_by_deck.items() if count > 0]
        if not nonzero:
            return ""

        nonzero.sort(key=lambda item: item[1], reverse=True)
        top = nonzero[:3]
        parts: list[str] = []
        for deck_id, count in top:
            name = self._deck_name(mw, deck_id) or f"Deck {deck_id}"
            parts.append(f"{name}: {count}")
        extra = len(nonzero) - len(top)
        suffix = f" (+{extra} more)" if extra > 0 else ""
        return "Remaining by deck: " + ", ".join(parts) + suffix

    def _get(self, node: Any, *keys: str) -> Any:
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    return node[key]
            return None

        for key in keys:
            if hasattr(node, key):
                return getattr(node, key)
        return None

    def _coerce_nonnegative_int(self, value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def _first_int(self, *values: Any) -> Optional[int]:
        for value in values:
            try:
                if value is None:
                    continue
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    def _is_node_iterable(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (str, bytes, dict)):
            return False
        return isinstance(value, Iterable)
