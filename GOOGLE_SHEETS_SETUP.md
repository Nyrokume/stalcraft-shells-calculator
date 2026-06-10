# Google Таблицы + MCP для проекта Concept-document

Репозиторий [mcp-google-sheets](https://github.com/xing5/mcp-google-sheets) клонирован в `mcp-google-sheets/`.  
Cursor подключается через `.cursor/mcp.json`.

## 1. Google Cloud (один раз)

1. Откройте [Google Cloud Console](https://console.cloud.google.com/).
2. Создайте проект (или выберите существующий).
3. **APIs & Services → Library** — включите:
   - Google Sheets API
   - Google Drive API
4. **IAM & Admin → Service Accounts → Create**:
   - Имя: `concept-document-sheets`
   - Роль: **Editor** (или минимум Drive + Sheets)
5. **Keys → Add key → JSON** — скачайте файл.
6. Сохраните как:

   ```
   config/google/service-account.json
   ```

## 2. Папка в Google Drive (настроено)

- Папка: [Concept-document](https://drive.google.com/drive/folders/1JIBv1JPDQLCmZC-SOMbd5DNI_QssGOgs)
- `DRIVE_FOLDER_ID`: `1JIBv1JPDQLCmZC-SOMbd5DNI_QssGOgs`
- Service account (должен быть **Редактор** в папке):
  `concept-document-sheet@excel-499010.iam.gserviceaccount.com`

Проверка доступа API: папка видна, `shared: true` ✓

### Service account не создаёт файлы (квота 0)

У `concept-document-sheet@...` нет своего хранилища. Файл должен создать **вы** (`dementiyrezak@gmail.com`).

**Вариант A — импорт CSV (самый быстрый):**

1. Откройте [Concept-document](https://drive.google.com/drive/folders/1JIBv1JPDQLCmZC-SOMbd5DNI_QssGOgs)
2. **Создать → Google Таблицы**
3. **Файл → Импорт → Загрузка** → `sever-profit-model.csv` → **UTF-8**

**Вариант B — скрипт заполняет вашу таблицу:**

1. Создайте пустую таблицу в папке
2. **Поделиться** → `concept-document-sheet@excel-499010.iam.gserviceaccount.com` → **Редактор**
3. Скопируйте ID из URL: `https://docs.google.com/spreadsheets/d/ЭТОТ_ID/edit`
4. ```powershell
   cd I:\Concept-document\mcp-google-sheets
   $env:SPREADSHEET_ID = "ЭТОТ_ID"
   uv run python ..\scripts\upload_sever_model.py
   ```

## 3. Установка uv (если ещё нет)

```powershell
pip install uv
```

Проверка MCP-сервера:

```powershell
cd I:\Concept-document\mcp-google-sheets
$env:SERVICE_ACCOUNT_PATH = "I:\Concept-document\config\google\service-account.json"
$env:DRIVE_FOLDER_ID = "ваш_folder_id"
uv run mcp-google-sheets
```

Должен стартовать без ошибок (Ctrl+C для выхода).

## 4. Калькулятор и графики в Google Таблице

Таблица: [sever-profit-model](https://docs.google.com/spreadsheets/d/1Sl8xecEC4VlyHCjuZv4ienrIerz2AL7esLyCu6DQkDU/edit)

**Починка #ERROR! в B37:C47:** Apps Script → Run → **`syncAndFixAll`** (читает **Лист1**, пишет числа в B37:C47, таблицы N=1..109).

**Вариант A — Apps Script (рекомендуется, 1 мин):**

1. Откройте таблицу → **Расширения → Apps Script**
2. Вставьте код из `scripts/CreateCalculator.gs`
3. **Выполнить** → `createCalculator` → разрешить доступ

Создастся лист **Калькулятор** с полями ввода, формулами и двумя графиками.

**Вариант B — локально:**

Откройте `calculator/index.html` в браузере — интерактивный калькулятор с графиками.

**Вариант C — скрипт Python** (если Sheets API доступен):

```powershell
cd I:\Concept-document\mcp-google-sheets
uv run python ..\scripts\setup_calculator.py
```

## 5. Перезапуск Cursor

**Settings → MCP** — сервер `google-sheets` должен быть зелёным.

После этого в чате можно писать: «создай таблицу с моделью севера», «обнови ячейку B3» и т.д.

## 6. Загрузка CSV вручную (без MCP в чате)

```powershell
cd I:\Concept-document\mcp-google-sheets
uv sync
cd ..
$env:SERVICE_ACCOUNT_PATH = "I:\Concept-document\config\google\service-account.json"
$env:DRIVE_FOLDER_ID = "ваш_folder_id"
uv run --directory mcp-google-sheets python ..\scripts\upload_sever_model.py
```

Скрипт создаст таблицу **«Дикий север — модель профита»** с данными из `sever-profit-model.csv`.

## Безопасность

- `service-account.json` в `.gitignore` — не коммитьте ключ.
- Доступ только к расшаренной папке Drive.
