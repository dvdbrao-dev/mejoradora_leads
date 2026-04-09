#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from jsonschema import validate, ValidationError


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 scripts/validate_record.py <schema.json> <record.json>")
        sys.exit(1)

    schema_path = Path(sys.argv[1])
    record_path = Path(sys.argv[2])

    if not schema_path.exists():
        print(f"ERROR: no existe el schema: {schema_path}")
        sys.exit(1)

    if not record_path.exists():
        print(f"ERROR: no existe el record: {record_path}")
        sys.exit(1)

    try:
        schema = load_json(schema_path)
    except Exception as e:
        print(f"ERROR leyendo schema: {e}")
        sys.exit(1)

    try:
        record = load_json(record_path)
    except Exception as e:
        print(f"ERROR leyendo record: {e}")
        sys.exit(1)

    try:
        validate(instance=record, schema=schema)
        print(f"OK: {record_path} es válido")
        sys.exit(0)
    except ValidationError as e:
        print(f"ERROR: {record_path} no es válido")
        print(f"Detalle: {e.message}")
        sys.exit(2)


if __name__ == "__main__":
    main()
