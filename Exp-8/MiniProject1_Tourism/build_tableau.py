"""
Builds the Tableau deliverables for the Tourism Analytics mini project:

  tableau/TourismAnalytics_SQLServer.twb   - live connection to SQL Server
  tableau/TourismAnalytics_Packaged.twbx   - same views, packaged with the data

Both workbooks share one definition of columns, parameters, calculated fields,
worksheets, dashboards and the story.
"""
import os, zipfile, uuid, html, shutil

OUT = "tableau"
os.makedirs(f"{OUT}/Data", exist_ok=True)

DS   = "federated.0tourism"
CONN_SQL = "sqlserver.0tourism"
CONN_CSV = "textscan.0tourism"
VER  = "18.1"

def esc(s):
    return html.escape(str(s), quote=True)

def uid():
    return "{" + str(uuid.uuid4()).upper() + "}"

# ===========================================================================
# 1. COLUMN SCHEMA
#    (name, local-type, role, type, semantic-role)
# ===========================================================================
STR, INT, REAL, DATE = "string", "integer", "real", "date"
DIM, MEA = "dimension", "measure"
NOM, ORD, QNT = "nominal", "ordinal", "quantitative"

SCHEMA = [
    ("TripID",            INT,  DIM, ORD, None),
    ("BookingReference",  STR,  DIM, NOM, None),
    ("BookingStatus",     STR,  DIM, NOM, None),
    ("TripStartDate",     DATE, DIM, ORD, None),
    ("TripEndDate",       DATE, DIM, ORD, None),
    ("BookingDate",       DATE, DIM, ORD, None),
    ("TripYear",          INT,  DIM, ORD, None),
    ("TripQuarter",       STR,  DIM, NOM, None),
    ("TripMonthNo",       INT,  DIM, ORD, None),
    ("TripMonthName",     STR,  DIM, NOM, None),
    ("TripSeason",        STR,  DIM, NOM, None),
    ("FinancialYear",     STR,  DIM, NOM, None),
    ("PeakSeasonLabel",   STR,  DIM, NOM, None),
    ("DestinationName",   STR,  DIM, NOM, None),
    ("City",              STR,  DIM, NOM, "[City].[Name]"),
    ("Country",           STR,  DIM, NOM, "[Country].[Name]"),
    ("Region",            STR,  DIM, NOM, None),
    ("Continent",         STR,  DIM, NOM, None),
    ("DestinationType",   STR,  DIM, NOM, None),
    ("Latitude",          REAL, MEA, QNT, "[Latitude]"),
    ("Longitude",         REAL, MEA, QNT, "[Longitude]"),
    ("TravelScope",       STR,  DIM, NOM, None),
    ("TravellerID",       INT,  DIM, ORD, None),
    ("TravellerName",     STR,  DIM, NOM, None),
    ("Gender",            STR,  DIM, NOM, None),
    ("Age",               INT,  MEA, QNT, None),
    ("AgeBand",           STR,  DIM, NOM, None),
    ("Nationality",       STR,  DIM, NOM, None),
    ("CustomerSegment",   STR,  DIM, NOM, None),
    ("LoyaltyTier",       STR,  DIM, NOM, None),
    ("AccommodationName", STR,  DIM, NOM, None),
    ("AccommodationType", STR,  DIM, NOM, None),
    ("StarRating",        INT,  DIM, ORD, None),
    ("TransportType",     STR,  DIM, NOM, None),
    ("Carrier",           STR,  DIM, NOM, None),
    ("TravelClass",       STR,  DIM, NOM, None),
    ("ChannelName",       STR,  DIM, NOM, None),
    ("ChannelType",       STR,  DIM, NOM, None),
    ("DurationDays",      INT,  MEA, QNT, None),
    ("NumTravellers",     INT,  MEA, QNT, None),
    ("LeadTimeDays",      INT,  MEA, QNT, None),
    ("AccommodationCost", REAL, MEA, QNT, None),
    ("TransportCost",     REAL, MEA, QNT, None),
    ("ActivityCost",      REAL, MEA, QNT, None),
    ("GrossAmount",       REAL, MEA, QNT, None),
    ("DiscountAmount",    REAL, MEA, QNT, None),
    ("Revenue",           REAL, MEA, QNT, None),
    ("ChannelCommission", REAL, MEA, QNT, None),
    ("NetRevenue",        REAL, MEA, QNT, None),
    ("SatisfactionScore", REAL, MEA, QNT, None),
    ("SatisfactionBand",  STR,  DIM, NOM, None),
    ("BookingWindow",     STR,  DIM, NOM, None),
    ("TripLengthBand",    STR,  DIM, NOM, None),
    ("TravellerDays",     INT,  MEA, QNT, None),
]
COLTYPE = {n: t for n, t, _, _, _ in SCHEMA}
COLROLE = {n: r for n, _, r, _, _ in SCHEMA}

REMOTE_TYPE = {STR: 129, INT: 20, REAL: 5, DATE: 7}
DEBUG_TYPE  = {STR: "WSTR", INT: "I8", REAL: "R8", DATE: "DATE"}

