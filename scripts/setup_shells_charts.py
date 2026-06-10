#!/usr/bin/env python3
"""Добавляет в Google Таблицу графики и лист с предложением по потасовкам v2."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY = ROOT / "config" / "google" / "service-account.json"
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID", "1iKLuFbdj90D-tyYTmu09CqVqUty9YLksSwuhSEGskHo"
)

# --- Потасовки v2: пул 3500, места 1-4 + бонус за вклад, AFK сохранён ---
POOL_TOTAL = 3500
STATIC_SHARE = 0.70  # 2450 гильз — фикс по месту
BONUS_SHARE = 0.30  # 1050 гильз — личный вклад в группе
STATIC_BY_PLACE = {1: 980, 2: 735, 3: 490, 4: 245}
MIN_CLAN_PCT = 5  # % очков группы — иначе 0 (как сейчас)
MIN_PLAYER_CLAN_PCT = 2  # AFK: <2% вклада в клане — без бонуса, 50% статики
TOP_N = 30


def build_chart_data() -> dict[str, list[list]]:
    """Данные для графиков: сравнение текущей и предлагаемой модели."""

    # Сценарий из патча 01.10.2025 (4 клана, этап)
    scenarios = [
        ("Лидер ~51%", 1, 51.44, 100),
        ("2 место ~32%", 2, 31.50, 60),
        ("3 место ~16%", 3, 15.75, 30),
        ("<5% (аннулир.)", 4, 1.31, 0),
    ]

    compare_rows = [
        ["Сценарий", "Место", "Доля %", "Текущая (1500)", "Предлож. (3500)", "Δ %"],
    ]
    for name, place, pct, top_player_pct in scenarios:
        cur_clan = round(1500 * pct / 100) if pct >= MIN_CLAN_PCT else 0
        cur_top = round(1000 * pct / 100) if pct >= MIN_CLAN_PCT else 0
        if pct >= MIN_CLAN_PCT:
            static = STATIC_BY_PLACE[place]
            bonus_clan = round(POOL_TOTAL * BONUS_SHARE * pct / 100)
            prop_clan = static + bonus_clan
            prop_top = round(
                static * top_player_pct / 100
                + POOL_TOTAL * BONUS_SHARE * pct / 100 * top_player_pct / 100
            )
        else:
            prop_clan = 0
            prop_top = 0
        delta = round((prop_top - cur_top) / cur_top * 100) if cur_top else 0
        compare_rows.append([name, place, pct, cur_top, prop_top, delta])

    # Сравнение режимов за день (макс на игрока)
    modes = [
        ["Режим", "Мин/день", "Типично", "Макс/день"],
        ["Потасовки (текущ.)", 0, 1300, 3000],
        ["Потасовки v2 (предл.)", 0, 3000, 7000],
        ["Турнир межсезонье", 2400, 4800, 7200],
        ["Турнир рейтинг C", 2400, 4800, 7200],
        ["Турнир рейтинг S", 9000, 17000, 21000],
    ]

    # Турнир рейтинг за этап
    tour_rows = [
        ["Ранг", "Победа", "Поражение"],
        ["E", 1250, 250],
        ["D", 1750, 500],
        ["C", 2400, 800],
        ["B", 3300, 1200],
        ["A", 4700, 1800],
        ["S", 7000, 3000],
    ]

    # Распределение пула v2
    pool_rows = [
        ["Компонент", "Гильзы", "Доля %"],
        ["Статика 1 место", 980, round(980 / POOL_TOTAL * 100, 1)],
        ["Статика 2 место", 735, round(735 / POOL_TOTAL * 100, 1)],
        ["Статика 3 место", 490, round(490 / POOL_TOTAL * 100, 1)],
        ["Статика 4 место", 245, round(245 / POOL_TOTAL * 100, 1)],
        ["Итого статика", sum(STATIC_BY_PLACE.values()), round(STATIC_SHARE * 100)],
        ["Бонус за вклад (группа)", round(POOL_TOTAL * BONUS_SHARE), round(BONUS_SHARE * 100)],
        ["ИТОГО пул/этап", POOL_TOTAL, 100],
    ]

    # Симуляция топ-игрока за 3 этапа
    day_rows = [
        ["Модель", "Этап 1", "Этап 2", "Этап 3", "За день"],
        ["Текущая (лидер ~51%)", 521, 521, 521, 1563],
        ["v2 (1 место, топ вклад)", 1520, 1520, 1520, 4560],
        ["v2 (2 место, средний)", 850, 850, 850, 2550],
        ["v2 (4 место, активный)", 280, 280, 280, 840],
    ]

    proposal_rows = [
        ["ПОТАСОВКИ v2 — ПРЕДЛОЖЕНИЕ"],
        [],
        ["Параметр", "Значение", "Комментарий"],
        ["Общий пул гильз/этап/группа", POOL_TOTAL, "Было 1500 (+133%)"],
        ["Статика по местам", "980 / 735 / 490 / 245", "70% пула, не зависит от разрыва в очках"],
        ["Бонус за вклад", round(POOL_TOTAL * BONUS_SHARE), "30% пула, по личным очкам в группе"],
        ["Мин. вклад клана", f"{MIN_CLAN_PCT}%", "Как сейчас — иначе 0"],
        ["Топ получателей", TOP_N, "Как сейчас"],
        ["AFK порог", f"<{MIN_PLAYER_CLAN_PCT}% вклада в клане", "Нет бонуса; статика ×50%"],
        ["AFK полный", "0 очков / 0 захватов", "0 гильз"],
        [],
        ["Формула статики на игрока"],
        ["", "= статика_места × (личные_очки / очки_клана)"],
        ["Формула бонуса на игрока"],
        ["", f"= {round(POOL_TOTAL * BONUS_SHARE)} × (личные_очки / очки_группы)"],
        [],
        ["Преимущества"],
        ["1", "Предсказуемая награда за место 1–4 — мотивация не «фармить %», а бороться за позицию"],
        ["2", "Сильный игрок получает больше за счёт бонуса, слабый AFK — меньше"],
        ["3", "Пул 3500 выравнивает потасовки с турниром C (2400/этап) по ценности"],
        ["4", "Сохранена анти-AFK: пороги 5% клан / 2% игрок / топ-30"],
    ]

    return {
        "Графики_данные": compare_rows
        + [[], []]
        + modes
        + [[], []]
        + tour_rows
        + [[], []]
        + pool_rows
        + [[], []]
        + day_rows,
        "Потасовки_v2": proposal_rows,
    }


def get_sheets_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit("pip install google-auth google-api-python-client") from None

    key = os.environ.get("SERVICE_ACCOUNT_PATH", str(DEFAULT_KEY))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = service_account.Credentials.from_service_account_file(key, scopes=scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def ensure_sheet(sheets, spreadsheet_id: str, title: str) -> int:
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in meta.get("sheets", []):
        if sh["properties"]["title"] == title:
            return sh["properties"]["sheetId"]
    resp = (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )
        .execute()
    )
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def write_values(sheets, spreadsheet_id: str, sheet: str, rows: list[list]) -> None:
    end_col = chr(ord("A") + max(len(r) for r in rows) - 1)
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet}'!A1:{end_col}{len(rows)}",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


def add_charts(sheets, spreadsheet_id: str, data_sheet_id: int) -> None:
    """Графики на листе Графики_данные."""
    requests = [
        # 1. Сравнение текущая vs v2 по сценариям (столбцы)
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Потасовки: топ-игрок за этап (1500 vs 3500)",
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Сценарий"},
                                {"position": "LEFT_AXIS", "title": "Гильзы"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 0,
                                                    "endRowIndex": 5,
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
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 0,
                                                    "endRowIndex": 5,
                                                    "startColumnIndex": 3,
                                                    "endColumnIndex": 4,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                                {
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 0,
                                                    "endRowIndex": 5,
                                                    "startColumnIndex": 4,
                                                    "endColumnIndex": 5,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                            ],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": data_sheet_id, "rowIndex": 0, "columnIndex": 8},
                            "widthPixels": 600,
                            "heightPixels": 350,
                        }
                    },
                }
            }
        },
        # 2. Сравнение режимов за день
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Макс. гильзы/день по режимам",
                        "basicChart": {
                            "chartType": "BAR",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Гильзы"},
                                {"position": "LEFT_AXIS", "title": "Режим"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 7,
                                                    "endRowIndex": 13,
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
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 7,
                                                    "endRowIndex": 13,
                                                    "startColumnIndex": 3,
                                                    "endColumnIndex": 4,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "BOTTOM_AXIS",
                                }
                            ],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": data_sheet_id, "rowIndex": 18, "columnIndex": 8},
                            "widthPixels": 600,
                            "heightPixels": 350,
                        }
                    },
                }
            }
        },
        # 3. Турнир рейтинг
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Турнир (рейтинг): гильзы за этап",
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Ранг"},
                                {"position": "LEFT_AXIS", "title": "Гильзы"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 15,
                                                    "endRowIndex": 22,
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
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 15,
                                                    "endRowIndex": 22,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                                {
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 15,
                                                    "endRowIndex": 22,
                                                    "startColumnIndex": 2,
                                                    "endColumnIndex": 3,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                            ],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": data_sheet_id, "rowIndex": 0, "columnIndex": 8},
                            "widthPixels": 600,
                            "heightPixels": 350,
                        }
                    },
                }
            }
        },
        # 4. Структура пула v2 (круговая)
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Потасовки v2: структура пула 3500",
                        "pieChart": {
                            "legendPosition": "RIGHT_LEGEND",
                            "domain": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": data_sheet_id,
                                            "startRowIndex": 24,
                                            "endRowIndex": 28,
                                            "startColumnIndex": 0,
                                            "endColumnIndex": 1,
                                        }
                                    ]
                                }
                            },
                            "series": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": data_sheet_id,
                                            "startRowIndex": 24,
                                            "endRowIndex": 28,
                                            "startColumnIndex": 1,
                                            "endColumnIndex": 2,
                                        }
                                    ]
                                }
                            },
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": data_sheet_id, "rowIndex": 36, "columnIndex": 8},
                            "widthPixels": 500,
                            "heightPixels": 350,
                        }
                    },
                }
            }
        },
        # 5. За 3 этапа (линия)
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Потасовки: гильзы лидера за 3 этапа",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Этап"},
                                {"position": "LEFT_AXIS", "title": "Гильзы"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 33,
                                                    "endRowIndex": 34,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 4,
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
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 33,
                                                    "endRowIndex": 34,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 4,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                                {
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": data_sheet_id,
                                                    "startRowIndex": 34,
                                                    "endRowIndex": 35,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 4,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                },
                            ],
                            "headerCount": 0,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": data_sheet_id, "rowIndex": 36, "columnIndex": 0},
                            "widthPixels": 550,
                            "heightPixels": 300,
                        }
                    },
                }
            }
        },
    ]
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def main() -> None:
    sheets = get_sheets_service()
    data = build_chart_data()

    for sheet_name, rows in data.items():
        ensure_sheet(sheets, SPREADSHEET_ID, sheet_name)
        write_values(sheets, SPREADSHEET_ID, sheet_name, rows)
        print(f"Записан лист: {sheet_name}")

    data_sheet_id = ensure_sheet(sheets, SPREADSHEET_ID, "Графики_данные")
    try:
        add_charts(sheets, SPREADSHEET_ID, data_sheet_id)
        print("Графики добавлены на лист «Графики_данные»")
    except Exception as exc:
        print(f"Графики: {exc}", file=sys.stderr)

    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    print(f"Готово: {url}")


if __name__ == "__main__":
    main()
