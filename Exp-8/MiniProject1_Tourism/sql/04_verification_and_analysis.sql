/* ===========================================================================
   MINI PROJECT I  -  TOURISM ANALYTICS
   Script 04 : Verification and analytical queries
   Run after script 03. Screenshot the output of Section A for the report --
   it proves the SQL Server connection and the loaded model.
   =========================================================================== */

USE TourismDW;
GO

/* ===========================================================================
   SECTION A -- LOAD VERIFICATION   (expected values in comments)
   =========================================================================== */
SELECT 'DimDate'           AS TableName, COUNT(*) AS [RowCount] FROM dbo.DimDate            -- 2191
UNION ALL SELECT 'DimDestination',       COUNT(*) FROM dbo.DimDestination                 --   32
UNION ALL SELECT 'DimTraveller',         COUNT(*) FROM dbo.DimTraveller                   -- 2400
UNION ALL SELECT 'DimAccommodation',     COUNT(*) FROM dbo.DimAccommodation               --  155
UNION ALL SELECT 'DimTransport',         COUNT(*) FROM dbo.DimTransport                   --   18
UNION ALL SELECT 'DimBookingChannel',    COUNT(*) FROM dbo.DimBookingChannel              --    9
UNION ALL SELECT 'stg.FactTrip_Raw',     COUNT(*) FROM stg.FactTrip_Raw                   --12060
UNION ALL SELECT 'dbo.FactTrip (clean)', COUNT(*) FROM dbo.FactTrip;                      --12000
GO

-- Post-clean integrity: every one of these must return 0
SELECT 'Duplicate booking refs' AS Check_, COUNT(*) - COUNT(DISTINCT BookingReference) AS Failures FROM dbo.FactTrip
UNION ALL SELECT 'Non-positive duration', COUNT(*) FROM dbo.FactTrip WHERE DurationDays <= 0
UNION ALL SELECT 'Negative revenue',      COUNT(*) FROM dbo.FactTrip WHERE Revenue < 0
UNION ALL SELECT 'Orphan destination',    COUNT(*) FROM dbo.FactTrip f
              LEFT JOIN dbo.DimDestination d ON d.DestinationID = f.DestinationID WHERE d.DestinationID IS NULL
UNION ALL SELECT 'Orphan date key',       COUNT(*) FROM dbo.FactTrip f
              LEFT JOIN dbo.DimDate dt ON dt.DateKey = f.StartDateKey WHERE dt.DateKey IS NULL;
GO

-- Status values should now be exactly four, in clean Title Case
SELECT BookingStatus, COUNT(*) AS Trips FROM dbo.FactTrip GROUP BY BookingStatus ORDER BY Trips DESC;
GO

/* ===========================================================================
   SECTION B -- HEADLINE KPIs  (these should match the Power BI cards)
   =========================================================================== */
SELECT
    COUNT(*)                                                   AS TotalBookings,
    SUM(NumTravellers)                                         AS TotalTravellers,
    CAST(SUM(Revenue)      / 10000000.0 AS DECIMAL(10,2))      AS TotalRevenue_Cr,
    CAST(SUM(NetRevenue)   / 10000000.0 AS DECIMAL(10,2))      AS NetRevenue_Cr,
    CAST(AVG(Revenue)                   AS DECIMAL(12,0))      AS AvgBookingValue,
    CAST(AVG(CAST(DurationDays AS DECIMAL(8,2))) AS DECIMAL(6,2)) AS AvgTripDuration,
    CAST(AVG(SatisfactionScore)         AS DECIMAL(4,2))       AS AvgSatisfaction,
    CAST(100.0 * SUM(CASE WHEN BookingStatus = 'Cancelled' THEN 1 ELSE 0 END)
         / COUNT(*)                     AS DECIMAL(6,2))       AS CancellationRatePct
FROM dbo.FactTrip;
GO

/* ===========================================================================
   SECTION C -- ANALYTICAL QUERIES behind the dashboard insights
   =========================================================================== */

-- C1. Top 10 destinations by revenue, with rank and share of total
SELECT TOP 10
    DestinationName, Country, DestinationType,
    CAST(TotalRevenue / 10000000.0 AS DECIMAL(10,2)) AS Revenue_Cr,
    TotalBookings, AvgSatisfaction, CancellationRatePct,
    RANK() OVER (ORDER BY TotalRevenue DESC)         AS RevenueRank,
    CAST(100.0 * TotalRevenue / SUM(TotalRevenue) OVER () AS DECIMAL(6,2)) AS PctOfTotalRevenue
FROM dbo.vw_DestinationScorecard
ORDER BY TotalRevenue DESC;
GO

