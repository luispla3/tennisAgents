# Operación continua

## Arranque

Desde `BetfairEnv`:

```powershell
python -m api.server
```

En otra consola:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8770/api/collector/start
Invoke-RestMethod http://127.0.0.1:8770/api/collector/status
```

El colector escribe el log rotativo en `.run/collector.log`. Para detenerlo:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8770/api/collector/stop
```

## Recuperación y persistencia

- Cada snapshot se escribe de forma atómica antes de notificar al sistema de
  análisis.
- La cola de análisis no conserva snapshots completos en memoria: los recupera
  del disco. Si el proceso se reinicia, continúa desde
  `last_processed_snapshot_at`.
- Los analistas se ejecutan una vez por partido y el generalista una vez por
  snapshot pendiente. Solo se marca `analysts_completed=true` si existen los
  cuatro informes y pasan la validación mínima de calidad.
- Si se acumulan varios snapshots, solo el más reciente y todavía fresco puede
  mutar el ledger. Los anteriores se registran en
  `analysis_superseded_batches`; un snapshot antiguo o de un partido terminado
  se marca `stale_skipped`/`finished_unanalyzed`. En `finished_unanalyzed` se
  intenta un último análisis; si no hay turno, se escribe un Wait sintético.
- Un snapshot con error se reintenta tres veces y después se reprograma con
  backoff persistente. **No** avanza `last_processed_snapshot_at`, por lo que
  no se pierde silenciosamente. Los pendientes se reanudan al reiniciar. Los
  fallos permanentes alcanzan `dead_letter` tras el máximo configurado; los
  errores transitorios de cuota/rate-limit quedan fuera de ese límite.
- Cada decisión tiene un journal atómico en `analysis_records/`. El JSONL,
  `context.md`, `decision.md`, saldo y cursor se confirman de forma idempotente.
- Un fallback técnico del LLM no se registra como `Wait` válido ni se acepta
  para entrenamiento.
- Los JSONL de auditoría rotan al alcanzar 100 MB. Los snapshots **no se podan
  mientras el partido no esté `finished`**
  (`TENNISAGENTS_SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED=true` por defecto). Al
  liquidar, se compactan a como máximo
  `TENNISAGENTS_SNAPSHOT_KEEP_AFTER_FINISH` (100) snapshots clave (primero,
  último y muestra uniforme) para auditoría post-mortem. Si
  `TENNISAGENTS_SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED=false`, vuelve el comportamiento
  clásico con tope `TENNISAGENTS_SNAPSHOT_RETENTION_COUNT` (20 000) solo sobre
  snapshots ya procesados; el exceso no procesable marca
  `snapshot_retention_blocked`.
- Al detener el colector: drain breve (`TENNISAGENTS_SHUTDOWN_DRAIN_SEC`, 5s),
  reconcile de partidos acabados, intento de Close/cash-out o liquidación por
  marcador (`TENNISAGENTS_SETTLE_OPEN_POSITIONS_ON_SHUTDOWN=true`) y, si queda
  algo abierto, void del stake
  (`TENNISAGENTS_VOID_OPEN_POSITIONS_ON_SHUTDOWN`).

## Ejecución automática 24/7 en Windows

El supervisor `ops/supervisor.py` mantiene activas la API y el colector. El
colector emite un heartbeat cada 30 segundos incluso durante ciclos largos; el
supervisor reinicia si esa señal queda obsoleta. Un ciclo con errores figura
como `degraded`/`failed`, y la salud del análisis se expone por API y en la UI.
Los logs rotativos son `.run/supervisor.log`, `.run/api.log` y
`.run/collector.log`.

Instalar la tarea de Windows (queda desactivada por defecto):

```powershell
cd C:\Users\luisp\tennisAgents\BetfairEnv
powershell -ExecutionPolicy Bypass -File .\ops\install_windows_task.ps1
```

Activarla y arrancar el sistema:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\manage_windows_task.ps1 -Action start
```

Consultar estado o detenerlo:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\manage_windows_task.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\ops\manage_windows_task.ps1 -Action stop
```

`stop` solicita primero el cierre coordinado del supervisor, API, colector y
workers de análisis. Solo usa terminación forzada como último recurso tras el
timeout; los journals y escrituras atómicas permiten reanudar un snapshot si
esa salida de emergencia fuese necesaria.

La tarea se ejecuta al arrancar Windows aunque no haya una terminal de Cursor
abierta ni un usuario conectado. Se registra como `SYSTEM` para conservar acceso
a Internet antes de que un usuario inicie sesión. El instalador solicita UAC y
ejecuta una autoprueba bajo esa misma cuenta sin arrancar el colector. Task
Scheduler intenta reiniciarla cada minuto si el supervisor falla.

Variables opcionales:

- `TENNISAGENTS_SUPERVISOR_CHECK_SEC` (por defecto `30`);
- `TENNISAGENTS_COLLECTOR_STALE_SEC` (por defecto `180`);
- `TENNISAGENTS_API_START_TIMEOUT_SEC` (por defecto `30`).