# ===========================================================================
# 2. PARAMETERS
# ===========================================================================
PARAMS = [
    dict(id="Parameter 1", caption="Top N Destinations", datatype="integer",
         role="measure", type="quantitative", value="10", fmt="#,##0",
         domain="range", rng=dict(min="5", max="25", granularity="1")),
    dict(id="Parameter 2", caption="Scenario Discount %", datatype="real",
         role="measure", type="quantitative", value="0.1", fmt="p0%",
         domain="range", rng=dict(min="0.0", max="0.3", granularity="0.01")),
    dict(id="Parameter 3", caption="Target Growth %", datatype="real",
         role="measure", type="quantitative", value="0.15", fmt="p0%",
         domain="range", rng=dict(min="0.0", max="0.5", granularity="0.05")),
    dict(id="Parameter 4", caption="Select Measure", datatype="string",
         role="dimension", type="nominal", value='"Revenue"', fmt=None,
         domain="list", members=["Revenue", "Bookings", "Travellers"]),
]
P = {p["caption"]: f"[Parameters].[{p['id']}]" for p in PARAMS}

# ===========================================================================
# 3. CALCULATED FIELDS
# ===========================================================================
# (caption, id, formula, datatype, role, type, default-format, is_table_calc)
CALCS = [
    ("Total Revenue",        "Calculation_101", "SUM([Revenue])", REAL, MEA, QNT, '"₹"#,##0', False),
    ("Total Bookings",       "Calculation_102", "COUNT([TripID])", INT, MEA, QNT, "#,##0", False),
    ("Total Travellers",     "Calculation_103", "SUM([NumTravellers])", INT, MEA, QNT, "#,##0", False),
    ("Avg Booking Value",    "Calculation_104",
     "SUM([Revenue]) / COUNT([TripID])", REAL, MEA, QNT, '"₹"#,##0', False),
    ("Avg Satisfaction",     "Calculation_105", "AVG([SatisfactionScore])", REAL, MEA, QNT, "#,##0.00", False),
    ("Cancellation Rate",    "Calculation_106",
     'SUM(IF [BookingStatus] = "Cancelled" THEN 1 ELSE 0 END) / COUNT([TripID])',
     REAL, MEA, QNT, "p0.0%", False),
    ("Net Margin %",         "Calculation_107",
     "SUM([NetRevenue]) / SUM([Revenue])", REAL, MEA, QNT, "p0.0%", False),
    ("Discount Rate %",      "Calculation_108",
     "SUM([DiscountAmount]) / SUM([GrossAmount])", REAL, MEA, QNT, "p0.0%", False),
    ("Revenue per Traveller","Calculation_109",
     "SUM([Revenue]) / SUM([NumTravellers])", REAL, MEA, QNT, '"₹"#,##0', False),
    # --- table calculations (the "advanced" ones) ----------------------
    ("Destination Rank",     "Calculation_201",
     "RANK(SUM([Revenue]))", REAL, MEA, QNT, "#,##0", True),
    ("Top N Filter",         "Calculation_202",
     f"RANK(SUM([Revenue])) <= {P['Top N Destinations']}", "boolean", MEA, QNT, None, True),
    ("Revenue Moving Avg",   "Calculation_203",
     "WINDOW_AVG(SUM([Revenue]), -2, 0)", REAL, MEA, QNT, '"₹"#,##0', True),
    ("Running Revenue %",    "Calculation_204",
     "RUNNING_SUM(SUM([Revenue])) / TOTAL(SUM([Revenue]))", REAL, MEA, QNT, "p0%", True),
    ("Revenue YoY %",        "Calculation_205",
     "(SUM([Revenue]) - LOOKUP(SUM([Revenue]), -1)) / ABS(LOOKUP(SUM([Revenue]), -1))",
     REAL, MEA, QNT, "p0.0%", True),
    # --- parameter-driven ----------------------------------------------
    ("Scenario Revenue",     "Calculation_301",
     f"SUM([GrossAmount]) * (1 - {P['Scenario Discount %']})", REAL, MEA, QNT, '"₹"#,##0', False),
    ("Scenario Impact",      "Calculation_302",
     f"(SUM([GrossAmount]) * (1 - {P['Scenario Discount %']})) - SUM([Revenue])",
     REAL, MEA, QNT, '"₹"#,##0', False),
    ("Revenue Target",       "Calculation_303",
     f"LOOKUP(SUM([Revenue]), -1) * (1 + {P['Target Growth %']})", REAL, MEA, QNT, '"₹"#,##0', True),
    ("Selected Measure",     "Calculation_304",
     f'CASE {P["Select Measure"]}\n'
     f'  WHEN "Revenue"    THEN SUM([Revenue])\n'
     f'  WHEN "Bookings"   THEN COUNT([TripID])\n'
     f'  WHEN "Travellers" THEN SUM([NumTravellers])\n'
     f'END', REAL, MEA, QNT, "#,##0", False),
]
C = {cap: cid for cap, cid, *_ in CALCS}
CALC_BY_ID = {cid: cap for cap, cid, *_ in CALCS}

