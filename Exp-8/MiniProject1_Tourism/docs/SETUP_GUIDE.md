# Mini Project I — Tourism Analytics
## Setup guide: SQL Server → Power BI → Tableau

Work through this once, in order. Budget about 45 minutes, most of it the SQL
Server download.

---

## Step 1 — Install SQL Server (about 20 minutes)

You need two free pieces of software.

**1a. SQL Server Express** (2025 at time of writing)

Download from `https://www.microsoft.com/en-in/sql-server/sql-server-downloads`
→ scroll to **Express** → Download now.

Run the installer and choose **Basic**. Accept the defaults. When it finishes,
the installer shows a **Connection String** box — the instance name is in there.
It will almost certainly be:

```
localhost\SQLEXPRESS
```

Write it down. Everything downstream uses it.

**1b. SQL Server Management Studio (SSMS)**

The Express installer has an **Install SSMS** button at the end — use it, or get
it from `https://aka.ms/ssmsfullsetup`. Install with defaults.

**Check it works:** open SSMS. In the connect dialog:

| Field | Value |
|---|---|
| Server type | Database Engine |
| Server name | `localhost\SQLEXPRESS` |
| Authentication | Windows Authentication |
| Encrypt | Mandatory (the default) |
| Trust server certificate | **tick this** |

You must tick **Trust server certificate**. A local Express instance uses a
self-signed certificate, and with Encrypt set to Mandatory the connection is
refused without it. Click **Connect**. If Object Explorer appears on the left, you are done here.

> If the server name doesn't work, open **SQL Server Configuration Manager** →
> SQL Server Services, and read the instance name shown next to "SQL Server".

---

## Step 2 — Build the database (about 5 minutes)

In SSMS, open and execute the five scripts from the `sql` folder **in order**.
Open each with File → Open → File, then press **F5**.

| # | Script | What it does | Time |
|---|---|---|---|
| 1 | `01_create_database.sql` | Creates `TourismDW`, 6 dimension tables, a staging table and the fact table | ~5 s |
| 2 | `02_load_data.sql` | Loads all 16,865 rows. No CSV files needed — the data is inside the script | 30–60 s |
| 3 | `03_clean_transform_model.sql` | Profiles the raw data, cleans it, applies the foreign keys and indexes, creates 4 analytical views | ~10 s |
| 4 | `04_verification_and_analysis.sql` | Verification counts and the analytical queries behind the dashboard insights | ~5 s |
| 5 | `05_export_extract_for_tableau.sql` | Exports the integrated view as the Tableau extract (see Step 4) | ~5 s |

**Script 2 is 2.4 MB.** If SSMS feels sluggish opening it, run it from the
command prompt instead — this is faster and uses no memory in SSMS:

```
sqlcmd -S localhost\SQLEXPRESS -E -d master -i "C:\full\path\to\sql\02_load_data.sql"
```

### Screenshots to take here

These go straight into the report.

1. **Script 3, Step 1 output** — the raw data quality profile. Shows 60 duplicate
   rows, 25 negative durations, and `NO SHOW` sitting in capitals beside the
   title-case statuses. (The count of distinct statuses reads 4, not 8: SQL
   Server's default collation is case-insensitive, so it groups `COMPLETED`
   with `Completed`. The casing defect is real and is still standardised during
   cleaning.)
2. **Script 3, Step 2 output** — raw 12,060 → clean 12,000, 60 rows removed.
3. **Script 4, Section A** — the row counts per table, and the integrity checks
   all returning 0.
4. **Object Explorer** expanded to show `TourismDW` → Tables and Views.

### What you should see

| Table | Rows |
|---|---|
| DimDate | 2,191 |
| DimDestination | 32 |
| DimTraveller | 2,400 |
| DimAccommodation | 155 |
| DimTransport | 18 |
| DimBookingChannel | 9 |
| stg.FactTrip_Raw | 12,060 |
| **dbo.FactTrip (clean)** | **12,000** |

---

## Step 3 — Open the Power BI project (about 5 minutes)

