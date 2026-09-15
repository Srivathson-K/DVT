/* ===========================================================================
   MINI PROJECT I  -  TOURISM ANALYTICS
   Script 03 : Data cleaning, transformation, modelling and analytical views
   Run after script 02.

   This script is the "data preparation" evidence for the project. It takes
   stg.FactTrip_Raw (which deliberately contains the kind of defects found in
   a real booking extract) and produces dbo.FactTrip, a clean, constrained,
   indexed fact table.
   =========================================================================== */

USE TourismDW;
GO
SET NOCOUNT ON;
GO

/* ---------------------------------------------------------------------------
   STEP 1 -- PROFILE THE RAW DATA
   Run this first and keep the output: it is the "before" picture that
   justifies every cleaning rule below.
   --------------------------------------------------------------------------- */
PRINT '=== STEP 1 : RAW DATA QUALITY PROFILE ===';

SELECT 'Total raw rows'              AS [Metric], COUNT(*) AS [Value] FROM stg.FactTrip_Raw
UNION ALL SELECT 'Distinct booking references', COUNT(DISTINCT BookingReference) FROM stg.FactTrip_Raw
UNION ALL SELECT 'Duplicate rows',              COUNT(*) - COUNT(DISTINCT BookingReference) FROM stg.FactTrip_Raw
UNION ALL SELECT 'Negative duration rows',      COUNT(*) FROM stg.FactTrip_Raw WHERE DurationDays <= 0
UNION ALL SELECT 'NULL satisfaction scores',    COUNT(*) FROM stg.FactTrip_Raw WHERE SatisfactionScore IS NULL
UNION ALL SELECT 'Distinct status values',      COUNT(DISTINCT BookingStatus) FROM stg.FactTrip_Raw
UNION ALL SELECT 'Rows with zero revenue',      COUNT(*) FROM stg.FactTrip_Raw WHERE Revenue <= 0;

-- inconsistent casing in the status column
SELECT BookingStatus, COUNT(*) AS RowCnt
FROM stg.FactTrip_Raw
GROUP BY BookingStatus
ORDER BY RowCnt DESC;
GO

/* ---------------------------------------------------------------------------
   STEP 2 -- CLEAN AND TRANSFORM
   Rules applied:
     R1  De-duplicate on BookingReference, keeping the lowest TripID
     R2  Repair negative DurationDays (sign-flip data-entry error) with ABS()
     R3  Standardise BookingStatus casing to Title Case
     R4  Drop any row whose foreign keys do not resolve (referential integrity)
     R5  Derive RevenuePerTraveller, RevenuePerDay, BookingWindow, TripLengthBand
   --------------------------------------------------------------------------- */
PRINT '=== STEP 2 : CLEAN AND LOAD dbo.FactTrip ===';

TRUNCATE TABLE dbo.FactTrip;
GO

WITH Deduped AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY BookingReference ORDER BY TripID) AS rn   -- R1
    FROM stg.FactTrip_Raw
),
Cleaned AS (
    SELECT
        d.TripID,
        d.BookingReference,
        d.TravellerID, d.DestinationID, d.AccommodationID, d.TransportID, d.ChannelID,
        d.BookingDateKey, d.StartDateKey, d.EndDateKey,
        ABS(d.DurationDays)                                     AS DurationDays,      -- R2
        d.NumTravellers, d.LeadTimeDays,
        d.AccommodationCost, d.TransportCost, d.ActivityCost,
        d.GrossAmount, d.DiscountAmount, d.Revenue,
        d.ChannelCommission, d.NetRevenue, d.SatisfactionScore,
        UPPER(LEFT(d.BookingStatus, 1))
            + LOWER(SUBSTRING(d.BookingStatus, 2, 50))          AS BookingStatusRaw   -- R3
    FROM Deduped d
    WHERE d.rn = 1
)
INSERT INTO dbo.FactTrip (
    TripID, BookingReference, TravellerID, DestinationID, AccommodationID,
    TransportID, ChannelID, BookingDateKey, StartDateKey, EndDateKey,
    DurationDays, NumTravellers, LeadTimeDays, AccommodationCost, TransportCost,
    ActivityCost, GrossAmount, DiscountAmount, Revenue, ChannelCommission,
    NetRevenue, SatisfactionScore, BookingStatus,
    RevenuePerTraveller, RevenuePerDay, BookingWindow, TripLengthBand)
