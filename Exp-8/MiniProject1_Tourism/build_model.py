"""
Builds the Power BI semantic model (TMSL / model.bim) for the Tourism
Analytics mini project.  Connects to SQL Server database TourismDW.
"""
import json, uuid, os

SM = "powerbi/TourismAnalytics.SemanticModel"
os.makedirs(SM, exist_ok=True)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def col(name, dtype, source=None, fmt=None, summarize="none", hidden=False,
        sort_by=None, category=None, is_key=False, desc=None):
    c = {
        "name": name,
        "dataType": dtype,
        "sourceColumn": source or name,
        "summarizeBy": summarize,
        "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}],
    }
    if fmt:      c["formatString"] = fmt
    if hidden:   c["isHidden"] = True
    if sort_by:  c["sortByColumn"] = sort_by
    if category: c["dataCategory"] = category
    if is_key:   c["isKey"] = True
    if desc:     c["description"] = desc
    return c

def calc_col(name, dtype, expr, fmt=None, sort_by=None, desc=None):
    c = {
        "type": "calculated",
        "name": name,
        "dataType": dtype,
        "expression": expr,
        "isDataTypeInferred": True,
        "summarizeBy": "none",
        "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}],
    }
    if fmt:     c["formatString"] = fmt
    if sort_by: c["sortByColumn"] = sort_by
    if desc:    c["description"] = desc
    return c

def measure(name, expr, fmt=None, folder=None, desc=None, hidden=False):
    m = {"name": name, "expression": expr}
    if fmt:    m["formatString"] = fmt
    if folder: m["displayFolder"] = folder
    if desc:   m["description"] = desc
    if hidden: m["isHidden"] = True
    m["annotations"] = [{"name": "PBI_FormatHint", "value": '{"isGeneralNumber":true}'}] if not fmt else []
    if not m["annotations"]:
        del m["annotations"]
    return m

def sql_partition(table, schema="dbo", extra_steps=None, final=None):
    """M query: SQL Server -> navigate -> optional transformation steps.

    The last step before `in` must not carry a trailing comma, so strip it.
    """
    steps = [
        "    Source = Sql.Database(ServerName, DatabaseName),",
        f'    {schema}_{table} = Source{{[Schema="{schema}",Item="{table}"]}}[Data],',
    ]
    if extra_steps:
        steps += [s.rstrip() for s in extra_steps]
    steps[-1] = steps[-1].rstrip().rstrip(",")          # no comma before `in`
    return {
        "name": table,
        "mode": "import",
        "source": {"type": "m",
                   "expression": ["let"] + steps + ["in", f"    {final or f'{schema}_{table}'}"]},
    }



def table(name, columns, partition, measures=None, hierarchies=None,
          data_category=None, hidden=False, desc=None):
    t = {"name": name, "columns": columns, "partitions": [partition]}
    if measures:      t["measures"] = measures
    if hierarchies:   t["hierarchies"] = hierarchies
    if data_category: t["dataCategory"] = data_category
    if hidden:        t["isHidden"] = True
    if desc:          t["description"] = desc
    t["annotations"] = [{"name": "PBI_ResultType", "value": "Table"}]
    return t

def hierarchy(name, levels):
    return {"name": name,
            "levels": [{"name": l, "ordinal": i, "column": l} for i, l in enumerate(levels)]}

def rel(from_t, from_c, to_t, to_c, active=True, name=None):
    r = {
        "name": name or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{from_t}{from_c}{to_t}{to_c}")),
        "fromTable": from_t, "fromColumn": from_c,
        "toTable": to_t, "toColumn": to_c,
    }
    if not active:
        r["isActive"] = False
    return r

INR   = '"₹"#,0'
INR2  = '"₹"#,0.00'
PCT   = '0.0%'
NUM   = '#,0'
DEC2  = '#,0.00'

