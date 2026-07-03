"""Captura de snapshots Betfair + Flashscore — cargado desde bytecode."""

from __future__ import annotations

import collector.paths  # noqa: F401
from _pyc_loader import bootstrap_pyc

bootstrap_pyc(__name__, __file__)