SELECT
    c.TripID, c.BookingReference, c.TravellerID, c.DestinationID, c.AccommodationID,
    c.TransportID, c.ChannelID, c.BookingDateKey, c.StartDateKey, c.EndDateKey,
    c.DurationDays, c.NumTravellers, c.LeadTimeDays, c.AccommodationCost,
    c.TransportCost, c.ActivityCost, c.GrossAmount, c.DiscountAmount, c.Revenue,
    c.ChannelCommission, c.NetRevenue, c.SatisfactionScore,
    -- 'No show' -> 'No Show' tidy-up after the generic title-casing above
    CASE WHEN c.BookingStatusRaw = 'No show' THEN 'No Show' ELSE c.BookingStatusRaw END,
    -- R5 : derived measures and bands
    CAST(c.Revenue / NULLIF(c.NumTravellers, 0) AS DECIMAL(14,2)),
    CAST(c.Revenue / NULLIF(c.DurationDays, 0)  AS DECIMAL(14,2)),
    CASE WHEN c.LeadTimeDays <= 7   THEN '1. Last Minute (0-7d)'
         WHEN c.LeadTimeDays <= 30  THEN '2. Short (8-30d)'
         WHEN c.LeadTimeDays <= 90  THEN '3. Medium (31-90d)'
         ELSE                            '4. Early Bird (90d+)' END,
    CASE WHEN c.DurationDays <= 3   THEN '1. Short Break (1-3d)'
         WHEN c.DurationDays <= 7   THEN '2. Week (4-7d)'
         WHEN c.DurationDays <= 14  THEN '3. Extended (8-14d)'
         ELSE                            '4. Long Haul (15d+)' END
FROM Cleaned c
-- R4 : referential integrity
INNER JOIN dbo.DimTraveller       t  ON t.TravellerID     = c.TravellerID
INNER JOIN dbo.DimDestination     ds ON ds.DestinationID  = c.DestinationID
INNER JOIN dbo.DimAccommodation   a  ON a.AccommodationID = c.AccommodationID
INNER JOIN dbo.DimTransport       tr ON tr.TransportID    = c.TransportID
INNER JOIN dbo.DimBookingChannel  ch ON ch.ChannelID      = c.ChannelID
INNER JOIN dbo.DimDate            db ON db.DateKey        = c.BookingDateKey
INNER JOIN dbo.DimDate            sd ON sd.DateKey        = c.StartDateKey
INNER JOIN dbo.DimDate            ed ON ed.DateKey        = c.EndDateKey;
GO

PRINT '=== STEP 2 RESULT ===';
SELECT 'Raw rows' AS [Stage], COUNT(*) AS [Rows] FROM stg.FactTrip_Raw
UNION ALL SELECT 'Clean rows', COUNT(*) FROM dbo.FactTrip
UNION ALL SELECT 'Rows removed', (SELECT COUNT(*) FROM stg.FactTrip_Raw) - (SELECT COUNT(*) FROM dbo.FactTrip);
GO

/* ---------------------------------------------------------------------------
   STEP 3 -- DATA MODELLING : foreign keys define the star schema
   --------------------------------------------------------------------------- */
PRINT '=== STEP 3 : APPLY RELATIONSHIPS ===';

ALTER TABLE dbo.DimAccommodation ADD CONSTRAINT FK_Acc_Dest
    FOREIGN KEY (DestinationID)   REFERENCES dbo.DimDestination(DestinationID);

ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_Traveller
    FOREIGN KEY (TravellerID)     REFERENCES dbo.DimTraveller(TravellerID);
ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_Destination
    FOREIGN KEY (DestinationID)   REFERENCES dbo.DimDestination(DestinationID);
ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_Accommodation
    FOREIGN KEY (AccommodationID) REFERENCES dbo.DimAccommodation(AccommodationID);
ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_Transport
    FOREIGN KEY (TransportID)     REFERENCES dbo.DimTransport(TransportID);
ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_Channel
    FOREIGN KEY (ChannelID)       REFERENCES dbo.DimBookingChannel(ChannelID);
ALTER TABLE dbo.FactTrip ADD CONSTRAINT FK_Fact_StartDate
    FOREIGN KEY (StartDateKey)    REFERENCES dbo.DimDate(DateKey);
