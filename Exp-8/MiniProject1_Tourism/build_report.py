"""
Builds the Power BI report (legacy report.json layout) for the Tourism
Analytics mini project, plus the PBIP wrapper files.
"""
import json, os, itertools

ROOT   = "powerbi"
NAME   = "TourismAnalytics"
REPORT = f"{ROOT}/{NAME}.Report"
SMODEL = f"{ROOT}/{NAME}.SemanticModel"
os.makedirs(REPORT, exist_ok=True)
os.makedirs(f"{REPORT}/StaticResources/RegisteredResources", exist_ok=True)

W, H = 1280, 720

# palette
INK   = "#1B2A41"
ACC   = "#0E7C7B"
ACC2  = "#F2A65A"
ACC3  = "#7A6FF0"
BG    = "#F4F6F8"
CARD  = "#FFFFFF"
MUTE  = "#5C6B7A"

_ids = itertools.count(1)
def vid(page, kind):
    return f"v{page}{kind}{next(_ids):04d}"

# ---------------------------------------------------------------------------
# expression helpers -- build the prototypeQuery pieces
# ---------------------------------------------------------------------------
ENTITY_ALIAS = {
    "DimDate": "d", "DimDestination": "ds", "DimTraveller": "t",
    "DimAccommodation": "a", "DimTransport": "tr", "DimBookingChannel": "c",
    "FactTrip": "f", "Discount Scenario": "sc",
}

class Q:
    """Accumulates From/Select entries for one visual's prototypeQuery."""
    def __init__(self):
        self.froms = {}
        self.selects = []
        self.refs = []

    def _src(self, entity):
        alias = ENTITY_ALIAS[entity]
        self.froms[alias] = entity
        return alias

    def column(self, entity, prop):
        a = self._src(entity)
        name = f"{entity}.{prop}"
        if name not in self.refs:
            self.selects.append({
                "Column": {"Expression": {"SourceRef": {"Source": a}}, "Property": prop},
                "Name": name,
                "NativeReferenceName": prop,
            })
            self.refs.append(name)
        return name

    def measure(self, prop, entity="FactTrip"):
        a = self._src(entity)
        name = f"{entity}.{prop}"
        if name not in self.refs:
            self.selects.append({
                "Measure": {"Expression": {"SourceRef": {"Source": a}}, "Property": prop},
                "Name": name,
                "NativeReferenceName": prop,
            })
            self.refs.append(name)
        return name

    def hierarchy(self, entity, hier, level):
        a = self._src(entity)
        name = f"{entity}.{hier}.{level}"
        if name not in self.refs:
            self.selects.append({
                "HierarchyLevel": {
                    "Expression": {"Hierarchy": {
                        "Expression": {"SourceRef": {"Source": a}}, "Hierarchy": hier}},
                    "Level": level},
                "Name": name,
                "NativeReferenceName": level,
            })
            self.refs.append(name)
        return name

    def build(self, order_by=None, top=None):
        pq = {
            "Version": 2,
            "From": [{"Name": a, "Entity": e, "Type": 0} for a, e in self.froms.items()],
            "Select": self.selects,
        }
        if order_by:
            name, direction = order_by
            sel = next(s for s in self.selects if s["Name"] == name)
            expr = {k: v for k, v in sel.items() if k in ("Column", "Measure", "HierarchyLevel")}
            pq["OrderBy"] = [{"Direction": direction, "Expression": expr}]
        if top:
            pq["Top"] = top
        return pq


def lit(text):
    return {"expr": {"Literal": {"Value": f"'{text}'"}}}

def lit_num(n):
    return {"expr": {"Literal": {"Value": f"{n}D"}}}

def lit_bool(b):
    return {"expr": {"Literal": {"Value": "true" if b else "false"}}}

def colour(hexv):
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hexv}'"}}}}}


