from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path

key = Path(__file__).resolve().parents[1] / "config" / "google" / "service-account.json"
folder = "1JIBv1JPDQLCmZC-SOMbd5DNI_QssGOgs"
creds = service_account.Credentials.from_service_account_file(
    str(key), scopes=["https://www.googleapis.com/auth/drive"]
)
drive = build("drive", "v3", credentials=creds, cache_discovery=False)
files = (
    drive.files()
    .list(
        q=f"'{folder}' in parents and trashed=false",
        fields="files(id,name,mimeType)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    )
    .execute()
    .get("files", [])
)
print("files in folder:", len(files))
for f in files:
    print(" -", f["name"], f["id"])
folder_meta = (
    drive.files()
    .get(fileId=folder, fields="owners(emailAddress),name", supportsAllDrives=True)
    .execute()
)
print("folder:", folder_meta.get("name"))
print("owner:", folder_meta.get("owners"))
about = drive.about().get(fields="storageQuota").execute()
print("service-account quota:", about.get("storageQuota"))
