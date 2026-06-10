#!/usr/bin/env python3
"""Добавляет лист «Калькулятор» и графики в Google Таблицу."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY = ROOT / "config" / "google" / "service-account.json"
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID", "1Sl8xecEC4VlyHCjuZv4ienrIerz2AL7esLyCu6DQkDU"
)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_NAME = "Калькулятор"


def auth_headers(key_path: Path) -> dict[str, str]:
    creds = service_account.Credentials.from_service_account_file(
        str(key_path), scopes=SCOPES
    )
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


def api(method: str, url: str, headers: dict, body: dict | None = None) -> dict:
    resp = requests.request(method, url, headers=headers, json=body, timeout=120)
    if not resp.ok:
        raise SystemExit(f"API {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.text else {}


def get_or_create_sheet(headers: dict) -> int:
    meta = api(
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}",
        headers,
    )
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == SHEET_NAME:
            return s["properties"]["sheetId"]

    result = api(
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
        headers,
        {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": SHEET_NAME,
                            "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1},
                        }
                    }
                }
            ]
        },
    )
    return result["replies"][0]["addSheet"]["properties"]["sheetId"]


def calculator_values() -> list[list]:
    return [
        ["КАЛЬКУЛЯТОР ХОДОК", "", "", "", ""],
        ["Параметр", "Значение", "Ед.", "", ""],
        ["Закуп за ходку", 17000, "₽", "", ""],
        ["Смерть при миграции", 0.05, "доля", "", ""],
        ["Смерть на севере", 0.35, "доля", "", ""],
        ["Лут при успешном выносе", 73927.4, "₽", "", ""],
        ["Количество ходок (N)", 5, "", "", ""],
        ["", "", "", "", ""],
        ["РЕЗУЛЬТАТ", "Значение", "", "", ""],
        ["P добраться на север", "=(1-B4)", "", "", ""],
        ["P успех (вынес)", "=(1-B4)*(1-B5)", "", "", ""],
        ["EV за 1 ходку", "=B11*B6-B3", "₽", "", ""],
        ["Затраты за N ходок", "=B7*B3", "₽", "", ""],
        ["Ожид. валовый лут", "=B7*B11*B6", "₽", "", ""],
        ["Ожид. чистый профит", "=B7*(B11*B6-B3)", "₽", "", ""],
        ["P (хотя бы 1 успех)", "=1-(1-B11)^B7", "", "", ""],
        ["Ожид. число выносов", "=B7*B11", "", "", ""],
        ["", "", "", "", ""],
        ["N ходок", "Чистый профит (ожид.)", "Затраты", "Валовый лут", ""],
    ] + [
        [n, f"=A{19+n}*(($B$11)*$B$6-$B$3)", f"=A{19+n}*$B$3", f"=A{19+n}*$B$11*$B$6", ""]
        for n in range(1, 16)
    ] + [
        ["", "", "", "", ""],
        ["k успехов", "Вероятность", "Чистый профит", "", ""],
    ] + [
        [
            k,
            f"=COMBIN($B$7,A{37+k})*POWER($B$11,A{37+k})*POWER(1-$B$11,$B$7-A{37+k})",
            f"=A{37+k}*$B$6-$B$7*$B$3",
            "",
            "",
        ]
        for k in range(0, 11)
    ]


def write_values(headers: dict) -> None:
    values = calculator_values()
    end_row = len(values)
    api(
        "PUT",
        (
            f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
            f"/values/'{SHEET_NAME}'!A1:E{end_row}?valueInputOption=USER_ENTERED"
        ),
        headers,
        {"values": values},
    )


def format_and_charts(headers: dict, sheet_id: int) -> None:
    requests_body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True, "fontSize": 14},
                            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 8},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.93, "green": 0.95, "blue": 0.98}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 8, "endRowIndex": 17},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.96, "blue": 0.9}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": 7,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 1, "green": 1, "blue": 0.85},
                            "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,numberFormat)",
                }
            },
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 5,
                    }
                }
            },
            {
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": "Ожидаемый профит vs число ходок",
                            "basicChart": {
                                "chartType": "LINE",
                                "legendPosition": "BOTTOM_LEGEND",
                                "axis": [
                                    {"position": "BOTTOM_AXIS", "title": "N ходок"},
                                    {"position": "LEFT_AXIS", "title": "₽"},
                                ],
                                "domains": [
                                    {
                                        "domain": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 18,
                                                        "endRowIndex": 34,
                                                        "startColumnIndex": 0,
                                                        "endColumnIndex": 1,
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "series": [
                                    {
                                        "series": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 18,
                                                        "endRowIndex": 34,
                                                        "startColumnIndex": 1,
                                                        "endColumnIndex": 2,
                                                    }
                                                ]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS",
                                        "color": {"red": 0.2, "green": 0.6, "blue": 0.2},
                                    },
                                    {
                                        "series": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 18,
                                                        "endRowIndex": 34,
                                                        "startColumnIndex": 2,
                                                        "endColumnIndex": 3,
                                                    }
                                                ]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS",
                                        "color": {"red": 0.8, "green": 0.2, "blue": 0.2},
                                    },
                                ],
                                "headerCount": 1,
                            },
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 5},
                                "widthPixels": 620,
                                "heightPixels": 360,
                            }
                        },
                    }
                }
            },
            {
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": "Распределение успехов (для выбранного N)",
                            "basicChart": {
                                "chartType": "COLUMN",
                                "legendPosition": "NO_LEGEND",
                                "axis": [
                                    {"position": "BOTTOM_AXIS", "title": "k успехов"},
                                    {"position": "LEFT_AXIS", "title": "Вероятность"},
                                ],
                                "domains": [
                                    {
                                        "domain": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 35,
                                                        "endRowIndex": 47,
                                                        "startColumnIndex": 0,
                                                        "endColumnIndex": 1,
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "series": [
                                    {
                                        "series": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 35,
                                                        "endRowIndex": 47,
                                                        "startColumnIndex": 1,
                                                        "endColumnIndex": 2,
                                                    }
                                                ]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS",
                                        "color": {"red": 0.25, "green": 0.45, "blue": 0.85},
                                    }
                                ],
                                "headerCount": 1,
                            },
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {"sheetId": sheet_id, "rowIndex": 20, "columnIndex": 5},
                                "widthPixels": 620,
                                "heightPixels": 360,
                            }
                        },
                    }
                }
            },
        ]
    }
    api(
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
        headers,
        requests_body,
    )


def main() -> None:
    key = Path(os.environ.get("SERVICE_ACCOUNT_PATH", str(DEFAULT_KEY)))
    if not key.is_file():
        raise SystemExit(f"Нет ключа: {key}")

    headers = auth_headers(key)
    sheet_id = get_or_create_sheet(headers)
    write_values(headers)
    format_and_charts(headers, sheet_id)
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={sheet_id}"
    print(f"Готово: {url}")


if __name__ == "__main__":
    main()
