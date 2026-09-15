const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, HeadingLevel,
  LevelFormat, PageBreak, convertInchesToTwip,
} = require('docx');
const fs = require('fs');

const FONT = 'Times New Roman';
const SZ = 24;        // 12pt
const SZS = 20;       // 10pt for tables
const PAGE_W = 9360;  // usable width in DXA (A4 minus 1" margins)

// --------------------------------------------------------------------------
const t = (text, o = {}) => new TextRun({
  text, font: FONT, size: o.size || SZ, bold: !!o.bold,
  italics: !!o.italics, underline: o.underline ? {} : undefined,
  color: o.color,
});

const p = (text, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.LEFT,
  spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 300 },
  indent: o.indent,
  children: Array.isArray(text) ? text : [t(text, o)],
});

const blank = (after = 120) => new Paragraph({ spacing: { after }, children: [t('')] });

// bold + underlined section heading, as the lab template requires
const section = (title) => new Paragraph({
  spacing: { before: 280, after: 160 },
  children: [t(title, { bold: true, underline: true })],
});

const stepLine = (n, caption) => new Paragraph({
  spacing: { before: 240, after: 120 },
  children: [t(`Step ${n}: ${caption}`, { bold: true })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: 'bullets', level: 0 },
  spacing: { after: 80, line: 300 },
  children: [t(text)],
});

const numbered = (text) => new Paragraph({
  numbering: { reference: 'algo', level: 0 },
  spacing: { after: 80, line: 300 },
  children: [t(text)],
});

const code = (text) => new Paragraph({
  spacing: { before: 60, after: 60, line: 260 },
  indent: { left: convertInchesToTwip(0.3) },
  shading: { type: ShadingType.CLEAR, fill: 'F2F4F6' },
  children: [new TextRun({ text, font: 'Consolas', size: 19 })],
});

// --------------------------------------------------------------------------
// table helper
// --------------------------------------------------------------------------
function makeTable(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scaled = widths.map(w => Math.round(w / total * PAGE_W));
  // fix rounding drift
  scaled[scaled.length - 1] += PAGE_W - scaled.reduce((a, b) => a + b, 0);

  const cell = (text, i, opts = {}) => new TableCell({
    width: { size: scaled[i], type: WidthType.DXA },
    shading: opts.head ? { type: ShadingType.CLEAR, fill: '1B2A41' } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { after: 0, line: 260 },
      children: [t(String(text), {
        size: SZS, bold: !!opts.head, color: opts.head ? 'FFFFFF' : undefined,
      })],
    })],
  });

  return new Table({
    columnWidths: scaled,
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: {
      top:    { style: BorderStyle.SINGLE, size: 4, color: 'AAB4BE' },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: 'AAB4BE' },
      left:   { style: BorderStyle.SINGLE, size: 4, color: 'AAB4BE' },
      right:  { style: BorderStyle.SINGLE, size: 4, color: 'AAB4BE' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: 'D6DCE2' },
      insideVertical:   { style: BorderStyle.SINGLE, size: 2, color: 'D6DCE2' },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, i, { head: true })),
      }),
      ...rows.map(r => new TableRow({
        children: r.map((c, i) => cell(c, i, {
          align: (i > 0 && /^[₹\d(\-]/.test(String(c))) ? AlignmentType.RIGHT : AlignmentType.LEFT,
        })),
      })),
    ],
  });
}

// screenshot placeholder box
function shot(figNo, what, where) {
  return [
    new Table({
      columnWidths: [PAGE_W],
      width: { size: PAGE_W, type: WidthType.DXA },
      borders: {
        top:    { style: BorderStyle.DASHED, size: 6, color: '8A96A3' },
        bottom: { style: BorderStyle.DASHED, size: 6, color: '8A96A3' },
        left:   { style: BorderStyle.DASHED, size: 6, color: '8A96A3' },
        right:  { style: BorderStyle.DASHED, size: 6, color: '8A96A3' },
      },
      rows: [new TableRow({
        children: [new TableCell({
          width: { size: PAGE_W, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: 'F7F9FA' },
          margins: { top: 260, bottom: 260, left: 140, right: 140 },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER, spacing: { after: 60 },
              children: [t('[ PASTE SCREENSHOT HERE ]', { bold: true, size: SZS, color: '5C6B7A' })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 },
              children: [t(what, { size: 18, italics: true, color: '5C6B7A' })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER, spacing: { before: 40, after: 0, line: 240 },
              children: [t('Where: ' + where, { size: 18, color: '8A96A3' })],
            }),
          ],
        })],
      })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 200 },
      children: [t(figNo, { size: SZS, italics: true })],
    }),
  ];
}

// ==========================================================================
const body = [];

