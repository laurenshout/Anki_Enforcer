from __future__ import annotations

import unittest

from anki_enforcer.services.progress import ProgressTracker


class FakeDecks:
    def __init__(self, names: dict[int, str]) -> None:
        self._names = names

    def name(self, deck_id: int) -> str | None:
        return self._names.get(deck_id)

    def get(self, deck_id: int) -> dict[str, str]:
        return {"name": self._names.get(deck_id, "")}


class FakeScheduler:
    def __init__(self, tree: object) -> None:
        self._tree = tree

    def deck_due_tree(self) -> object:
        return self._tree


class FakeCollection:
    def __init__(
        self,
        deck_names: dict[int, str],
        due_tree: object | None = None,
        search_results: dict[str, list[int]] | None = None,
    ) -> None:
        self.decks = FakeDecks(deck_names)
        self.sched = FakeScheduler(due_tree) if due_tree is not None else None
        self._search_results = search_results or {}

    def find_cards(self, query: str) -> list[int]:
        return list(self._search_results.get(query, []))


class FakeMainWindow:
    def __init__(self, col: object | None) -> None:
        self.col = col


class ProgressTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = ProgressTracker()

    def test_disabled_addon_is_always_complete(self) -> None:
        status = self.tracker.get_status(FakeMainWindow(col=None), {"enabled": False})
        self.assertTrue(status.complete)
        self.assertEqual(status.reason, "Add-on is disabled.")

    def test_scheduler_tree_counts_cards_and_formats_reason(self) -> None:
        mw = FakeMainWindow(
            FakeCollection(
                deck_names={1: "Core Deck", 2: "Side Deck"},
                due_tree=[
                    {"deck_id": 1, "new_count": 1, "learn_count": 2, "review_count": 3},
                    {"deckId": 2, "new": 0, "learn": 1, "review": 0},
                ],
            )
        )

        status = self.tracker.get_status(
            mw,
            {"enabled": True, "required_deck_ids": [1, 2]},
        )

        self.assertFalse(status.complete)
        self.assertEqual(status.remaining_cards, 7)
        self.assertIn("7 card(s) left", status.reason)
        self.assertIn("Core Deck: 6", status.reason)
        self.assertIn("Side Deck: 1", status.reason)

    def test_search_fallback_escapes_quotes_in_deck_name(self) -> None:
        query = 'deck:"Biology \\"A\\"" is:due'
        mw = FakeMainWindow(
            FakeCollection(
                deck_names={5: 'Biology "A"'},
                due_tree=None,
                search_results={query: [1, 2, 3]},
            )
        )

        status = self.tracker.get_status(
            mw,
            {"enabled": True, "required_deck_ids": [5]},
        )

        self.assertFalse(status.complete)
        self.assertEqual(status.remaining_cards, 3)
        self.assertIn("Biology \"A\": 3", status.reason)

    def test_missing_collection_reports_not_ready(self) -> None:
        status = self.tracker.get_status(
            FakeMainWindow(col=None),
            {"enabled": True, "required_deck_ids": [1]},
        )

        self.assertFalse(status.complete)
        self.assertEqual(status.reason, "Collection is not ready yet.")

    def test_no_remaining_cards_marks_complete(self) -> None:
        mw = FakeMainWindow(
            FakeCollection(deck_names={1: "Done Deck"}, due_tree=[{"deck_id": 1, "review_count": 0}])
        )

        status = self.tracker.get_status(
            mw,
            {"enabled": True, "required_deck_ids": [1]},
        )

        self.assertTrue(status.complete)
        self.assertEqual(status.remaining_cards, 0)


if __name__ == "__main__":
    unittest.main()
