# DECISIONS — Mejoradora Leads

Log append-only de decisiones arquitectónicas y estratégicas.
Una decisión por bloque. Fecha, decisión, razón, consecuencia.
Nadie revierte una decisión sin abrir una nueva entrada explicando por qué.

---

## 2026-04-28 — Pausa de pipeline automático

**Decisión:** Apagar cron semanal, Hermes Agent y SMS automático.
**Razón:** 0 contratos cerrados después de 3 semanas construyendo. 
Construir más sin vender es trampa de procastinación.
**Consecuencia:** Volver a contacto manual (llamada y visita) hasta tener 
3 contratos firmados antes de retomar automatización.

---

## 2026-04-28 — Adoptar `.context/` como single source of truth

**Decisión:** Toda conversación con cualquier LLM se inicia leyendo 
`.context/PROJECT.md`, `.context/DECISIONS.md`, `.context/STATE.md`.
**Razón:** Pérdida de contexto entre sesiones de Claude, ChatGPT, Gemini, 
Grok genera derivas y opiniones contradictorias.
**Consecuencia:** Un solo lugar canónico actualizado en Git. AGENTS.md
en raíz hace que Codex lo respete automáticamente.

---

## 2026-04-28 — Reducir LLMs en uso a 2 (Codex + Claude.ai)

**Decisión:** Codex CLI para código sobre el repo. Claude.ai para diseño,
auditoría, copywriting y conversaciones largas. Salir de Gemini y Grok.
**Razón:** 4 LLMs en paralelo generan opiniones contradictorias y aumentan
el coste cognitivo de decidir.
**Consecuencia:** Menos ruido, más velocidad. Codex respeta AGENTS.md
automáticamente. Claude.ai recibe el contexto al pegarle .context/.

---

## 2026-04-28 — Eliminar agentes Esther y Auditor (pendiente)

**Decisión:** Quitar agents/esther y agents/auditor del pipeline.
**Razón:** Esther pide a Paco lo que ya hace y a Manolo lo que ya hace
(intermediario sin valor). Auditor marca "requiere_revisión" por defecto
bloqueando todo el copy generado.
**Consecuencia:** Pipeline más rápido y barato. Pendiente ejecutar.

---

## 2026-04-28 — SMS engine debe usar copy de Manolo, no template hardcoded

**Decisión:** scripts/sms_engine.py debe leer la variante "autoridad" del
bloque manolo de cada run JSON antes de caer al template genérico.
**Razón:** Bug detectado: estamos pagando OpenAI tokens para generar 3
variantes de copy por lead y luego tirando todo al SMS.
**Consecuencia:** Pendiente ejecutar (Prompt Codex 3).

---

## 2026-05-11 — Nuevo norte: prospección pura

**Decisión:** La herramienta pasa a modo prospección. 3 contratos cerrados externamente. Habilitado iterar features de búsqueda y exportación.
**Razón:** El objetivo comercial manual está cumplido. Ahora David necesita volumen de leads cualificados para una teleoperadora que consiga visitas.
**Consecuencia:** Se habilitan features de búsqueda dirigida por cubierta, exportación teleoperadora y mejora de clasificación con Sonnet 4.6.

---

## 2026-05-11 — Retirar agente Manolo

**Decisión:** Mover agents/manolo/ a legacy/agents/manolo/. Eliminar la fase Manolo de scripts/route.py. El pipeline queda: Paco clasifica → fin.
**Razón:** Ya no hay outreach digital (WhatsApp/SMS). La teleoperadora llama por teléfono con un argumento corto generado por un nuevo agente "Pitcher" que sustituirá a Manolo en una fase posterior.
**Consecuencia:** route.py se simplifica. Tier A y B se guardan directamente como aprobados tras Paco sin generar mensajes. Manolo queda en legacy/.

---

## 2026-05-11 — Sonnet 4.6 como modelo principal del pipeline

**Decisión:** Migrar Paco de gpt-4o-mini a claude-sonnet-4-6 vía API Anthropic. Nueva variable de entorno ANTHROPIC_API_KEY para la API key dedicada con 100€ de presupuesto.
**Razón:** gpt-4o-mini produce falsos negativos en leads ambiguos. Sonnet 4.6 mejora clasificación a coste marginal (~0.006€/lead). Con 100€ caben >15.000 clasificaciones.
**Consecuencia:** route.py usa call_claude_agent para Paco en todos los tiers. Se mantiene call_openai_agent como fallback si ANTHROPIC_API_KEY no está definida. Se añade tracking de coste por lead en el run JSON.

---

## 2026-05-11 — Unificar catálogo de plantas

**Decisión:** data/plants.json pasa a ser el único catálogo oficial de plantas. data/plants_soldelia.json se elimina por duplicado.
**Razón:** Había dos ficheros con el mismo propósito y referencias repartidas entre scripts, Makefile y dashboard.
**Consecuencia:** Las rutas operativas apuntan a data/plants.json. Las nuevas cubiertas se añaden con scripts/manage_plants.py add o make add-plant.

---
