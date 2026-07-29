from __future__ import annotations

import sys
import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BETFAIR_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BETFAIR_ROOT.parent
for path in (PROJECT_ROOT, BETFAIR_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from collector.analysis_runner import (  # noqa: E402
    AutomatedAnalysisRunner,
    _market_selection,
    _settlement_result,
    _snapshot_tradeable,
)
from collector.match_status import sets_won_from_score  # noqa: E402
from tennisAgents.dataflows.market_resolve import (  # noqa: E402
    build_game_winners_from_scores,
)
from collector import analysis_runner as analysis_module  # noqa: E402
from api import collector_control  # noqa: E402
from collector.control_signals import watch_stop_file  # noqa: E402
from collector.storage import _snapshot_filename  # noqa: E402
from collector import storage  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from tennisAgents.agents.generalist import (  # noqa: E402
    _bet_calibration_fields,
    _diversification_prompt_hint,
    _market_family,
    _open_market_lines,
    _portfolio_capital_brief,
    _save_turn_log,
    _target_call,
    _turn_log,
    create_generalist_llm,
)
from tennisAgents.graph.propagation import Propagator  # noqa: E402


def snapshot(*, score: str = "1-0", odds: float = 2.0) -> dict:
    return {
        "timestamp": "2026-07-22T10:00:00.123456+00:00",
        "flashscore_match_id": "fs-1",
        "flashscore": {
            "score": score,
            "match": {"id": "fs-1"},
        },
        "betfair": {
            "markets": [
                {
                    "market_id": "m-1",
                    "market_type": "MATCH_ODDS",
                    "status": "OPEN",
                    "runners": [
                        {
                            "name": "Player A",
                            "selection_id": 1,
                            "status": "ACTIVE",
                            "odds_decimal": odds,
                        },
                        {
                            "name": "Player B",
                            "selection_id": 2,
                            "status": "ACTIVE",
                            "odds_decimal": 3.0,
                        },
                    ],
                }
            ]
        },
    }


def record(name: str, arguments: dict) -> dict:
    return {
        "turn_id": "turn-1",
        "step_index": 0,
        "match": {
            "player_a": "Player A",
            "player_b": "Player B",
            "tournament": "Test",
            "match_date": "2026-07-22",
        },
        "target": {
            "tool_call": {
                "name": name,
                "technical_fallback": False,
                "arguments": arguments,
            }
        },
        "outcome": {
            "accepted_for_training": False,
            "label_source": "pending_validation",
        },
    }


def runner(**config_overrides) -> AutomatedAnalysisRunner:
    instance = object.__new__(AutomatedAnalysisRunner)
    instance.config = {
        "automated_wallet_balance": 100.0,
        "void_unresolved_markets_on_finish": True,
        "void_unresolved_on_indecisive_finish": True,
        "void_open_positions_on_shutdown": True,
        "settle_open_positions_on_shutdown": True,
        "shutdown_drain_sec": 0,
        "minimum_bet_edge": 0.02,
        "minimum_bet_stake": 1.0,
        "match_odds_short_odds_max": 1.25,
        "match_odds_short_min_edge": 0.05,
        "max_stake_fraction": 0.20,
        "max_total_exposure_fraction": 0.50,
        **config_overrides,
    }
    instance._lock = threading.Lock()
    instance._processing = set()
    instance._event_locks_guard = threading.Lock()
    instance._event_locks = {}
    instance._shutting_down = False
    instance._retry_timers = {}
    return instance


def _bind_runner_persistence(engine: AutomatedAnalysisRunner) -> None:
    engine._save_analysis_meta = AutomatedAnalysisRunner._save_analysis_meta.__get__(
        engine,
        AutomatedAnalysisRunner,
    )
    engine._event_score_history = AutomatedAnalysisRunner._event_score_history.__get__(
        engine,
        AutomatedAnalysisRunner,
    )
    engine._event_lock = AutomatedAnalysisRunner._event_lock.__get__(
        engine,
        AutomatedAnalysisRunner,
    )
    engine._latest_snapshot = AutomatedAnalysisRunner._latest_snapshot.__get__(
        engine,
        AutomatedAnalysisRunner,
    )
    engine._close_or_settle_open_positions_on_shutdown = (
        AutomatedAnalysisRunner._close_or_settle_open_positions_on_shutdown.__get__(
            engine,
            AutomatedAnalysisRunner,
        )
    )
    engine.reconcile_finished_matches = (
        AutomatedAnalysisRunner.reconcile_finished_matches.__get__(
            engine,
            AutomatedAnalysisRunner,
        )
    )
    engine._void_open_positions_on_shutdown = (
        AutomatedAnalysisRunner._void_open_positions_on_shutdown.__get__(
            engine,
            AutomatedAnalysisRunner,
        )
    )
    engine.shutdown = AutomatedAnalysisRunner.shutdown.__get__(
        engine,
        AutomatedAnalysisRunner,
    )


class ReliabilityTests(unittest.TestCase):
    def test_tradeable_snapshot_requires_flashscore_link(self) -> None:
        healthy, reason = _snapshot_tradeable(snapshot())
        self.assertTrue(healthy)
        self.assertEqual(reason, "")

        missing = snapshot()
        missing["flashscore_match_id"] = None
        missing["flashscore"]["match"]["id"] = None
        healthy, reason = _snapshot_tradeable(missing)
        self.assertFalse(healthy)
        self.assertIn("Flashscore", reason)

        # Lag 0-0 con mercados de set avanzados ya no bloquea el Bet.
        advanced = snapshot(score="0-0")
        advanced["betfair"]["markets"][0]["market_type"] = "SET_3_GAME_1_WINNER"
        healthy, reason = _snapshot_tradeable(advanced)
        self.assertTrue(healthy)
        self.assertEqual(reason, "")

    def test_market_selection_resolves_spanish_aliases(self) -> None:
        snap = snapshot()
        snap["betfair"]["markets"].append(
            {
                "market_id": "m-game",
                "market_type": "SET_2_GAME_7_WINNER",
                "name": "Set 2 - Juego 7 - Ganador",
                "status": "OPEN",
                "runners": [
                    {
                        "name": "Player A",
                        "selection_id": 11,
                        "status": "ACTIVE",
                        "odds_decimal": 1.8,
                    }
                ],
            }
        )
        market, selection = _market_selection(
            snap,
            "Set 2 - Juego 7 - Ganador",
            "Player A",
        )
        self.assertEqual(market["market_id"], "m-game")
        self.assertEqual(selection["selection_id"], 11)

        market, selection = _market_selection(snap, "match_winner", "Player A")
        self.assertEqual(market["market_id"], "m-1")
        self.assertEqual(selection["selection_id"], 1)

    def test_market_selection_resolves_real_runner(self) -> None:
        market, selection = _market_selection(
            snapshot(),
            "MATCH_ODDS",
            "Player A",
        )
        self.assertEqual(market["market_id"], "m-1")
        self.assertEqual(selection["selection_id"], 1)

    def test_bet_uses_real_odds_and_unique_position(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 10.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 90.0)
        self.assertEqual(len(meta["open_positions"]), 1)
        position = meta["open_positions"][0]
        self.assertEqual(position["entry_odds"], 2.0)
        self.assertTrue(position["position_id"].startswith("123:"))
        call = committed["target"]["tool_call"]
        self.assertEqual(call["arguments"]["odds"], 2.0)
        self.assertEqual(call["arguments"]["position_id"], position["position_id"])

    def test_overbet_is_rejected_without_balance_change(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(),
            {"wallet_balance": 100.0, "available_balance": 5.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 10.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 5.0)
        self.assertEqual(meta["open_positions"], [])
        self.assertEqual(committed["target"]["tool_call"]["name"], "wait")
        self.assertTrue(committed["target"]["tool_call"]["policy_rejected"])

    def test_bet_with_negative_edge_is_rejected(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(odds=2.0),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 5.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.4,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 100.0)
        self.assertEqual(committed["target"]["tool_call"]["name"], "wait")
        self.assertIn(
            "Edge insuficiente",
            committed["target"]["tool_call"]["arguments"]["reason"],
        )

    def test_stake_above_diversification_cap_is_rejected(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 25.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 100.0)
        self.assertEqual(committed["target"]["tool_call"]["name"], "wait")
        self.assertIn(
            "tope de diversificación",
            committed["target"]["tool_call"]["arguments"]["reason"],
        )

    def test_total_exposure_cap_is_rejected(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(),
            {
                "wallet_balance": 100.0,
                "available_balance": 55.0,
                "open_positions": [
                    {
                        "position_id": "123:old:1",
                        "market": "MATCH_ODDS",
                        "selection": "Player B",
                        "remaining_stake": 45.0,
                        "initial_stake": 45.0,
                        "entry_odds": 3.0,
                    }
                ],
            },
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 10.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 55.0)
        self.assertEqual(len(meta["open_positions"]), 1)
        self.assertIn(
            "Exposición total",
            committed["target"]["tool_call"]["arguments"]["reason"],
        )

    def test_stake_below_minimum_is_rejected(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 0.5,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        self.assertEqual(meta["available_balance"], 100.0)
        self.assertEqual(committed["target"]["tool_call"]["name"], "wait")
        self.assertIn(
            "inferior al mínimo",
            committed["target"]["tool_call"]["arguments"]["reason"],
        )

    def test_short_match_odds_requires_higher_edge(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(odds=1.20),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 5.0,
                    "confidence": 0.7,
                    # implícita ~0.833; edge ~0.027 < 0.05 corto
                    "estimated_probability": 0.86,
                },
            ),
        )
        self.assertEqual(committed["target"]["tool_call"]["name"], "wait")
        self.assertIn(
            "MATCH_ODDS corto",
            committed["target"]["tool_call"]["arguments"]["reason"],
        )

    def test_bet_commit_writes_calibration_fields(self) -> None:
        meta, committed = runner()._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(odds=2.0),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 10.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        args = committed["target"]["tool_call"]["arguments"]
        self.assertEqual(args["implied_probability"], 0.5)
        self.assertAlmostEqual(args["edge"], 0.1)
        self.assertEqual(args["stake_pct_wallet"], 0.1)
        self.assertEqual(args["stake_pct_available"], 0.1)
        self.assertEqual(args["market_family"], "match_odds")
        self.assertEqual(meta["available_balance"], 90.0)

    def test_market_family_and_diversification_hint(self) -> None:
        self.assertEqual(_market_family("MATCH_ODDS"), "match_odds")
        self.assertEqual(_market_family("SET_2_GAME_3_WINNER"), "game")
        self.assertEqual(_market_family("SET_BETTING"), "set")
        multi = snapshot()
        multi["betfair"]["markets"].append(
            {
                "market_id": "m-game",
                "market_type": "SET_1_GAME_1_WINNER",
                "status": "OPEN",
                "runners": [
                    {
                        "name": "Player A",
                        "selection_id": 11,
                        "status": "ACTIVE",
                        "odds_decimal": 1.8,
                    }
                ],
            }
        )
        lines = _open_market_lines(multi)
        families = {line["market_family"] for line in lines}
        self.assertIn("game", families)
        self.assertIn("match_odds", families)
        hint = _diversification_prompt_hint(lines)
        self.assertIn("MATCH_ODDS", hint)
        self.assertIn("candidatas iguales", hint)
        self.assertNotIn("prioriza set/juego", hint.casefold())

    def test_portfolio_capital_brief_and_market_lines(self) -> None:
        brief = _portfolio_capital_brief(
            {
                "wallet_balance": 100.0,
                "available_balance": 70.0,
                "open_positions": [
                    {
                        "market": "MATCH_ODDS",
                        "remaining_stake": 20.0,
                    },
                    {
                        "market": "SET_BETTING",
                        "remaining_stake": 10.0,
                    },
                ],
            }
        )
        self.assertEqual(brief["total_exposure"], 30.0)
        self.assertEqual(brief["exposure_fraction"], 0.3)
        self.assertEqual(brief["suggested_max_single_stake"], 10.0)
        lines = _open_market_lines(snapshot())
        self.assertGreaterEqual(len(lines), 2)
        implied = {round(line["implied_probability"], 4) for line in lines}
        self.assertIn(0.5, implied)
        self.assertIn(0.3333, implied)
        self.assertTrue(all(line.get("market_family") for line in lines))

    def test_partial_close_releases_stake_and_realizes_pnl(self) -> None:
        engine = runner()
        opened_meta, opened_record = engine._prepare_commit(
            "123",
            "2026-07-22T10:00:00+00:00",
            snapshot(odds=2.0),
            {"wallet_balance": 100.0, "available_balance": 100.0},
            record(
                "bet",
                {
                    "market": "MATCH_ODDS",
                    "option": "Player A",
                    "stake": 10.0,
                    "confidence": 0.7,
                    "estimated_probability": 0.6,
                },
            ),
        )
        position_id = opened_meta["open_positions"][0]["position_id"]
        closed_meta, closed_record = engine._prepare_commit(
            "123",
            "2026-07-22T10:01:00+00:00",
            snapshot(odds=1.5),
            opened_meta,
            record(
                "close",
                {
                    "position_id": position_id,
                    "match_id": opened_meta["open_positions"][0]["match_id"],
                    "close_percentage": 0.5,
                    "confidence": 0.8,
                },
            ),
        )
        self.assertAlmostEqual(
            closed_meta["open_positions"][0]["remaining_stake"],
            5.0,
        )
        self.assertAlmostEqual(closed_meta["realized_pnl"], 5 * (2 / 1.5 - 1))
        self.assertAlmostEqual(
            closed_meta["available_balance"],
            90 + 5 + 5 * (2 / 1.5 - 1),
        )
        self.assertEqual(
            closed_record["target"]["tool_call"]["arguments"]["exit_odds"],
            1.5,
        )

    def test_settlement_only_resolves_supported_markets(self) -> None:
        entry = {
            "winner": "player1",
            "player1": "Player A",
            "player2": "Player B",
            "sets_won": {"player1": 2, "player2": 0},
            "sets_detail": [{"player1": 6, "player2": 3}, {"player1": 6, "player2": 2}],
            "score": "6-3 6-2",
        }
        self.assertTrue(
            _settlement_result(
                {"market": "MATCH_ODDS", "selection": "Player A"},
                entry,
            )
        )
        self.assertFalse(
            _settlement_result(
                {"market": "MATCH_ODDS", "selection": "Player B"},
                entry,
            )
        )
        self.assertIsNone(
            _settlement_result(
                {"market": "SET_1_GAME_3_WINNER", "selection": "Player A"},
                entry,
            )
        )
        self.assertTrue(
            _settlement_result(
                {"market": "SET_1_GAME_3_WINNER", "selection": "Player A"},
                entry,
                game_winners={(1, 3): "player1"},
            )
        )
        self.assertTrue(
            _settlement_result(
                {"market": "BOTH_PLAYERS_TO_WIN_A_SET_YES/NO", "selection": "No"},
                entry,
            )
        )
        self.assertIsNone(
            _settlement_result(
                {
                    "market": "PLAYER_A_TO_WIN_AT_LEAST_1_SET",
                    "selection": "Player A Unknown",
                },
                entry,
            )
        )

    def test_sets_won_ignores_incomplete_sets(self) -> None:
        self.assertEqual(
            sets_won_from_score("3-6 6-1 3-5"),
            {"player1": 1, "player2": 1},
        )
        self.assertEqual(
            sets_won_from_score("6-4 6-2"),
            {"player1": 2, "player2": 0},
        )
        self.assertIsNone(sets_won_from_score("5-4 0-0"))

    def test_decisive_sets_mark_match_finished(self) -> None:
        from collector.match_status import (
            match_decided_by_sets,
            sets_required_to_win,
            should_mark_finished,
        )

        self.assertEqual(sets_required_to_win("ATP 250 Barcelona"), 2)
        self.assertEqual(sets_required_to_win("Wimbledon"), 3)
        self.assertEqual(sets_required_to_win("Wimbledon Qualifying"), 2)

        # Mejor de 3: 2 sets bastan aunque el status diga "En juego".
        entry = {
            "competition": "ATP Challenger",
            "status": "En juego",
            "score": "6-3 6-4",
            "sets_won": {"player1": 0, "player2": 0},
        }
        decided, sets_won, winner = match_decided_by_sets(entry)
        self.assertTrue(decided)
        self.assertEqual(sets_won, {"player1": 2, "player2": 0})
        self.assertEqual(winner, "player1")
        self.assertTrue(
            should_mark_finished(
                entry,
                in_betfair_live=True,
                in_flashscore_live=True,
            )
        )

        # Mejor de 5: 2-1 aún no decide.
        slam = {
            "competition": "Australian Open",
            "status": "En juego",
            "score": "6-3 3-6 6-4",
        }
        decided, _, _ = match_decided_by_sets(slam)
        self.assertFalse(decided)
        slam["score"] = "6-3 3-6 6-4 6-2"
        decided, sets_won, winner = match_decided_by_sets(slam)
        self.assertTrue(decided)
        self.assertEqual(sets_won, {"player1": 3, "player2": 1})
        self.assertEqual(winner, "player1")

    def test_list_all_matches_hides_stale_ghosts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                now = datetime.now(timezone.utc).isoformat()
                old = (datetime.now(timezone.utc) - timedelta(days=24)).isoformat()
                storage.save_index(
                    {
                        "updated_at": now,
                        "matches": {
                            "35777012": {
                                "player1": "A",
                                "player2": "B",
                                "competition": "Wimbledon 2026",
                                "is_stale": True,
                                "stale_at": now,
                                "last_snapshot_at": old,
                                "is_live": False,
                            },
                            "35864111": {
                                "player1": "C",
                                "player2": "D",
                                "competition": "Tampere Challenger 2026",
                                "is_live": True,
                                "status": "En juego",
                                "last_snapshot_at": now,
                            },
                        },
                    }
                )
                active = storage.list_all_matches()
                all_matches = storage.list_all_matches(include_inactive=True)
            finally:
                storage.DATA_DIR = original_data_dir
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["event_id"], "35864111")
            self.assertEqual(len(all_matches), 2)

    def test_historical_ghost_dropped_from_index(self) -> None:
        from collector.snapshot import _should_drop_entry

        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=24)).isoformat()
        stale_at = (now - timedelta(minutes=5)).isoformat()
        entry = {
            "is_stale": True,
            "stale_at": stale_at,
            "last_snapshot_at": old,
            "is_live": False,
        }
        self.assertTrue(_should_drop_entry(entry, now))

    def test_game_winners_from_score_progression(self) -> None:
        winners = build_game_winners_from_scores(
            ["6-3 2-0", "6-3 3-0", "6-3 3-1", "6-3 4-1"]
        )
        self.assertEqual(winners[(2, 3)], "player1")
        self.assertEqual(winners[(2, 4)], "player2")
        self.assertEqual(winners[(2, 5)], "player1")

    def test_stale_betfair_live_does_not_overwrite_flashscore_scoreboard(self) -> None:
        import collector.paths  # noqa: F401
        from collector.score_merge import build_flashscore_section

        section = build_flashscore_section(
            {
                "id": "fs-1",
                "player1": "A",
                "player2": "B",
                "score": "0-0",
                "status": "En juego",
            },
            None,
            {
                "BA": "6",
                "BB": "4",
                "BC": "3",
                "BD": "2",
                "AG": "1",
                "AH": "0",
            },
            live_score={
                "sets_won": {"player1": 0, "player2": 0},
                "current_set": {"player1": 0, "player2": 0},
                "current_game": {"player1": "30", "player2": "40"},
                "serving": "player1",
            },
        )
        self.assertEqual(section["score"], "6-4 3-2")
        self.assertEqual(section["sets_won"], {"player1": 1, "player2": 0})
        self.assertNotIn("current_points", section)

    def test_betfair_live_can_advance_current_set_when_ahead(self) -> None:
        import collector.paths  # noqa: F401
        from collector.score_merge import build_flashscore_section

        section = build_flashscore_section(
            {
                "id": "fs-1",
                "player1": "A",
                "player2": "B",
                "score": "6-4 2-1",
                "sets_won": {"player1": 1, "player2": 0},
                "status": "En juego",
            },
            None,
            None,
            live_score={
                "sets_won": {"player1": 1, "player2": 0},
                "current_set": {"player1": 3, "player2": 1},
                "current_game": {"player1": "15", "player2": "0"},
                "serving": "player2",
            },
        )
        self.assertEqual(section["score"], "6-4 3-1")
        self.assertEqual(section["sets_won"], {"player1": 1, "player2": 0})
        self.assertEqual(section["current_points"]["player1"], "15")
        self.assertEqual(section["serving"], "player2")

    def test_flashscore_ag_ignored_when_contradicts_sets_detail(self) -> None:
        import collector.paths  # noqa: F401
        from collector.score_merge import build_flashscore_section

        section = build_flashscore_section(
            {
                "id": "fs-1",
                "player1": "A",
                "player2": "B",
                "score": "6-4 3-2",
                "sets_won": {"player1": 2, "player2": 0},
                "status": "En juego",
            },
            None,
            {
                "BA": "6",
                "BB": "4",
                "BC": "3",
                "BD": "2",
                "AG": "2",
                "AH": "0",
            },
        )
        self.assertEqual(section["score"], "6-4 3-2")
        self.assertEqual(section["sets_won"], {"player1": 1, "player2": 0})

    def test_save_snapshot_syncs_index_last_snapshot_at(self) -> None:
        import collector.paths  # noqa: F401
        from collector.storage import load_index, load_meta, save_snapshot

        event_id = "99999001"
        ts = "2026-07-26T14:00:00.000000+00:00"
        save_snapshot(
            event_id,
            {
                "timestamp": ts,
                "betfair_event_id": event_id,
                "betfair": {"player1": "A", "player2": "B"},
            },
        )
        meta = load_meta(event_id)
        self.assertEqual(meta.get("last_snapshot_at"), ts)
        index = load_index()
        entry = index.get("matches", {}).get(event_id)
        if entry is not None:
            self.assertEqual(entry.get("last_snapshot_at"), ts)

    def test_void_open_positions_on_shutdown_module(self) -> None:
        import collector.paths  # noqa: F401
        from collector.shutdown_utils import void_open_positions_on_shutdown
        from collector.storage import load_meta, match_dir, save_meta

        event_id = "99999002"
        match_dir(event_id).mkdir(parents=True, exist_ok=True)
        save_meta(
            event_id,
            {
                "wallet_balance": 100.0,
                "available_balance": 90.0,
                "open_positions": [
                    {
                        "position_id": "pos-1",
                        "remaining_stake": 10.0,
                        "initial_stake": 10.0,
                    }
                ],
                "position_history": [],
            },
        )
        voided = void_open_positions_on_shutdown({"void_open_positions_on_shutdown": True})
        self.assertGreaterEqual(voided, 1)
        meta = load_meta(event_id)
        self.assertEqual(meta.get("open_positions"), [])
        self.assertEqual(meta.get("available_balance"), 100.0)

    def test_snapshot_filename_preserves_microseconds(self) -> None:
        first = _snapshot_filename(
            datetime(2026, 7, 22, 10, 0, 0, 1, tzinfo=timezone.utc)
        )
        second = _snapshot_filename(
            datetime(2026, 7, 22, 10, 0, 0, 2, tzinfo=timezone.utc)
        )
        self.assertNotEqual(first, second)

    def test_turn_log_records_real_odds_and_rejects_fallback_for_training(self) -> None:
        market_snapshot = {
            "primary_market": {},
            "markets": snapshot()["betfair"]["markets"],
        }
        target = _target_call(
            {
                "name": "Bet",
                "id": "real-call",
                "args": {
                    "market": "MATCH_ODDS",
                    "selection": "Player A",
                    "stake": 5,
                    "confidence": 0.5,
                    "estimated_probability": 0.6,
                    "rationale": "Test",
                },
            },
            market_snapshot,
            state={
                "wallet_balance": 100.0,
                "available_balance": 100.0,
            },
        )
        self.assertEqual(target["arguments"]["odds"], 2.0)
        self.assertEqual(target["arguments"]["market_id"], "m-1")
        self.assertEqual(target["arguments"]["implied_probability"], 0.5)
        self.assertAlmostEqual(target["arguments"]["edge"], 0.1)
        self.assertEqual(target["arguments"]["stake_pct_wallet"], 0.05)
        self.assertEqual(target["arguments"]["market_family"], "match_odds")
        calib = _bet_calibration_fields(
            stake=5,
            odds=2.0,
            estimated_probability=0.6,
            wallet_balance=100.0,
            available_balance=100.0,
            market="MATCH_ODDS",
        )
        self.assertEqual(calib["stake_pct_wallet"], 0.05)

        state = {
            "player_of_interest": "Player A",
            "opponent": "Player B",
            "match_date": "2026-07-22",
            "tournament": "Test",
            "wallet_balance": 100.0,
            "available_balance": 100.0,
            "step_index": 0,
        }
        fallback = _turn_log(
            state,
            {
                "name": "Wait",
                "id": "fallback_wait",
                "args": {
                    "match_id": "test",
                    "rationale": "fallback",
                    "confidence": 0,
                },
            },
        )
        self.assertTrue(
            fallback["target"]["tool_call"]["technical_fallback"]
        )
        self.assertFalse(fallback["outcome"]["accepted_for_training"])

    def test_turn_log_append_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "turns.jsonl"
            item = {"turn_id": "turn-1", "value": 1}
            _save_turn_log(item, str(path))
            _save_turn_log(item, str(path))
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)

    def test_index_recovers_from_atomic_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                storage.save_index(
                    {"updated_at": None, "matches": {"123": {"status": "live"}}}
                )
                storage.index_path().write_text("{invalid", encoding="utf-8")
                recovered = storage.load_index()
            finally:
                storage.DATA_DIR = original_data_dir
            self.assertIn("123", recovered["matches"])

    def test_meta_recovers_ledger_from_atomic_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                storage.save_meta(
                    "123",
                    {
                        "available_balance": 90.0,
                        "open_positions": [{"position_id": "p-1"}],
                    },
                )
                (storage.match_dir("123") / "meta.json").write_text(
                    "{invalid",
                    encoding="utf-8",
                )
                recovered = storage.load_meta("123")
            finally:
                storage.DATA_DIR = original_data_dir
            self.assertEqual(recovered["available_balance"], 90.0)
            self.assertEqual(recovered["open_positions"][0]["position_id"], "p-1")

    def test_analysis_meta_preserves_newer_collector_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                storage.save_meta(
                    "123",
                    {"last_snapshot_at": "2026-07-22T10:01:00+00:00"},
                )
                storage.save_meta(
                    "123",
                    {
                        "last_snapshot_at": "2026-07-22T10:00:00+00:00",
                        "last_analysis_step": 1,
                    },
                    preserve_existing_keys=("last_snapshot_at",),
                )
                recovered = storage.load_meta("123")
            finally:
                storage.DATA_DIR = original_data_dir
            self.assertEqual(
                recovered["last_snapshot_at"],
                "2026-07-22T10:01:00+00:00",
            )
            self.assertEqual(recovered["last_analysis_step"], 1)

    def test_legacy_unsettled_turns_are_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = analysis_module.DATA_DIR
            analysis_module.DATA_DIR = Path(temporary)
            try:
                event_dir = Path(temporary) / "123"
                event_dir.mkdir()
                turns_path = event_dir / "generalist_turns.jsonl"
                turns_path.write_text(
                    json.dumps(
                        {
                            "target": {
                                "tool_call": {
                                    "name": "wait",
                                    "arguments": {
                                        "confidence": 0,
                                        "reason": (
                                            "El modelo no ejecutó una tool call válida; "
                                            "se espera por seguridad."
                                        ),
                                    },
                                }
                            },
                            "outcome": {
                                "accepted_for_training": True,
                                "eventual_match_winner": None,
                                "pnl_after_match": None,
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                changed = runner().sanitize_training_labels()
                updated = json.loads(turns_path.read_text(encoding="utf-8"))
            finally:
                analysis_module.DATA_DIR = original_data_dir
            self.assertEqual(changed, 1)
            self.assertFalse(updated["outcome"]["accepted_for_training"])
            self.assertTrue(
                updated["target"]["tool_call"]["technical_fallback"]
            )

    def test_legacy_ledger_is_quarantined_and_balance_reset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            analysis_module.DATA_DIR = Path(temporary)
            try:
                storage.save_meta(
                    "123",
                    {
                        "wallet_balance": 100.0,
                        "available_balance": 0.0,
                        "open_positions": [
                            {
                                "position_id": "legacy-match-id",
                                "stake": 150.0,
                            }
                        ],
                    },
                )
                changed = runner().migrate_legacy_ledgers()
                migrated = storage.load_meta("123")
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir
            self.assertEqual(changed, 1)
            self.assertEqual(migrated["ledger_schema_version"], 2)
            self.assertEqual(migrated["available_balance"], 100.0)
            self.assertEqual(migrated["open_positions"], [])
            self.assertEqual(
                migrated["legacy_positions_quarantined"][0]["stake"],
                150.0,
            )

    def test_manual_generalist_persists_while_collector_can_defer(self) -> None:
        class FakeLlm:
            def bind_tools(self, *_args, **_kwargs):
                return self

            def invoke(self, _prompt):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "Wait",
                            "id": "wait-1",
                            "args": {
                                "match_id": "test",
                                "rationale": "Sin señal suficiente.",
                                "confidence": 0.8,
                                "next_trigger": "Nueva cuota.",
                            },
                        }
                    ],
                )

        with tempfile.TemporaryDirectory() as temporary:
            turns_path = Path(temporary) / "turns.jsonl"
            context_path = Path(temporary) / "context.md"
            state = {
                "player_of_interest": "Player A",
                "opponent": "Player B",
                "match_date": "2026-07-22",
                "tournament": "Test",
                "wallet_balance": 100.0,
                "available_balance": 100.0,
                "step_index": 0,
                "generalist_turns_log": str(turns_path),
                "context_path": str(context_path),
                "scraper_snapshot": {
                    "timestamp": "2026-07-22T10:00:00+00:00",
                    "betfair": {},
                    "flashscore": {},
                },
                "defer_generalist_persistence": False,
            }
            node = create_generalist_llm(FakeLlm())
            node(state)
            self.assertTrue(turns_path.exists())
            self.assertTrue(context_path.exists())

    def test_analysis_and_settlement_share_event_lock(self) -> None:
        engine = runner()
        process_started = threading.Event()
        allow_process_finish = threading.Event()
        settlement_called = threading.Event()

        def fake_process(*_args):
            process_started.set()
            allow_process_finish.wait(timeout=5)

        def fake_settlement(_event_id, _entry):
            settlement_called.set()
            return True

        engine._process_snapshot_locked = fake_process
        engine._reconcile_finished_match = fake_settlement
        original_load_index = analysis_module.load_index
        analysis_module.load_index = lambda: {
            "matches": {
                "123": {
                    "is_finished": True,
                    "finished_at": "2026-07-22T11:00:00+00:00",
                }
            }
        }
        try:
            process_thread = threading.Thread(
                target=engine._process_snapshot,
                args=("123", {}, {}, "2026-07-22T10:00:00+00:00"),
            )
            settlement_thread = threading.Thread(
                target=engine.reconcile_finished_matches
            )
            process_thread.start()
            self.assertTrue(process_started.wait(timeout=2))
            settlement_thread.start()
            time.sleep(0.1)
            self.assertFalse(settlement_called.is_set())
            allow_process_finish.set()
            process_thread.join(timeout=2)
            settlement_thread.join(timeout=2)
        finally:
            analysis_module.load_index = original_load_index
        self.assertTrue(settlement_called.is_set())

    def test_backlog_is_coalesced_to_latest_live_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            analysis_module.DATA_DIR = Path(temporary)
            engine = AutomatedAnalysisRunner()
            try:
                now = datetime.now(timezone.utc)
                timestamps = [
                    (now - timedelta(seconds=offset)).isoformat()
                    for offset in (3, 2, 1)
                ]
                for timestamp in timestamps:
                    item = snapshot()
                    item["timestamp"] = timestamp
                    storage.save_snapshot("123", item)
                captured = []

                def fake_process(event_id, _snapshot, _entry, cursor):
                    captured.append(cursor)
                    meta = storage.load_meta(event_id)
                    meta["last_processed_snapshot_at"] = cursor
                    engine._save_analysis_meta(event_id, meta)

                engine._process_snapshot = fake_process
                engine._pending = {"123": {"is_live": True, "status": "En juego"}}
                engine._processing = {"123"}
                engine._drain_event("123")
                meta = storage.load_meta("123")
            finally:
                engine.shutdown()
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir
            self.assertEqual(captured, [timestamps[-1]])
            self.assertEqual(
                meta["analysis_superseded_batches"][-1]["count"],
                2,
            )

    def test_stale_snapshot_never_mutates_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            analysis_module.DATA_DIR = Path(temporary)
            engine = AutomatedAnalysisRunner()
            try:
                item = snapshot()
                item["timestamp"] = (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ).isoformat()
                storage.save_snapshot("123", item)
                called = []
                engine._process_snapshot = lambda *_args: called.append(True)
                engine._pending = {"123": {"is_live": True, "status": "En juego"}}
                engine._processing = {"123"}
                engine._drain_event("123")
                meta = storage.load_meta("123")
            finally:
                engine.shutdown()
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir
            self.assertEqual(called, [])
            self.assertEqual(meta["analysis_status"], "stale_skipped")
            self.assertEqual(
                meta["last_processed_snapshot_at"],
                item["timestamp"],
            )

    def test_permanent_failure_moves_snapshot_to_dead_letter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            analysis_module.DATA_DIR = Path(temporary)
            engine = AutomatedAnalysisRunner()
            try:
                engine.config["analysis_max_failures_per_snapshot"] = 1
                item = snapshot()
                item["timestamp"] = datetime.now(timezone.utc).isoformat()
                storage.save_snapshot("123", item)

                def fail_process(*_args):
                    raise ValueError("schema permanently invalid")

                engine._process_snapshot = fail_process
                engine._pending = {"123": {"is_live": True, "status": "En juego"}}
                engine._processing = {"123"}
                engine._drain_event("123")
                meta = storage.load_meta("123")
                dead_letters = list(
                    (storage.match_dir("123") / "dead_letters").glob("*.json")
                )
            finally:
                engine.shutdown()
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir
            self.assertEqual(meta["analysis_status"], "dead_letter")
            self.assertEqual(len(meta["analysis_dead_letters"]), 1)
            self.assertEqual(len(dead_letters), 1)

    def test_concurrent_start_requests_spawn_one_collector(self) -> None:
        class FakeProcess:
            pid = 4242

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            originals = {
                "RUN_DIR": collector_control.RUN_DIR,
                "PID_FILE": collector_control.PID_FILE,
                "STOP_FILE": collector_control.STOP_FILE,
                "CONTROL_LOCK_FILE": collector_control.CONTROL_LOCK_FILE,
                "LAST_CYCLE_FILE": collector_control.LAST_CYCLE_FILE,
                "Popen": collector_control.subprocess.Popen,
                "_pid_alive": collector_control._pid_alive,
            }
            spawn_count = 0
            spawn_lock = threading.Lock()

            def fake_popen(*_args, **_kwargs):
                nonlocal spawn_count
                with spawn_lock:
                    spawn_count += 1
                return FakeProcess()

            collector_control.RUN_DIR = run_dir
            collector_control.PID_FILE = run_dir / "collector.pid"
            collector_control.STOP_FILE = run_dir / "collector.stop"
            collector_control.CONTROL_LOCK_FILE = run_dir / "control.lock"
            collector_control.LAST_CYCLE_FILE = run_dir / "last_cycle"
            collector_control.subprocess.Popen = fake_popen
            collector_control._pid_alive = lambda pid: pid == 4242
            try:
                threads = [
                    threading.Thread(target=collector_control.start_collector)
                    for _ in range(2)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=3)
            finally:
                for name, value in originals.items():
                    if name == "Popen":
                        collector_control.subprocess.Popen = value
                    else:
                        setattr(collector_control, name, value)
            self.assertEqual(spawn_count, 1)

    def test_stop_file_triggers_cooperative_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stop_file = Path(temporary) / "collector.stop"
            stop_event = threading.Event()
            watcher = threading.Thread(
                target=watch_stop_file,
                args=(stop_event, stop_file),
            )
            watcher.start()
            stop_file.write_text("stop", encoding="utf-8")
            self.assertTrue(stop_event.wait(timeout=2))
            watcher.join(timeout=2)
            self.assertFalse(watcher.is_alive())

    def test_snapshot_commit_is_end_to_end_idempotent(self) -> None:
        class FakeGraph:
            propagator = Propagator()

            def run_analysts_once(self, _state):
                reports = {
                    key: f"# {key}\n" + ("evidencia " * 150)
                    for key in analysis_module.REPORT_KEYS
                }
                return {
                    **reports,
                    "analyst_errors": {},
                    "analysts_completed_count": 4,
                    "analysts_expected_count": 4,
                }

            def run_generalist_timestep(self, _state):
                return {
                    "technical_fallback": False,
                    "generalist_record": record(
                        "wait",
                        {
                            "reason": "Sin edge suficiente.",
                            "confidence": 0.8,
                            "next_trigger": "Cambio de cuota.",
                            "notes": "",
                        },
                    ),
                }

        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            analysis_module.DATA_DIR = Path(temporary)
            try:
                engine = runner()
                engine.config.update(
                    {
                        "project_dir": str(PROJECT_ROOT),
                        "results_dir": temporary,
                        "analyst_report_min_chars": 1000,
                        "tool_outputs_log": str(
                            Path(temporary) / "tool_outputs.jsonl"
                        ),
                    }
                )
                engine._get_graph = lambda: FakeGraph()
                current_snapshot = snapshot()
                entry = {
                    "player1": "Player A",
                    "player2": "Player B",
                    "competition": "Test",
                    "is_live": True,
                }
                cursor = "2026-07-22T10:00:00.123456+00:00"
                engine._process_snapshot(
                    "123",
                    current_snapshot,
                    entry,
                    cursor,
                )
                engine._process_snapshot(
                    "123",
                    current_snapshot,
                    entry,
                    cursor,
                )
                committed_meta = storage.load_meta("123")
                event_dir = storage.match_dir("123")
                turns = (
                    event_dir / "generalist_turns.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

            self.assertEqual(
                committed_meta["last_processed_snapshot_at"],
                cursor,
            )
            self.assertEqual(len(committed_meta["previous_actions"]), 1)
            self.assertEqual(len(turns), 1)
            self.assertTrue((event_dir / "context.md").exists())
            self.assertTrue((event_dir / "decision.md").exists())
            self.assertEqual(
                len(list((event_dir / "analysis_records").glob("*.json"))),
                1,
            )

    def test_indecisive_finish_voids_unresolved_positions(self) -> None:
        engine = runner()
        _bind_runner_persistence(engine)
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            temp_path = Path(temporary)
            storage.DATA_DIR = temp_path
            analysis_module.DATA_DIR = temp_path
            storage.match_dir("999").mkdir(parents=True, exist_ok=True)
            storage.save_meta(
                "999",
                {
                    "open_positions": [
                        {
                            "position_id": "999:test:1",
                            "market": "SET_BETTING",
                            "selection": "Player A 2-1",
                            "remaining_stake": 3.0,
                            "initial_stake": 3.0,
                            "entry_odds": 4.5,
                        }
                    ],
                    "available_balance": 97.0,
                    "wallet_balance": 100.0,
                    "position_history": [],
                    "analysis_player1": "Player A",
                    "analysis_player2": "Player B",
                },
            )
            entry = {
                "finished_at": "2026-07-26T09:24:22+00:00",
                "is_finished": True,
                "score": "6-3 5-5",
                "player1": "Player A",
                "player2": "Player B",
                "competition": "Tampere Challenger 2026",
            }
            try:
                engine._reconcile_finished_match("999", entry)
                meta = storage.load_meta("999")
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

        self.assertEqual(meta["open_positions"], [])
        self.assertAlmostEqual(meta["available_balance"], 100.0)
        self.assertTrue(
            any(item.get("event") == "voided" for item in meta["position_history"])
        )

    def test_reconcile_session_on_startup_heals_stuck_and_drift(self) -> None:
        engine = runner()
        _bind_runner_persistence(engine)
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            temp_path = Path(temporary)
            storage.DATA_DIR = temp_path
            analysis_module.DATA_DIR = temp_path
            event_id = "777"
            storage.match_dir(event_id).mkdir(parents=True, exist_ok=True)
            storage.save_meta(
                event_id,
                {
                    "analysis_status": "generalist_running",
                    "analysis_current_snapshot_at": "2026-07-26T10:00:00+00:00",
                    "analysts_completed": True,
                    "analysis_tournament": "San Marino Challenger 2026",
                    "analysis_tournament_surface": "grass",
                    "last_snapshot_at": "2026-07-26T12:00:00+00:00",
                    "wallet_balance": 100.0,
                    "available_balance": 100.0,
                },
            )
            reports_dir = storage.match_dir(event_id) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "players_report.md").write_text(
                "x" * 1200,
                encoding="utf-8",
            )
            snapshot_path = storage.match_dir(event_id) / "2026-07-26T12-00-00.000000+00-00.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-07-26T12:00:00+00:00",
                        "betfair": {
                            "player1": "A",
                            "player2": "B",
                            "competition": "San Marino Challenger 2026",
                        },
                        "flashscore": {
                            "match": {
                                "tournament": (
                                    "CHALLENGER MEN - SINGLES: San Marino (San Marino), clay"
                                )
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            index = {
                "updated_at": "2026-07-26T12:00:00+00:00",
                "matches": {
                    event_id: {
                        "player1": "A",
                        "player2": "B",
                        "is_live": True,
                        "last_snapshot_at": "2026-07-26T10:00:00+00:00",
                    }
                },
            }
            storage.save_index(index)
            try:
                stats = engine.reconcile_session_on_startup()
                meta = storage.load_meta(event_id)
                synced_index = storage.load_index()
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

        self.assertGreaterEqual(stats["stuck_status_reset"], 1)
        self.assertGreaterEqual(stats["analysts_invalidated"], 1)
        self.assertEqual(meta["analysis_status"], "running")
        self.assertFalse(meta.get("analysts_completed"))
        self.assertEqual(meta.get("analysis_tournament_surface"), "clay")
        self.assertEqual(
            synced_index["matches"][event_id]["last_snapshot_at"],
            "2026-07-26T12:00:00+00:00",
        )

    def test_shutdown_voids_open_positions(self) -> None:
        engine = runner()
        _bind_runner_persistence(engine)
        engine._executor = type("X", (), {"shutdown": lambda *args, **kwargs: None})()
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            temp_path = Path(temporary)
            storage.DATA_DIR = temp_path
            analysis_module.DATA_DIR = temp_path
            storage.match_dir("888").mkdir(parents=True, exist_ok=True)
            storage.save_meta(
                "888",
                {
                    "open_positions": [
                        {
                            "position_id": "888:test:1",
                            "market": "MATCH_ODDS",
                            "selection": "Player A",
                            "remaining_stake": 5.0,
                            "initial_stake": 5.0,
                            "entry_odds": 1.5,
                        }
                    ],
                    "available_balance": 95.0,
                    "wallet_balance": 100.0,
                    "position_history": [],
                },
            )
            try:
                engine.shutdown()
                meta = storage.load_meta("888")
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

        self.assertEqual(meta["open_positions"], [])
        self.assertAlmostEqual(meta["available_balance"], 100.0)
        self.assertEqual(meta["settlement_status"], "voided_on_shutdown")

    def test_shutdown_closes_position_with_live_odds(self) -> None:
        engine = runner()
        _bind_runner_persistence(engine)
        engine._executor = type("X", (), {"shutdown": lambda *args, **kwargs: None})()
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            temp_path = Path(temporary)
            storage.DATA_DIR = temp_path
            analysis_module.DATA_DIR = temp_path
            event_id = "889"
            storage.match_dir(event_id).mkdir(parents=True, exist_ok=True)
            snap = snapshot(odds=2.0)
            snap["timestamp"] = "2026-07-27T16:00:00.000000+00:00"
            storage.save_snapshot(event_id, snap)
            storage.save_meta(
                event_id,
                {
                    "open_positions": [
                        {
                            "position_id": "889:test:1",
                            "market": "MATCH_ODDS",
                            "selection": "Player A",
                            "selection_id": 1,
                            "market_id": "m-1",
                            "remaining_stake": 10.0,
                            "initial_stake": 10.0,
                            "entry_odds": 2.0,
                        }
                    ],
                    "available_balance": 90.0,
                    "wallet_balance": 100.0,
                    "realized_pnl": 0.0,
                    "position_history": [],
                    "analysis_player1": "Player A",
                    "analysis_player2": "Player B",
                },
            )
            try:
                engine.shutdown()
                meta = storage.load_meta(event_id)
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

        self.assertEqual(meta["open_positions"], [])
        # entry 2.0 / exit 2.0 → pnl 0; saldo vuelve a 100
        self.assertAlmostEqual(meta["available_balance"], 100.0)
        self.assertEqual(meta["settlement_status"], "settled_on_shutdown")
        self.assertTrue(
            any(
                item.get("event") == "closed_on_shutdown"
                for item in (meta.get("position_history") or [])
            )
        )

    def test_prune_skips_until_finished_then_keeps_key_samples(self) -> None:
        from collector import config as collector_config
        from collector.storage import (
            _snapshot_filename,
            list_snapshot_files,
            prune_match_snapshots,
            save_meta,
        )

        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            original_flag = collector_config.SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED
            original_keep = collector_config.SNAPSHOT_KEEP_AFTER_FINISH
            storage.DATA_DIR = Path(temporary)
            collector_config.SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED = True
            storage.SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED = True
            collector_config.SNAPSHOT_KEEP_AFTER_FINISH = 5
            storage.SNAPSHOT_KEEP_AFTER_FINISH = 5
            event_id = "9001"
            match_path = storage.match_dir(event_id)
            match_path.mkdir(parents=True, exist_ok=True)
            timestamps = []
            for index in range(12):
                ts = datetime(2026, 7, 27, 12, 0, index, tzinfo=timezone.utc)
                timestamps.append(ts.isoformat())
                filename = _snapshot_filename(ts)
                payload = snapshot()
                payload["timestamp"] = ts.isoformat()
                (match_path / filename).write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )
            save_meta(
                event_id,
                {
                    "analysis_status": "running",
                    "snapshots_count": 12,
                    "last_processed_snapshot_at": timestamps[-1],
                },
            )
            try:
                skipped = prune_match_snapshots(event_id)
                self.assertTrue(skipped.get("skipped"))
                self.assertEqual(len(list_snapshot_files(event_id)), 12)

                save_meta(
                    event_id,
                    {
                        "analysis_status": "finished",
                        "snapshots_count": 12,
                        "last_processed_snapshot_at": timestamps[-1],
                    },
                )
                pruned = prune_match_snapshots(event_id)
                remaining = list_snapshot_files(event_id)
            finally:
                storage.DATA_DIR = original_data_dir
                collector_config.SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED = original_flag
                storage.SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED = original_flag
                collector_config.SNAPSHOT_KEEP_AFTER_FINISH = original_keep
                storage.SNAPSHOT_KEEP_AFTER_FINISH = original_keep

        self.assertFalse(pruned.get("skipped"))
        self.assertLessEqual(len(remaining), 5)
        self.assertGreaterEqual(pruned.get("pruned", 0), 7)

    def test_health_ignores_missing_reports_while_analysts_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                storage.save_index(
                    {
                        "matches": {
                            "1001": {
                                "player1": "A",
                                "player2": "B",
                                "is_live": True,
                                "last_snapshot_at": "2026-07-27T10:00:00+00:00",
                            }
                        }
                    }
                )
                storage.match_dir("1001").mkdir(parents=True, exist_ok=True)
                storage.save_meta(
                    "1001",
                    {
                        "analysis_status": "analysts_running",
                        "analysis_started_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "last_snapshot_at": "2026-07-27T10:00:00+00:00",
                    },
                )
                health = storage.analysis_health_summary()
            finally:
                storage.DATA_DIR = original_data_dir

        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["events_unhealthy"], 0)

    def test_health_degrades_when_analysts_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_data_dir = storage.DATA_DIR
            storage.DATA_DIR = Path(temporary)
            try:
                storage.save_index(
                    {
                        "matches": {
                            "1002": {
                                "player1": "A",
                                "player2": "B",
                                "is_live": True,
                                "last_snapshot_at": "2026-07-27T10:00:00+00:00",
                            }
                        }
                    }
                )
                storage.match_dir("1002").mkdir(parents=True, exist_ok=True)
                started = (
                    datetime.now(timezone.utc) - timedelta(seconds=900)
                ).isoformat()
                storage.save_meta(
                    "1002",
                    {
                        "analysis_status": "analysts_running",
                        "analysis_started_at": started,
                        "last_snapshot_at": "2026-07-27T10:00:00+00:00",
                    },
                )
                health = storage.analysis_health_summary()
            finally:
                storage.DATA_DIR = original_data_dir

        self.assertEqual(health["status"], "degraded")
        self.assertEqual(health["events_unhealthy"], 1)
        self.assertTrue(health["details"][0].get("analysts_timed_out"))

    def test_ensure_terminal_wait_turn_writes_journal(self) -> None:
        engine = runner()
        _bind_runner_persistence(engine)
        with tempfile.TemporaryDirectory() as temporary:
            original_storage_data_dir = storage.DATA_DIR
            original_analysis_data_dir = analysis_module.DATA_DIR
            temp_path = Path(temporary)
            storage.DATA_DIR = temp_path
            analysis_module.DATA_DIR = temp_path
            storage.match_dir("35871663").mkdir(parents=True, exist_ok=True)
            storage.save_meta(
                "35871663",
                {
                    "analysis_player1": "Player A",
                    "analysis_player2": "Player B",
                    "analysis_tournament": "Test Open",
                    "analysis_match_date": "2026-07-27",
                    "wallet_balance": 100.0,
                    "available_balance": 100.0,
                },
            )
            try:
                wrote = engine._ensure_terminal_wait_turn(
                    "35871663",
                    {"player1": "Player A", "player2": "Player B"},
                    reason="El partido terminó antes de analizar el backlog.",
                    snapshot_timestamp="2026-07-27T12:00:00+00:00",
                    label_source="finished_unanalyzed",
                )
                turns_path = (
                    storage.match_dir("35871663") / "generalist_turns.jsonl"
                )
                lines = [
                    line
                    for line in turns_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                turn = json.loads(lines[0])
                wrote_again = engine._ensure_terminal_wait_turn(
                    "35871663",
                    {"player1": "Player A", "player2": "Player B"},
                    reason="duplicado",
                    snapshot_timestamp="2026-07-27T12:00:00+00:00",
                    label_source="finished_unanalyzed",
                )
            finally:
                storage.DATA_DIR = original_storage_data_dir
                analysis_module.DATA_DIR = original_analysis_data_dir

        self.assertTrue(wrote)
        self.assertFalse(wrote_again)
        self.assertEqual(len(lines), 1)
        self.assertEqual(turn["target"]["tool_call"]["name"], "wait")
        self.assertTrue(turn["target"]["tool_call"].get("synthetic"))
        self.assertEqual(turn["outcome"]["label_source"], "finished_unanalyzed")
        self.assertFalse(turn["outcome"]["accepted_for_training"])

    def test_ensure_scraper_paths_purges_foreign_modules(self) -> None:
        from collector import paths as paths_module
        import types

        fake = types.ModuleType("betfair_scraper")
        fake.__file__ = str(
            Path(sys.prefix) / "Lib" / "site-packages" / "betfair_scraper" / "__init__.py"
        )
        previous = sys.modules.get("betfair_scraper")
        sys.modules["betfair_scraper"] = fake
        try:
            removed = paths_module._purge_foreign_scraper_modules()
            paths_module.ensure_scraper_paths()
            self.assertIn("betfair_scraper", removed)
            self.assertNotIn("betfair_scraper", sys.modules)
        finally:
            if previous is not None:
                sys.modules["betfair_scraper"] = previous
            else:
                sys.modules.pop("betfair_scraper", None)


if __name__ == "__main__":
    unittest.main()
