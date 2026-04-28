# STATE — Mejoradora Leads

> AUTO-GENERADO por bin/brief el 2026-04-28 12:05 UTC
> NO editar a mano. Ejecutar `./bin/brief` para regenerar.

## Repo

- Branch: master
- Status: master...origin/master
- Cambios sin commitear: 6 archivos

### Últimos 8 commits

```
6858c89 feat(dashboard): fases 1-3 con geocoding, event log y dashboard v2
5768b0b chore: ignorar logs SMS y artefactos Codex
1ddac9d fix: dinahosting sms command for tier a sends
af46d0c docs: README — actualizar estado 2026-04-23 (puertos, leads, plantas, Obsidian)
744f267 feat: SMS engine integrado con Dinahosting API
ec24c06 docs: arquitectura producto Soldelia + preparación SMS engine
514a118 feat: cron semanal automático para scraping + pipeline Soldelia (lunes 08:00)
348fc33 test: smoke test para endpoint /api/stats/soldelia
```

## Volumen de código

- Líneas Python totales: 4972
- Scripts en scripts/: 22
- Tests: 1

## Datos operativos

- Leads en runs/: 410
- Plantas Soldelia activas: 33
- SMS enviados (log local): 8

## Crons activos

```
ninguno
```

## Procesos detectados en VPS

```
ninguno
```

## Últimas 5 decisiones

```
## 2026-04-28 — Pausa de pipeline automático
## 2026-04-28 — Adoptar `.context/` como single source of truth
## 2026-04-28 — Reducir LLMs en uso a 2 (Codex + Claude.ai)
## 2026-04-28 — Eliminar agentes Esther y Auditor (pendiente)
## 2026-04-28 — SMS engine debe usar copy de Manolo, no template hardcoded
```

## Pendientes urgentes (mantener manualmente)

- [ ] Llamar Bodegas Castaño 968 79 11 15 (Yecla, planta CS Yecla I/II/III)
- [ ] Cambiar password Dinahosting (sigue expuesta en chats)
- [ ] Ejecutar Prompt Codex 2 — limpieza repo (Esther, Auditor, scrapers)
- [ ] Ejecutar Prompt Codex 3 — SMS engine usa copy de Manolo
- [ ] Filtrar 105 leads → 20 viables manualmente