def visual(page, kind, x, y, w, h, vtype, projections=None, pq=None,
           title=None, subtitle=None, objects=None, z=None, tab=None,
           background=CARD, show_title=True, filters=None):
    name = vid(page, kind)
    single = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if projections:
        single["projections"] = projections
    if pq:
        single["prototypeQuery"] = pq
    if objects:
        single["objects"] = objects

    vc = {}
    if title is not None and show_title:
        tprops = {
            "text": lit(title),
            "fontColor": colour(INK),
            "fontSize": lit_num(12),
            "background": colour("#FFFFFF00"),
            "alignment": lit("left"),
            "titleWrap": lit_bool(True),
        }
        vc["title"] = [{"properties": tprops}]
    if subtitle is not None:
        vc["subTitle"] = [{"properties": {
            "text": lit(subtitle), "fontColor": colour(MUTE), "fontSize": lit_num(9),
            "show": lit_bool(True)}}]
    if background:
        vc["background"] = [{"properties": {
            "color": colour(background), "show": lit_bool(True), "transparency": lit_num(0)}}]
        vc["border"] = [{"properties": {
            "show": lit_bool(True), "color": colour("#E3E8ED"), "radius": lit_num(6)}}]
    if vc:
        single["vcObjects"] = vc

    zz = z if z is not None else next(_ids)
    cfg = {
        "name": name,
        "layouts": [{"id": 0, "position": {
            "x": x, "y": y, "z": zz, "width": w, "height": h,
            "tabOrder": tab if tab is not None else zz}}],
        "singleVisual": single,
    }
    out = {
        "x": x, "y": y, "z": zz, "width": w, "height": h,
        "config": json.dumps(cfg),
        "filters": json.dumps(filters or []),
    }
    return out


def textbox(page, x, y, w, h, runs, align="left", background=None):
    """runs = [(text, size, colour, bold)]"""
    paragraphs = [{
        "horizontalTextAlignment": align,
        "textRuns": [{
            "value": t,
            "textStyle": {"fontSize": f"{sz}pt", "color": cl,
                          "fontWeight": "bold" if bold else "normal",
                          "fontFamily": "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"},
        } for (t, sz, cl, bold) in runs],
    }]
    return visual(page, "tb", x, y, w, h, "textbox",
                  objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                  title=None, background=background, show_title=False)


def card(page, x, y, w, h, meas, label, fmt_size=26, entity="FactTrip"):
    q = Q(); ref = q.measure(meas, entity)
    return visual(page, "cd", x, y, w, h, "card",
                  projections={"Values": [{"queryRef": ref}]},
                  pq=q.build(),
                  title=label,
                  objects={
                      "labels": [{"properties": {
                          "color": colour(ACC), "fontSize": lit_num(fmt_size),
                          "labelDisplayUnits": lit_num(0)}}],
                      "categoryLabels": [{"properties": {"show": lit_bool(False)}}],
                  })


def slicer(page, x, y, w, h, entity, prop, title, mode="Basic"):
    q = Q(); ref = q.column(entity, prop)
    objs = {
        "general": [{"properties": {"orientation": lit_num(2 if mode == "Basic" else 1)}}],
        "selection": [{"properties": {
            "selectAllCheckboxEnabled": lit_bool(True), "singleSelect": lit_bool(False)}}],
    }
    if mode == "Dropdown":
        objs["general"] = [{"properties": {"orientation": lit_num(1), "filter": {}}}]
    return visual(page, "sl", x, y, w, h, "slicer",
                  projections={"Values": [{"queryRef": ref}]},
                  pq=q.build(), title=title, objects=objs)


def page(name, display, ordinal, visuals, filters=None, bg=BG):
    cfg = {
        "visibility": 0,
        "objects": {
            "background": [{"properties": {
                "color": colour(bg), "transparency": lit_num(0)}}],
            "displayArea": [{"properties": {"verticalAlignment": lit("Top")}}],
        },
    }
    return {
        "name": name,
        "displayName": display,
        "displayOption": 1,
        "height": H, "width": W,
        "ordinal": ordinal,
        "config": json.dumps(cfg),
        "filters": json.dumps(filters or []),
        "visualContainers": visuals,
    }