1. Open **Power BI Desktop**.
2. File → Open → Browse → select `powerbi\TourismAnalytics.pbip`.
3. Power BI will ask for credentials for `localhost\SQLEXPRESS`. Choose
   **Windows** → *Use my current credentials* → **Connect**.
4. You will then get an **Encryption Support** prompt saying it could not
   connect using an encrypted connection. Click **OK** to continue unencrypted
   — same self-signed-certificate situation as SSMS, and fine for a local
   instance.
5. If Power BI offers to *upgrade the report format to PBIR* or *upgrade the
   semantic model to TMDL*, choose **Don't upgrade** both times. Those
   conversions are one-way and the project does not need them.
6. It loads 6 dimension tables plus the fact table. Wait for the refresh to
   finish — the fact table is 12,000 rows and takes a few seconds.

**If your instance is not `localhost\SQLEXPRESS`:** Home → Transform data →
Manage Parameters → set **ServerName** to your instance → Close & Apply.
That's the only change needed; every query uses the parameter.

7. **Save As → `TourismAnalytics.pbix`**. This is the file you submit.

### What's in it

| | |
|---|---|
| Pages | 6 |
| Visuals | 50 |
| DAX measures | 51, in 9 display folders |
| Calculated columns | 14 |
| Relationships | 9 (3 inactive: two alternate date roles used by `USERELATIONSHIP`, plus the snowflake link) |
| Hierarchies | 4 |
| Power Query steps | Filtering, type changes, 3 added custom columns on `FactTrip` |

### Two things to finish by hand

**Drill-through (30 seconds).** Go to page **6. Destination Detail**. In the
Visualizations pane, find the **Drill through** well and drag
`DimDestination → DestinationName` into it. Now right-clicking any destination
on page 2 offers *Drill through → 6. Destination Detail*.

**Conditional formatting (1 minute).** On page 2, select the **Destination
scorecard** matrix → Format → Cell elements → turn on **Background colour** for
`Avg Satisfaction`, and **Data bars** for `Total Revenue`. On page 3, do the same
for the heat map matrix. This is what the rubric means by "appropriate
formatting".

### Screenshots to take

One per page, full window, with the filter pane visible. Plus one of the
**Model view** showing the star schema, and one of **Power Query Editor** showing
the applied steps on `FactTrip`.

---

## Step 4 — Open the Tableau workbook (about 10 minutes)

> **Read this first if you are on Tableau Public.** Tableau Public cannot
> connect to SQL Server, or to any database. Its connectors are limited to
> Excel, text/CSV, spatial, statistical and a few web sources — SQL Server,
> Oracle, MySQL and PostgreSQL are Tableau Desktop only. So on Public you use
> the **packaged** workbook, which consumes an extract exported from the
> database rather than connecting to it live.

You have two files.

| File | Edition | How it gets the data |
|---|---|---|
| `TourismAnalytics_Packaged.twbx` | **Tableau Public** or Desktop | Extract exported from `dbo.vw_TripAnalysis` |
| `TourismAnalytics_SQLServer.twb` | Tableau Desktop only | Live Custom SQL on `dbo.vw_TripAnalysis` |

Both contain the same 19 worksheets, 3 dashboards, 18 calculated fields and
4 parameters.

### 4a. Make the extract genuinely a SQL Server output

Do this so the extract is demonstrably the database's output rather than a file
that merely sits beside it — it is what keeps the "data source" part of the
rubric defensible on Public.

1. In SSMS, open and run `sql\05_export_extract_for_tableau.sql`.
2. Tools → Options → Query Results → SQL Server → Results to Grid → tick
   **Include column headers when copying or saving the results**. Reopen the
   query window for this to take effect.
3. Run the query, right-click the results grid → **Save Results As…** →
   `TourismTripAnalysis.csv`.
4. You should get **12,000 rows × 54 columns**, matching the packaged extract
   exactly. Screenshot the row count — that is Fig. 8.13 in the report.

### 4b. Open the workbook

1. Open **Tableau Public** → File → Open →
   `TourismAnalytics_Packaged.twbx`.
2. Screenshot the **Data Source** tab showing the 54 fields.