# ---------------------------------------------------------------------------
# DimDate
# ---------------------------------------------------------------------------
dim_date = table(
    "DimDate",
    [
        col("DateKey", "int64", fmt="0", hidden=True, is_key=True),
        col("FullDate", "dateTime", fmt="dd mmm yyyy"),
        col("Year", "int64", fmt="0"),
        col("Quarter", "string"),
        col("MonthNo", "int64", fmt="0", hidden=True),
        col("MonthName", "string", sort_by="MonthNo"),
        col("MonthYear", "string", sort_by="DateKey"),
        col("DayOfMonth", "int64", fmt="0"),
        col("DayName", "string"),
        col("WeekOfYear", "int64", fmt="0"),
        col("DayOfYear", "int64", fmt="0", hidden=True),
        col("IsWeekend", "boolean", hidden=True),
        col("Season", "string"),
        col("FinancialYear", "string"),
        col("IsPeakSeason", "boolean"),
        calc_col("Season Sort", "int64",
                 'SWITCH( DimDate[Season], "Winter", 1, "Summer", 2, "Monsoon", 3, "Autumn", 4, 5 )',
                 fmt="0"),
        calc_col("Peak Season Label", "string",
                 'IF ( DimDate[IsPeakSeason], "Peak Season", "Off Peak" )'),
        calc_col("Year Quarter", "string",
                 'DimDate[Year] & "-" & DimDate[Quarter]'),
    ],
    sql_partition("DimDate", extra_steps=[
        '    #"Changed Type" = Table.TransformColumnTypes(dbo_DimDate,{{"FullDate", type date}}),',
        '    #"Sorted Rows" = Table.Sort(#"Changed Type",{{"DateKey", Order.Ascending}}),',
    ], final='#"Sorted Rows"'),
    hierarchies=[hierarchy("Calendar Hierarchy", ["Year", "Quarter", "MonthName"])],
    data_category="Time",
    desc="Conformed calendar dimension. Marked as the model date table for time intelligence.",
)
dim_date["columns"][1]["isKey"] = False  # FullDate not the key; DateKey is

# ---------------------------------------------------------------------------
# DimDestination
# ---------------------------------------------------------------------------
dim_dest = table(
    "DimDestination",
    [
        col("DestinationID", "int64", fmt="0", hidden=True),
        col("DestinationName", "string", category="Place"),
        col("City", "string", category="City"),
        col("StateProvince", "string", category="StateOrProvince"),
        col("Country", "string", category="Country"),
        col("Region", "string"),
        col("Continent", "string", category="Continent"),
        col("DestinationType", "string"),
        col("Latitude", "double", fmt=DEC2, category="Latitude"),
        col("Longitude", "double", fmt=DEC2, category="Longitude"),
        col("CostIndex", "double", fmt=DEC2),
        col("PopularityIndex", "double", fmt=DEC2),
        col("IsDomestic", "boolean", hidden=True),
        calc_col("Travel Scope", "string",
                 'IF ( DimDestination[IsDomestic], "Domestic", "International" )'),
        calc_col("Destination Label", "string",
                 'DimDestination[DestinationName] & " (" & DimDestination[Country] & ")"'),
        calc_col("Cost Tier", "string",
                 'SWITCH ( TRUE(),\n'
                 '    DimDestination[CostIndex] >= 1.8, "1. Premium",\n'
                 '    DimDestination[CostIndex] >= 1.2, "2. Upper Mid",\n'
                 '    DimDestination[CostIndex] >= 0.8, "3. Mid",\n'
                 '    "4. Value" )'),
    ],
    sql_partition("DimDestination", extra_steps=[
        '    #"Changed Type" = Table.TransformColumnTypes(dbo_DimDestination,'
        '{{"Latitude", type number}, {"Longitude", type number}}),',
        '    #"Trimmed Text" = Table.TransformColumns(#"Changed Type",'
        '{{"DestinationName", Text.Trim, type text}, {"Country", Text.Trim, type text}}),',
    ], final='#"Trimmed Text"'),
    hierarchies=[hierarchy("Geography Hierarchy", ["Continent", "Country", "DestinationName"])],
    desc="Destination master with geography for map visuals and a drill-down hierarchy.",
)

