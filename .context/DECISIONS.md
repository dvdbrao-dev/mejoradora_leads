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