GO

-- Indexes to keep Power BI / Tableau refreshes fast
CREATE NONCLUSTERED INDEX IX_Fact_StartDate   ON dbo.FactTrip(StartDateKey)  INCLUDE (Revenue, NetRevenue, NumTravellers);
CREATE NONCLUSTERED INDEX IX_Fact_Destination ON dbo.FactTrip(DestinationID) INCLUDE (Revenue, SatisfactionScore);
CREATE NONCLUSTERED INDEX IX_Fact_Channel     ON dbo.FactTrip(ChannelID)     INCLUDE (Revenue, ChannelCommission);
CREATE NONCLUSTERED INDEX IX_Fact_Status      ON dbo.FactTrip(BookingStatus);
GO

/* ---------------------------------------------------------------------------
   STEP 4 -- ANALYTICAL VIEWS
   vw_TripAnalysis is the single wide view Tableau connects to.
   Power BI connects to the individual tables so it can build its own model.
   --------------------------------------------------------------------------- */
PRINT '=== STEP 4 : CREATE VIEWS ===';
GO

CREATE OR ALTER VIEW dbo.vw_TripAnalysis AS
SELECT
    f.TripID, f.BookingReference, f.BookingStatus,
    -- date
    sd.FullDate       AS TripStartDate,
    ed.FullDate       AS TripEndDate,
    bd.FullDate       AS BookingDate,
    sd.[Year]         AS TripYear,
    sd.[Quarter]      AS TripQuarter,
    sd.MonthNo        AS TripMonthNo,
    sd.MonthName      AS TripMonthName,
    sd.MonthYear      AS TripMonthYear,
    sd.Season         AS TripSeason,
    sd.FinancialYear,
    sd.IsPeakSeason,
    sd.IsWeekend      AS StartsOnWeekend,
    -- destination
    d.DestinationName, d.City, d.StateProvince, d.Country, d.Region, d.Continent,
    d.DestinationType, d.Latitude, d.Longitude, d.IsDomestic,
    CASE WHEN d.IsDomestic = 1 THEN 'Domestic' ELSE 'International' END AS TravelScope,
    -- traveller
    t.TravellerID, t.TravellerName, t.Gender, t.Age, t.AgeBand, t.Nationality,
    t.CustomerSegment, t.LoyaltyTier, t.IsRepeatCustomer,
    -- accommodation & transport
    a.AccommodationName, a.AccommodationType, a.StarRating, a.AvgRating AS PropertyRating,
    tr.TransportType, tr.Carrier, tr.TravelClass,
    -- channel
    c.ChannelName, c.ChannelType, c.CommissionRate,
    -- measures
    f.DurationDays, f.NumTravellers, f.LeadTimeDays,
    f.AccommodationCost, f.TransportCost, f.ActivityCost,
    f.GrossAmount, f.DiscountAmount, f.Revenue, f.ChannelCommission, f.NetRevenue,
    f.RevenuePerTraveller, f.RevenuePerDay,
    f.SatisfactionScore, f.BookingWindow, f.TripLengthBand,
    CAST(f.DiscountAmount * 100.0 / NULLIF(f.GrossAmount, 0) AS DECIMAL(6,2)) AS DiscountPct,
    f.NumTravellers * f.DurationDays AS TravellerDays
FROM dbo.FactTrip f
JOIN dbo.DimDate           sd ON sd.DateKey        = f.StartDateKey
JOIN dbo.DimDate           ed ON ed.DateKey        = f.EndDateKey
JOIN dbo.DimDate           bd ON bd.DateKey        = f.BookingDateKey
JOIN dbo.DimDestination    d  ON d.DestinationID   = f.DestinationID
JOIN dbo.DimTraveller      t  ON t.TravellerID     = f.TravellerID
JOIN dbo.DimAccommodation  a  ON a.AccommodationID = f.AccommodationID
JOIN dbo.DimTransport      tr ON tr.TransportID    = f.TransportID
JOIN dbo.DimBookingChannel c  ON c.ChannelID       = f.ChannelID;
GO

