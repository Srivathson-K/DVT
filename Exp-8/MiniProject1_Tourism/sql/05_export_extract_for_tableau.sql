/* ===========================================================================
   MINI PROJECT I  -  TOURISM ANALYTICS
   Script 05 : Export the Tableau extract from SQL Server

   WHY THIS SCRIPT EXISTS
   ----------------------
   Tableau Public cannot connect to a database. Its connectors are limited to
   Excel, text/CSV, spatial, statistical and a few web sources -- SQL Server,
   Oracle, MySQL and PostgreSQL are Tableau Desktop only.

   So the integration and preparation work is done in SQL Server (the view
   dbo.vw_TripAnalysis joins the fact table to all six dimensions), and the
   result of that view is exported once as a flat extract that Tableau Public
   consumes. Running this script is what makes the extract shipped in
   TourismAnalytics_Packaged.twbx demonstrably a SQL Server output rather than
   a file that merely happens to sit beside it.

   HOW TO EXPORT
   -------------
   Option A -- SSMS results grid (quickest)
     1. Run the SELECT below.
     2. Right-click anywhere in the results grid -> Save Results As...
     3. Save as  TourismTripAnalysis.csv
     4. IMPORTANT: Tools -> Options -> Query Results -> SQL Server ->
        Results to Grid -> tick "Include column headers when copying or
        saving the results", then reopen the query window. Without this the
        CSV has no header row.

   Option B -- Import and Export Wizard (more reliable for large results)
     1. Object Explorer -> right-click TourismDW -> Tasks -> Export Data...
     2. Source: SQL Server Native Client, database TourismDW
     3. Destination: Flat File Destination, format Delimited, comma,
        tick "Column names in the first data row"
     4. Choose "Write a query to specify the data to transfer" and paste the
        SELECT below.

   Either way you should get 12,000 data rows and 54 columns.
   =========================================================================== */

USE TourismDW;
GO

SELECT
    TripID, BookingReference, BookingStatus,
    TripStartDate, TripEndDate, BookingDate,
    TripYear, TripQuarter, TripMonthNo, TripMonthName, TripSeason, FinancialYear,
    CASE WHEN IsPeakSeason = 1 THEN 'Peak Season' ELSE 'Off Peak' END AS PeakSeasonLabel,
    DestinationName, City, Country, Region, Continent, DestinationType,
    Latitude, Longitude, TravelScope,
    TravellerID, TravellerName, Gender, Age, AgeBand, Nationality,
    CustomerSegment, LoyaltyTier,
    AccommodationName, AccommodationType, StarRating,
    TransportType, Carrier, TravelClass,
    ChannelName, ChannelType,
    DurationDays, NumTravellers, LeadTimeDays,
    AccommodationCost, TransportCost, ActivityCost,
    GrossAmount, DiscountAmount, Revenue, ChannelCommission, NetRevenue,
    SatisfactionScore,
    CASE WHEN SatisfactionScore IS NULL     THEN 'Not Rated'
         WHEN SatisfactionScore >= 8        THEN 'Promoter (8-10)'
         WHEN SatisfactionScore >= 6        THEN 'Passive (6-7.9)'
         ELSE                                    'Detractor (<6)' END AS SatisfactionBand,
    BookingWindow, TripLengthBand,
    TravellerDays
FROM dbo.vw_TripAnalysis
ORDER BY TripID;
GO

/* Verification: this must return 12000 */
SELECT COUNT(*) AS ExtractRowCount FROM dbo.vw_TripAnalysis;
GO