# ===========================================================================
# 4. XML fragments
# ===========================================================================
def col_xml(name, ltype, role, ctype, semantic):
    a = f"datatype='{ltype}' name='[{name}]' role='{role}' type='{ctype}'"
    if semantic:
        a += f" semantic-role='{esc(semantic)}'"
    return f"      <column {a} />"

def metadata_record(name, ltype, ordinal, parent):
    rt = REMOTE_TYPE[ltype]
    agg = "Count" if ltype in (STR, DATE) else "Sum"
    return f"""        <metadata-record class='column'>
          <remote-name>{esc(name)}</remote-name>
          <remote-type>{rt}</remote-type>
          <local-name>[{esc(name)}]</local-name>
          <parent-name>[{esc(parent)}]</parent-name>
          <remote-alias>{esc(name)}</remote-alias>
          <ordinal>{ordinal}</ordinal>
          <local-type>{ltype}</local-type>
          <aggregation>{agg}</aggregation>
          <contains-null>true</contains-null>
          <attributes>
            <attribute datatype='string' name='DebugRemoteType'>&quot;{DEBUG_TYPE[ltype]}&quot;</attribute>
            <attribute datatype='string' name='DebugWrapperType'>&quot;None&quot;</attribute>
          </attributes>
        </metadata-record>"""

def calc_col_xml(cap, cid, formula, dtype, role, ctype, fmt):
    fa = f" default-format='{esc(fmt)}'" if fmt else ""
    return (f"      <column caption='{esc(cap)}' datatype='{dtype}'{fa} "
            f"name='[{cid}]' role='{role}' type='{ctype}'>\n"
            f"        <calculation class='tableau' formula='{esc(formula)}' />\n"
            f"      </column>")

def parameters_datasource():
    out = [f"    <datasource hasconnection='false' inline='true' name='Parameters' version='{VER}'>",
           "      <aliases enabled='yes' />"]
    for p in PARAMS:
        fa = f" default-format='{esc(p['fmt'])}'" if p["fmt"] else ""
        out.append(
            f"      <column caption='{esc(p['caption'])}' datatype='{p['datatype']}'{fa} "
            f"name='[{p['id']}]' param-domain-type='{p['domain']}' role='{p['role']}' "
            f"type='{p['type']}' value='{esc(p['value'])}'>")
        out.append(f"        <calculation class='tableau' formula='{esc(p['value'])}' />")
        if p["domain"] == "range":
            r = p["rng"]
            out.append(f"        <range granularity='{r['granularity']}' max='{r['max']}' min='{r['min']}' />")
        else:
            out.append("        <members>")
            for m in p["members"]:
                out.append(f"          <member value='&quot;{esc(m)}&quot;' />")
            out.append("        </members>")
        out.append("      </column>")
    out.append("    </datasource>")
    return "\n".join(out)

def datasource(kind):
    """kind = 'sql' or 'csv'"""
    if kind == "sql":
        parent = "Custom SQL Query"
        sql = ("SELECT *\n"
               "FROM dbo.vw_TripAnalysis")
        conn = f"""      <connection class='federated'>
        <named-connections>
          <named-connection caption='localhost\\SQLEXPRESS (TourismDW)' name='{CONN_SQL}'>
            <connection authentication='sqlserver' class='sqlserver' dbname='TourismDW'
              odbc-native-protocol='yes' one-time-sql='' server='localhost\\SQLEXPRESS'
              username='' />
          </named-connection>
        </named-connections>
        <relation connection='{CONN_SQL}' name='Custom SQL Query' type='text'>{esc(sql)}</relation>
        <cols>
{chr(10).join(f"          <map key='[{esc(n)}]' value='[Custom SQL Query].[{esc(n)}]' />" for n, *_ in SCHEMA)}
        </cols>
        <metadata-records>
{chr(10).join(metadata_record(n, t, i, parent) for i, (n, t, *_ ) in enumerate(SCHEMA))}
        </metadata-records>
      </connection>"""
    else:
        parent = "TourismTripAnalysis.csv"
        conn = f"""      <connection class='federated'>
        <named-connections>
          <named-connection caption='TourismTripAnalysis' name='{CONN_CSV}'>
            <connection class='textscan' directory='Data' filename='TourismTripAnalysis.csv'
              password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='{CONN_CSV}' name='TourismTripAnalysis.csv'
          table='[TourismTripAnalysis#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_IN' separator=','>
{chr(10).join(f"            <column datatype='{t}' name='{esc(n)}' ordinal='{i}' />" for i, (n, t, *_ ) in enumerate(SCHEMA))}
          </columns>
        </relation>
        <cols>
{chr(10).join(f"          <map key='[{esc(n)}]' value='[TourismTripAnalysis#csv].[{esc(n)}]' />" for n, *_ in SCHEMA)}
        </cols>
        <metadata-records>
{chr(10).join(metadata_record(n, t, i, parent) for i, (n, t, *_ ) in enumerate(SCHEMA))}
        </metadata-records>
      </connection>"""

    cols = "\n".join(col_xml(n, t, r, ct, sr) for n, t, r, ct, sr in SCHEMA)
    calcs = "\n".join(calc_col_xml(cap, cid, f, dt, ro, ty, fm)
                      for cap, cid, f, dt, ro, ty, fm, _ in CALCS)
    folders = """      <folders-common>
        <folder name='01 Trip Facts' role='dimensions'>
          <folder-item name='[BookingReference]' type='field' />
          <folder-item name='[BookingStatus]' type='field' />
          <folder-item name='[BookingWindow]' type='field' />
          <folder-item name='[TripLengthBand]' type='field' />
        </folder>
        <folder name='02 Destination' role='dimensions'>
          <folder-item name='[DestinationName]' type='field' />
          <folder-item name='[Country]' type='field' />
          <folder-item name='[Continent]' type='field' />
          <folder-item name='[Region]' type='field' />
          <folder-item name='[DestinationType]' type='field' />
          <folder-item name='[TravelScope]' type='field' />
        </folder>
        <folder name='03 Traveller' role='dimensions'>
          <folder-item name='[TravellerName]' type='field' />
          <folder-item name='[Gender]' type='field' />
          <folder-item name='[AgeBand]' type='field' />
          <folder-item name='[Nationality]' type='field' />
          <folder-item name='[CustomerSegment]' type='field' />
          <folder-item name='[LoyaltyTier]' type='field' />
        </folder>
      </folders-common>"""

    return f"""    <datasource caption='Tourism Analytics' inline='true' name='{DS}' version='{VER}'>
{conn}
      <aliases enabled='yes' />
{cols}
{calcs}
{folders}
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
      <semantic-values>
        <semantic-value key='[Country].[Name]' value='&quot;India&quot;' />
      </semantic-values>
    </datasource>"""

