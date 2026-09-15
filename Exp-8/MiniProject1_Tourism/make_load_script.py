"""Emit sql/02_load_data.sql : self-contained INSERT statements for TourismDW."""
import pandas as pd, math

BATCH = 500

def lit(v, col, dtypes):
    if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
        return "NULL"
    if dtypes[col] in ("str", "date"):
        return "'" + str(v).replace("'", "''") + "'"
    if dtypes[col] == "bit":
        return str(int(v))
    return str(v)

def emit(f, table, df, dtypes):
    cols = list(df.columns)
    collist = ", ".join(f"[{c}]" for c in cols)
    f.write(f"\n/* ---------- {table} : {len(df):,} rows ---------- */\n")
    recs = df.to_dict("records")
    for i in range(0, len(recs), BATCH):
        chunk = recs[i:i + BATCH]
        f.write(f"INSERT INTO {table} ({collist}) VALUES\n")
        rows = []
        for r in chunk:
            rows.append("(" + ",".join(lit(r[c], c, dtypes) for c in cols) + ")")
        f.write(",\n".join(rows) + ";\nGO\n")

S, N, B, D = "str", "num", "bit", "date"

specs = [
    ("dbo.DimDate", "DimDate.csv", dict(
        DateKey=N, FullDate=D, Year=N, Quarter=S, MonthNo=N, MonthName=S, MonthYear=S,
        DayOfMonth=N, DayName=S, WeekOfYear=N, DayOfYear=N, IsWeekend=B, Season=S,
        FinancialYear=S, IsPeakSeason=B)),
    ("dbo.DimDestination", "DimDestination.csv", dict(
        DestinationID=N, DestinationName=S, City=S, StateProvince=S, Country=S, Region=S,
        Continent=S, DestinationType=S, Latitude=N, Longitude=N, CostIndex=N,
        PopularityIndex=N, IsDomestic=B)),
    ("dbo.DimTraveller", "DimTraveller.csv", dict(
        TravellerID=N, TravellerName=S, Gender=S, Age=N, AgeBand=S, Nationality=S,
        SignupDate=D, CustomerSegment=S, LoyaltyTier=S, IsRepeatCustomer=B)),
    ("dbo.DimAccommodation", "DimAccommodation.csv", dict(
        AccommodationID=N, AccommodationName=S, AccommodationType=S, StarRating=N,
        DestinationID=N, PriceIndex=N, AvgRating=N)),
    ("dbo.DimTransport", "DimTransport.csv", dict(
        TransportID=N, TransportType=S, Carrier=S, TravelClass=S, CostFactor=N,
        IsInternationalCapable=B)),
    ("dbo.DimBookingChannel", "DimBookingChannel.csv", dict(
        ChannelID=N, ChannelName=S, ChannelType=S, CommissionRate=N)),
    ("stg.FactTrip_Raw", "FactTrip.csv", dict(
        TripID=N, BookingReference=S, TravellerID=N, DestinationID=N, AccommodationID=N,
        TransportID=N, ChannelID=N, BookingDateKey=N, StartDateKey=N, EndDateKey=N,
        DurationDays=N, NumTravellers=N, LeadTimeDays=N, AccommodationCost=N,
        TransportCost=N, ActivityCost=N, GrossAmount=N, DiscountAmount=N, Revenue=N,
        ChannelCommission=N, NetRevenue=N, SatisfactionScore=N, BookingStatus=S)),
]

with open("sql/02_load_data.sql", "w", encoding="utf-8") as f:
    f.write("""/* ===========================================================================
   MINI PROJECT I  -  TOURISM ANALYTICS
   Script 02 : Load data
   Self-contained -- no CSV files or BULK INSERT permissions needed.
   Run after script 01. Takes roughly 30-60 seconds.
   =========================================================================== */

USE TourismDW;
GO
SET NOCOUNT ON;
GO
""")
    for table, csv, dtypes in specs:
        df = pd.read_csv("data/" + csv)
        emit(f, table, df, dtypes)
    f.write("""
PRINT 'Script 02 complete: all dimension tables and stg.FactTrip_Raw loaded.';
GO
""")

import os
print("sql/02_load_data.sql  ->  {:.1f} MB".format(os.path.getsize("sql/02_load_data.sql") / 1e6))