-- C2. Seasonality: revenue by month, indexed against the monthly average
WITH M AS (
    SELECT TripMonthName AS MonthName, TripMonthNo AS MonthNo, SUM(Revenue) AS Rev
    FROM dbo.vw_TripAnalysis GROUP BY TripMonthName, TripMonthNo
)
SELECT MonthName,
       CAST(Rev / 10000000.0 AS DECIMAL(10,2))                        AS Revenue_Cr,
       CAST(100.0 * Rev / AVG(Rev) OVER () AS DECIMAL(6,1))           AS SeasonalityIndex
FROM M ORDER BY MonthNo;
GO

-- C3. Channel profitability: gross vs net after commission
SELECT ChannelName, ChannelType,
       COUNT(*)                                                AS Bookings,
       CAST(SUM(Revenue)/10000000.0 AS DECIMAL(10,2))          AS Revenue_Cr,
       CAST(SUM(ChannelCommission)/100000.0 AS DECIMAL(10,2))  AS Commission_Lakh,
       CAST(SUM(NetRevenue)/10000000.0 AS DECIMAL(10,2))       AS NetRevenue_Cr,
       CAST(100.0*SUM(NetRevenue)/SUM(Revenue) AS DECIMAL(6,2)) AS NetMarginPct
FROM dbo.vw_TripAnalysis
GROUP BY ChannelName, ChannelType
ORDER BY SUM(NetRevenue) DESC;
GO

-- C4. Booking window vs cancellation: does booking early reduce cancellations?
SELECT BookingWindow,
       COUNT(*) AS Bookings,
       CAST(AVG(Revenue) AS DECIMAL(12,0)) AS AvgBookingValue,
       CAST(100.0*SUM(CASE WHEN BookingStatus='Cancelled' THEN 1 ELSE 0 END)/COUNT(*) AS DECIMAL(6,2)) AS CancellationRatePct
FROM dbo.vw_TripAnalysis GROUP BY BookingWindow ORDER BY BookingWindow;
GO

-- C5. Loyalty tier value: does the discount given to top tiers pay for itself?
SELECT LoyaltyTier,
       COUNT(DISTINCT TravellerID)                              AS Travellers,
       COUNT(*)                                                 AS Trips,
       CAST(1.0*COUNT(*)/COUNT(DISTINCT TravellerID) AS DECIMAL(6,2)) AS TripsPerTraveller,
       CAST(AVG(Revenue) AS DECIMAL(12,0))                      AS AvgTripValue,
       CAST(AVG(DiscountPct) AS DECIMAL(6,2))                   AS AvgDiscountPct,
       CAST(AVG(SatisfactionScore) AS DECIMAL(4,2))             AS AvgSatisfaction
FROM dbo.vw_TripAnalysis
GROUP BY LoyaltyTier
ORDER BY AVG(Revenue) DESC;
GO

-- C6. Year-on-year growth by travel scope
WITH Y AS (
    SELECT TripYear, TravelScope, SUM(Revenue) AS Rev
    FROM dbo.vw_TripAnalysis GROUP BY TripYear, TravelScope
)
SELECT TripYear, TravelScope,
       CAST(Rev/10000000.0 AS DECIMAL(10,2)) AS Revenue_Cr,
       CAST(100.0*(Rev - LAG(Rev) OVER (PARTITION BY TravelScope ORDER BY TripYear))
            / NULLIF(LAG(Rev) OVER (PARTITION BY TravelScope ORDER BY TripYear),0) AS DECIMAL(6,1)) AS YoYGrowthPct
FROM Y ORDER BY TravelScope, TripYear;
GO

-- C7. Satisfaction drivers: star rating vs peak season
SELECT StarRating,
       CAST(AVG(CASE WHEN IsPeakSeason=1 THEN SatisfactionScore END) AS DECIMAL(4,2)) AS PeakSeasonScore,
       CAST(AVG(CASE WHEN IsPeakSeason=0 THEN SatisfactionScore END) AS DECIMAL(4,2)) AS OffPeakScore,
       COUNT(*) AS Trips
FROM dbo.vw_TripAnalysis
WHERE SatisfactionScore IS NOT NULL
GROUP BY StarRating ORDER BY StarRating;
GO

-- C8. Top 20 travellers by lifetime value (feeds the drill-through page)
SELECT TOP 20 TravellerName, Nationality, CustomerSegment, LoyaltyTier,
       TripCount, CAST(LifetimeValue AS DECIMAL(14,0)) AS LifetimeValue,
       AvgTripValue, AvgSatisfaction, ValueQuartile
FROM dbo.vw_TravellerValue ORDER BY LifetimeValue DESC;
GO

PRINT 'Script 04 complete.';
GO
