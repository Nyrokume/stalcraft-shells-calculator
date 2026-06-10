#!/usr/bin/env python3
"""Синхронизация Калькулятора через Sheets API (с retry). Запуск: uv run python scripts/mcp_sync_calculator.py"""

from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

SPREADSHEET_ID = "1Sl8xecEC4VlyHCjuZv4ienrIerz2AL7esLyCu6DQkDU"
KEY = Path(__file__).resolve().parents[1] / "config" / "google" / "service-account.json"
MAX_N = 109
RETRIES = 5


def auth_headers() -> dict[str, str]:
    creds = service_account.Credentials.from_service_account_file(
        str(KEY),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


def api(method: str, url: str, headers: dict, **kwargs) -> dict:
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.request(method, url, headers=headers, timeout=90, **kwargs)
            if r.ok:
                return r.json() if r.text else {}
            last_err = f"HTTP {r.status_code}: {r.text[:300]}"
        except requests.RequestException as e:
            last_err = str(e)
        if attempt < RETRIES:
            time.sleep(2 * attempt)
    raise SystemExit(f"Sheets API failed after {RETRIES} tries: {last_err}")


def parse_num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.,\-]", "", str(v).replace(",", "."))
    try:
        return float(s)
    except ValueError:
        return None


def read_params(rows: list[list]) -> dict:
    p = {"zkp": 17000.0, "migrate": 0.05, "sever": 0.35, "n": 5, "loot": 73927.4}
    for row in rows:
        if len(row) < 3:
            continue
        name = str(row[1]).lower()
        val = parse_num(row[2])
        if val is None:
            continue
        if "avgzkp" in name or "закуп" in name:
            p["zkp"] = val
        elif "migratedth" in name or "миграции" in name:
            p["migrate"] = val / 100 if val > 1 else val
        elif "severdeath" in name or ("севере" in name and "жизн" not in name):
            p["sever"] = val / 100 if val > 1 else val
        elif "attemp" in name or "попыт" in name:
            p["n"] = max(1, int(round(val)))
    p["p_ok"] = (1 - p["migrate"]) * (1 - p["sever"])
    if p["p_ok"] > 0:
        for row in rows:
            if len(row) < 3:
                continue
            name = str(row[1]).lower()
            val = parse_num(row[2])
            if val and ("avgvns" in name or "avgprf" in name):
                p["loot"] = (val / p["n"] + p["zkp"]) / p["p_ok"]
                break
    return p


def comb(n: int, k: int) -> float:
    return math.comb(n, k) if 0 <= k <= n else 0.0


def main() -> None:
    h = auth_headers()
    meta = api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}", h)
    sheets = [s["properties"]["title"] for s in meta["sheets"]]
    sheet1 = sheets[0]
    calc = "Калькулятор" if "Калькулятор" in sheets else sheets[-1]
    print("Листы:", sheets)

    s1 = api(
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{sheet1}'!A1:E80",
        h,
    ).get("values", [])
    p = read_params(s1)
    print("Параметры:", p)

    n, pok, zkp, loot = int(p["n"]), p["p_ok"], p["zkp"], p["loot"]
    binom = [["k успехов", "Вероятность", "Чистый профит"]]
    for k in range(11):
        if k > n:
            binom.append([k, "", ""])
        else:
            prob = comb(n, k) * (pok**k) * ((1 - pok) ** (n - k))
            binom.append([k, round(prob, 6), round(k * loot - n * zkp, 2)])

    ranges = {
        f"'{calc}'!B3:B7": [
            [p["zkp"]],
            [p["migrate"]],
            [p["sever"]],
            [p["loot"]],
            [n],
        ],
        f"'{calc}'!A36:C47": binom,
    }

    profit_hdr = [["N ходок", "Чистый профит", "Затраты", "Валовый лут", "P(≥1 успех)"]]
    profit = []
    for i in range(1, MAX_N + 1):
        r = 120 + i
        profit.append(
            [
                i,
                f"=A{r}*(($B$11)*$B$6-$B$3)",
                f"=A{r}*$B$3",
                f"=A{r}*$B$11*$B$6",
                f"=1-(1-$B$11)^A{r}",
            ]
        )
    ranges[f"'{calc}'!A120:E120"] = profit_hdr
    ranges[f"'{calc}'!A121:E{120 + MAX_N}"] = profit

    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": k, "values": v} for k, v in ranges.items()],
    }
    api(
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchUpdate",
        h,
        json=body,
    )
    print(f"OK: {calc} B37:C47 + N=1..{MAX_N}")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")


if __name__ == "__main__":
    main()
