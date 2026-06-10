#!/usr/bin/env python3
"""Загружает sever-profit-model.csv в Google Таблицу.

Режимы:
  по умолчанию — создать файл в папке Drive (нужна квота; у service account её нет);
  SPREADSHEET_ID=... — заполнить уже созданную вами таблицу (рекомендуется).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "sever-profit-model.csv"
DEFAULT_KEY = ROOT / "config" / "google" / "service-account.json"


def load_env() -> tuple[str, str | None]:
    key_path = os.environ.get("SERVICE_ACCOUNT_PATH", str(DEFAULT_KEY))
    folder_id = os.environ.get("DRIVE_FOLDER_ID", "").strip()
    if not Path(key_path).is_file():
        raise SystemExit(
            f"Нет ключа: {key_path}\n"
            "Положите service-account.json.\n"
            "Инструкция: GOOGLE_SHEETS_SETUP.md"
        )
    if not folder_id or folder_id == "PASTE_YOUR_DRIVE_FOLDER_ID_HERE":
        folder_id = None
    return key_path, folder_id


def ensure_folder(drive, folder_id: str | None) -> str:
    if folder_id:
        return folder_id
    name = "Concept-document"
    found = (
        drive.files()
        .list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false",
            fields="files(id,name)",
            pageSize=1,
        )
        .execute()
        .get("files", [])
    )
    if found:
        return found[0]["id"]
    created = (
        drive.files()
        .create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        )
        .execute()
    )
    return created["id"]


def read_csv_rows() -> list[list[str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def folder_owner_email(drive, folder_id: str) -> str:
    meta = (
        drive.files()
        .get(fileId=folder_id, fields="owners(emailAddress)", supportsAllDrives=True)
        .execute()
    )
    owners = meta.get("owners") or []
    if not owners:
        raise SystemExit("Не удалось определить владельца папки Drive.")
    return owners[0]["emailAddress"]


def upload_via_drive(drive, folder_id: str, title: str) -> tuple[str, str]:
    """Загрузка CSV через Drive API (конвертация в Google Sheet)."""
    from googleapiclient.http import MediaFileUpload

    owner = folder_owner_email(drive, folder_id)
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id],
    }
    media = MediaFileUpload(
        str(CSV_PATH),
        mimetype="text/csv",
        resumable=True,
    )
    created = (
        drive.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    file_id = created["id"]
    drive.permissions().create(
        fileId=file_id,
        transferOwnership=True,
        body={"type": "user", "role": "owner", "emailAddress": owner},
        supportsAllDrives=True,
    ).execute()
    return file_id, created.get("webViewLink", "")


def format_sheet(sheets, spreadsheet_id: str, sheet_id: int) -> None:
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"bold": True},
                                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            }
                        },
                        "fields": "userEnteredFormat(textFormat,backgroundColor)",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 6,
                        }
                    }
                },
            ]
        },
    ).execute()


def fill_existing_sheet(sheets, spreadsheet_id: str, rows: list[list[str]]) -> None:
    end_col = chr(ord("A") + max(len(r) for r in rows) - 1)
    end_row = len(rows)
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Sheet1!A1:{end_col}{end_row}",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = meta["sheets"][0]["properties"]["sheetId"]
    format_sheet(sheets, spreadsheet_id, sheet_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spreadsheet-id",
        default=os.environ.get("SPREADSHEET_ID", "").strip(),
        help="ID существующей таблицы (создайте вручную в папке Concept-document)",
    )
    args = parser.parse_args()
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit(
            "Установите зависимости:\n"
            "  cd mcp-google-sheets && uv sync"
        ) from None

    key_path, folder_id_env = load_env()
    rows = read_csv_rows()
    if not rows:
        raise SystemExit(f"Пустой файл: {CSV_PATH}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)

    if args.spreadsheet_id:
        fill_existing_sheet(sheets, args.spreadsheet_id, rows)
        url = f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit"
        print(f"Готово (заполнена существующая таблица): {url}")
        return

    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    folder_id = ensure_folder(drive, folder_id_env)
    title = "Дикий север — модель профита"

    try:
        spreadsheet_id, web_link = upload_via_drive(drive, folder_id, title)
    except Exception as exc:
        if "storageQuotaExceeded" in str(exc):
            raise SystemExit(
                "Service account не может создавать файлы (квота 0).\n"
                "1) В папке Concept-document создайте пустую Google Таблицу.\n"
                "2) Поделитесь ею с concept-document-sheet@excel-499010.iam.gserviceaccount.com (Редактор).\n"
                "3) Запустите:\n"
                "   $env:SPREADSHEET_ID='ID_из_URL'; uv run python ..\\scripts\\upload_sever_model.py\n"
                "Или: Файл → Импорт → sever-profit-model.csv (UTF-8)."
            ) from exc
        raise

    url = web_link or f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    try:
        meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        format_sheet(sheets, spreadsheet_id, meta["sheets"][0]["properties"]["sheetId"])
    except OSError:
        print("Форматирование пропущено (Sheets API недоступен), данные загружены.")

    print(f"Готово: {url}")
    print(f"DRIVE_FOLDER_ID={folder_id}")


if __name__ == "__main__":
    main()
