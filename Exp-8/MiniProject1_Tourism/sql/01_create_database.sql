/* ===========================================================================
   MINI PROJECT I  -  TOURISM ANALYTICS
   Script 01 : Create database, schemas and tables
   Run this first, in SQL Server Management Studio (SSMS), against your
   local SQL Server instance.
   =========================================================================== */

USE master;
GO

IF DB_ID('TourismDW') IS NOT NULL
BEGIN
    ALTER DATABASE TourismDW SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE TourismDW;
END
GO

CREATE DATABASE TourismDW;
GO

USE TourismDW;
GO

/* ---------------------------------------------------------------------------
   Schemas
   stg = staging layer, holds the raw extract exactly as received (with its
         data-quality problems intact)
   dbo = presentation layer, holds the cleaned, conformed star schema that
         Power BI and Tableau connect to
   --------------------------------------------------------------------------- */
CREATE SCHEMA stg;
GO

/* ===========================================================================
   DIMENSION TABLES
   =========================================================================== */

CREATE TABLE dbo.DimDate (
    DateKey         INT           NOT NULL,
    FullDate        DATE          NOT NULL,
    [Year]          INT           NOT NULL,
    [Quarter]       VARCHAR(2)    NOT NULL,
    MonthNo         INT           NOT NULL,
    MonthName       VARCHAR(15)   NOT NULL,
    MonthYear       VARCHAR(10)   NOT NULL,
    DayOfMonth      INT           NOT NULL,
    DayName         VARCHAR(12)   NOT NULL,
    WeekOfYear      INT           NOT NULL,
    DayOfYear       INT           NOT NULL,
    IsWeekend       BIT           NOT NULL,
    Season          VARCHAR(12)   NOT NULL,
    FinancialYear   VARCHAR(10)   NOT NULL,
    IsPeakSeason    BIT           NOT NULL,
    CONSTRAINT PK_DimDate PRIMARY KEY CLUSTERED (DateKey)
);
GO

CREATE TABLE dbo.DimDestination (
    DestinationID   INT           NOT NULL,
    DestinationName VARCHAR(60)   NOT NULL,
    City            VARCHAR(40)   NOT NULL,
    StateProvince   VARCHAR(40)   NOT NULL,
    Country         VARCHAR(40)   NOT NULL,
    Region          VARCHAR(30)   NOT NULL,
    Continent       VARCHAR(20)   NOT NULL,
    DestinationType VARCHAR(20)   NOT NULL,
    Latitude        DECIMAL(9,4)  NOT NULL,
    Longitude       DECIMAL(9,4)  NOT NULL,
    CostIndex       DECIMAL(6,3)  NOT NULL,
    PopularityIndex DECIMAL(6,3)  NOT NULL,
    IsDomestic      BIT           NOT NULL,
    CONSTRAINT PK_DimDestination PRIMARY KEY CLUSTERED (DestinationID)
);
GO

CREATE TABLE dbo.DimTraveller (
    TravellerID      INT          NOT NULL,
    TravellerName    VARCHAR(60)  NOT NULL,
    Gender           VARCHAR(10)  NOT NULL,
    Age              INT          NOT NULL,
    AgeBand          VARCHAR(10)  NOT NULL,
    Nationality      VARCHAR(40)  NOT NULL,
    SignupDate       DATE         NOT NULL,
    CustomerSegment  VARCHAR(20)  NOT NULL,
    LoyaltyTier      VARCHAR(10)  NOT NULL,
    IsRepeatCustomer BIT          NOT NULL,
    CONSTRAINT PK_DimTraveller PRIMARY KEY CLUSTERED (TravellerID)
);
GO

CREATE TABLE dbo.DimAccommodation (
    AccommodationID   INT          NOT NULL,
    AccommodationName VARCHAR(60)  NOT NULL,
    AccommodationType VARCHAR(25)  NOT NULL,
    StarRating        INT          NOT NULL,
    DestinationID     INT          NOT NULL,
    PriceIndex        DECIMAL(6,3) NOT NULL,
    AvgRating         DECIMAL(4,1) NOT NULL,
    CONSTRAINT PK_DimAccommodation PRIMARY KEY CLUSTERED (AccommodationID)
);
GO

