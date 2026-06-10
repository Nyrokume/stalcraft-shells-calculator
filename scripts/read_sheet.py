import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1Sl8xecEC4VlyHCjuZv4ienrIerz2AL7esLyCu6DQkDU"
key = Path(__file__).resolve().parents[1] / "config" / "google" / "service-account.json"
creds = service_account.Credentials.from_service_account_file(
    str(key),
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
)
sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
meta = sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
print("sheets:", [s["properties"]["title"] for s in meta["sheets"]])
for s in meta["sheets"]:
    title = s["properties"]["title"]
    data = sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{title}'!A1:F50").execute()
    print("---", title, "---")
    for row in data.get("values", [])[:30]:
        print(row)
