#!/usr/bin/env python3
"""
route.py — Orquestador de agentes Openfang
Toma leads limpios y los pasa por el pipeline: Paco → Manolo
Requiere: pip install openai
"""

import json
import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib import error as urlerror
from urllib import request as urlrequest

try:
    from openai import OpenAI
    openai_client = OpenAI()
except ImportError:
    print("❌ Instala el SDK: pip install openai")
    exit(1)

BASE_DIR = Path(__file__).parent.parent
AGENTS_DIR = BASE_DIR / "agents"
OUTPUTS_DIR = BASE_DIR / "outputs"
RUNS_DIR = BASE_DIR / "runs"

OPENAI_MODEL = "gpt-4o-mini"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
FORBIDDEN_MANOLO_PATTERNS = (
    r"surplus(?:_pct)?",
    r"excedent\w*",
    r"excedente\w*",
    r"porcent\w*",
    r"%",
)


def parse_json_response(raw: str) -> dict:
    raw = (raw or "").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": str(e), "raw": raw}


def load_system_prompt(agent_name: str) -> str:
    path = AGENTS_DIR / agent_name / "system.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No se encontró system prompt para: {agent_name}")


def call_openai_agent(agent_name: str, user_message: str) -> dict:
    system = load_system_prompt(agent_name)
    print(f"  🤖 [OpenAI] Llamando a {agent_name}...")

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=600,
        messages=[
            {"role": "system", "content": system + "\n\nResponde ÚNICAMENTE con JSON válido. Sin texto adicional ni markdown."},
            {"role": "user", "content": user_message}
        ],
    )
    raw = response.choices[0].message.content.strip()
    return parse_json_response(raw)


def call_claude_agent(agent_name: str, user_message: str) -> dict:
    system = load_system_prompt(agent_name)
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        return {"error": "ANTHROPIC_API_KEY no definida"}

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 600,
        "system": system + "\n\nResponde ÚNICAMENTE con JSON válido. Sin texto adicional ni markdown.",
        "messages": [{"role": "user", "content": user_message}],
    }

    req = urlrequest.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": anthropic_api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=90) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
    except urlerror.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}", "raw": details}
    except Exception as exc:
        return {"error": str(exc)}

    content = parsed.get("content", [])
    text_blocks = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_blocks.append(item.get("text", ""))

    return parse_json_response("\n".join(text_blocks))


def call_manolo_agent(
    agent_name: str,
    user_message: str,
    tier: str,
    model: Literal["claude", "gpt"] = "claude",
) -> tuple[str, dict]:
    if model == "claude":
        print(f"  🤖 [Anthropic:{CLAUDE_MODEL}] Llamando a manolo...")
        return "claude", call_claude_agent(agent_name, user_message)

    if model == "gpt":
        print(f"  🤖 [OpenAI:{OPENAI_MODEL}] Llamando a manolo...")
        return "gpt", call_openai_agent(agent_name, user_message)

    return model, {"error": f"Modelo inválido para Manolo: {model}", "tier": tier}


def choose_manolo_model(tier: str) -> str:
    return "claude" if tier == "A" else "gpt"


