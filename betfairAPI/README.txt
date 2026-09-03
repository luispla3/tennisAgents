Betfair Exchange API (MATCH_ODDS tenis in-play)
================================================

Uso rápido
----------
1. Copia `.env.example` a `.env` y pon usuario/contraseña
   (2FA: contraseña + código en BETFAIR_PASSWORD).
2. `python login.py`  → guarda `.session_token`
3. `python test_inplay_tennis.py`  → prueba listado in-play
4. El colector BetfairEnv importa `exchange_tennis.py` en cada ciclo con
   snapshots pendientes y escribe `betfair_exchange` en el JSON.

Identificadores en snapshot
---------------------------
- Sportsbook: `betfair.book = "SPORTSBOOK"`
- Exchange:   `betfair_exchange.book = "EXCHANGE"`
  (solo MATCH_ODDS por ahora)