def header(p, title, sub):
    return [
        visual(p, "hd", 0, 0, W, 58, "textbox",
               objects={"general": [{"properties": {"paragraphs": [{
                   "horizontalTextAlignment": "left",
                   "textRuns": [{"value": title, "textStyle": {
                       "fontSize": "20pt", "color": "#FFFFFF", "fontWeight": "bold",
                       "fontFamily": "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"}}],
               }, {
                   "horizontalTextAlignment": "left",
                   "textRuns": [{"value": sub, "textStyle": {
                       "fontSize": "9pt", "color": "#C7D3E0",
                       "fontFamily": "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"}}],
               }]}}]},
               title=None, show_title=False, background=INK),
    ]


# ===========================================================================
# PAGE 1 -- EXECUTIVE OVERVIEW
# ===========================================================================
p = 1
v1 = header(p, "Tourism Analytics  |  Executive Overview",
            "IndiaTrails Travel  ·  source: SQL Server TourismDW  ·  travel dates 2023-2026")

# KPI cards
kpis = [
    ("Revenue (Cr)",       "Total Revenue"),
    ("Total Bookings",     "Bookings"),
    ("Total Travellers",   "Travellers"),
    ("Avg Booking Value",  "Avg Booking Value"),
    ("Avg Satisfaction",   "Avg Satisfaction"),
    ("Cancellation Rate %","Cancellation Rate"),
]
cw = 196
for i, (meas, label) in enumerate(kpis):
    v1.append(card(p, 14 + i * (cw + 8), 68, cw, 86, meas, label))