// ---- header -------------------------------------------------------------
body.push(new Paragraph({
  spacing: { after: 200 },
  children: [t('EX. NO: 8', { bold: true })],
}));
body.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 320 },
  children: [t('MINI PROJECT I – TOURISM ANALYTICS DASHBOARD USING POWER BI AND TABLEAU',
    { bold: true })],
}));

// ---- AIM ----------------------------------------------------------------
body.push(section('AIM'));
body.push(p('To design and develop an end-to-end business intelligence solution for a tour ' +
  'operator by retrieving data from a SQL Server data warehouse, preparing and modelling ' +
  'that data, and building an interactive Power BI dashboard and a Tableau dashboard and ' +
  'story that apply the data connection, transformation, modelling, calculation, advanced ' +
  'visualisation and interactivity concepts covered in Unit IV and Unit V.',
  { align: AlignmentType.JUSTIFIED }));

// ---- ALGORITHM ----------------------------------------------------------
body.push(section('ALGORITHM'));
[
  'Select the Tourism Analytics domain from the five domains provided and define the business problem to be answered.',
  'Design a dimensional (star schema) data warehouse consisting of one fact table and six conformed dimension tables.',
  'Create the database TourismDW in SQL Server, with a staging schema for the raw extract and a presentation schema for the cleaned model.',
  'Load the raw booking extract into the staging table stg.FactTrip_Raw and load all six dimension tables.',
  'Profile the raw data in T-SQL to identify duplicate records, invalid values and inconsistent categories.',
  'Clean and transform the staged data into dbo.FactTrip by de-duplicating, repairing invalid durations, standardising category values, enforcing referential integrity and deriving additional analytical columns.',
  'Apply primary keys, foreign keys and non-clustered indexes so that the star schema relationships are physically enforced in the database.',
  'Create analytical views that join the fact table to the dimensions and pre-compute scorecard, trend and customer-value aggregations.',
  'Connect Power BI Desktop to SQL Server using a parameterised server name, and import the fact and dimension tables.',
  'Apply further cleaning and transformation in Power Query: filter invalid rows, set data types and add custom columns.',
  'Build the Power BI data model by defining relationships, hierarchies, calculated columns and DAX measures, including time-intelligence, ranking and what-if measures.',
  'Design a six-page Power BI report with KPI cards, advanced visualisations, slicers, drill-down and drill-through, and apply consistent formatting.',
  'Export the integrated view from SQL Server as the Tableau extract, and connect Tableau to it.',
  'Create calculated fields, table calculations, parameters and filters in Tableau, and build the worksheets that use them.',
  'Assemble three interactive Tableau dashboards, add filter and highlight actions, and combine the dashboards into a Tableau story.',
  'Interpret the dashboards, record the insights obtained and document the complete solution.',
].forEach(s => body.push(numbered(s)));

// ---- PROGRAM ------------------------------------------------------------
body.push(section('PROGRAM'));

// Step 1 -----------------------------------------------------------------
body.push(stepLine(1, 'Domain and problem statement'));
body.push(p('Domain: Tourism Analytics.', { align: AlignmentType.JUSTIFIED }));
body.push(p('IndiaTrails Travel is a tour operator selling domestic and international ' +
  'holiday packages through its own website and app, a call centre, walk-in branches, ' +
  'online travel agencies and partner agents. Bookings, traveller details, destinations, ' +
  'accommodation, transport and pricing are held in an operational system and extracted ' +
  'nightly into a data warehouse. Management can see total sales, but cannot answer the ' +
  'questions that actually drive profit.', { align: AlignmentType.JUSTIFIED }));
body.push(p('The mini project sets out to answer six of them:', { after: 100 }));
[
  'Which destinations generate the most revenue, and how concentrated is that revenue?',
  'How strongly does demand vary by season, and when should capacity be bought?',
  'Which booking channels are genuinely profitable once commission is deducted?',
  'Does the loyalty discount programme pay for itself in extra trips?',
  'What drives traveller satisfaction, and where is it being eroded?',
  'How far ahead do travellers book, and does that relate to cancellation?',
].forEach(s => body.push(bullet(s)));