-- Destination scorecard: one row per destination with the headline KPIs
CREATE OR ALTER VIEW dbo.vw_DestinationScorecard AS
SELECT
    d.DestinationID, d.DestinationName, d.Country, d.Region, d.Continent,
    d.DestinationType,
    CASE WHEN d.IsDomestic = 1 THEN 'Domestic' ELSE 'International' END AS TravelScope,
    d.Latitude, d.Longitude,
    COUNT(*)                                              AS TotalBookings,
    SUM(CASE WHEN f.BookingStatus = 'Completed' THEN 1 ELSE 0 END) AS CompletedTrips,
    SUM(CASE WHEN f.BookingStatus = 'Cancelled' THEN 1 ELSE 0 END) AS CancelledTrips,
    CAST(SUM(CASE WHEN f.BookingStatus = 'Cancelled' THEN 1.0 ELSE 0 END) * 100.0
         / NULLIF(COUNT(*), 0) AS DECIMAL(6,2))           AS CancellationRatePct,
    SUM(f.Revenue)                                        AS TotalRevenue,
    SUM(f.NetRevenue)                                     AS TotalNetRevenue,
    CAST(AVG(f.Revenue) AS DECIMAL(14,2))                 AS AvgBookingValue,
    CAST(AVG(CAST(f.DurationDays AS DECIMAL(8,2))) AS DECIMAL(6,2)) AS AvgTripDuration,
    SUM(f.NumTravellers)                                  AS TotalTravellers,
    CAST(AVG(f.SatisfactionScore) AS DECIMAL(4,2))        AS AvgSatisfaction,
    CAST(SUM(f.DiscountAmount) * 100.0 / NULLIF(SUM(f.GrossAmount), 0) AS DECIMAL(6,2)) AS AvgDiscountPct
FROM dbo.FactTrip f
JOIN dbo.DimDestination d ON d.DestinationID = f.DestinationID
GROUP BY d.DestinationID, d.DestinationName, d.Country, d.Region, d.Continent,
         d.DestinationType, d.IsDomestic, d.Latitude, d.Longitude;
GO

-- Monthly trend with a 3-month moving average, computed server-side
CREATE OR ALTER VIEW dbo.vw_MonthlyTrend AS
WITH M AS (
    SELECT sd.[Year], sd.MonthNo, MIN(sd.MonthYear) AS MonthYear,
           SUM(f.Revenue)   AS Revenue,
           COUNT(*)         AS Bookings,
           SUM(f.NumTravellers) AS Travellers,
           AVG(f.SatisfactionScore) AS AvgSatisfaction
    FROM dbo.FactTrip f
    JOIN dbo.DimDate sd ON sd.DateKey = f.StartDateKey
    GROUP BY sd.[Year], sd.MonthNo
)
SELECT *,
       CAST(AVG(Revenue) OVER (ORDER BY [Year], MonthNo
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS DECIMAL(14,2)) AS Revenue3MonthMA,
       LAG(Revenue, 12) OVER (ORDER BY [Year], MonthNo)                 AS RevenueSameMonthLastYear
FROM M;
GO

-- Traveller RFM-style segmentation, used for the drill-through page
CREATE OR ALTER VIEW dbo.vw_TravellerValue AS
SELECT
    t.TravellerID, t.TravellerName, t.Gender, t.AgeBand, t.Nationality,
    t.CustomerSegment, t.LoyaltyTier,
    COUNT(*)                                        AS TripCount,
    SUM(f.Revenue)                                  AS LifetimeValue,
    CAST(AVG(f.Revenue) AS DECIMAL(14,2))           AS AvgTripValue,
    MAX(sd.FullDate)                                AS LastTripDate,
    DATEDIFF(DAY, MAX(sd.FullDate), '2026-12-31')   AS DaysSinceLastTrip,
    CAST(AVG(f.SatisfactionScore) AS DECIMAL(4,2))  AS AvgSatisfaction,
    NTILE(4) OVER (ORDER BY SUM(f.Revenue) DESC)    AS ValueQuartile
FROM dbo.FactTrip f
JOIN dbo.DimTraveller t ON t.TravellerID = f.TravellerID
JOIN dbo.DimDate     sd ON sd.DateKey    = f.StartDateKey
GROUP BY t.TravellerID, t.TravellerName, t.Gender, t.AgeBand, t.Nationality,
         t.CustomerSegment, t.LoyaltyTier;
GO

PRINT 'Script 03 complete: data cleaned, model built, 4 analytical views created.';
GO