# ---------------------------------------------------------------------------
# DimTraveller
# ---------------------------------------------------------------------------
dim_trav = table(
    "DimTraveller",
    [
        col("TravellerID", "int64", fmt="0", hidden=True),
        col("TravellerName", "string"),
        col("Gender", "string"),
        col("Age", "int64", fmt="0"),
        col("AgeBand", "string"),
        col("Nationality", "string", category="Country"),
        col("SignupDate", "dateTime", fmt="dd mmm yyyy"),
        col("CustomerSegment", "string"),
        col("LoyaltyTier", "string"),
        col("IsRepeatCustomer", "boolean"),
        calc_col("Loyalty Tier Sort", "int64",
                 'SWITCH ( DimTraveller[LoyaltyTier], "Blue", 1, "Silver", 2, "Gold", 3, "Platinum", 4, 5 )',
                 fmt="0"),
        calc_col("Tenure Days", "int64",
                 'DATEDIFF ( DimTraveller[SignupDate], DATE ( 2026, 12, 31 ), DAY )', fmt="0"),
        calc_col("Tenure Band", "string",
                 'SWITCH ( TRUE(),\n'
                 '    DimTraveller[Tenure Days] >= 900, "1. Long Standing (2y+)",\n'
                 '    DimTraveller[Tenure Days] >= 540, "2. Established (1.5-2y)",\n'
                 '    DimTraveller[Tenure Days] >= 180, "3. Growing (6m-1.5y)",\n'
                 '    "4. New (<6m)" )'),
    ],
    sql_partition("DimTraveller", extra_steps=[
        '    #"Changed Type" = Table.TransformColumnTypes(dbo_DimTraveller,{{"SignupDate", type date}}),',
        '    #"Cleaned Names" = Table.TransformColumns(#"Changed Type",'
        '{{"TravellerName", each Text.Proper(Text.Trim(_)), type text}}),',
    ], final='#"Cleaned Names"'),
    hierarchies=[hierarchy("Customer Hierarchy", ["CustomerSegment", "LoyaltyTier", "TravellerName"])],
)
dim_trav["columns"][10]["sortByColumn"] = None
del dim_trav["columns"][10]["sortByColumn"]
# make LoyaltyTier sort by its numeric helper
for c in dim_trav["columns"]:
    if c["name"] == "LoyaltyTier":
        c["sortByColumn"] = "Loyalty Tier Sort"

# ---------------------------------------------------------------------------
# DimAccommodation / DimTransport / DimBookingChannel
# ---------------------------------------------------------------------------
dim_acc = table(
    "DimAccommodation",
    [
        col("AccommodationID", "int64", fmt="0", hidden=True),
        col("AccommodationName", "string"),
        col("AccommodationType", "string"),
        col("StarRating", "int64", fmt="0"),
        col("DestinationID", "int64", fmt="0", hidden=True),
        col("PriceIndex", "double", fmt=DEC2),
        col("AvgRating", "double", fmt=DEC2),
        calc_col("Star Rating Label", "string",
                 'REPT ( "*", DimAccommodation[StarRating] ) & " (" & DimAccommodation[StarRating] & ")"'),
    ],
    sql_partition("DimAccommodation"),
)

dim_trn = table(
    "DimTransport",
    [
        col("TransportID", "int64", fmt="0", hidden=True),
        col("TransportType", "string"),
        col("Carrier", "string"),
        col("TravelClass", "string"),
        col("CostFactor", "double", fmt=DEC2),
        col("IsInternationalCapable", "boolean"),
        calc_col("Carrier Class", "string",
                 'DimTransport[Carrier] & " - " & DimTransport[TravelClass]'),
    ],
    sql_partition("DimTransport"),
)

dim_chan = table(
    "DimBookingChannel",
    [
        col("ChannelID", "int64", fmt="0", hidden=True),
        col("ChannelName", "string"),
        col("ChannelType", "string"),
        col("CommissionRate", "double", fmt=PCT),
    ],
    sql_partition("DimBookingChannel"),
    hierarchies=[hierarchy("Channel Hierarchy", ["ChannelType", "ChannelName"])],
)

