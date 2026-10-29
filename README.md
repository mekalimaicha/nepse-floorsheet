# NEPSE Floorsheet Scraper

Saves one CSV per trading day in `data/`, for example `data/2026-10-30_Floorsheet.csv`.

Columns (16):
`contractId, stockSymbol, buyerMemberId, sellerMemberId, contractQuantity, contractRate,
contractAmount, businessDate, tradeBookId, stockId, buyerBrokerName, sellerBrokerName,
tradeTime, securityName, tradeDate, tradeClock`

`tradeDate` (2026-10-28) and `tradeClock` (14:59:59.999526) are the date and time split out of `tradeTime`.

## What runs automatically

| Job | When (Nepal time) | Source | Trade time? |
|---|---|---|---|
| Daily Floorsheet | 3:30 PM, Sunday to Friday | nepalstock.com | Yes |
| Historical Backfill | nightly, 7:05 PM and 12:45 AM, stops by ~6 AM | merolagani.com | No (blank) |
| Test Historical Access | only when you click it | nepalstock.com | tells us if past dates work |

Saturdays and days with no data are skipped (no blank files). On holidays the daily job saves nothing.

## Setup from zero (first time)

1. Create a free account at https://github.com and sign in.
2. Click **+** (top right) > **New repository**. Name: `nepse-floorsheet`. Choose **Public**.
   Click **Create repository**.
3. Click **uploading an existing file**. Unzip this project on your computer, then drag in
   everything inside the folder: `scraper`, `data`, `.github`, `requirements.txt`, `README.md`,
   `.gitignore`. The hidden `.github` folder (with `workflows` inside) must be included.
   If your computer hides it: Windows File Explorer > View > Show > Hidden items.
   Click **Commit changes**.
4. Allow saving files: **Settings > Actions > General > Workflow permissions** >
   **Read and write permissions** > **Save**.
5. **Test 1, today's data:** **Actions** tab > **Daily Floorsheet** > **Run workflow** >
   leave the date empty > **Run workflow**. After a few minutes `data/2026-10-30_Floorsheet.csv`
   (the latest trading day) should appear. (If the market is closed, the latest trading day is saved.)
6. **Test 2, history:** **Actions** > **Test Historical Access** > **Run workflow** with a past
   date such as `2026-10-27`. Open the finished run and copy the log text. Send it to Claude.
7. **Test 3, backfill:** **Actions** > **Historical Backfill** > **Run workflow**.
   After it finishes, `data/` should contain files starting `2014-05-05`.

If a run shows a red cross, click it, open the failed step, copy the red error text and send it to Claude.

## If you already uploaded version 1

Delete the old `scraper`, `.github` and `requirements.txt` from the repository, then upload the new ones
(**Add file > Upload files**). Keep your existing `data` folder if it has files. Then do steps 4 to 7.

## Things to know

- GitHub scheduled jobs can start 5 to 30 minutes late. That is normal.
- GitHub pauses scheduled jobs after 60 days with no repository activity. The bot's own
  commits normally count; if jobs stop, press **Enable workflow** in the Actions tab.
- Use a **public** repository. A private one has only 2,000 free minutes per month.
- Historical backfill covers about 2,900 trading days and will take several weeks of nights.
- Historical files from Merolagani have **blank** `tradeTime`, `tradeClock` and `tradeBookId`.
  Broker names, company names and stockId come from `data/lookups/` (built from the 28 Oct 2026 file).
  Brokers or stocks that stopped trading before that date may be blank until found by the scraper.
- File name format is set in `scraper/common.py` (`FILENAME_FORMAT`).
- Please check each site's terms of use. The scraper pauses between pages to be polite.