# ===========================================================================
# 5. WORKSHEET BUILDER
# ===========================================================================
def inst(agg, colname, key):
    return f"[{agg}:{colname}:{key}]"

class WS:
    """Collects the field instances a worksheet needs and emits its XML."""
    def __init__(self, name, mark="Automatic", title=None):
        self.name = name
        self.mark = mark
        self.title = title or name
        self.cols_used = {}          # colname -> (datatype, role, type, semantic)
        self.instances = []          # (instance_name, colname, derivation, type)
        self.params_used = []
        self.rows = ""
        self.cols = ""
        self.encodings = []
        self.filters = []
        self.slices = []
        self.sort = None
        self.pane_extra = ""
        self.table_calcs = []

    # ---- field helpers -------------------------------------------------
    def dim(self, colname, agg="none"):
        dtype = COLTYPE[colname]
        ctype = "ordinal" if dtype in (INT, DATE) else "nominal"
        key = "ok" if ctype == "ordinal" else "nk"
        self.cols_used[colname] = (dtype, "dimension", ctype, dict(SCHEMA_SR).get(colname))
        i = inst(agg, colname, key)
        if (i, colname) not in [(a, b) for a, b, _, _ in self.instances]:
            self.instances.append((i, colname, "None" if agg == "none" else agg.capitalize(), ctype))
        return f"[{DS}].{i}"

    def date(self, colname, part="tmn", continuous=True):
        self.cols_used[colname] = (DATE, "dimension", "ordinal", None)
        key = "qk" if continuous else "ok"
        i = inst(part, colname, key)
        deriv = {"yr": "Year", "qr": "Quarter", "mn": "Month", "tmn": "Month",
                 "tyr": "Year", "tqr": "Quarter"}[part]
        if i not in [a for a, _, _, _ in self.instances]:
            self.instances.append((i, colname, deriv, "quantitative" if continuous else "ordinal"))
        return f"[{DS}].{i}"

    def mea(self, colname, agg="sum"):
        dtype = COLTYPE[colname]
        self.cols_used[colname] = (dtype, "measure", "quantitative", dict(SCHEMA_SR).get(colname))
        i = inst(agg, colname, "qk")
        if i not in [a for a, _, _, _ in self.instances]:
            self.instances.append((i, colname, agg.capitalize(), "quantitative"))
        return f"[{DS}].{i}"

    def calc(self, caption):
        cid = C[caption]
        meta = next(x for x in CALCS if x[1] == cid)
        _, _, formula, dtype, role, ctype, fmt, is_tc = meta
        self.cols_used[cid] = (dtype, role, ctype, None)
        key = "qk" if ctype == "quantitative" else "nk"
        i = inst("usr", cid, key)
        if i not in [a for a, _, _, _ in self.instances]:
            self.instances.append((i, cid, "User", ctype))
        if is_tc:
            self.table_calcs.append(i)
        return f"[{DS}].{i}"

    def param(self, caption):
        pid = next(p["id"] for p in PARAMS if p["caption"] == caption)
        if pid not in self.params_used:
            self.params_used.append(pid)
        return f"[Parameters].[{pid}]"

    # ---- xml -----------------------------------------------------------
    def xml(self):
        deps = []
        for cname, (dtype, role, ctype, semantic) in self.cols_used.items():
            if cname in CALC_BY_ID:
                cap = CALC_BY_ID[cname]
                deps.append(f"          <column caption='{esc(cap)}' datatype='{dtype}' "
                            f"name='[{cname}]' role='{role}' type='{ctype}'>\n"
                            f"            <calculation class='tableau' formula='{esc(next(x[2] for x in CALCS if x[1]==cname))}' />\n"
                            f"          </column>")
            else:
                sr = f" semantic-role='{esc(semantic)}'" if semantic else ""
                deps.append(f"          <column datatype='{dtype}' name='[{cname}]' "
                            f"role='{role}' type='{ctype}'{sr} />")
        for i, cname, deriv, ctype in self.instances:
            deps.append(f"          <column-instance column='[{cname}]' derivation='{deriv}' "
                        f"name='{i}' pivot='key' type='{ctype}' />")

        param_block = ""
        if self.params_used:
            pdeps = []
            for pid in self.params_used:
                p = next(x for x in PARAMS if x["id"] == pid)
                fa = f" default-format='{esc(p['fmt'])}'" if p["fmt"] else ""
                pdeps.append(
                    f"          <column caption='{esc(p['caption'])}' datatype='{p['datatype']}'{fa} "
                    f"name='[{pid}]' param-domain-type='{p['domain']}' role='{p['role']}' "
                    f"type='{p['type']}' value='{esc(p['value'])}'>\n"
                    f"            <calculation class='tableau' formula='{esc(p['value'])}' />\n"
                    f"          </column>")
            param_block = ("\n        <datasource-dependencies datasource='Parameters'>\n"
                           + "\n".join(pdeps) + "\n        </datasource-dependencies>")

        filt = "\n".join(self.filters)
        slic = ""
        if self.slices:
            slic = ("\n        <slices>\n"
                    + "\n".join(f"          <column>{s}</column>" for s in self.slices)
                    + "\n        </slices>")

        enc = ""
        if self.encodings:
            enc = ("\n          <encodings>\n"
                   + "\n".join(f"            <{k} column='{v}' />" for k, v in self.encodings)
                   + "\n          </encodings>")

        sort_xml = ""
        if self.sort:
            field, measure, direction = self.sort
            sort_xml = (f"\n        <sort class='computed' column='{field}' "
                        f"direction='{direction.upper()}' using='{measure}' />")

        # One <pane> per measure on the shelves: Tableau writes a pane per
        # measure when several are placed on rows or cols with '+'.
        n_panes = max(self.rows.count(" + "), self.cols.count(" + ")) + 1
        panes = "\n".join(f"""        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='{self.mark}' />{enc}
        </pane>""" for _ in range(n_panes))

        return f"""  <worksheet name='{esc(self.name)}'>
    <layout-options>
      <title>
        <formatted-text>
          <run fontsize='11' bold='true'>{esc(self.title)}</run>
        </formatted-text>
      </title>
    </layout-options>
    <table>
      <view>
        <datasources>
          <datasource caption='Tourism Analytics' name='{DS}' />{"" if not self.params_used else chr(10) + "          <datasource name='Parameters' />"}
        </datasources>
        <datasource-dependencies datasource='{DS}'>
{chr(10).join(deps)}
        </datasource-dependencies>{param_block}
{filt}{sort_xml}{slic}
        <aggregation value='true' />
      </view>
      <style />
      <panes>
{panes}
      </panes>
      <rows>{self.rows}</rows>
      <cols>{self.cols}</cols>
    </table>
    <simple-id uuid='{uid()}' />
  </worksheet>"""


