#!/usr/bin/env python3
"""Smoke tests para endpoints del dashboard."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.dashboard import app, get_soldelia_stats


def test_stats_soldelia_endpoint() -> None:
    """La ruta y su handler de stats Soldelia devuelven la estructura esperada."""
    route_paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/stats/soldelia" in route_paths, "Endpoint /api/stats/soldelia no registrado"

    data = get_soldelia_stats()

    required_fields = [
        "total_leads",
        "tier_a",
        "tier_b",
        "tier_c",
        "discard",
        "con_telefono",
        "plantas_activas",
        "plantas_top",
        "comision_estimada_ano1_eur",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    assert isinstance(data["total_leads"], int)
    assert isinstance(data["tier_a"], int)
    assert isinstance(data["tier_b"], int)
    assert isinstance(data["tier_c"], int)
    assert isinstance(data["discard"], int)
    assert isinstance(data["con_telefono"], int)
    assert isinstance(data["plantas_activas"], int)
    assert isinstance(data["plantas_top"], list)
    assert isinstance(data["comision_estimada_ano1_eur"], (int, float))

    assert data["total_leads"] == (
        data["tier_a"] + data["tier_b"] + data["tier_c"] + data["discard"]
    ), "Total leads should equal sum of tiers"
    assert data["con_telefono"] <= data["total_leads"], "Leads con teléfono cannot exceed total"
    assert data["plantas_activas"] >= 0
    assert data["comision_estimada_ano1_eur"] >= 0


if __name__ == "__main__":
    test_stats_soldelia_endpoint()
    print("✓ test_stats_soldelia_endpoint passed")
    print("✓ All tests passed")