# ---------------------------------------------------------------------------
# FactTrip  (with Power Query transformation steps)
# ---------------------------------------------------------------------------
fact_steps = [
    '    #"Removed Blank Rows" = Table.SelectRows(dbo_FactTrip, each [TripID] <> null and [Revenue] <> null),',
    '    #"Filtered Valid Trips" = Table.SelectRows(#"Removed Blank Rows", '
    'each [DurationDays] > 0 and [NumTravellers] > 0 and [Revenue] > 0),',
    '    #"Changed Type" = Table.TransformColumnTypes(#"Filtered Valid Trips",'
    '{{"Revenue", type number}, {"NetRevenue", type number}, {"GrossAmount", type number}, '
    '{"DiscountAmount", type number}, {"SatisfactionScore", type number}}),',
    '    #"Added Satisfaction Band" = Table.AddColumn(#"Changed Type", "Satisfaction Band", '
    'each if [SatisfactionScore] = null then "Not Rated" '
    'else if [SatisfactionScore] >= 8 then "Promoter (8-10)" '
    'else if [SatisfactionScore] >= 6 then "Passive (6-7.9)" '
    'else "Detractor (<6)", type text),',
    '    #"Added Discount Pct" = Table.AddColumn(#"Added Satisfaction Band", "DiscountPct", '
    'each if [GrossAmount] = 0 then 0 else [DiscountAmount] / [GrossAmount], type number),',
    '    #"Added Traveller Days" = Table.AddColumn(#"Added Discount Pct", "TravellerDays", '
    'each [NumTravellers] * [DurationDays], Int64.Type)',
]

fact_cols = [
    col("TripID", "int64", fmt="0", hidden=True),
    col("BookingReference", "string"),
    col("TravellerID", "int64", fmt="0", hidden=True),
    col("DestinationID", "int64", fmt="0", hidden=True),
    col("AccommodationID", "int64", fmt="0", hidden=True),
    col("TransportID", "int64", fmt="0", hidden=True),
    col("ChannelID", "int64", fmt="0", hidden=True),
    col("BookingDateKey", "int64", fmt="0", hidden=True),
    col("StartDateKey", "int64", fmt="0", hidden=True),
    col("EndDateKey", "int64", fmt="0", hidden=True),
    col("DurationDays", "int64", fmt=NUM),
    col("NumTravellers", "int64", fmt=NUM),
    col("LeadTimeDays", "int64", fmt=NUM),
    col("AccommodationCost", "decimal", fmt=INR),
    col("TransportCost", "decimal", fmt=INR),
    col("ActivityCost", "decimal", fmt=INR),
    col("GrossAmount", "decimal", fmt=INR),
    col("DiscountAmount", "decimal", fmt=INR),
    col("Revenue", "decimal", fmt=INR),
    col("ChannelCommission", "decimal", fmt=INR),
    col("NetRevenue", "decimal", fmt=INR),
    col("SatisfactionScore", "double", fmt=DEC2),
    col("BookingStatus", "string"),
    col("RevenuePerTraveller", "decimal", fmt=INR),
    col("RevenuePerDay", "decimal", fmt=INR),
    col("BookingWindow", "string"),
    col("TripLengthBand", "string"),
    col("Satisfaction Band", "string"),
    col("DiscountPct", "double", fmt=PCT),
    col("TravellerDays", "int64", fmt=NUM),
    calc_col("Trip Value Category", "string",
             'SWITCH ( TRUE(),\n'
             '    FactTrip[Revenue] >= 600000, "1. Premium (6L+)",\n'
             '    FactTrip[Revenue] >= 300000, "2. High (3-6L)",\n'
             '    FactTrip[Revenue] >= 150000, "3. Mid (1.5-3L)",\n'
             '    "4. Entry (<1.5L)" )'),
    calc_col("Is Cancelled", "int64", 'IF ( FactTrip[BookingStatus] = "Cancelled", 1, 0 )', fmt="0"),
    calc_col("Trip Margin", "decimal",
             'FactTrip[NetRevenue] - FactTrip[AccommodationCost] * 0.72 '
             '- FactTrip[TransportCost] * 0.88 - FactTrip[ActivityCost] * 0.55', fmt=INR,
             desc="Estimated gross margin after supplier cost of sale."),
]