LLM por defecto (colector automático incluido):

- Proveedor: `openrouter`
- Backend: `https://openrouter.ai/api/v1`
- Analistas (`quick_think_llm`): `deepseek/deepseek-v4-flash-0731`
- Generalista (`deep_think_llm`): `deepseek/deepseek-v4-flash`
- Clave requerida: `OPENROUTER_API_KEY` en `.env`

Sobrescribibles con:

- `TENNISAGENTS_LLM_PROVIDER`
- `TENNISAGENTS_LLM_BASE_URL`
- `TENNISAGENTS_DEEP_THINK_LLM`
- `TENNISAGENTS_QUICK_THINK_LLM`

Los parámetros de análisis se pueden ajustar con:

- `TENNISAGENTS_LLM_TIMEOUT_SEC` (por defecto `180`);
- `TENNISAGENTS_LLM_MAX_RETRIES` (por defecto `1`);
- `TENNISAGENTS_AUTOMATED_ANALYSIS_WORKERS` (por defecto `2`);
- `TENNISAGENTS_ANALYSIS_RETRY_DELAY_SEC` (por defecto `60`);
- `TENNISAGENTS_ANALYSIS_SNAPSHOT_MAX_AGE_SEC` (por defecto `300`);
- `TENNISAGENTS_ANALYSIS_MAX_FAILURES_PER_SNAPSHOT` (por defecto `12`);
- `TENNISAGENTS_PROVIDER_CIRCUIT_BREAKER_SEC` (por defecto `900`);
- `TENNISAGENTS_ANALYST_REPORT_MIN_CHARS` (por defecto `1000`);
- `TENNISAGENTS_ANALYSTS_MAX_RUNTIME_SEC` (por defecto `600`): no degrada
  health por `missing_reports` mientras `analysts_running` dentro de este
  límite; también acota reintentos in-process de analistas;
- `TENNISAGENTS_ANALYSTS_IN_PROCESS_RETRIES` (por defecto `3`);
- `TENNISAGENTS_ANALYSTS_RETRY_SLEEP_SEC` (por defecto `5`);
- `TENNISAGENTS_CAPTURE_GAP_WARN_SEC` (por defecto `300`): log de gap si el
  hueco entre ciclos supera el umbral (sleep/crash);
- `TENNISAGENTS_NO_SNAPSHOT_ALERT_SEC` (por defecto `900`): alerta si hay
  partidos activos y no llegan snapshots nuevos;
- `TENNISAGENTS_MINIMUM_BET_EDGE` (por defecto `0.02`);
- `TENNISAGENTS_MINIMUM_BET_STAKE` (por defecto `1.0`);
- `TENNISAGENTS_MATCH_ODDS_SHORT_ODDS_MAX` (por defecto `1.25`);
- `TENNISAGENTS_MATCH_ODDS_SHORT_MIN_EDGE` (por defecto `0.05`);
- `TENNISAGENTS_MAX_STAKE_FRACTION` (por defecto `0.20`);
- `TENNISAGENTS_MAX_TOTAL_EXPOSURE_FRACTION` (por defecto `0.50`);
- `TENNISAGENTS_SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED` (por defecto `true`);
- `TENNISAGENTS_SNAPSHOT_KEEP_AFTER_FINISH` (por defecto `100`);
- `TENNISAGENTS_PURGE_ORPHAN_MATCH_DIRS` (por defecto `false`): si `true`,
  borra directorios de partido fuera del índice live tras
  `TENNISAGENTS_STALE_SNAPSHOT_HOURS` (6 h). **Nunca** borra dirs con
  `generalist_turns.jsonl`, reports o analysis_records. El clear manual de la
  UI/API sigue siendo la única forma de vaciar el dataset a propósito;
- `TENNISAGENTS_SETTLE_OPEN_POSITIONS_ON_SHUTDOWN` (por defecto `true`);
- `TENNISAGENTS_SHUTDOWN_DRAIN_SEC` (por defecto `5`);
- `TENNISAGENTS_AUDIT_LOG_MAX_BYTES` (por defecto `104857600`).

Si un partido termina sin turno de generalista, el colector intenta un último
análisis del snapshot más reciente; si falla, escribe un **Wait sintético**
(`label_source=finished_unanalyzed` / `finished_without_generalist`) antes de
avanzar el cursor, para no dejar partidos `finished` sin journal.

## Contabilidad simulada y políticas

- El bankroll es una simulación aislada por partido, pensada para comparar
  trayectorias con el mismo saldo inicial; no representa una caja global real.
