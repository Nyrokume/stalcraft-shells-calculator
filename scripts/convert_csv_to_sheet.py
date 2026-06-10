from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path

key = Path(__file__).resolve().parents[1] / "config" / "google" / "service-account.json"
folder = "1JIBv1JPDQLCmZC-SOMbd5DNI_QssGOgs"
csv_id = "17Ur3zfuKzkCu2ABy29vCmP_kxskVU1DG"
title = "Дикий север — модель профита"

creds = service_account.Credentials.from_service_account_file(
    str(key), scopes=["https://www.googleapis.com/auth/drive"]
)
drive = build("drive", "v3", credentials=creds, cache_discovery=False)

copied = (
    drive.files()
    .copy(
        fileId=csv_id,
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder],
        },
        supportsAllDrives=True,
        fields="id, webViewLink",
    )
    .execute()
)

sheet_id = copied["id"]
url = copied.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
print(url)
print(f"SPREADSHEET_ID={sheet_id}")