# Revenue trend, combo: monthly revenue column + 3M moving average line
q = Q()
cat  = q.column("DimDate", "MonthYear")
y1   = q.measure("Total Revenue")
y2   = q.measure("Revenue 3M Moving Avg")
v1.append(visual(p, "ln", 14, 162, 800, 258, "lineClusteredColumnComboChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Y":  [{"queryRef": y1}],
                              "Y2": [{"queryRef": y2}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Monthly revenue with 3-month moving average",
                 subtitle="Columns = revenue in the month; line = smoothed trend",
                 objects={"dataPoint": [{"properties": {"fill": colour(ACC)}}],
                          "legend": [{"properties": {"show": lit_bool(True),
                                                     "position": lit("Top")}}]}))

# Revenue by travel scope (donut)
q = Q()
cat = q.column("DimDestination", "Travel Scope")
val = q.measure("Total Revenue")
v1.append(visual(p, "dn", 822, 162, 444, 258, "donutChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Revenue split: domestic vs international",
                 objects={"legend": [{"properties": {"show": lit_bool(True),
                                                     "position": lit("Right")}}],
                          "labels": [{"properties": {"labelStyle": lit("Both")}}]}))

# Top destinations bar
q = Q()
cat = q.column("DimDestination", "DestinationName")
val = q.measure("Total Revenue")
v1.append(visual(p, "br", 14, 428, 500, 236, "clusteredBarChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2), top=10),
                 title="Top 10 destinations by revenue",
                 objects={"dataPoint": [{"properties": {"fill": colour(ACC)}}],
                          "labels": [{"properties": {"show": lit_bool(True)}}]}))

# Revenue by customer segment (treemap)
q = Q()
grp = q.column("DimTraveller", "CustomerSegment")
val = q.measure("Total Revenue")
v1.append(visual(p, "tm", 522, 428, 372, 236, "treemap",
                 projections={"Group": [{"queryRef": grp}], "Values": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Revenue by customer segment"))

# Slicers
v1.append(slicer(p, 902, 428, 180, 236, "DimDate", "Year", "Travel year"))
v1.append(slicer(p, 1090, 428, 176, 236, "DimDate", "Season", "Season"))

page1 = page("ReportSection01", "1. Executive Overview", 0, v1)

# ===========================================================================
# PAGE 2 -- DESTINATION PERFORMANCE
# ===========================================================================
p = 2
v2 = header(p, "Destination Performance",
            "Drill down Continent → Country → Destination. Right-click a destination to drill through to its detail page.")

# Map
q = Q()
cat  = q.column("DimDestination", "Country")
size = q.measure("Total Revenue")
v2.append(visual(p, "mp", 14, 68, 620, 300, "map",
                 projections={"Category": [{"queryRef": cat}], "Size": [{"queryRef": size}]},
                 pq=q.build(order_by=(size, 2)),
                 title="Revenue by country",
                 subtitle="Bubble size = revenue (requires an internet connection for map tiles)"))

# Drill-down column chart on the geography hierarchy
q = Q()
lvl = q.hierarchy("DimDestination", "Geography Hierarchy", "Continent")
val = q.measure("Total Revenue")
v2.append(visual(p, "dd", 642, 68, 624, 300, "clusteredColumnChart",
                 projections={"Category": [{"queryRef": lvl}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Revenue by geography (drill-down enabled)",
                 subtitle="Use the drill controls to move Continent → Country → Destination",
                 objects={"dataPoint": [{"properties": {"fill": colour(ACC3)}}]}))

# Scatter: bookings vs avg booking value, sized by revenue
q = Q()
det = q.column("DimDestination", "DestinationName")
xr  = q.measure("Total Bookings")
yr  = q.measure("Avg Booking Value")
sz  = q.measure("Total Revenue")
ser = q.column("DimDestination", "DestinationType")
v2.append(visual(p, "sc", 14, 376, 620, 288, "scatterChart",
                 projections={"Category": [{"queryRef": det}],
                              "X": [{"queryRef": xr}],
                              "Y": [{"queryRef": yr}],
                              "Size": [{"queryRef": sz}],
                              "Series": [{"queryRef": ser}]},
                 pq=q.build(),
                 title="Volume vs value by destination",
                 subtitle="X = bookings, Y = average booking value, bubble = total revenue"))

# Destination scorecard matrix
q = Q()
row  = q.column("DimDestination", "DestinationName")
m1   = q.measure("Total Revenue")
m2   = q.measure("Total Bookings")
m3   = q.measure("Avg Booking Value")
m4   = q.measure("Avg Satisfaction")
m5   = q.measure("Cancellation Rate %")
m6   = q.measure("Destination Rank")
v2.append(visual(p, "mx", 642, 376, 624, 288, "pivotTable",
                 projections={"Rows": [{"queryRef": row}],
                              "Values": [{"queryRef": m6}, {"queryRef": m1},
                                         {"queryRef": m2}, {"queryRef": m3},
                                         {"queryRef": m4}, {"queryRef": m5}]},
                 pq=q.build(order_by=(m1, 2)),
                 title="Destination scorecard",
                 subtitle="Ranked by revenue; conditional formatting applied to satisfaction"))

page2 = page("ReportSection02", "2. Destination Performance", 1, v2)

# ===========================================================================
# PAGE 3 -- SEASONALITY AND TRENDS
# ===========================================================================
p = 3
v3 = header(p, "Seasonality & Growth",
            "How demand moves through the year, and how each year compares with the last.")

# Month x Year heat matrix
q = Q()
row = q.column("DimDate", "MonthName")
cl  = q.column("DimDate", "Year")
val = q.measure("Total Revenue")
v3.append(visual(p, "hm", 14, 68, 500, 300, "pivotTable",
                 projections={"Rows": [{"queryRef": row}],
                              "Columns": [{"queryRef": cl}],
                              "Values": [{"queryRef": val}]},
                 pq=q.build(),
                 title="Revenue heat map: month by year",
                 subtitle="Apply background colour formatting to see the seasonal pattern"))

# YoY growth column chart
q = Q()
cat = q.column("DimDate", "MonthYear")
val = q.measure("Revenue YoY %")
v3.append(visual(p, "yy", 522, 68, 744, 300, "columnChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Year-on-year revenue growth",
                 subtitle="Compares each month against the same month last year",
                 objects={"dataPoint": [{"properties": {"fill": colour(ACC2)}}]}))

# Ribbon chart: destination type rank over time
q = Q()
cat = q.column("DimDate", "Quarter")
ser = q.column("DimDestination", "DestinationType")
val = q.measure("Total Revenue")
v3.append(visual(p, "rb", 14, 376, 620, 288, "ribbonChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Series": [{"queryRef": ser}],
                              "Y": [{"queryRef": val}]},
                 pq=q.build(),
                 title="How destination types rank across quarters",
                 subtitle="Ribbon width shows revenue; crossings show rank changes"))

# Booking window analysis
q = Q()
cat = q.column("FactTrip", "BookingWindow")
y1  = q.measure("Total Bookings")
y2  = q.measure("Cancellation Rate %")
v3.append(visual(p, "bw", 642, 376, 400, 288, "lineClusteredColumnComboChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Y": [{"queryRef": y1}],
                              "Y2": [{"queryRef": y2}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Booking window vs cancellation rate"))

v3.append(slicer(p, 1050, 376, 216, 288, "DimDestination", "Travel Scope", "Travel scope"))

page3 = page("ReportSection03", "3. Seasonality & Growth", 2, v3)

# ===========================================================================
# PAGE 4 -- CUSTOMER AND CHANNEL
# ===========================================================================
p = 4
v4 = header(p, "Customer & Channel",
            "Who travels, how they book, and what each channel actually leaves on the table.")

# Channel waterfall: gross revenue down to net
q = Q()
cat = q.column("DimBookingChannel", "ChannelName")
val = q.measure("Total Commission")
v4.append(visual(p, "wf", 14, 68, 620, 290, "waterfallChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Commission paid away, by channel",
                 subtitle="Every rupee here is revenue that never reaches net"))

# Channel net margin bar
q = Q()
cat = q.column("DimBookingChannel", "ChannelName")
val = q.measure("Net Margin %")
v4.append(visual(p, "nm", 642, 68, 624, 290, "clusteredBarChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Net margin by channel",
                 objects={"dataPoint": [{"properties": {"fill": colour(ACC)}}],
                          "labels": [{"properties": {"show": lit_bool(True)}}]}))

# Loyalty tier analysis
q = Q()
cat = q.column("DimTraveller", "LoyaltyTier")
y1  = q.measure("Avg Booking Value")
y2  = q.measure("Discount Rate %")
v4.append(visual(p, "ly", 14, 366, 410, 298, "lineClusteredColumnComboChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Y": [{"queryRef": y1}],
                              "Y2": [{"queryRef": y2}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Loyalty tier: average value vs discount given"))

# Age band / gender
q = Q()
cat = q.column("DimTraveller", "AgeBand")
ser = q.column("DimTraveller", "Gender")
val = q.measure("Total Bookings")
v4.append(visual(p, "ag", 432, 366, 410, 298, "clusteredColumnChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Series": [{"queryRef": ser}],
                              "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Bookings by age band and gender"))

# Top travellers table
q = Q()
c1 = q.column("DimTraveller", "TravellerName")
c2 = q.column("DimTraveller", "Nationality")
c3 = q.column("DimTraveller", "LoyaltyTier")
m1 = q.measure("Total Bookings")
m2 = q.measure("Total Revenue")
v4.append(visual(p, "tv", 850, 366, 416, 298, "tableEx",
                 projections={"Values": [{"queryRef": c1}, {"queryRef": c2},
                                         {"queryRef": c3}, {"queryRef": m1},
                                         {"queryRef": m2}]},
                 pq=q.build(order_by=(m2, 2), top=25),
                 title="Highest-value travellers"))

page4 = page("ReportSection04", "4. Customer & Channel", 3, v4)

# ===========================================================================
# PAGE 5 -- SCENARIO PLANNING (what-if)
# ===========================================================================
p = 5
v5 = header(p, "Discount Scenario Planning",
            "Move the slider to reprice every booking at a single discount level and see what it does to revenue.")

v5.append(slicer(p, 14, 68, 300, 130, "Discount Scenario", "Discount %",
                 "Scenario discount", mode="Basic"))

v5.append(card(p, 322, 68, 300, 130, "Total Revenue", "Actual revenue"))
v5.append(card(p, 630, 68, 300, 130, "Revenue at Scenario Discount", "Revenue at scenario discount"))
v5.append(card(p, 938, 68, 328, 130, "Scenario Revenue Impact", "Impact vs actual"))

# Scenario by destination
q = Q()
cat = q.column("DimDestination", "DestinationName")
y1  = q.measure("Total Revenue")
y2  = q.measure("Revenue at Scenario Discount")
v5.append(visual(p, "sn", 14, 206, 760, 300, "clusteredColumnChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Y": [{"queryRef": y1}, {"queryRef": y2}]},
                 pq=q.build(order_by=(y1, 2), top=12),
                 title="Actual vs scenario revenue, top 12 destinations"))

# Pareto
q = Q()
cat = q.column("DimDestination", "DestinationName")
y1  = q.measure("Total Revenue")
y2  = q.measure("Pareto Revenue %")
v5.append(visual(p, "pr", 782, 206, 484, 300, "lineClusteredColumnComboChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Y": [{"queryRef": y1}],
                              "Y2": [{"queryRef": y2}]},
                 pq=q.build(order_by=(y1, 2), top=20),
                 title="Pareto: how concentrated is revenue?",
                 subtitle="Line shows cumulative share of total revenue"))

# Target gauge
q = Q()
y   = q.measure("Total Revenue")
tgt = q.measure("Revenue Target")
v5.append(visual(p, "gg", 14, 514, 380, 150, "gauge",
                 projections={"Y": [{"queryRef": y}], "TargetValue": [{"queryRef": tgt}]},
                 pq=q.build(),
                 title="Revenue against the 15% growth target"))

# Trip length funnel
q = Q()
cat = q.column("FactTrip", "TripLengthBand")
val = q.measure("Total Bookings")
v5.append(visual(p, "fn", 402, 514, 372, 150, "funnel",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Bookings by trip length"))

# Satisfaction by star rating and season
q = Q()
cat = q.column("DimAccommodation", "StarRating")
ser = q.column("DimDate", "Peak Season Label")
val = q.measure("Avg Satisfaction")
v5.append(visual(p, "st", 782, 514, 484, 150, "clusteredColumnChart",
                 projections={"Category": [{"queryRef": cat}],
                              "Series": [{"queryRef": ser}],
                              "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Satisfaction: star rating vs peak season"))

page5 = page("ReportSection05", "5. Scenario Planning", 4, v5)

# ===========================================================================
# PAGE 6 -- DESTINATION DETAIL (drill-through target)
# ===========================================================================
p = 6
v6 = header(p, "Destination Detail",
            "Drill-through target. Reached by right-clicking a destination on page 2.")

for i, (meas, label) in enumerate([
        ("Total Revenue", "Revenue"), ("Total Bookings", "Bookings"),
        ("Avg Booking Value", "Avg booking value"), ("Avg Satisfaction", "Satisfaction"),
        ("Cancellation Rate %", "Cancellation rate"), ("Destination Rank", "Revenue rank")]):
    v6.append(card(p, 14 + i * 210, 68, 200, 86, meas, label))

q = Q()
cat = q.column("DimDate", "MonthYear")
val = q.measure("Total Revenue")
v6.append(visual(p, "tr", 14, 162, 760, 250, "lineChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(cat, 1)),
                 title="Revenue over time for the selected destination"))

q = Q()
cat = q.column("DimAccommodation", "AccommodationType")
val = q.measure("Total Revenue")
v6.append(visual(p, "ac", 782, 162, 484, 250, "clusteredBarChart",
                 projections={"Category": [{"queryRef": cat}], "Y": [{"queryRef": val}]},
                 pq=q.build(order_by=(val, 2)),
                 title="Revenue by accommodation type"))

q = Q()
c1 = q.column("FactTrip", "BookingReference")
c2 = q.column("DimTraveller", "TravellerName")
c3 = q.column("DimTraveller", "CustomerSegment")
c4 = q.column("FactTrip", "BookingStatus")
c5 = q.column("FactTrip", "DurationDays")
m1 = q.measure("Total Revenue")
m2 = q.measure("Avg Satisfaction")
v6.append(visual(p, "dt", 14, 420, 1252, 244, "tableEx",
                 projections={"Values": [{"queryRef": c1}, {"queryRef": c2},
                                         {"queryRef": c3}, {"queryRef": c4},
                                         {"queryRef": c5}, {"queryRef": m1},
                                         {"queryRef": m2}]},
                 pq=q.build(order_by=(m1, 2), top=200),
                 title="Individual bookings"))

# page-level drill-through filter on DestinationName
drill_filter = [{
    "name": "DrillDestination",
    "expression": {"Column": {
        "Expression": {"SourceRef": {"Entity": "DimDestination"}},
        "Property": "DestinationName"}},
    "type": "Categorical",
    "howCreated": 2,
    "objects": {},
    "ordinal": 0,
}]
page6 = page("ReportSection06", "6. Destination Detail", 5, v6, filters=drill_filter)

# ===========================================================================
# report.json
# ===========================================================================
# No custom base-theme reference: Power BI Desktop applies its shipped default
# theme, and every visual below sets its own colours explicitly.
report_config = {
    "version": "5.43",
    "activeSectionIndex": 0,
    "defaultDrillFilterOtherVisuals": True,
    "settings": {
        "useStylableVisualContainerHeader": True,
        "exportDataMode": 1,
        "useNewFilterPaneExperience": True,
        "allowChangeFilterTypes": True,
        "useCrossReportDrillthrough": False,
    },
    "objects": {
        "outspacePane": [{"properties": {
            "expanded": lit_bool(False),
            "backgroundColor": colour("#FFFFFF"),
        }}],
    },
}

report = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
    "config": json.dumps(report_config),
    "layoutOptimization": 0,
    "publicCustomVisuals": [],
    "resourcePackages": [],
    "sections": [page1, page2, page3, page4, page5, page6],
}

with open(f"{REPORT}/report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# PBIP wrapper files
# ---------------------------------------------------------------------------
with open(f"{ROOT}/{NAME}.pbip", "w", encoding="utf-8") as f:
    json.dump({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/pbip/definition/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, f, indent=2)

with open(f"{REPORT}/definition.pbir", "w", encoding="utf-8") as f:
    json.dump({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    }, f, indent=2)

with open(f"{SMODEL}/definition.pbism", "w", encoding="utf-8") as f:
    json.dump({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definition/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {"qnaEnabled": True},
    }, f, indent=2)

for folder, ftype, disp in [(REPORT, "Report", f"{NAME}"),
                            (SMODEL, "SemanticModel", f"{NAME}")]:
    with open(f"{folder}/.platform", "w", encoding="utf-8") as f:
        json.dump({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": ftype, "displayName": disp},
            "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
        }, f, indent=2)

nvis = sum(len(s["visualContainers"]) for s in report["sections"])
print(f"report.json written: {len(report['sections'])} pages, {nvis} visual containers")
for s in report["sections"]:
    print(f"  {s['displayName']:32s} {len(s['visualContainers']):>2} visuals")