fact_measures = [
    # --- Volume -----------------------------------------------------------
    measure("Total Bookings", "COUNTROWS ( FactTrip )", NUM, "01 Volume"),
    measure("Total Travellers", "SUM ( FactTrip[NumTravellers] )", NUM, "01 Volume"),
    measure("Traveller Days", "SUM ( FactTrip[TravellerDays] )", NUM, "01 Volume"),
    measure("Distinct Travellers", "DISTINCTCOUNT ( FactTrip[TravellerID] )", NUM, "01 Volume"),
    measure("Distinct Destinations", "DISTINCTCOUNT ( FactTrip[DestinationID] )", NUM, "01 Volume"),
    measure("Completed Bookings",
            'CALCULATE ( [Total Bookings], FactTrip[BookingStatus] = "Completed" )', NUM, "01 Volume"),
    measure("Cancelled Bookings",
            'CALCULATE ( [Total Bookings], FactTrip[BookingStatus] = "Cancelled" )', NUM, "01 Volume"),

    # --- Value ------------------------------------------------------------
    measure("Total Revenue", "SUM ( FactTrip[Revenue] )", INR, "02 Value"),
    measure("Gross Amount", "SUM ( FactTrip[GrossAmount] )", INR, "02 Value"),
    measure("Net Revenue", "SUM ( FactTrip[NetRevenue] )", INR, "02 Value"),
    measure("Total Discount", "SUM ( FactTrip[DiscountAmount] )", INR, "02 Value"),
    measure("Total Commission", "SUM ( FactTrip[ChannelCommission] )", INR, "02 Value"),
    measure("Gross Margin", "SUM ( FactTrip[Trip Margin] )", INR, "02 Value"),
    measure("Revenue (Cr)", "DIVIDE ( [Total Revenue], 10000000 )", '#,0.00" Cr"', "02 Value"),
    measure("Net Revenue (Cr)", "DIVIDE ( [Net Revenue], 10000000 )", '#,0.00" Cr"', "02 Value"),

    # --- Averages / ratios ------------------------------------------------
    measure("Avg Booking Value", "DIVIDE ( [Total Revenue], [Total Bookings] )", INR, "03 Averages"),
    measure("Revenue per Traveller", "DIVIDE ( [Total Revenue], [Total Travellers] )", INR, "03 Averages"),
    measure("Avg Trip Duration", "AVERAGE ( FactTrip[DurationDays] )", DEC2, "03 Averages"),
    measure("Avg Lead Time", "AVERAGE ( FactTrip[LeadTimeDays] )", DEC2, "03 Averages"),
    measure("Avg Satisfaction", "AVERAGE ( FactTrip[SatisfactionScore] )", DEC2, "03 Averages"),
    measure("Avg Party Size", "AVERAGE ( FactTrip[NumTravellers] )", DEC2, "03 Averages"),
    measure("Cancellation Rate %", "DIVIDE ( [Cancelled Bookings], [Total Bookings] )", PCT, "04 Ratios"),
    measure("Net Margin %", "DIVIDE ( [Net Revenue], [Total Revenue] )", PCT, "04 Ratios"),
    measure("Discount Rate %", "DIVIDE ( [Total Discount], [Gross Amount] )", PCT, "04 Ratios"),
    measure("Commission Rate %", "DIVIDE ( [Total Commission], [Total Revenue] )", PCT, "04 Ratios"),
    measure("Gross Margin %", "DIVIDE ( [Gross Margin], [Total Revenue] )", PCT, "04 Ratios"),
    measure("Promoter %",
            'DIVIDE (\n'
            '    CALCULATE ( [Total Bookings], FactTrip[Satisfaction Band] = "Promoter (8-10)" ),\n'
            '    CALCULATE ( [Total Bookings], NOT ISBLANK ( FactTrip[SatisfactionScore] ) )\n'
            ')', PCT, "04 Ratios"),

    # --- Time intelligence ------------------------------------------------
    measure("Revenue YTD", "TOTALYTD ( [Total Revenue], DimDate[FullDate] )", INR, "05 Time Intelligence"),
    measure("Revenue QTD", "TOTALQTD ( [Total Revenue], DimDate[FullDate] )", INR, "05 Time Intelligence"),
    measure("Revenue PY",
            "CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( DimDate[FullDate] ) )",
            INR, "05 Time Intelligence"),
    measure("Revenue YoY", "[Total Revenue] - [Revenue PY]", INR, "05 Time Intelligence"),
    measure("Revenue YoY %", "DIVIDE ( [Revenue YoY], [Revenue PY] )", PCT, "05 Time Intelligence"),
    measure("Revenue PM",
            "CALCULATE ( [Total Revenue], PREVIOUSMONTH ( DimDate[FullDate] ) )",
            INR, "05 Time Intelligence"),
    measure("Revenue MoM %", "DIVIDE ( [Total Revenue] - [Revenue PM], [Revenue PM] )",
            PCT, "05 Time Intelligence"),
    measure("Revenue 3M Moving Avg",
            'AVERAGEX (\n'
            '    DATESINPERIOD ( DimDate[FullDate], MAX ( DimDate[FullDate] ), -3, MONTH ),\n'
            '    CALCULATE ( [Total Revenue] )\n'
            ')', INR, "05 Time Intelligence",
            desc="Three-month moving average, used to smooth the seasonal swing on the trend page."),
    measure("Revenue Rolling 12M",
            'CALCULATE (\n'
            '    [Total Revenue],\n'
            '    DATESINPERIOD ( DimDate[FullDate], MAX ( DimDate[FullDate] ), -12, MONTH )\n'
            ')', INR, "05 Time Intelligence"),
    measure("Running Total Revenue",
            'CALCULATE (\n'
            '    [Total Revenue],\n'
            '    FILTER (\n'
            '        ALLSELECTED ( DimDate[FullDate] ),\n'
            '        DimDate[FullDate] <= MAX ( DimDate[FullDate] )\n'
            '    )\n'
            ')', INR, "05 Time Intelligence"),
    measure("Bookings by Booking Date",
            'CALCULATE (\n'
            '    [Total Bookings],\n'
            '    USERELATIONSHIP ( FactTrip[BookingDateKey], DimDate[DateKey] )\n'
            ')', NUM, "05 Time Intelligence",
            desc="Uses the inactive booking-date relationship instead of the travel-date one."),

    # --- Ranking and contribution ----------------------------------------
    measure("Destination Rank",
            'IF (\n'
            '    NOT ISBLANK ( [Total Revenue] ),\n'
            '    RANKX ( ALL ( DimDestination[DestinationName] ), [Total Revenue],, DESC, DENSE )\n'
            ')', "0", "06 Ranking"),
    measure("Revenue % of Total",
            'DIVIDE ( [Total Revenue], CALCULATE ( [Total Revenue], ALLSELECTED ( DimDestination ) ) )',
            PCT, "06 Ranking"),
    measure("Top 5 Destinations Revenue",
            'CALCULATE (\n'
            '    [Total Revenue],\n'
            '    TOPN ( 5, ALL ( DimDestination[DestinationName] ), [Total Revenue], DESC )\n'
            ')', INR, "06 Ranking"),
    measure("Pareto Revenue %",
            'VAR CurrentRev = [Total Revenue]\n'
            'VAR AllDest =\n'
            '    ADDCOLUMNS ( ALLSELECTED ( DimDestination[DestinationName] ), "@Rev", [Total Revenue] )\n'
            'VAR CumRev =\n'
            '    SUMX ( FILTER ( AllDest, [@Rev] >= CurrentRev ), [@Rev] )\n'
            'VAR GrandTotal = SUMX ( AllDest, [@Rev] )\n'
            'RETURN\n'
            '    DIVIDE ( CumRev, GrandTotal )', PCT, "06 Ranking",
            desc="Cumulative share of revenue, ordered from the largest destination down."),

    # --- Targets and KPI --------------------------------------------------
    measure("Revenue Target",
            'VAR PriorYear = [Revenue PY]\n'
            'RETURN IF ( NOT ISBLANK ( PriorYear ), PriorYear * 1.15 )', INR, "07 Targets",
            desc="Business target: 15% growth on the same period last year."),
    measure("Target Variance", "[Total Revenue] - [Revenue Target]", INR, "07 Targets"),
    measure("Target Achievement %", "DIVIDE ( [Total Revenue], [Revenue Target] )", PCT, "07 Targets"),
    measure("Revenue Trend Indicator",
            'VAR G = [Revenue YoY %]\n'
            'RETURN\n'
            '    SWITCH ( TRUE(),\n'
            '        ISBLANK ( G ), "",\n'
            '        G >= 0.15, "▲ Ahead of target",\n'
            '        G >= 0,    "▲ Growing",\n'
            '        "▼ Declining" )', None, "07 Targets"),
    measure("Satisfaction Status",
            'VAR S = [Avg Satisfaction]\n'
            'RETURN\n'
            '    SWITCH ( TRUE(),\n'
            '        ISBLANK ( S ), "No ratings",\n'
            '        S >= 7, "Good",\n'
            '        S >= 6, "Acceptable",\n'
            '        "Needs attention" )', None, "07 Targets"),

    # --- What-if scenario -------------------------------------------------
    measure("Revenue at Scenario Discount",
            'VAR Adj = SELECTEDVALUE ( \'Discount Scenario\'[Discount %], 0 )\n'
            'RETURN\n'
            '    SUMX (\n'
            '        FactTrip,\n'
            '        FactTrip[GrossAmount] * ( 1 - Adj )\n'
            '    )', INR, "08 What-If",
            desc="Revenue if every booking were sold at the scenario discount instead of its actual one."),
    measure("Scenario Revenue Impact",
            "[Revenue at Scenario Discount] - [Total Revenue]", INR, "08 What-If"),

    # --- Dynamic titles ---------------------------------------------------
    measure("Dynamic Title Destination",
            '"Revenue performance - " & \n'
            '    IF ( ISFILTERED ( DimDestination[DestinationName] ),\n'
            '        CONCATENATEX ( VALUES ( DimDestination[DestinationName] ), '
            'DimDestination[DestinationName], ", " ),\n'
            '        "all destinations" )', None, "09 Titles"),
    measure("Dynamic Title Period",
            'VAR MinD = MIN ( DimDate[FullDate] )\n'
            'VAR MaxD = MAX ( DimDate[FullDate] )\n'
            'RETURN FORMAT ( MinD, "dd MMM yyyy" ) & "  to  " & FORMAT ( MaxD, "dd MMM yyyy" )',
            None, "09 Titles"),
]