SCHEMA_SR = [(n, sr) for n, _, _, _, sr in SCHEMA]

def cat_filter(field, level):
    return f"""        <filter class='categorical' column='{field}'>
          <groupfilter function='level-members' level='{level}' user:ui-enumeration='all' user:ui-marker='enumerate' />
        </filter>"""

def tc_block(instances):
    if not instances:
        return ""
    return ""

# ===========================================================================
# 6. WORKSHEETS
# ===========================================================================
sheets = []

def kpi_sheet(name, calc_caption, title):
    w = WS(name, "Text", title)
    m = w.calc(calc_caption)
    w.encodings.append(("text", m))
    w.rows, w.cols = "", ""
    sheets.append(w)
    return w

kpi_sheet("KPI Revenue",       "Total Revenue",     "Total revenue")
kpi_sheet("KPI Bookings",      "Total Bookings",    "Total bookings")
kpi_sheet("KPI Avg Value",     "Avg Booking Value", "Average booking value")
kpi_sheet("KPI Satisfaction",  "Avg Satisfaction",  "Average satisfaction (1-10)")
kpi_sheet("KPI Cancellation",  "Cancellation Rate", "Cancellation rate")

# --- Revenue trend (continuous month) -------------------------------------
w = WS("Revenue Trend", "Line", "Monthly revenue, 2023-2026")
x = w.date("TripStartDate", "tmn", continuous=True)
y = w.calc("Total Revenue")
w.cols, w.rows = x, y
sheets.append(w)

