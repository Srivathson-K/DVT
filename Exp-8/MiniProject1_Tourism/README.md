# Mini Project I — Tourism Analytics
### Data Visualization Techniques · Experiment 8

Start with **`docs/SETUP_GUIDE.pdf`**. It walks through installing SQL Server,
running the scripts, and opening both tools, in order.

---

## What's here

```
data/                              Source CSVs (7 files, 16,865 rows)
sql/
  01_create_database.sql           TourismDW, schemas, 8 tables
  02_load_data.sql                 All data as INSERT statements (2.4 MB, self-contained)
  03_clean_transform_model.sql     Profiling, cleaning, FKs, indexes, 4 analytical views
  04_verification_and_analysis.sql Verification counts + the 8 queries behind the insights
  05_export_extract_for_tableau.sql Exports the integrated view as the Tableau extract
powerbi/
  TourismAnalytics.pbip            Open this in Power BI Desktop, then Save As .pbix
  TourismAnalytics.SemanticModel/  Model: 51 DAX measures, 14 calculated columns
  TourismAnalytics.Report/         Report: 6 pages, 50 visuals
tableau/
  TourismAnalytics_Packaged.twbx   Use this on Tableau Public — submit this one
  TourismAnalytics_SQLServer.twb   Live SQL Server connection; Tableau Desktop only
  Data/TourismTripAnalysis.csv     The packaged extract (12,000 rows × 54 fields)
docs/
  Exp8_MiniProject1_Tourism.docx   The report, in your lab template
  Exp8_MiniProject1_Tourism.pdf
  SETUP_GUIDE.pdf                  Read this first
build_*.py / build_docx.js         The generators, if anything needs regenerating
```

## A note on Tableau Public

Tableau Public cannot connect to SQL Server, or any database — its connectors
are limited to Excel, text/CSV, spatial, statistical and a few web sources.
So the integration and cleaning happen in SQL Server (`dbo.vw_TripAnalysis`),
and script 05 exports that view as the extract the packaged workbook consumes.
Run script 05 and screenshot the row count: that is what makes the extract
demonstrably a database output rather than a loose file. If you later get
Tableau Desktop, `TourismAnalytics_SQLServer.twb` connects to the same view
live and needs no other change.

## The dataset

A tour operator's booking warehouse: 12,000 clean bookings over 2023–2026,
32 destinations, 2,400 travellers, ₹296.91 crore revenue. Star schema —
one fact table, six dimensions.

The raw extract in `stg.FactTrip_Raw` deliberately contains 60 duplicate
bookings, 25 negative durations and 8 casings of `BookingStatus` for 4 real
statuses. Script 03 profiles and fixes all of it, which is the data-preparation
evidence the rubric asks for.

## Rubric coverage

| Requirement | Where it is |
|---|---|
| SQL Server connectivity | Scripts 01–05; Power BI parameterised connection; Tableau extract exported from `dbo.vw_TripAnalysis` |
| Data cleaning and transformation | Script 03 (T-SQL) + Power Query steps on FactTrip |
| Data modelling and relationships | FKs in script 03; 9 relationships in Power BI, 3 inactive (two alternate date roles + the snowflake link) |
| Measures and calculated columns | 51 DAX measures, 14 calculated columns |
| DAX calculations | Time intelligence, RANKX, Pareto, USERELATIONSHIP, what-if |
| KPIs and cards | Page 1 card strip; gauge against target on page 5 |
| Slicers and filters | Slicers on pages 1 and 3; 4 filters on every Tableau worksheet |
| Drill-down and drill-through | Geography hierarchy on page 2; page 6 is the drill-through target |
| Advanced visualisations | Ribbon, waterfall, Pareto combo, treemap, scatter, gauge, funnel, map, heat matrix |
| Tableau calculated fields | 18, of which 6 are table calculations |
| Tableau parameters | 4, driving Top N, scenario pricing, target and measure swapping |
| Tableau dashboards and story | 3 dashboards; story built in Step 4 of the setup guide |
| Documentation | `docs/Exp8_MiniProject1_Tourism.docx` |

## Three things left to do by hand

All three are quick, and the setup guide has exact instructions:

1. **Power BI** — drag `DestinationName` into the Drill through well on page 6,
   and turn on conditional formatting for the two matrices.
2. **Tableau** — run script 05 and export the extract from SSMS, then apply the
   `Top N Filter` field to the Filters shelf, add two dashboard actions, and
   build the story from the three dashboards.
3. **Both** — take the screenshots and paste them into the labelled placeholders
   in the report.

These were left as manual steps on purpose: they are one or two clicks each in
the UI, and hand-writing the underlying XML for them risks a file that won't
open at all.
