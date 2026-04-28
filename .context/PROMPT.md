# Cómo abrir una sesión nueva con Claude.ai (o cualquier LLM web)

## Codex CLI: NO necesita esto

Codex lee AGENTS.md automáticamente. Solo escribe tu pregunta directa.

## Claude.ai, ChatGPT, etc.: usa este flujo

### 1. Regenera STATE
```bash
cd ~/mejoradora_leads && ./bin/brief
```

### 2. Copia el contexto al portapapeles
```bash
cat AGENTS.md .context/PROJECT.md .context/DECISIONS.md .context/STATE.md
```

### 3. Pega esto al chat antes de tu pregunta

---

Soy David Braojos, founder de Mejoradora Leads. Te paso el contexto canónico
del proyecto en 4 documentos. Léelos antes de responder. Si tu propuesta
contradice DECISIONS.md, aviso explícitamente y propón abrir una entrada
nueva en lugar de revertir silenciosamente.

[PEGAR AQUÍ EL OUTPUT DEL CAT DE PASO 2]

Mi pregunta de hoy:
[ESCRIBIR PREGUNTA]

---

## Al cerrar la sesión

Si tomaste alguna decisión arquitectónica o estratégica importante:
```bash
nano .context/DECISIONS.md
# (añadir entrada al final con fecha de hoy)
./bin/brief
git add -A && git commit -m "session: [resumen breve]"
```