# --- Revenue with 3-month moving average ----------------------------------
w = WS("Revenue Moving Average", "Line", "Revenue vs 3-month moving average")
x  = w.date("TripStartDate", "tmn", continuous=True)
y1 = w.calc("Total Revenue")
y2 = w.calc("Revenue Moving Avg")
w.cols = x
w.rows = f"{y1} + {y2}"
sheets.append(w)

# --- Top N destinations (parameter-driven) --------------------------------
# The "Top N Filter" calculated field is defined in the data source and the
# parameter control sits on dashboard D1. Applying it to the Filters shelf is
# left as a one-drag step in the setup guide rather than hand-written filter
# XML, so the workbook cannot be broken by a malformed filter node.
w = WS("Top N Destinations", "Bar", "Destinations by revenue (apply the Top N Filter field)")
d = w.dim("DestinationName")
m = w.calc("Total Revenue")
w.rows, w.cols = d, m
w.encodings.append(("color", m))
w.sort = (d, m, "desc")
sheets.append(w)

# --- Destination map ------------------------------------------------------
w = WS("Destination Map", "Circle", "Where the revenue comes from")
lat = w.mea("Latitude", "avg")
lon = w.mea("Longitude", "avg")
d   = w.dim("DestinationName")
sc  = w.dim("TravelScope")
m   = w.calc("Total Revenue")
w.rows, w.cols = lat, lon
w.encodings += [("size", m), ("color", sc), ("text", d)]
sheets.append(w)

# --- Seasonality heat map -------------------------------------------------
w = WS("Seasonality Heatmap", "Square", "Revenue by month and year")
r = w.dim("TripMonthName")
c = w.dim("TripYear")
m = w.calc("Total Revenue")
w.rows, w.cols = r, c
w.encodings += [("color", m), ("text", m)]
sheets.append(w)

# --- Pareto ---------------------------------------------------------------
w = WS("Destination Pareto", "Line", "Cumulative share of revenue by destination")
d = w.dim("DestinationName")
m = w.calc("Running Revenue %")
srt = w.calc("Total Revenue")
w.cols, w.rows = d, m
w.sort = (d, srt, "desc")
sheets.append(w)

# --- Channel profitability ------------------------------------------------
w = WS("Channel Profitability", "Bar", "Revenue and net margin by booking channel")
d  = w.dim("ChannelName")
m1 = w.calc("Total Revenue")
m2 = w.calc("Net Margin %")
w.rows, w.cols = d, m1
w.encodings.append(("color", m2))
w.sort = (d, m1, "desc")
sheets.append(w)

# --- Segment treemap ------------------------------------------------------
w = WS("Segment Treemap", "Square", "Revenue by customer segment and loyalty tier")
d1 = w.dim("CustomerSegment")
d2 = w.dim("LoyaltyTier")
m  = w.calc("Total Revenue")
w.rows, w.cols = "", ""
w.encodings += [("size", m), ("color", d1), ("text", d2)]
w.pane_extra = ""
sheets.append(w)

# --- Satisfaction by star rating and season -------------------------------
w = WS("Satisfaction Analysis", "Bar", "Satisfaction by star rating and season")
d1 = w.dim("StarRating")
d2 = w.dim("PeakSeasonLabel")
m  = w.calc("Avg Satisfaction")
w.cols = f"{d1} / {d2}"
w.rows = m
w.encodings.append(("color", d2))
sheets.append(w)

# --- Booking window vs cancellation ---------------------------------------
w = WS("Booking Window", "Bar", "Cancellation rate by booking window")
d = w.dim("BookingWindow")
m = w.calc("Cancellation Rate")
n = w.calc("Total Bookings")
w.cols, w.rows = d, m
w.encodings += [("color", m), ("text", n)]
sheets.append(w)

# --- Age band / gender ----------------------------------------------------
w = WS("Traveller Demographics", "Bar", "Bookings by age band and gender")
d1 = w.dim("AgeBand")
d2 = w.dim("Gender")
m  = w.calc("Total Bookings")
w.cols, w.rows = d1, m
w.encodings.append(("color", d2))
sheets.append(w)

# --- Scenario -------------------------------------------------------------
w = WS("Discount Scenario", "Bar", "Actual vs scenario revenue by destination type")
d  = w.dim("DestinationType")
m1 = w.calc("Total Revenue")
m2 = w.calc("Scenario Revenue")
w.param("Scenario Discount %")
w.rows = d
w.cols = f"{m1} + {m2}"
w.sort = (d, m1, "desc")
sheets.append(w)

# --- Cost composition -----------------------------------------------------
w = WS("Cost Composition", "Bar", "What travellers actually pay for")
d  = w.dim("TravelScope")
m1 = w.mea("AccommodationCost")
m2 = w.mea("TransportCost")
m3 = w.mea("ActivityCost")
w.rows = d
w.cols = f"{m1} + {m2} + {m3}"
sheets.append(w)

