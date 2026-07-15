"""Cliente HTTP para la API interna de Flashscore."""

from __future__ import annotations

import re
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_FSIGN = "SW9D1eZo"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

SPORT_IDS = {
    "tennis": 2,
    "tenis": 2,
    "football": 1,
    "futbol": 1,
    "basketball": 3,
    "baloncesto": 3,
    "hockey": 4,
}


class FlashscoreError(Exception):
    """Error al consultar Flashscore."""


class FlashscoreClient:
    """Acceso a feeds internos de Flashscore."""

    def __init__(
        self,
        locale: str = "es",
        fsign: Optional[str] = None,
        auto_fetch_fsign: bool = True,
    ) -> None:
        self.locale = locale
        self.base_url = "https://www.flashscore.es" if locale == "es" else f"https://www.flashscore.{locale}"
        self.feed_base = "https://global.flashscore.ninja"
        self._fsign = fsign
        if auto_fetch_fsign and not fsign:
            self._fsign = self._fetch_fsign() or DEFAULT_FSIGN
        elif not self._fsign:
            self._fsign = DEFAULT_FSIGN

    def _fetch_fsign(self) -> Optional[str]:
        try:
            html = self._get_text(f"{self.base_url}/tenis/")
        except FlashscoreError:
            return None
        for pattern in (
            r'"feed_sign"\s*:\s*"([^"]+)"',
            r"feedSign\s*:\s*['\"]([^'\"]+)['\"]",
            r"window\.environment\s*=\s*(\{.*?\});",
        ):
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                continue
            value = match.group(1)
            if value.startswith("{"):
                sign_match = re.search(r'"feed_sign"\s*:\s*"([^"]+)"', value)
                if sign_match:
                    return sign_match.group(1)
            else:
                return value
        return None

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": DEFAULT_USER_AGENT,
            "x-fsign": self._fsign or DEFAULT_FSIGN,
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

    def _get_text(self, url: str) -> str:
        request = Request(url, headers=self._headers())
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise FlashscoreError(f"HTTP {exc.code} al consultar {url}") from exc
        except URLError as exc:
            raise FlashscoreError(f"Error de red al consultar {url}: {exc.reason}") from exc

    def get_daily_feed(self, sport_id: int = 2, day_offset: int = 0) -> str:
        """Partidos del día. day_offset: 0=hoy, 1=mañana, -1=ayer."""
        path = f"/{sport_id}/x/feed/f_{sport_id}_{day_offset}_1_{self.locale}_1"
        return self._get_text(f"{self.feed_base}{path}")

    def get_match_stats(self, match_id: str) -> str:
        """Estadísticas del partido (df_st)."""
        path = f"/2/x/feed/df_st_1_{match_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def get_match_summary(self, match_id: str) -> str:
        """Resumen del partido (df_sui)."""
        path = f"/2/x/feed/df_sui_1_{match_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def get_match_scoreboard(self, match_id: str) -> str:
        """Marcador por sets del partido (df_su)."""
        path = f"/2/x/feed/df_su_1_{match_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def get_match_core(self, match_id: str) -> str:
        """Metadatos del partido (dc), incluye sets cuando están disponibles."""
        path = f"/2/x/feed/dc_1_{match_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def get_match_detail(self, match_id: str) -> str:
        """Detalle punto a punto (df_mh)."""
        path = f"/2/x/feed/df_mh_1_{match_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def get_player_results(
        self,
        player_id: str,
        sport_id: int = 2,
        page: int = 0,
    ) -> str:
        """Historial de resultados de un jugador (pr feed)."""
        path = f"/{sport_id}/x/feed/pr_2_167_{player_id}_{page}_1_{self.locale}_1_s"
        return self._get_text(f"{self.feed_base}{path}")

    def get_player_meta(self, player_id: str, sport_id: int = 2) -> str:
        """Metadatos del jugador (pm feed), incluye slug del perfil."""
        path = f"/{sport_id}/x/feed/pm_1_{player_id}"
        return self._get_text(f"{self.feed_base}{path}")

    def sport_id(self, sport: str) -> int:
        key = sport.lower().strip()
        if key not in SPORT_IDS:
            raise FlashscoreError(f"Deporte no soportado: {sport}. Opciones: {', '.join(sorted(set(SPORT_IDS)))}")
        return SPORT_IDS[key]
