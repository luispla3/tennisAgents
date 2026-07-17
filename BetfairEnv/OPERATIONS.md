# Operación continua

## Arranque

Desde `BetfairEnv`:

```powershell
python api/server.py
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
  snapshot pendiente.
- Un snapshot con error se reintenta tres veces con backoff. Después queda
  marcado como error y el sistema continúa con el siguiente; hay que revisar
  `analysis_error` en `/api/matches`.
- Los JSONL de auditoría rotan al alcanzar 100 MB. Los snapshots tienen una
  retención configurable de 20 000 por partido:
  `TENNISAGENTS_SNAPSHOT_RETENTION_COUNT`.

## Supervisión recomendada

Para semanas de operación no conviene dejar el proceso sin supervisor. Usar
Windows Task Scheduler, NSSM o un servicio equivalente para:

1. arrancar la API al iniciar sesión/servidor;
2. reiniciar la API si termina;
3. consultar periódicamente `/api/collector/status`;
4. alertar si `last_cycle_at` queda obsoleto, si el log contiene errores
   repetidos o si un partido lleva demasiado tiempo en
   `analysis_status=error`.

Los parámetros de análisis se pueden ajustar con:

- `TENNISAGENTS_LLM_TIMEOUT_SEC` (por defecto `180`);
- `TENNISAGENTS_LLM_MAX_RETRIES` (por defecto `1`);
- `TENNISAGENTS_AUTOMATED_ANALYSIS_WORKERS` (por defecto `2`);
- `TENNISAGENTS_AUDIT_LOG_MAX_BYTES` (por defecto `104857600`).

## Aspectos críticos

- Debe existir una sola instancia del colector. Arrancarlo mediante el endpoint
  de control evita normalmente duplicados mediante `collector.pid`.
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