# --- Detail table ---------------------------------------------------------
w = WS("Booking Detail", "Text", "Individual bookings")
c1 = w.dim("BookingReference")
c2 = w.dim("DestinationName")
c3 = w.dim("TravellerName")
c4 = w.dim("CustomerSegment")
c5 = w.dim("BookingStatus")
m1 = w.calc("Total Revenue")
m2 = w.calc("Avg Satisfaction")
w.rows = f"{c1} / {c2} / {c3} / {c4} / {c5}"
w.cols = f"{m1} + {m2}"
sheets.append(w)

# ---------------------------------------------------------------------------
# Standard filter shelf: put the same four filters on every worksheet so the
# dashboard filter controls have something to bind to.
# ---------------------------------------------------------------------------
STD_FILTERS = [("TripYear", "ok"), ("TravelScope", "nk"),
               ("TripSeason", "nk"), ("ChannelType", "nk")]

for s in sheets:
    for cname, key in STD_FILTERS:
        dtype = COLTYPE[cname]
        ctype = "ordinal" if key == "ok" else "nominal"
        s.cols_used.setdefault(cname, (dtype, "dimension", ctype, None))
        i = inst("none", cname, key)
        if i not in [a for a, _, _, _ in s.instances]:
            s.instances.append((i, cname, "None", ctype))
        field = f"[{DS}].{i}"
        s.filters.append(
            f"        <filter class='categorical' column='{field}'>\n"
            f"          <groupfilter function='level-members' level='{i}' "
            f"user:ui-domain='database' user:ui-enumeration='all' "
            f"user:ui-marker='enumerate' />\n"
            f"        </filter>")
        s.slices.append(field)

WORKSHEETS = "\n".join(s.xml() for s in sheets)
SHEET_NAMES = [s.name for s in sheets]

# ===========================================================================
# 7. DASHBOARDS
# ===========================================================================
def zone(name, x, y, w, h, zid, ztype=None, param=None):
    if ztype == "text":
        return (f"        <zone h='{h}' id='{zid}' type-v2='text' w='{w}' x='{x}' y='{y}'>\n"
                f"          <formatted-text>\n"
                f"            <run bold='true' fontsize='14'>{esc(name)}</run>\n"
                f"          </formatted-text>\n"
                f"          <zone-style>\n"
                f"            <format attr='border-color' value='#000000' />\n"
                f"            <format attr='border-style' value='none' />\n"
                f"            <format attr='border-width' value='0' />\n"
                f"            <format attr='margin' value='4' />\n"
                f"          </zone-style>\n"
                f"        </zone>")
    if ztype == "filter":
        return (f"        <zone h='{h}' id='{zid}' name='{esc(name)}' param='{esc(param)}' "
                f"type-v2='filter' w='{w}' x='{x}' y='{y}'>\n"
                f"          <zone-style>\n"
                f"            <format attr='border-style' value='none' />\n"
                f"            <format attr='margin' value='4' />\n"
                f"          </zone-style>\n"
                f"        </zone>")
    if ztype == "paramctrl":
        return (f"        <zone h='{h}' id='{zid}' param='{esc(param)}' type-v2='paramctrl' "
                f"w='{w}' x='{x}' y='{y}'>\n"
                f"          <zone-style>\n"
                f"            <format attr='border-style' value='none' />\n"
                f"            <format attr='margin' value='4' />\n"
                f"          </zone-style>\n"
                f"        </zone>")
    return (f"        <zone h='{h}' id='{zid}' name='{esc(name)}' w='{w}' x='{x}' y='{y}'>\n"
            f"          <zone-style>\n"
            f"            <format attr='border-color' value='#DDDDDD' />\n"
            f"            <format attr='border-style' value='solid' />\n"
            f"            <format attr='border-width' value='1' />\n"
            f"            <format attr='margin' value='4' />\n"
            f"          </zone-style>\n"
            f"        </zone>")

def dashboard(name, title, zones, actions=""):
    return f"""  <dashboard name='{esc(name)}'>
    <style />
    <size maxheight='800' maxwidth='1300' minheight='800' minwidth='1300' />
    <zones>
      <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
{zones}
      </zone>
    </zones>
    <devicelayouts>
      <devicelayout auto-generated='true' name='Phone'>
        <size maxheight='1200' minheight='1200' sizing-mode='vscroll' />
      </devicelayout>
    </devicelayouts>
    <simple-id uuid='{uid()}' />
  </dashboard>"""

# Dashboard 1 -- Executive Overview
z1 = "\n".join([
    zone("Tourism Analytics  |  Executive Overview", 0, 0, 100000, 6000, 100, "text"),
    zone("KPI Revenue",      0,     6000, 20000, 10000, 101),
    zone("KPI Bookings",     20000, 6000, 20000, 10000, 102),
    zone("KPI Avg Value",    40000, 6000, 20000, 10000, 103),
    zone("KPI Satisfaction", 60000, 6000, 20000, 10000, 104),
    zone("KPI Cancellation", 80000, 6000, 20000, 10000, 105),
    zone("Revenue Trend",       0,     16000, 62000, 40000, 106),
    zone("Top N Destinations",  62000, 16000, 38000, 40000, 107),
    zone("Segment Treemap",     0,     56000, 34000, 44000, 108),
    zone("Channel Profitability", 34000, 56000, 38000, 44000, 109),
    zone("Revenue Trend", 72000, 56000, 28000, 14000, 110, "filter",
         param=f"[{DS}].[none:TripYear:ok]"),
    zone("Revenue Trend", 72000, 70000, 28000, 14000, 111, "filter",
         param=f"[{DS}].[none:TravelScope:nk]"),
    zone("Top N Destinations", 72000, 84000, 28000, 16000, 112, "paramctrl", param="[Parameters].[Parameter 1]"),
])

