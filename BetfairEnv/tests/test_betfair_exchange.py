from __future__ import annotations

import sys
import unittest
from pathlib import Path

BETFAIR_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BETFAIR_ROOT.parent
for path in (PROJECT_ROOT, BETFAIR_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from collector.betfair_exchange import (  # noqa: E402
    BOOK_EXCHANGE,
    BOOK_SPORTSBOOK,
    build_exchange_section,
    tag_sportsbook_market,
    tag_sportsbook_section,
)


class BetfairExchangeSnapshotTests(unittest.TestCase):
    def test_tag_sportsbook_section_marks_book(self) -> None:
        section = {
            "player1": "A",
            "player2": "B",
            "primary_market": {
                "market_type": "MATCH_ODDS",
                "runners": [{"name": "A", "odds_decimal": 1.5}],
            },
            "markets": [
                {
                    "market_type": "MATCH_ODDS",
                    "runners": [{"name": "A", "odds_decimal": 1.5}],
                }
            ],
        }
        tagged = tag_sportsbook_section(section)
        self.assertEqual(tagged["book"], BOOK_SPORTSBOOK)
        self.assertEqual(tagged["primary_market"]["book"], BOOK_SPORTSBOOK)
        self.assertEqual(tagged["primary_market"]["runners"][0]["book"], BOOK_SPORTSBOOK)
        self.assertEqual(tagged["markets"][0]["book"], BOOK_SPORTSBOOK)
        self.assertEqual(tagged["markets"][0]["runners"][0]["book"], BOOK_SPORTSBOOK)

    def test_tag_sportsbook_market_none(self) -> None:
        self.assertIsNone(tag_sportsbook_market(None))

    def test_build_exchange_section_hit(self) -> None:
        odds = {
            "123": {
                "book": BOOK_EXCHANGE,
                "market_type": "MATCH_ODDS",
                "market_id": "1.99",
                "runners": [
                    {
                        "book": BOOK_EXCHANGE,
                        "name": "A",
                        "best_back": 1.8,
                        "best_lay": 1.85,
                    }
                ],
            }
        }
        section = build_exchange_section("123", odds)
        self.assertEqual(section["book"], BOOK_EXCHANGE)
        self.assertIsNone(section["error"])
        self.assertEqual(section["match_odds"]["market_id"], "1.99")
        self.assertEqual(section["match_odds"]["runners"][0]["best_back"], 1.8)

    def test_build_exchange_section_miss_uses_fetch_error(self) -> None:
        section = build_exchange_section("999", {}, fetch_error="auth fail")
        self.assertEqual(section["book"], BOOK_EXCHANGE)
        self.assertIsNone(section["match_odds"])
        self.assertEqual(section["error"], "auth fail")

    def test_build_exchange_section_miss_default_message(self) -> None:
        section = build_exchange_section(42, {})
        self.assertIn("42", section["error"] or "")


if __name__ == "__main__":
    unittest.main()
