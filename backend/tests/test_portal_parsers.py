import json
from pathlib import Path

import portal_parsers as p

FIX = Path(__file__).parent / "fixtures"
load = lambda n: json.loads((FIX / n).read_text(encoding="utf-8"))


def test_parse_accounts():
    out = p.parse_accounts(load("accounts.json"))
    assert out[0]["account_number"] == "ACC-1"
    assert out[0]["account_name"] == "Juan Perez"
    assert out[0]["is_billing_suspended"] is False
    assert out[0]["next_due_date"].startswith("2026-11-02")


def test_parse_accounts_accepts_unwrapped():
    payload = load("accounts.json")["content"]
    assert len(p.parse_accounts(payload)) == 1


def test_parse_service_lines():
    out = p.parse_service_lines(load("service_lines.json"))
    assert out[0]["service_line_number"] == "SL-1"
    assert out[0]["plan"] == "Residencial"
    assert out[0]["terminals"][0]["kit_number"] == "KIT400651113"
    assert out[0]["address"] == "Caracas, VE"
    assert out[0]["latitude"] == 10.48
    assert out[0]["region_code"] == "VE"                        # país de la SL
    assert out[0]["activation_date"] == "2026-01-01T00:00:00Z"  # fecha de activación


def test_parse_service_lines_no_terminals():
    out = p.parse_service_lines({"content": [{"serviceLineNumber": "SL-9"}]})
    assert out[0]["terminals"] == []


def test_parse_balance():
    assert p.parse_balance(load("balance.json")) == (23797.44, "UYU")


def test_parse_balance_empty():
    assert p.parse_balance({"content": {"balances": []}}) is None


def test_parse_usage_sums_cycles():
    out = p.parse_usage(load("usage.json"))
    assert out["cycle_gb"] == 6.0      # ciclo abierto (sin endDate)
    assert out["limit_gb"] == 100.0
    assert out["total_gb"] == 42.0     # suma de ciclos = desde activación
    assert len(out["cycles"]) == 2     # historial de ciclos para la web
    assert out["cycles"][1]["gb"] == 36.0


def test_parse_usage_not_found_is_unknown():
    out = p.parse_usage({"isValid": False, "errors": [{"errorMessage": "not_found"}]})
    assert out["unknown"] is True and out["cycle_gb"] is None
