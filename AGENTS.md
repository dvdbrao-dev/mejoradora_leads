# AGENTS.md — Instrucciones permanentes para asistentes IA

Este fichero es leído automáticamente por Codex y debe ser referenciado por 
cualquier otro LLM (Claude, ChatGPT) al inicio de cada sesión.

## Identidad del proyecto

Mejoradora Leads es la consultoría energética de David Braojos en Granada y 
Lanjarón (Andalucía). NO es un SaaS, NO se va a licenciar, es herramienta 
INTERNA para el negocio comercial de David. Doble producto: cambio de 
comercializadora + PPA solar Soldelia para empresas cercanas a las 33 plantas.

## Norte estratégico (no negociable hasta tener 3 contratos firmados)

1. Cerrar 3 contratos manualmente vía llamada y visita presencial.
2. Solo entonces automatizar lo que dolió hacer a mano.
3. NO añadir features nuevas. NO licenciar. NO escalar prematuramente.

## Reglas para asistentes IA

ANTES de proponer cambios, lee SIEMPRE en este orden:
1. .context/PROJECT.md (qué es este proyecto)
2. .context/DECISIONS.md (decisiones tomadas, no revertir sin razón)
3. .context/STATE.md (estado actual generado por bin/brief)

NUNCA hagas:
- Refactor de paths o abstracciones sin entrada nueva en DECISIONS.md
- Añadir nuevos LLM providers, frameworks, dashboards o agentes
- Generar documentación nueva en raíz del repo (va en .context/ o docs/)
- Reactivar cron, Hermes, SMS automático sin permiso explícito
- Proponer "Obsidian", "Cursor", "Supabase", "Vercel" — usamos lo que ya hay

SIEMPRE haz:
- Commits atómicos con mensaje descriptivo
- Preguntar antes de borrar archivos versionados
- Mantener respuestas concretas y ejecutables, sin teoría
- Detectar y avisar si una propuesta contradice DECISIONS.md

## Stack técnico (no cambia sin DECISIONS.md)

- VPS Hetzner Ubuntu 24 en 5.78.69.147
- Python 3.10 + FastAPI + Uvicorn
- OpenAI API (gpt-4o-mini para Manolo Tier A/B)
- NVIDIA NIM (z-ai/glm4.7 para volumen barato)
- Google Places API
- Crawl4AI (NO usar Firecrawl)
- Dinahosting para SMS
- Repo: github.com/dvdbrao-dev/mejoradora_leads

## Anti-patrones reconocidos (no repetir)

- Sustituir vender por construir
- Consultar 4 LLMs con el mismo problema y mezclar opiniones
- Refactorizar paths/abstracciones sin clientes que paguen
- Generar copy con LLM y hardcodear template en SMS engine
- Crear documentación estratégica nueva (ya hay 7 docs, basta)