def sanitize_text_for_manolo(text: str) -> str:
    clean = text or ""
    # Remueve porcentajes numéricos y cualquier fragmento con términos sensibles.
    clean = re.sub(r"\b\d+(?:[.,]\d+)?\s*%", "", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"[^,.;:\n]*?(?:surplus_pct|surplus|excedente|15\.27|%)[^,.;:\n]*",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    for pattern in FORBIDDEN_MANOLO_PATTERNS:
        clean = re.sub(pattern, " ", clean, flags=re.IGNORECASE)
    return " ".join(clean.split())


def has_forbidden_manolo_term(text: str) -> bool:
    return any(re.search(pattern, text or "", flags=re.IGNORECASE) for pattern in FORBIDDEN_MANOLO_PATTERNS)


def sanitize_payload_for_manolo(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            key_text = str(key)
            if has_forbidden_manolo_term(key_text):
                continue
            sanitized_item = sanitize_payload_for_manolo(item)
            if isinstance(sanitized_item, str):
                sanitized_item = sanitized_item.strip()
                if not sanitized_item:
                    continue
            cleaned[key_text] = sanitized_item
        return cleaned
    if isinstance(value, list):
        return [sanitize_payload_for_manolo(item) for item in value]
    if isinstance(value, str):
        return sanitize_text_for_manolo(value)
    return value


def run_pipeline(lead: dict) -> dict:
    lead_name = lead.get("lead_name", "Lead desconocido")
    print(f"\n📋 Procesando: {lead_name}")
    print("─" * 50)

    run = {
        "lead_id": lead.get("lead_id"),
        "lead_name": lead_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "lead": lead,
    }

    # Paso 1: Paco califica el lead
    paco_result = call_openai_agent(
        "paco",
        f"Califica este lead:\n{json.dumps(lead, ensure_ascii=False, indent=2)}"
    )
    run["paco"] = paco_result

    tier = paco_result.get("tier", "C")
    confidence = paco_result.get("confidence_level", "LOW")
    run["tier"] = tier
    print(f"  🔍 Paco → Tier {tier} | Confidence: {confidence}")

    if tier == "DISCARD":
        run["status"] = "descartado_por_paco"
        save_run(run)
        print("  ❌ Paco descartó el lead")
        return run

    if tier == "C":
        run["status"] = "tier_c_en_espera"
        save_run(run)
        print("  📦 Tier C — guardado sin procesar")
        return run

    # Paso 2: Manolo genera mensajes usando el análisis de Paco
    sanitized_lead_name = sanitize_text_for_manolo(str(lead.get("lead_name", "")))
    sanitized_sector = sanitize_text_for_manolo(str(lead.get("sector", "")))
    sanitized_address = sanitize_text_for_manolo(str(lead.get("address", "")))
    sanitized_phone = sanitize_text_for_manolo(str(lead.get("phone", "no disponible")))
    sanitized_plant_name = sanitize_text_for_manolo(str(lead.get("plant_name", "planta solar cercana")))
    sanitized_distance = sanitize_text_for_manolo(str(lead.get("distance_km", "desconocida")))
    sanitized_power_kw = sanitize_text_for_manolo(str(lead.get("plant_power_kw", "desconocida")))
    sanitized_paco_why = sanitize_text_for_manolo(str(paco_result.get("why", "")))

    manolo_msg = f"""Escribe 3 variantes de mensaje (anti_venta, dolor_perdida, 
autoridad) para este lead.

Lead:
- Nombre: {sanitized_lead_name}
- Sector: {sanitized_sector}
- Dirección: {sanitized_address}
- Teléfono: {sanitized_phone}

Datos de la planta solar más cercana:
- Planta: {sanitized_plant_name}
- Distancia: {sanitized_distance} km
- Potencia: {sanitized_power_kw} kW

Contexto comercial de Paco (limpio): {sanitized_paco_why}

Genera exactamente 3 variantes. JSON válido y completo."""
    manolo_model = choose_manolo_model(tier)
    run["manolo_model"] = manolo_model
    _, manolo_result = call_manolo_agent(
        "manolo",
        manolo_msg,
        tier,
        model=manolo_model,
    )
    run["manolo"] = manolo_result

    # Manolo puede devolver array de variantes o un solo objeto
    if isinstance(manolo_result, list):
        msgs = manolo_result
    else:
        msgs = [manolo_result]

    print(f"  ✍️  Manolo → {len(msgs)} variante(s) generadas")

    run["status"] = "aprobado"
    status_icon = "✅"

    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    print(f"  {status_icon} Pipeline completado — Tier {tier} | {run['status']}")

    return run


def save_run(run: dict):
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "messages").mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lead_slug = run.get("lead_id", "unknown")

    # Run completo
    run_path = RUNS_DIR / f"{lead_slug}_{timestamp}.json"
    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)

    # Mensajes por separado
    if "manolo" in run:
        msg_path = OUTPUTS_DIR / "messages" / f"{lead_slug}_{timestamp}.json"
        with open(msg_path, "w", encoding="utf-8") as f:
            json.dump(run["manolo"], f, ensure_ascii=False, indent=2)

    print(f"  💾 Run guardado en {run_path}")
    return run_path


def main():
    parser = argparse.ArgumentParser(description="Openfang Pipeline Orchestrator")
    parser.add_argument("input", help="JSON limpio (archivo o lead individual)")
    parser.add_argument("--dry-run", action="store_true", help="No guardar resultados")
    args = parser.parse_args()

    filepath = Path(args.input)
    if not filepath.exists():
        print(f"❌ Archivo no encontrado: {filepath}")
        return

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    leads = data if isinstance(data, list) else [data]
    print(f"\n🚀 Openfang Pipeline — {len(leads)} lead(s) a procesar")

    results = []
    for lead in leads:
        run = run_pipeline(lead)
        results.append(run)
        if not args.dry_run and run.get("status") != "descartado_por_paco":
            save_run(run)

    # Resumen
    print("\n" + "═" * 50)
    print("📊 RESUMEN")
    for r in results:
        tier = r.get("tier", "—")
        print(f"  {r['lead_name']}: Tier {tier} | {r['status']}")


if __name__ == "__main__":
    main()