> On Tableau Desktop instead, open `TourismAnalytics_SQLServer.twb`, enter
> server `localhost\SQLEXPRESS`, database `TourismDW`, **Windows
> Authentication** → Sign In, and screenshot the Data Source tab with the
> Custom SQL Query box visible.

> **Saving on Tableau Public:** older versions could only save to the public
> web. Check **File → Save As** on yours — if a local `.twbx` option is offered,
> use it. If not, save to Tableau Public, set the visualisation to **hidden**
> in your profile, and download the `.twbx` back from there.

### What's in it

| | |
|---|---|
| Worksheets | 19 |
| Dashboards | 3 |
| Calculated fields | 18, of which 6 are table calculations |
| Parameters | 4 |
| Filters | 4 on every worksheet, exposed as controls on the dashboards |

Table calculations used: `RANK`, `WINDOW_AVG`, `RUNNING_SUM` / `TOTAL`, `LOOKUP`.

### Three things to finish by hand

These are quick and they are each worth marks, so don't skip them.

**1. Apply the Top N filter (10 seconds).**
Open the **Top N Destinations** worksheet. From the Data pane, drag
**Top N Filter** onto the Filters shelf → tick **True** → OK. The chart now
respects the *Top N Destinations* parameter control on dashboard D1.

**2. Add two dashboard actions (2 minutes).**
On **D1 Executive Overview**: Dashboard menu → Actions → Add Action → **Highlight**.

| Field | Value |
|---|---|
| Name | Highlight destination |
| Source sheets | D1, with *Top N Destinations* ticked |
| Target sheets | D1, all |
| Run action on | Hover |
| Selected fields | DestinationName |

On **D2 Destination & Seasonality**: Actions → Add Action → **Filter**.

| Field | Value |
|---|---|
| Name | Filter detail by destination |
| Source sheets | D2, *Destination Map* |
| Target sheets | D3 Customer & Channel |
| Run action on | Select |
| Clearing the selection | Show all values |

**3. Build the story (3 minutes).**
Story menu → New Story. Drag dashboard **D1** onto the story point, then click
**Blank** to add the next point and drag **D2**, and so on. Type these captions:

| Point | Dashboard | Caption |
|---|---|---|
| 1 | D1 Executive Overview | Revenue grew 43% from 2023 to 2026, but 91% of it is international travel |
| 2 | D2 Destination & Seasonality | Demand swings 2.2× between the June trough and the December peak |
| 3 | D3 Customer & Channel | OTAs take 14–16% commission; direct channels keep 98% of revenue |
| 4 | D1 Executive Overview | Loyalty discounts cost margin without buying extra trips per traveller |

Rename the story to `Tourism Analytics Story`.

Then save the workbook. On Tableau Public use File → Save As and take the local
`.twbx` option if it is offered; otherwise save to Tableau Public with the
visualisation hidden and download the `.twbx` back.

### Screenshots to take

Data Source tab, each of the 3 dashboards, the story, one worksheet showing the
Calculated Field dialog open, and one showing a parameter control in use.

---

## Step 5 — Finish the report

Open `Exp8_MiniProject1_Tourism.docx`. Every screenshot has a labelled
placeholder box telling you exactly what belongs there. Replace the box with
your screenshot, keep the caption, and export to PDF.

---

## If something goes wrong

**"Cannot connect to localhost\SQLEXPRESS".** Open SQL Server Configuration
Manager → SQL Server Services → make sure *SQL Server (SQLEXPRESS)* is Running.
If it isn't, right-click → Start.

**Power BI: "We couldn't authenticate with the credentials provided".**
File → Options and settings → Data source settings → clear the saved permission
for the server, then refresh and pick Windows authentication again.

**Power BI: the report opens but visuals show errors.** Check the refresh
finished. If a single visual complains about a field, it is almost always
because the refresh was cancelled partway — Home → Refresh and let it complete.

**Tableau: "Unable to connect to the server".** Same check as above, and make
sure you typed the instance as `localhost\SQLEXPRESS` with a backslash.

**Tableau: a worksheet is blank.** Check the four filter cards on the right —
if one has nothing ticked, right-click it → *Select All*.