// Step 2 -----------------------------------------------------------------
body.push(stepLine(2, 'Dataset description'));
body.push(p('The warehouse follows a star schema: one fact table at the grain of one row ' +
  'per booking, surrounded by six dimension tables.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(80));
body.push(makeTable(
  ['Table', 'Type', 'Rows', 'Cols', 'Description'],
  [
    ['dbo.FactTrip', 'Fact', '12,000', '27', 'One row per booking: costs, revenue, discount, commission, duration, party size, lead time, satisfaction, status'],
    ['dbo.DimDate', 'Dimension', '2,191', '15', 'Calendar 2022–2027 with year, quarter, month, financial year, season and peak-season flag'],
    ['dbo.DimDestination', 'Dimension', '32', '13', 'Destination, city, country, region, continent, type, latitude/longitude, cost and popularity index'],
    ['dbo.DimTraveller', 'Dimension', '2,400', '10', 'Traveller name, gender, age band, nationality, customer segment, loyalty tier, signup date'],
    ['dbo.DimAccommodation', 'Dimension', '155', '7', 'Property name, type, star rating, price index, average rating'],
    ['dbo.DimTransport', 'Dimension', '18', '6', 'Transport type, carrier, travel class, cost factor'],
    ['dbo.DimBookingChannel', 'Dimension', '9', '4', 'Channel name, channel type and commission rate'],
    ['stg.FactTrip_Raw', 'Staging', '12,060', '23', 'The raw extract before cleaning, retained as evidence'],
  ], [22, 12, 10, 8, 48]));
body.push(blank(60));
body.push(p('Travel dates span 1 January 2023 to 31 December 2026, covering 12,000 clean ' +
  'bookings, 35,635 travellers and ₹296.91 crore of gross revenue.',
  { align: AlignmentType.JUSTIFIED }));

// Step 3 -----------------------------------------------------------------
body.push(stepLine(3, 'Data source: connecting to SQL Server'));
body.push(p('The database was created and loaded on a local SQL Server 2022 Express ' +
  'instance. Both Power BI and Tableau connect to the same instance, so the two tools ' +
  'report identical figures.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(60));
body.push(makeTable(['Property', 'Value'], [
  ['Server', 'localhost\\SQLEXPRESS'],
  ['Database', 'TourismDW'],
  ['Authentication', 'Windows Authentication'],
  ['Power BI connectivity', 'Import mode, server name held as a Power Query parameter'],
  ['Tableau connectivity', 'Live connection using a Custom SQL query on dbo.vw_TripAnalysis'],
], [30, 70]));
body.push(blank(100));
body.push(...shot('Fig. 8.1 – SQL Server Object Explorer showing the TourismDW database',
  'SSMS Object Explorer with TourismDW expanded to show Tables and Views',
  'SSMS, left-hand pane'));

// Step 4 -----------------------------------------------------------------
body.push(stepLine(4, 'Data preparation: profiling and cleaning'));
body.push(p('The extract was deliberately treated as untrusted. It was loaded first into ' +
  'stg.FactTrip_Raw and profiled before any use. Profiling found four defects:',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(80));
body.push(makeTable(
  ['Defect found in the raw extract', 'Count', 'Cleaning rule applied'],
  [
    ['Duplicate bookings (same BookingReference)', '60', 'ROW_NUMBER() over BookingReference, keep the lowest TripID'],
    ['Negative DurationDays (sign-flip entry error)', '25', 'Repair with ABS(), rather than discard the booking'],
    ['Inconsistent BookingStatus casing — 362 rows stored in upper case', '362', 'UPPER(LEFT(..,1)) + LOWER(SUBSTRING(..,2,50)), then a special case for "No Show". Note: SQL Server\'s default collation is case-insensitive, so the profile query reports 4 distinct values rather than 8; the defect is still visible in the output, where NO SHOW appears in capitals beside title-case values'],
    ['Missing SatisfactionScore', '2,197', 'Left as NULL — cancelled and future trips genuinely have no rating, so imputing would distort the average'],
  ], [42, 10, 48]));
body.push(blank(80));
body.push(p('Rows whose foreign keys did not resolve were excluded by inner-joining every ' +
  'dimension during the load. Four analytical columns were then derived: ' +
  'RevenuePerTraveller, RevenuePerDay, BookingWindow and TripLengthBand.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(60));
body.push(makeTable(['Stage', 'Rows'], [
  ['Raw rows in stg.FactTrip_Raw', '12,060'],
  ['Clean rows in dbo.FactTrip', '12,000'],
  ['Rows removed', '60'],
], [60, 40]));
body.push(blank(100));
body.push(...shot('Fig. 8.2 – Raw data quality profile before cleaning',
  'Results grid from Script 03, Step 1 — the profile and the eight BookingStatus values',
  'SSMS results pane after running 03_clean_transform_model.sql'));
body.push(...shot('Fig. 8.3 – Row counts and integrity checks after cleaning',
  'Results grid from Script 04, Section A — table row counts and the integrity checks returning 0',
  'SSMS results pane after running 04_verification_and_analysis.sql'));

// Step 5 -----------------------------------------------------------------
body.push(stepLine(5, 'Data modelling: the star schema'));
body.push(p('Foreign keys were applied in SQL Server so that the star schema is enforced ' +
  'by the database rather than only assumed by the reporting tools. Non-clustered indexes ' +
  'were added on the four most frequently filtered columns.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(60));
body.push(makeTable(['Relationship', 'Cardinality', 'Notes'], [
  ['FactTrip → DimDate (StartDateKey)', 'Many-to-one', 'Active. Drives all time intelligence'],
  ['FactTrip → DimDate (BookingDateKey)', 'Many-to-one', 'Inactive; activated in DAX with USERELATIONSHIP'],
  ['FactTrip → DimDate (EndDateKey)', 'Many-to-one', 'Inactive; retained for return-date analysis'],
  ['FactTrip → DimDestination', 'Many-to-one', 'Active'],
  ['FactTrip → DimTraveller', 'Many-to-one', 'Active'],
  ['FactTrip → DimAccommodation', 'Many-to-one', 'Active'],
  ['FactTrip → DimTransport', 'Many-to-one', 'Active'],
  ['FactTrip → DimBookingChannel', 'Many-to-one', 'Active'],
  ['DimAccommodation → DimDestination', 'Many-to-one', 'Inactive. Kept for documentation only: with the direct FactTrip → DimDestination relationship active, leaving this one active would give Power BI two paths to DimDestination and an ambiguous model'],
], [34, 18, 48]));
body.push(blank(80));
body.push(p('Four analytical views were created on top of the model: vw_TripAnalysis (the ' +
  'fully integrated wide view used by Tableau), vw_DestinationScorecard, vw_MonthlyTrend ' +
  '(with a three-month moving average and a same-month-last-year comparison computed by ' +
  'window functions) and vw_TravellerValue (an NTILE-based customer value segmentation).',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(100));
body.push(...shot('Fig. 8.4 – Star schema in Power BI Model view',
  'Power BI Model view showing FactTrip at the centre with the six dimensions and the two dashed inactive relationships',
  'Power BI Desktop, Model view (left rail, third icon)'));

body.push(new Paragraph({ children: [new PageBreak()] }));

// Step 6 -----------------------------------------------------------------
body.push(stepLine(6, 'Power BI: data connection and Power Query transformation'));
body.push(p('The server name is held as a Power Query parameter so the solution moves ' +
  'between machines without editing any query. Each table is retrieved by navigating the ' +
  'SQL Server catalogue:', { align: AlignmentType.JUSTIFIED }));
body.push(code('Source = Sql.Database(ServerName, DatabaseName),'));
body.push(code('dbo_FactTrip = Source{[Schema="dbo",Item="FactTrip"]}[Data],'));
body.push(blank(60));
body.push(p('A second layer of transformation is applied in Power Query on FactTrip:',
  { after: 100 }));
[
  'Removed Blank Rows — drops rows with a null TripID or Revenue.',
  'Filtered Valid Trips — keeps only rows with a positive duration, party size and revenue.',
  'Changed Type — sets the five monetary and score columns to decimal number.',
  'Added Satisfaction Band — a conditional column classifying each rating as Promoter, Passive, Detractor or Not Rated.',
  'Added Discount Pct — DiscountAmount divided by GrossAmount, guarded against division by zero.',
  'Added Traveller Days — NumTravellers multiplied by DurationDays.',
].forEach(s => body.push(bullet(s)));
body.push(blank(100));
body.push(...shot('Fig. 8.5 – Power Query Editor showing the applied steps on FactTrip',
  'Power Query Editor with the FactTrip query selected and the Applied Steps list visible on the right',
  'Power BI Desktop → Home → Transform data'));

// Step 7 -----------------------------------------------------------------
body.push(stepLine(7, 'Power BI: calculated columns and DAX measures'));
body.push(p('The model contains 14 calculated columns and 51 DAX measures organised into ' +
  'nine display folders. The measures below are representative of each category.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(80));
body.push(makeTable(['Measure', 'DAX expression', 'Category'], [
  ['Total Revenue', 'SUM ( FactTrip[Revenue] )', 'Base'],
  ['Avg Booking Value', 'DIVIDE ( [Total Revenue], [Total Bookings] )', 'Ratio'],
  ['Cancellation Rate %', 'DIVIDE ( [Cancelled Bookings], [Total Bookings] )', 'Ratio'],
  ['Net Margin %', 'DIVIDE ( [Net Revenue], [Total Revenue] )', 'Ratio'],
  ['Revenue YTD', 'TOTALYTD ( [Total Revenue], DimDate[FullDate] )', 'Time intelligence'],
  ['Revenue PY', 'CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( DimDate[FullDate] ) )', 'Time intelligence'],
  ['Revenue YoY %', 'DIVIDE ( [Revenue YoY], [Revenue PY] )', 'Time intelligence'],
  ['Revenue 3M Moving Avg', 'AVERAGEX ( DATESINPERIOD ( DimDate[FullDate], MAX ( DimDate[FullDate] ), -3, MONTH ), CALCULATE ( [Total Revenue] ) )', 'Time intelligence'],
  ['Running Total Revenue', 'CALCULATE ( [Total Revenue], FILTER ( ALLSELECTED ( DimDate[FullDate] ), DimDate[FullDate] <= MAX ( DimDate[FullDate] ) ) )', 'Time intelligence'],
  ['Bookings by Booking Date', 'CALCULATE ( [Total Bookings], USERELATIONSHIP ( FactTrip[BookingDateKey], DimDate[DateKey] ) )', 'Inactive relationship'],
  ['Destination Rank', 'RANKX ( ALL ( DimDestination[DestinationName] ), [Total Revenue], , DESC, DENSE )', 'Ranking'],
  ['Pareto Revenue %', 'Cumulative share using ADDCOLUMNS, FILTER and SUMX over ALLSELECTED destinations', 'Ranking'],
  ['Revenue Target', 'IF ( NOT ISBLANK ( [Revenue PY] ), [Revenue PY] * 1.15 )', 'Target'],
  ['Target Achievement %', 'DIVIDE ( [Total Revenue], [Revenue Target] )', 'Target'],
  ['Revenue at Scenario Discount', "SUMX ( FactTrip, FactTrip[GrossAmount] * ( 1 - SELECTEDVALUE ( 'Discount Scenario'[Discount %], 0 ) ) )", 'What-if'],
  ['Dynamic Title Destination', 'Concatenates the selected destinations into the visual title', 'Dynamic title'],
], [23, 57, 20]));
body.push(blank(80));
body.push(p('A what-if parameter table, Discount Scenario, was generated with ' +
  'GENERATESERIES ( 0, 0.30, 0.01 ) and bound to a slicer so the whole book can be ' +
  're-priced at a single discount level.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(100));
body.push(...shot('Fig. 8.6 – DAX measures organised in display folders',
  'Power BI Data view or the Fields pane with the measure display folders expanded',
  'Power BI Desktop, Fields pane on the right'));

body.push(new Paragraph({ children: [new PageBreak()] }));

// Step 8 -----------------------------------------------------------------
body.push(stepLine(8, 'Power BI: dashboard design'));
body.push(p('The report has six pages and fifty visuals.', { after: 100 }));
body.push(makeTable(['Page', 'Visuals used', 'Concepts demonstrated'], [
  ['1. Executive Overview', 'Six KPI cards, line-and-clustered-column combo, donut, bar, treemap, two slicers', 'KPIs and cards, combo chart, slicers'],
  ['2. Destination Performance', 'Map, drill-down column chart on the geography hierarchy, scatter, matrix scorecard', 'Maps, drill-down, drill-through source, conditional formatting'],
  ['3. Seasonality & Growth', 'Month × year matrix heat map, YoY column chart, ribbon chart, combo chart', 'Advanced visualisations, time intelligence'],
  ['4. Customer & Channel', 'Waterfall, bar, combo, clustered column, table', 'Waterfall, multi-measure comparison'],
  ['5. Scenario Planning', 'What-if slicer, three cards, clustered column, Pareto combo, gauge, funnel, clustered column', 'What-if parameter, gauge against target, Pareto'],
  ['6. Destination Detail', 'Six cards, line chart, bar chart, detail table', 'Drill-through target page'],
], [24, 40, 36]));
body.push(blank(100));
[
  ['Fig. 8.7 – Power BI page 1: Executive Overview', 'The full Executive Overview page with the KPI card strip and all filters cleared'],
  ['Fig. 8.8 – Power BI page 2: Destination Performance', 'The Destination Performance page, with the drill-down chart expanded to country level'],
  ['Fig. 8.9 – Power BI page 3: Seasonality & Growth', 'The Seasonality page with the heat map showing background conditional formatting'],
  ['Fig. 8.10 – Power BI page 4: Customer & Channel', 'The Customer & Channel page'],
  ['Fig. 8.11 – Power BI page 5: Scenario Planning', 'The Scenario Planning page with the discount slicer set to a non-zero value'],
  ['Fig. 8.12 – Power BI page 6: Destination Detail reached by drill-through', 'The Destination Detail page after right-clicking a destination on page 2 and choosing Drill through'],
].forEach(([fig, what]) => body.push(...shot(fig, what, 'Power BI Desktop, Report view')));

body.push(new Paragraph({ children: [new PageBreak()] }));

// Step 9 -----------------------------------------------------------------
body.push(stepLine(9, 'Tableau: connection and data integration'));
body.push(p('The integration itself is performed in SQL Server. The view ' +
  'dbo.vw_TripAnalysis joins the fact table to all six dimension tables and exposes a ' +
  'single clean relation of 54 fields, which keeps the join logic in one place and ' +
  'guarantees that Tableau and Power BI report identical figures.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(60));
body.push(p('Tableau consumes that view in one of two ways depending on the edition ' +
  'available:', { after: 100 }));
body.push(makeTable(['Edition', 'Connection method', 'Workbook'], [
  ['Tableau Desktop', 'Live connection to SQL Server using a Custom SQL query on dbo.vw_TripAnalysis', 'TourismAnalytics_SQLServer.twb'],
  ['Tableau Public', 'The view is exported from SQL Server as a flat extract, which the packaged workbook consumes', 'TourismAnalytics_Packaged.twbx'],
], [20, 52, 28]));
body.push(blank(80));
body.push(p('Tableau Public does not support database connectors — it reads only Excel, ' +
  'text, spatial, statistical and a small number of web sources, with SQL Server, Oracle, ' +
  'MySQL and PostgreSQL restricted to Tableau Desktop. This project was therefore built ' +
  'against the extract route, and script 05_export_extract_for_tableau.sql is the exact ' +
  'query used to produce that extract from the database:',
  { align: AlignmentType.JUSTIFIED }));
body.push(code('SELECT ... FROM dbo.vw_TripAnalysis ORDER BY TripID;   -- 12,000 rows x 54 columns'));
body.push(blank(60));
body.push(p('The extract is therefore a SQL Server output, not an independent data file: ' +
  'all cleaning, conforming and joining happens in the database, and Tableau receives the ' +
  'result. The Tableau Desktop workbook connecting live to the same view is included ' +
  'alongside it for completeness.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(100));
body.push(...shot('Fig. 8.13 – Exporting the integrated view from SQL Server for Tableau',
  'SSMS results grid from 05_export_extract_for_tableau.sql, with the 12,000-row count visible',
  'SSMS, after running script 05'));
body.push(...shot('Fig. 8.14 – Tableau Data Source tab',
  'The Data Source tab showing the extract and the 54 fields it exposes',
  'Tableau, Data Source tab at the bottom left'));

// Step 10 ----------------------------------------------------------------
body.push(stepLine(10, 'Tableau: calculated fields, parameters and filters'));
body.push(p('Eighteen calculated fields were created, six of which are table calculations, ' +
  'together with four parameters.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(80));
body.push(makeTable(['Calculated field', 'Formula', 'Type'], [
  ['Total Revenue', 'SUM([Revenue])', 'Aggregate'],
  ['Avg Booking Value', 'SUM([Revenue]) / COUNT([TripID])', 'Aggregate'],
  ['Cancellation Rate', 'SUM(IF [BookingStatus] = "Cancelled" THEN 1 ELSE 0 END) / COUNT([TripID])', 'Aggregate'],
  ['Net Margin %', 'SUM([NetRevenue]) / SUM([Revenue])', 'Aggregate'],
  ['Destination Rank', 'RANK(SUM([Revenue]))', 'Table calculation'],
  ['Revenue Moving Avg', 'WINDOW_AVG(SUM([Revenue]), -2, 0)', 'Table calculation'],
  ['Running Revenue %', 'RUNNING_SUM(SUM([Revenue])) / TOTAL(SUM([Revenue]))', 'Table calculation'],
  ['Revenue YoY %', '(SUM([Revenue]) - LOOKUP(SUM([Revenue]), -1)) / ABS(LOOKUP(SUM([Revenue]), -1))', 'Table calculation'],
  ['Top N Filter', 'RANK(SUM([Revenue])) <= [Top N Destinations]', 'Table calc + parameter'],
  ['Scenario Revenue', 'SUM([GrossAmount]) * (1 - [Scenario Discount %])', 'Parameter-driven'],
  ['Revenue Target', 'LOOKUP(SUM([Revenue]), -1) * (1 + [Target Growth %])', 'Parameter-driven'],
  ['Selected Measure', 'CASE [Select Measure] WHEN "Revenue" THEN SUM([Revenue]) WHEN "Bookings" THEN COUNT([TripID]) WHEN "Travellers" THEN SUM([NumTravellers]) END', 'Parameter-driven'],
], [22, 58, 20]));
body.push(blank(80));
body.push(makeTable(['Parameter', 'Data type', 'Domain', 'Used by'], [
  ['Top N Destinations', 'Integer', 'Range 5 to 25, step 1', 'Top N Filter, on the Top N Destinations worksheet'],
  ['Scenario Discount %', 'Float', 'Range 0% to 30%, step 1%', 'Scenario Revenue and Scenario Impact'],
  ['Target Growth %', 'Float', 'Range 0% to 50%, step 5%', 'Revenue Target'],
  ['Select Measure', 'String', 'Revenue / Bookings / Travellers', 'Selected Measure, for measure swapping'],
], [22, 14, 26, 38]));
body.push(blank(80));
body.push(p('Four filters — travel year, travel scope, season and channel type — are placed ' +
  'on every worksheet and exposed as interactive controls on the dashboards.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(100));
body.push(...shot('Fig. 8.15 – Calculated field and parameter definitions in Tableau',
  'A calculated field editor open on Running Revenue %, with the parameter list visible in the Data pane',
  'Tableau, Data pane → right-click a calculated field → Edit'));

body.push(new Paragraph({ children: [new PageBreak()] }));

// Step 11 ----------------------------------------------------------------
body.push(stepLine(11, 'Tableau: worksheets, dashboards and story'));
body.push(p('Nineteen worksheets were built and assembled into three dashboards and one ' +
  'story.', { after: 100 }));
body.push(makeTable(['Dashboard', 'Worksheets', 'Interactivity'], [
  ['D1 Executive Overview', 'Five KPI tiles, revenue trend line, Top N destinations bar, segment treemap, channel profitability bar', 'Year and travel-scope filter controls, Top N parameter control, highlight action on destination'],
  ['D2 Destination & Seasonality', 'Destination map, month × year heat map, destination Pareto, satisfaction analysis', 'Filter action from the map to the detail table on D3'],
  ['D3 Customer & Channel', 'Traveller demographics, booking window, cost composition, discount scenario, booking detail table', 'Scenario discount parameter control, channel type and season filter controls'],
], [24, 44, 32]));
body.push(blank(100));
[
  ['Fig. 8.16 – Tableau dashboard D1: Executive Overview', 'The complete D1 dashboard with the Top N parameter slider visible'],
  ['Fig. 8.17 – Tableau dashboard D2: Destination & Seasonality', 'The complete D2 dashboard with the map and heat map'],
  ['Fig. 8.18 – Tableau dashboard D3: Customer & Channel', 'The complete D3 dashboard with the discount parameter set to a non-zero value'],
  ['Fig. 8.19 – Tableau story', 'The story with all four story points visible along the navigator strip'],
].forEach(([fig, what]) => body.push(...shot(fig, what, 'Tableau')));

body.push(new Paragraph({ children: [new PageBreak()] }));

// Step 12 ----------------------------------------------------------------
body.push(stepLine(12, 'Insights obtained'));

body.push(p('Insight 1 — Revenue is growing, but the growth is almost entirely international.',
  { bold: true, after: 100 }));
body.push(makeTable(['Travel scope', 'Bookings', 'Revenue (₹ Cr)', 'Avg booking value', 'Share of revenue'], [
  ['International', '8,731', '270.39', '₹3,09,693', '91.1%'],
  ['Domestic', '3,269', '26.51', '₹81,101', '8.9%'],
], [22, 16, 20, 22, 20]));
body.push(blank(60));
body.push(p('International trips are 72.8% of bookings but 91.1% of revenue, because the ' +
  'average international booking is worth 3.8 times the average domestic one. International ' +
  'revenue grew every year (+18.1%, +13.1%, +7.0%); domestic revenue fell 4.1% in 2026 after ' +
  'a strong 2025. Total revenue rose 43% between 2023 and 2026.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 2 — Demand swings by a factor of 2.2 across the year.',
  { bold: true, after: 100 }));
body.push(makeTable(['Month', 'Revenue (₹ Cr)', 'Seasonality index'], [
  ['December', '37.07', '150'],
  ['October', '34.13', '138'],
  ['May', '31.62', '128'],
  ['April', '31.16', '126'],
  ['November', '29.91', '121'],
  ['June (lowest)', '16.83', '68'],
], [34, 33, 33]));
body.push(blank(60));
body.push(p('December earns 2.2 times what June earns. The peak months — April, May, ' +
  'October, November and December — carry a further 18% price premium, which means capacity ' +
  'bought in advance for those months is where margin is won or lost.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 3 — Online travel agencies buy volume at a real cost to margin.',
  { bold: true, after: 100 }));
body.push(makeTable(['Channel', 'Type', 'Bookings', 'Revenue (₹ Cr)', 'Commission (₹ L)', 'Net margin'], [
  ['MakeMyTrip', 'OTA', '1,956', '49.92', '698.94', '86.0%'],
  ['Booking.com', 'OTA', '1,785', '42.92', '643.87', '85.0%'],
  ['Expedia', 'OTA', '1,481', '37.34', '597.49', '84.0%'],
  ['Company Website', 'Direct', '1,582', '39.01', '78.02', '98.0%'],
  ['Mobile App', 'Direct', '1,431', '35.35', '70.70', '98.0%'],
  ['Walk-in Branch', 'Offline', '621', '14.86', '0.00', '100.0%'],
], [22, 12, 14, 18, 18, 16]));
body.push(blank(60));
body.push(p('The three OTAs together bring 43% of bookings but surrender ₹19.4 crore in ' +
  'commission. MakeMyTrip is the largest channel by gross revenue, yet the company website ' +
  'delivers more net revenue than Booking.com on fewer bookings. Shifting even a tenth of ' +
  'OTA volume to the direct channels would be worth roughly ₹1.9 crore a year at current ' +
  'rates.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 4 — The loyalty discount is not buying additional trips.',
  { bold: true, after: 100 }));
body.push(makeTable(['Loyalty tier', 'Travellers', 'Trips', 'Trips per traveller', 'Avg discount', 'Avg trip value'], [
  ['Blue', '425', '2,141', '5.04', '3.27%', '₹2,85,138'],
  ['Silver', '605', '3,050', '5.04', '6.16%', '₹2,35,807'],
  ['Gold', '546', '2,766', '5.07', '9.40%', '₹2,40,538'],
  ['Platinum', '809', '4,043', '5.00', '13.43%', '₹2,40,918'],
], [18, 16, 13, 19, 16, 18]));
body.push(blank(60));
body.push(p('Trips per traveller is essentially flat at about 5.0 across all four tiers, ' +
  'while the average discount rises from 3.3% to 13.4%. The programme is therefore ' +
  'transferring margin to the most loyal travellers without generating extra bookings from ' +
  'them. This is the clearest commercial finding in the dataset and would justify a ' +
  'controlled test of a lower Platinum discount.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 5 — Peak season costs half a satisfaction point at every quality level.',
  { bold: true, after: 100 }));
body.push(makeTable(['Star rating', 'Peak season score', 'Off-peak score', 'Difference'], [
  ['5 star', '6.80', '7.32', '−0.52'],
  ['4 star', '6.35', '6.90', '−0.55'],
  ['3 star', '5.91', '6.49', '−0.58'],
  ['2 star', '5.50', '6.03', '−0.53'],
], [25, 25, 25, 25]));
body.push(blank(60));
body.push(p('The penalty is almost identical at every star rating, which points to crowding ' +
  'and service strain during peak months rather than to any particular grade of property. ' +
  'Upgrading accommodation would not fix it; managing peak-season capacity would.',
  { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 6 — Booking earlier does not reduce cancellation.',
  { bold: true, after: 100 }));
body.push(makeTable(['Booking window', 'Bookings', 'Avg booking value', 'Cancellation rate'], [
  ['Last minute (0–7 days)', '347', '₹2,63,886', '6.05%'],
  ['Short (8–30 days)', '3,752', '₹2,46,831', '6.50%'],
  ['Medium (31–90 days)', '6,609', '₹2,46,280', '7.13%'],
  ['Early bird (90+ days)', '1,292', '₹2,50,548', '6.81%'],
], [30, 18, 26, 26]));
body.push(blank(60));
body.push(p('Cancellation sits in a narrow 6.1% to 7.1% band regardless of how far ahead ' +
  'the booking was made, so lead time is not a useful predictor of cancellation risk here. ' +
  'Last-minute bookings are also the most valuable on average, which argues against ' +
  'discounting late inventory too aggressively.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(120));

body.push(p('Insight 7 — Revenue is broadly spread, not concentrated.',
  { bold: true, after: 100 }));
body.push(p('The top ten destinations account for 48.4% of revenue across 32 destinations, ' +
  'and no single destination exceeds 5.8%. London Explorer leads at ₹17.08 crore (5.75%), ' +
  'followed by Bangkok & Phuket at ₹14.70 crore and Maldives Atolls at ₹14.60 crore. This ' +
  'is a healthier distribution than the classic 80/20 pattern and means no single ' +
  'destination failing would threaten the business — but it also means there is no obvious ' +
  'place to concentrate marketing spend.', { align: AlignmentType.JUSTIFIED }));
body.push(blank(60));
body.push(p('Transport is the largest single cost component at 46.8% of gross booking value, ' +
  'ahead of accommodation at 28.6% and activities at 24.6%, which reflects how ' +
  'international the mix is.', { align: AlignmentType.JUSTIFIED }));

// ---- RESULT -------------------------------------------------------------
body.push(section('RESULT'));
body.push(p('Thus a complete Tourism Analytics business intelligence solution was designed ' +
  'and developed. Data was retrieved from a SQL Server data warehouse, profiled, cleaned ' +
  'and modelled into a star schema; an interactive six-page Power BI dashboard with 51 DAX ' +
  'measures, 14 calculated columns, nine relationships and a what-if parameter was built; a Tableau ' +
  'workbook with 19 worksheets, 18 calculated fields, 4 parameters, 3 dashboards and a ' +
  'story was built on an extract of the same integrated view; and the resulting dashboards were interpreted ' +
  'to produce seven business insights. The outputs were verified successfully.',
  { align: AlignmentType.JUSTIFIED }));

// ==========================================================================
const doc = new Document({
  creator: 'TT',
  title: 'Mini Project I - Tourism Analytics',
  numbering: {
    config: [
      {
        reference: 'algo',
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 520, hanging: 300 } },
                   run: { font: FONT, size: SZ } },
        }],
      },
      {
        reference: 'bullets',
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 520, hanging: 300 } },
                   run: { font: FONT, size: SZ } },
        }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: FONT, size: SZ }, paragraph: { spacing: { line: 300 } } },
    },
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1080, bottom: 1440, left: 1440 } },
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('docs/Exp8_MiniProject1_Tourism.docx', buf);
  console.log('docs/Exp8_MiniProject1_Tourism.docx written:', (buf.length / 1024).toFixed(1), 'KB');
});
