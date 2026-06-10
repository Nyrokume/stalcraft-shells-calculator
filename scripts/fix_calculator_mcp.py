#!/usr/bin/env python3
"""Читает Лист1, чинит Калькулятор B37:C47, расширяет таблицы до N=109."""

from __future__ import annotations

import math
import re
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

SPREADSHEET_ID = "1Sl8xecEC4VlyHCjuZv4ienrIerz2AL7esLyCu6DQkDU"
KEY = Path(__file__).resolve().parents[1] / "config" / "google" / "service-account.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def headers() -> dict[str, str]:
    creds = service_account.Credentials.from_service_account_file(str(KEY), scopes=SCOPES)
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


def get_values(h: dict, sheet: str, range_a1: str) -> list[list]:
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
        f"/values/'{sheet}'!{range_a1}"
    )
    r = requests.get(url, headers=h, timeout=120)
    r.raise_for_status()
    return r.json().get("values", [])


def batch_update(h: dict, body: dict) -> dict:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
    r = requests.post(url, headers=h, json=body, timeout=120)
    if not r.ok:
        raise SystemExit(f"batchUpdate {r.status_code}: {r.text[:800]}")
    return r.json()


def update_values(h: dict, sheet: str, range_a1: str, values: list, option: str = "USER_ENTERED") -> None:
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
        f"/values/'{sheet}'!{range_a1}?valueInputOption={option}"
    )
    r = requests.put(url, headers=h, json={"values": values}, timeout=120)
    if not r.ok:
        raise SystemExit(f"update {r.status_code}: {r.text[:800]}")


def parse_num(s) -> float | None:
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    t = re.sub(r"[^\d.\-]", "", t)
    try:
        return float(t)
    except ValueError:
        return None


def read_params_from_sheet1(rows: list[list]) -> dict:
    """Парсит sever-profit-model.csv-структуру на Лист1."""
    params: dict[str, float] = {}
    key_map = {
        "avgzkp": "zkp",
        "migrate": "migrate",
        "migratedth": "migrate",
        "severdeath": "sever",
        "attemp": "n",
        "avgprf": "avgprf",
        "avgvns": "avgvns",
    }
    for row in rows:
        if len(row) < 3:
            continue
        section, name, val = row[0].strip(), row[1].strip().lower(), row[2]
        if section.startswith("Входные") or name:
            num = parse_num(val)
            if num is None:
                continue
            for pat, key in key_map.items():
                if pat in name.replace(" ", ""):
                    params[key] = num
                    break
    # defaults
    zkp = params.get("zkp", 17000)
    migrate = params.get("migrate", 0.05)
    if migrate > 1:
        migrate /= 100
    sever = params.get("sever", 0.35)
    if sever > 1:
        sever /= 100
    n = int(params.get("n", 5))
    p_ok = (1 - migrate) * (1 - sever)
    loot = params.get("loot")
    if loot is None:
        avg = params.get("avgvns") or params.get("avgprf") or 143333.33
        loot = (avg / n + zkp) / p_ok if p_ok else 73927.4
    return {"zkp": zkp, "migrate": migrate, "sever": sever, "n": n, "loot": loot, "p_ok": p_ok}


def comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k)


def binom_pmf(n: int, p: float, k: int) -> float:
    if k < 0 or k > n:
        return 0.0
    return comb(n, k) * (p**k) * ((1 - p) ** (n - k))


def main() -> None:
    h = headers()
    meta = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}",
        headers=h,
        timeout=120,
    )
    meta.raise_for_status()
    sheets = [s["properties"]["title"] for s in meta.json()["sheets"]]
    print("Листы:", sheets)

    sheet1_name = sheets[0]
    sheet1 = get_values(h, sheet1_name, "A1:E100")
    params = read_params_from_sheet1(sheet1)
    print("Параметры с Лист1:", params)

    calc_name = "Калькулятор" if "Калькулятор" in sheets else sheets[-1]

    # Ввод на Калькуляторе — числа с Лист1 (без формул → нет #ERROR от ссылок)
    update_values(
        h,
        calc_name,
        "B3:B7",
        [
            [params["zkp"]],
            [params["migrate"]],
            [params["sever"]],
            [params["loot"]],
            [params["n"]],
        ],
        option="RAW",
    )

    # B37:C47 — считаем в Python и пишем RAW (гарантированно без #ERROR)
    n = int(params["n"])
    p = params["p_ok"]
    zkp, loot = params["zkp"], params["loot"]
    header = [["k успехов", "Вероятность", "Чистый профит"]]
    rows = []
    for k in range(0, 11):
        if k > n:
            rows.append([k, "", ""])
        else:
            prob = binom_pmf(n, p, k)
            net = k * loot - n * zkp
            rows.append([k, prob, net])
    update_values(h, calc_name, "A36:C47", header + rows, option="RAW")

    # Формулы результатов (англ. — Sheets локализует)
    update_values(
        h,
        calc_name,
        "B10:B18",
        [
            ["=1-B4"],
            ["=(1-B4)*(1-B5)"],
            ["=B11*B6-B3"],
            ["=B7*B3"],
            ["=B7*B11*B6"],
            ["=B7*(B11*B6-B3)"],
            ["=1-(1-B11)^B7"],
            ["=1-B4^B7"],
            ["=B7*B11"],
        ],
    )

    # Таблица N=1..109 (ходки / «графики» данных)
    max_n = 109
    prob_header = [["N ходок", "Чистый профит (ожид.)", "Затраты", "Валовый лут", "P(≥1 успех)"]]
    prob_rows = []
    ev1 = p * loot - zkp
    for i in range(1, max_n + 1):
        prob_rows.append(
            [
                i,
                f"=A{i+119}*(($B$11)*$B$6-$B$3)",
                f"=A{i+119}*$B$3",
                f"=A{i+119}*$B$11*$B$6",
                f"=1-(1-$B$11)^A{i+119}",
            ]
        )
    # place at row 120
    start = 120
    update_values(h, calc_name, f"A{start}:E{start}", prob_header)
    # fix row refs in formulas - use absolute row numbers
    fixed_rows = []
    for i in range(1, max_n + 1):
        r = start + i
        fixed_rows.append(
            [
                i,
                f"=A{r}*(($B$11)*$B$6-$B$3)",
                f"=A{r}*$B$3",
                f"=A{r}*$B$11*$B$6",
                f"=1-(1-$B$11)^A{r}",
            ]
        )
    update_values(h, calc_name, f"A{start+1}:E{start+max_n}", fixed_rows)

    # P добег / успех vs N до 109 — row 230
    start2 = 230
    update_values(h, calc_name, f"A{start2}:D{start2}", [["N", "P (≥1 добег)", "P (≥1 успех)", "P (0 успехов)"]])
    rows2 = []
    for i in range(1, max_n + 1):
        r = start2 + i
        rows2.append(
            [
                i,
                f"=1-$B$4^A{r}",
                f"=1-(1-$B$11)^A{r}",
                f"=(1-$B$11)^A{r}",
            ]
        )
    update_values(h, calc_name, f"A{start2+1}:D{start2+max_n}", rows2)

    print(f"OK: {calc_name} B37:C47 + таблицы до N={max_n}")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")


if __name__ == "__main__":
    main()