fact_trip = table(
    "FactTrip",
    fact_cols,
    sql_partition("FactTrip", extra_steps=fact_steps, final='#"Added Traveller Days"'),
    measures=fact_measures,
    desc="Trip booking fact table at one row per booking, loaded from the cleaned dbo.FactTrip.",
)

# ---------------------------------------------------------------------------
# What-If parameter table (calculated)
# ---------------------------------------------------------------------------
discount_scenario = {
    "name": "Discount Scenario",
    "columns": [
        {
            "type": "calculatedTableColumn",
            "name": "Discount %",
            "dataType": "decimal",
            "isDataTypeInferred": True,
            "sourceColumn": "[Value]",
            "formatString": "0.0%",
            "summarizeBy": "none",
            "sortByColumn": "Discount %",
            "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}],
        }
    ],
    "partitions": [{
        "name": "Discount Scenario",
        "mode": "import",
        "source": {"type": "calculated", "expression": "GENERATESERIES ( 0, 0.30, 0.01 )"},
    }],
    "annotations": [
        {"name": "PBI_Id", "value": "discount_scenario"},
        {"name": "PBI_ResultType", "value": "Table"},
    ],
}
del discount_scenario["columns"][0]["sortByColumn"]

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
model = {
    "name": "TourismAnalytics",
    "compatibilityLevel": 1567,
    "model": {
        "culture": "en-IN",
        "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "discourageImplicitMeasures": False,
        "sourceQueryCulture": "en-IN",
        "expressions": [
            {
                "name": "ServerName",
                "kind": "m",
                # NB: backslash is NOT an escape character in M string literals,
                # so a single backslash here is exactly what reaches the engine.
                "expression": [
                    '"localhost\\SQLEXPRESS"',
                    'meta [IsParameterQuery=true, '
                    'List={"localhost\\SQLEXPRESS", "localhost", ".\\SQLEXPRESS", '
                    '"(localdb)\\MSSQLLocalDB"}, '
                    'DefaultValue="localhost\\SQLEXPRESS", Type="Text", '
                    'IsParameterQueryRequired=true]'
                ],
                "annotations": [{"name": "PBI_NavigationStepName", "value": "Navigation"},
                                {"name": "PBI_ResultType", "value": "Text"}],
            },
            {
                "name": "DatabaseName",
                "kind": "m",
                "expression": [
                    '"TourismDW"',
                    'meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
                ],
                "annotations": [{"name": "PBI_ResultType", "value": "Text"}],
            },
        ],
        "tables": [dim_date, dim_dest, dim_trav, dim_acc, dim_trn, dim_chan,
                   fact_trip, discount_scenario],
        "relationships": [
            rel("FactTrip", "StartDateKey",    "DimDate", "DateKey"),
            rel("FactTrip", "BookingDateKey",  "DimDate", "DateKey", active=False),
            rel("FactTrip", "EndDateKey",      "DimDate", "DateKey", active=False),
            rel("FactTrip", "DestinationID",   "DimDestination", "DestinationID"),
            rel("FactTrip", "TravellerID",     "DimTraveller", "TravellerID"),
            rel("FactTrip", "AccommodationID", "DimAccommodation", "AccommodationID"),
            rel("FactTrip", "TransportID",     "DimTransport", "TransportID"),
            rel("FactTrip", "ChannelID",       "DimBookingChannel", "ChannelID"),
            rel("DimAccommodation", "DestinationID", "DimDestination", "DestinationID", active=False),
        ],
        "annotations": [
            {"name": "PBI_QueryOrder",
             "value": json.dumps(["ServerName", "DatabaseName", "DimDate", "DimDestination",
                                  "DimTraveller", "DimAccommodation", "DimTransport",
                                  "DimBookingChannel", "FactTrip"])},
            {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            {"name": "PBI_ProTooling", "value": '["DevMode"]'},
        ],
    },
}

# Mark DimDate as the date table
for t in model["model"]["tables"]:
    if t["name"] == "DimDate":
        for c in t["columns"]:
            if c["name"] == "FullDate":
                c["isKey"] = True
        t["annotations"] = t.get("annotations", []) + [
            {"name": "PBI_MarkedDateTable", "value": "true"}]
    # DateKey should not also be a key
    if t["name"] == "DimDate":
        for c in t["columns"]:
            if c["name"] == "DateKey":
                c.pop("isKey", None)

with open(f"{SM}/model.bim", "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2, ensure_ascii=False)

n_meas = len(fact_measures)
n_calc = sum(1 for t in model["model"]["tables"] for c in t["columns"]
             if c.get("type") == "calculated")
print(f"model.bim written")
print(f"  tables        : {len(model['model']['tables'])}")
print(f"  relationships : {len(model['model']['relationships'])} "
      f"({sum(1 for r in model['model']['relationships'] if r.get('isActive') is False)} inactive)")
print(f"  measures      : {n_meas}")
print(f"  calc columns  : {n_calc}")
print(f"  hierarchies   : {sum(len(t.get('hierarchies', [])) for t in model['model']['tables'])}")