CREATE TABLE dbo.DimTransport (
    TransportID            INT          NOT NULL,
    TransportType          VARCHAR(20)  NOT NULL,
    Carrier                VARCHAR(30)  NOT NULL,
    TravelClass            VARCHAR(20)  NOT NULL,
    CostFactor             DECIMAL(6,3) NOT NULL,
    IsInternationalCapable BIT          NOT NULL,
    CONSTRAINT PK_DimTransport PRIMARY KEY CLUSTERED (TransportID)
);
GO

CREATE TABLE dbo.DimBookingChannel (
    ChannelID      INT          NOT NULL,
    ChannelName    VARCHAR(30)  NOT NULL,
    ChannelType    VARCHAR(15)  NOT NULL,
    CommissionRate DECIMAL(6,4) NOT NULL,
    CONSTRAINT PK_DimBookingChannel PRIMARY KEY CLUSTERED (ChannelID)
);
GO

/* ===========================================================================
   STAGING FACT TABLE  (raw -- no constraints, allows the dirty rows in)
   =========================================================================== */

CREATE TABLE stg.FactTrip_Raw (
    TripID            INT,
    BookingReference  VARCHAR(20),
    TravellerID       INT,
    DestinationID     INT,
    AccommodationID   INT,
    TransportID       INT,
    ChannelID         INT,
    BookingDateKey    INT,
    StartDateKey      INT,
    EndDateKey        INT,
    DurationDays      INT,
    NumTravellers     INT,
    LeadTimeDays      INT,
    AccommodationCost DECIMAL(14,2),
    TransportCost     DECIMAL(14,2),
    ActivityCost      DECIMAL(14,2),
    GrossAmount       DECIMAL(14,2),
    DiscountAmount    DECIMAL(14,2),
    Revenue           DECIMAL(14,2),
    ChannelCommission DECIMAL(14,2),
    NetRevenue        DECIMAL(14,2),
    SatisfactionScore DECIMAL(4,1) NULL,
    BookingStatus     VARCHAR(20)
);
GO

/* ===========================================================================
   PRESENTATION FACT TABLE  (cleaned -- populated by script 03)
   =========================================================================== */

CREATE TABLE dbo.FactTrip (
    TripID            INT           NOT NULL,
    BookingReference  VARCHAR(20)   NOT NULL,
    TravellerID       INT           NOT NULL,
    DestinationID     INT           NOT NULL,
    AccommodationID   INT           NOT NULL,
    TransportID       INT           NOT NULL,
    ChannelID         INT           NOT NULL,
    BookingDateKey    INT           NOT NULL,
    StartDateKey      INT           NOT NULL,
    EndDateKey        INT           NOT NULL,
    DurationDays      INT           NOT NULL,
    NumTravellers     INT           NOT NULL,
    LeadTimeDays      INT           NOT NULL,
    AccommodationCost DECIMAL(14,2) NOT NULL,
    TransportCost     DECIMAL(14,2) NOT NULL,
    ActivityCost      DECIMAL(14,2) NOT NULL,
    GrossAmount       DECIMAL(14,2) NOT NULL,
    DiscountAmount    DECIMAL(14,2) NOT NULL,
    Revenue           DECIMAL(14,2) NOT NULL,
    ChannelCommission DECIMAL(14,2) NOT NULL,
    NetRevenue        DECIMAL(14,2) NOT NULL,
    SatisfactionScore DECIMAL(4,1)  NULL,
    BookingStatus     VARCHAR(20)   NOT NULL,
    -- derived during cleaning
    RevenuePerTraveller DECIMAL(14,2) NOT NULL,
    RevenuePerDay       DECIMAL(14,2) NOT NULL,
    BookingWindow       VARCHAR(30)   NOT NULL,
    TripLengthBand      VARCHAR(30)   NOT NULL,
    CONSTRAINT PK_FactTrip PRIMARY KEY CLUSTERED (TripID)
);
GO

PRINT 'Script 01 complete: TourismDW created with 6 dimension tables, 1 staging table and 1 fact table.';
GO