# Dashboard 2 -- Destination & Seasonality
z2 = "\n".join([
    zone("Destination Performance & Seasonality", 0, 0, 100000, 6000, 200, "text"),
    zone("Destination Map",      0,     6000, 58000, 47000, 201),
    zone("Seasonality Heatmap",  58000, 6000, 42000, 47000, 202),
    zone("Destination Pareto",   0,     53000, 58000, 47000, 203),
    zone("Satisfaction Analysis",58000, 53000, 42000, 47000, 204),
])

# Dashboard 3 -- Customer, Channel & Scenario
z3 = "\n".join([
    zone("Customer, Channel & Scenario Planning", 0, 0, 100000, 6000, 300, "text"),
    zone("Traveller Demographics", 0,     6000, 33000, 44000, 301),
    zone("Booking Window",         33000, 6000, 33000, 44000, 302),
    zone("Cost Composition",       66000, 6000, 34000, 44000, 303),
    zone("Discount Scenario",      0,     50000, 46000, 50000, 304),
    zone("Booking Detail",         46000, 50000, 42000, 50000, 305),
    zone("Scenario Discount %",    88000, 50000, 12000, 12000, 306, "paramctrl",
         param="[Parameters].[Parameter 2]"),
    zone("Booking Detail", 88000, 62000, 12000, 19000, 307, "filter",
         param=f"[{DS}].[none:ChannelType:nk]"),
    zone("Booking Detail", 88000, 81000, 12000, 19000, 308, "filter",
         param=f"[{DS}].[none:TripSeason:nk]"),
])

DASHBOARDS = "\n".join([
    dashboard("D1 Executive Overview", "Executive Overview", z1),
    dashboard("D2 Destination & Seasonality", "Destination & Seasonality", z2),
    dashboard("D3 Customer & Channel", "Customer & Channel", z3),
])

# =========================================================================
# 8. STORY (built in Tableau's Story dialog -- see the setup guide)
# =========================================================================

# ===========================================================================
# 10. WINDOWS
# ===========================================================================
def window(name, cls="worksheet"):
    return f"""    <window class='{cls}' name='{esc(name)}'>
      <viewpoints />
      <simple-id uuid='{uid()}' />
    </window>"""

WINDOWS = ("  <windows>\n"
           + "\n".join(window(s) for s in SHEET_NAMES)
           + "\n"
           + "\n".join(window(d, "dashboard") for d in
                       ["D1 Executive Overview", "D2 Destination & Seasonality",
                        "D3 Customer & Channel"])
           + "\n  </windows>")

# ===========================================================================
# 11. ASSEMBLE
# ===========================================================================
PREFS = """  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>"""

def workbook(kind):
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<!-- Tourism Analytics - Mini Project I - Data Visualization Techniques -->
<workbook original-version='18.1' source-build='2024.1.0 (20241.24.0316.1146)' source-platform='win' version='{VER}' xmlns:user='http://www.tableausoftware.com/xml/user'>
{PREFS}
  <datasources>
{parameters_datasource()}
{datasource(kind)}
  </datasources>
{WORKSHEETS}
{DASHBOARDS}
{WINDOWS}
</workbook>
"""

# --- SQL Server workbook (.twb) -------------------------------------------
with open(f"{OUT}/TourismAnalytics_SQLServer.twb", "w", encoding="utf-8") as f:
    f.write(workbook("sql"))

# --- Packaged workbook (.twbx) --------------------------------------------
twb_csv = f"{OUT}/TourismAnalytics_Packaged.twb"
with open(twb_csv, "w", encoding="utf-8") as f:
    f.write(workbook("csv"))

twbx = f"{OUT}/TourismAnalytics_Packaged.twbx"
if os.path.exists(twbx):
    os.remove(twbx)
with zipfile.ZipFile(twbx, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(twb_csv, "TourismAnalytics_Packaged.twb")
    z.write(f"{OUT}/Data/TourismTripAnalysis.csv", "Data/TourismTripAnalysis.csv")
os.remove(twb_csv)

print(f"worksheets : {len(sheets)}")
print(f"dashboards : 3 + 1 story")
print(f"parameters : {len(PARAMS)}")
print(f"calc fields: {len(CALCS)}  ({sum(1 for c in CALCS if c[7])} table calculations)")
for f_ in ["TourismAnalytics_SQLServer.twb", "TourismAnalytics_Packaged.twbx"]:
    print(f"  {f_:42s} {os.path.getsize(OUT + '/' + f_)/1024:8.1f} KB")