- `Bet` se rechaza si falta Flashscore, no hay mercados abiertos, el mercado no
  está abierto, la selección no existe, el stake es ≤ 0 o inferior a
  `TENNISAGENTS_MINIMUM_BET_STAKE` (por defecto 1), el stake supera el saldo, el
  stake supera `TENNISAGENTS_MAX_STAKE_FRACTION` del wallet (por defecto 20%), la
  exposición total supera `TENNISAGENTS_MAX_TOTAL_EXPOSURE_FRACTION` (por
  defecto 50%), o el edge calculado es inferior al mínimo. En `MATCH_ODDS` con
  cuota ≤ `TENNISAGENTS_MATCH_ODDS_SHORT_ODDS_MAX` (1.25) se exige edge ≥
  `TENNISAGENTS_MATCH_ODDS_SHORT_MIN_EDGE` (5%). Un marcador Flashscore
  retrasado (p.ej. 0-0 con mercados de set 2/3) ya no bloquea por sí solo.
- El generalista convierte a Wait cualquier Bet con stake ≤ 0 antes de
  persistir. Las líneas abiertas de **todas** las familias (incluido
  MATCH_ODDS) se presentan como candidatas iguales; el prompt pide elegir la
  de mejor EV, no prohibir ni forzar un tipo de mercado. El journal guarda
  calibración homogénea: implícita, edge, stake% wallet/available y
  `market_family`.
- El generalista recibe un resumen de cartera y las líneas abiertas con
  probabilidad implícita; debe comparar edges entre mercados, dimensionar con
  quarter-Kelly aproximado y evitar concentración correlacionada de capital.
  Las pérdidas de trayectoria son esperables hasta entrenar el modelo.
- El matching de mercados acepta `market_type`, alias (`match_winner` →
  `MATCH_ODDS`) y el name visible en español del snapshot.
- La cuota, probabilidad implícita, probabilidad estimada, edge, market ID,
  selection ID y un `position_id` único quedan guardados.
- `Close` exige una posición no ambigua, admite cierre parcial y calcula el
  cash-out simulado con la cuota actual. Si el mercado ya no cotiza pero el
  resultado del mercado es demostrable por progresión de marcador, liquida
  sin cuota; si no, mantiene la posición hasta el cierre.
- Al finalizar un partido se liquidan mercados demostrables (`MATCH_ODDS`,
  set betting, correct score de set, totales, both-to-win-a-set y juegos
  reconstruidos por progresión de snapshots). Los no demostrables se anulan
  (void, stake devuelto) si `TENNISAGENTS_VOID_UNRESOLVED_MARKETS_ON_FINISH=true`
  (por defecto).
- Un partido se considera terminado cuando el marcador de sets es decisivo:
  2 sets en torneos normales (mejor de 3) o 3 sets en Grand Slam (mejor de 5),
  aunque el estado textual siga en "En juego". Un `sets_won` a 0-0 no bloquea
  esa detección si el score ya muestra sets completos.
- El marcador del snapshot toma como base el scoreboard de Flashscore. El
  `live_score` de Betfair solo lo actualiza si va al día o por delante; un
  live stale (0-0 eterno) ya no genera scores fantasma tipo `0-0 6-4`.
- En el primer arranque, los saldos/posiciones del esquema antiguo se aíslan en
  `legacy_positions_quarantined`, se restaura el wallet simulado y se marca
  `ledger_schema_version=2`. No se mezclan posiciones legacy irreconciliables
  con el ledger nuevo.

## Comprobación de salud

```powershell
python -m ops.supervisor --validate --network --llm

$status = Invoke-RestMethod http://127.0.0.1:8770/api/collector/status
$status.cycle_state
$status.analysis_health

Invoke-RestMethod http://127.0.0.1:8770/api/matches
Invoke-RestMethod http://127.0.0.1:8770/api/matches/EVENT_ID/artifacts
```

No se considera saludable si `cycle_state` es `degraded`/`failed`,
`analysis_health.status` es `degraded`, existe `analysis_error`, faltan
informes o hay backlog creciente.

## Aspectos críticos

- Debe existir una sola instancia del colector. El endpoint serializa start/stop
  con un lock interproceso y valida que el PID pertenece realmente a
  `collector/runner.py`.
- El supervisor no puede capturar datos mientras Windows está suspendido,
  apagado o instalando actualizaciones. Después del arranque se recupera solo,
  pero habrá un hueco en los snapshots durante esa interrupción. Para cero
  interrupciones hace falta ejecutar el proyecto en un servidor siempre activo.
- En este equipo la suspensión conectado a corriente está desactivada. En
  batería Windows puede suspenderse; para operación continua debe permanecer
  conectado a corriente.
- Hay que verificar límites, saldo y disponibilidad de Betfair, Flashscore,
  proveedores meteorológicos y del LLM. Un proveedor caído no debe interpretarse
  como una señal de apuesta válida.
- El `Bet`, `Wait` y `Close` del generalista registran decisiones y actualizan
  un wallet simulado; **no ejecutan órdenes reales en Betfair**. Antes de
  automatizar dinero real hace falta un ejecutor de órdenes separado, idempotente,
  con reconciliación de posiciones, límites de riesgo y apagado de emergencia.
- Probar primero durante varias horas con credenciales de solo lectura y
  comprobar que snapshots, informes, `context.md` y decisiones se recuperan
  correctamente después de reiniciar el proceso.
