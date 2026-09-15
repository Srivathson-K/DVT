"""
Tourism Analytics -- synthetic star-schema data generator
Mini Project I : Data Visualization Techniques
Generates a dimensional model (6 dimensions + 1 fact) for SQL Server.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(20260914)
OUT = "data"

# ----------------------------------------------------------------------------
# 1. DimDate
# ----------------------------------------------------------------------------
start, end = date(2023, 1, 1), date(2026, 12, 31)
# DimDate is padded a year either side so booking dates (before travel) and
# end dates (after travel) always resolve to a valid date key.
cal_days = pd.date_range(date(2022, 1, 1), date(2027, 12, 31), freq="D")
days = pd.date_range(start, end, freq="D")   # trips only start inside 2023-2026

def season_of(m):
    if m in (12, 1, 2):  return "Winter"
    if m in (3, 4, 5):   return "Summer"
    if m in (6, 7, 8, 9): return "Monsoon"
    return "Autumn"

dim_date = pd.DataFrame({
    "DateKey":   [int(d.strftime("%Y%m%d")) for d in cal_days],
    "FullDate":  cal_days.date,
    "Year":      cal_days.year,
    "Quarter":   ["Q" + str(q) for q in cal_days.quarter],
    "MonthNo":   cal_days.month,
    "MonthName": cal_days.strftime("%B"),
    "MonthYear": cal_days.strftime("%b-%Y"),
    "DayOfMonth":cal_days.day,
    "DayName":   cal_days.strftime("%A"),
    "WeekOfYear":cal_days.isocalendar().week.astype(int).values,
    "DayOfYear": cal_days.dayofyear,
})
dim_date["IsWeekend"]     = dim_date["DayName"].isin(["Saturday", "Sunday"]).map({True: 1, False: 0})
dim_date["Season"]        = dim_date["MonthNo"].map(season_of)
dim_date["FinancialYear"] = np.where(dim_date["MonthNo"] >= 4,
                                     "FY" + dim_date["Year"].astype(str).str[2:] + "-" + (dim_date["Year"] + 1).astype(str).str[2:],
                                     "FY" + (dim_date["Year"] - 1).astype(str).str[2:] + "-" + dim_date["Year"].astype(str).str[2:])
dim_date["IsPeakSeason"]  = dim_date["MonthNo"].isin([4, 5, 10, 11, 12]).map({True: 1, False: 0})

# ----------------------------------------------------------------------------
# 2. DimDestination
# ----------------------------------------------------------------------------
destinations = [
    # Name, City, State/Province, Country, Region, Continent, Type, Lat, Lon, CostIdx, PopIdx
    ("Goa Beaches",            "Panaji",      "Goa",              "India",       "South Asia",      "Asia",          "Beach",     15.4909,  73.8278, 0.85, 1.35),
    ("Jaipur Heritage Circuit","Jaipur",      "Rajasthan",        "India",       "South Asia",      "Asia",          "Heritage",  26.9124,  75.7873, 0.75, 1.20),
    ("Manali Hills",           "Manali",      "Himachal Pradesh", "India",       "South Asia",      "Asia",          "Hill Station",32.2396, 77.1887, 0.70, 1.15),
    ("Kerala Backwaters",      "Alappuzha",   "Kerala",           "India",       "South Asia",      "Asia",          "Nature",     9.4981,  76.3388, 0.80, 1.10),
    ("Andaman Islands",        "Port Blair",  "Andaman & Nicobar","India",       "South Asia",      "Asia",          "Island",    11.6234,  92.7265, 1.15, 0.70),
    ("Leh Ladakh Expedition",  "Leh",         "Ladakh",           "India",       "South Asia",      "Asia",          "Adventure", 34.1526,  77.5771, 1.10, 0.65),
    ("Varanasi Ghats",         "Varanasi",    "Uttar Pradesh",    "India",       "South Asia",      "Asia",          "Pilgrimage",25.3176,  82.9739, 0.55, 0.90),
    ("Bali Retreat",           "Denpasar",    "Bali",             "Indonesia",   "South East Asia", "Asia",          "Beach",     -8.6500, 115.2167, 1.20, 1.25),
    ("Bangkok & Phuket",       "Bangkok",     "Bangkok",          "Thailand",    "South East Asia", "Asia",          "City Break",13.7563, 100.5018, 1.05, 1.30),
    ("Singapore City Break",   "Singapore",   "Singapore",        "Singapore",   "South East Asia", "Asia",          "City Break", 1.3521, 103.8198, 1.45, 1.05),
    ("Dubai Desert & City",    "Dubai",       "Dubai",            "UAE",         "Middle East",     "Asia",          "City Break",25.2048,  55.2708, 1.55, 1.20),
    ("Maldives Atolls",        "Male",        "Kaafu",            "Maldives",    "South Asia",      "Asia",          "Island",     4.1755,  73.5093, 2.30, 0.85),
    ("Kathmandu & Pokhara",    "Kathmandu",   "Bagmati",          "Nepal",       "South Asia",      "Asia",          "Adventure", 27.7172,  85.3240, 0.70, 0.75),
    ("Colombo & Kandy",        "Colombo",     "Western",          "Sri Lanka",   "South Asia",      "Asia",          "Heritage",   6.9271,  79.8612, 0.80, 0.70),
    ("Paris & Loire Valley",   "Paris",       "Ile-de-France",    "France",      "Western Europe",  "Europe",        "City Break",48.8566,   2.3522, 1.95, 0.95),
    ("Swiss Alps Tour",        "Interlaken",  "Bern",             "Switzerland", "Western Europe",  "Europe",        "Hill Station",46.6863,  7.8632, 2.40, 0.80),
    ("Rome & Amalfi Coast",    "Rome",        "Lazio",            "Italy",       "Southern Europe", "Europe",        "Heritage",  41.9028,  12.4964, 1.85, 0.90),
    ("London Explorer",        "London",      "England",          "United Kingdom","Western Europe","Europe",        "City Break",51.5074,  -0.1278, 2.05, 0.85),
    ("Santorini Islands",      "Thira",       "South Aegean",     "Greece",      "Southern Europe", "Europe",        "Island",    36.3932,  25.4615, 1.75, 0.75),
    ("Iceland Northern Lights","Reykjavik",   "Capital Region",   "Iceland",     "Northern Europe", "Europe",        "Nature",    64.1466, -21.9426, 2.20, 0.55),
    ("New York City Break",    "New York",    "New York",         "USA",         "North America",   "North America", "City Break",40.7128, -74.0060, 2.10, 0.80),
    ("Grand Canyon Trail",     "Flagstaff",   "Arizona",          "USA",         "North America",   "North America", "Adventure", 35.1983, -111.6513,1.70, 0.60),
    ("Toronto & Niagara",      "Toronto",     "Ontario",          "Canada",      "North America",   "North America", "Nature",    43.6532, -79.3832, 1.65, 0.60),
    ("Cancun Riviera",         "Cancun",      "Quintana Roo",     "Mexico",      "Latin America",   "North America", "Beach",     21.1619, -86.8515, 1.40, 0.70),
    ("Rio de Janeiro",         "Rio de Janeiro","Rio de Janeiro", "Brazil",      "Latin America",   "South America", "City Break",-22.9068,-43.1729, 1.30, 0.50),
    ("Machu Picchu Trek",      "Cusco",       "Cusco",            "Peru",        "Latin America",   "South America", "Adventure", -13.5319,-71.9675,1.35, 0.45),
    ("Cape Town & Safari",     "Cape Town",   "Western Cape",     "South Africa","Africa",          "Africa",        "Wildlife",  -33.9249, 18.4241, 1.50, 0.55),
    ("Serengeti Safari",       "Arusha",      "Arusha",           "Tanzania",    "Africa",          "Africa",        "Wildlife",  -3.3869,  36.6830, 1.80, 0.40),
    ("Cairo & Nile Cruise",    "Cairo",       "Cairo",            "Egypt",       "Africa",          "Africa",        "Heritage",  30.0444,  31.2357, 1.25, 0.60),
    ("Sydney & Great Barrier Reef","Sydney",  "New South Wales",  "Australia",   "Oceania",         "Oceania",       "Beach",     -33.8688,151.2093, 2.00, 0.65),
    ("Queenstown Adventure",   "Queenstown",  "Otago",            "New Zealand", "Oceania",         "Oceania",       "Adventure", -45.0312,168.6626, 1.90, 0.45),
    ("Tokyo & Kyoto",          "Tokyo",       "Tokyo",            "Japan",       "East Asia",       "Asia",          "City Break",35.6762, 139.6503, 1.95, 0.90),
]
dim_destination = pd.DataFrame(destinations, columns=[
    "DestinationName","City","StateProvince","Country","Region","Continent",
    "DestinationType","Latitude","Longitude","CostIndex","PopularityIndex"])
dim_destination.insert(0, "DestinationID", range(1, len(dim_destination) + 1))
dim_destination["IsDomestic"] = (dim_destination["Country"] == "India").map({True: 1, False: 0})

# ----------------------------------------------------------------------------
# 3. DimTraveller
# ----------------------------------------------------------------------------
N_TRAV = 2400
first_m = ["Arjun","Rahul","Vikram","Karthik","Aditya","Rohan","Siddharth","Nikhil","Aravind","Manish",
           "James","Michael","David","Daniel","Thomas","Oliver","Lucas","Noah","Ethan","Liam",
           "Hiroshi","Wei","Ahmed","Omar","Carlos","Mateo","Pierre","Hans","Marco","Ivan"]
first_f = ["Ananya","Priya","Divya","Meera","Sneha","Kavya","Lakshmi","Nandini","Ishita","Shruti",
           "Emma","Olivia","Sophia","Charlotte","Amelia","Isabella","Mia","Ava","Grace","Chloe",
           "Yuki","Mei","Fatima","Layla","Sofia","Valentina","Camille","Anna","Giulia","Elena"]
last = ["Sharma","Iyer","Reddy","Nair","Patel","Menon","Rao","Kulkarni","Bose","Chatterjee","Gupta","Singh",
        "Smith","Johnson","Williams","Brown","Jones","Miller","Davis","Wilson","Taylor","Anderson",
        "Tanaka","Chen","Khan","Al-Sayed","Garcia","Rodriguez","Dubois","Muller","Rossi","Petrov"]

nationalities = ["India","United Kingdom","USA","Germany","France","Australia","Canada","Singapore",
                 "UAE","Japan","Netherlands","Italy","Spain","China","South Africa"]
nat_w = np.array([46,8,8,5,4,4,4,3.5,3.5,3,2.5,2,2,2,2.5]); nat_w = nat_w / nat_w.sum()

gender = rng.choice(["Male","Female"], N_TRAV, p=[0.53, 0.47])
names = [f"{rng.choice(first_m if g=='Male' else first_f)} {rng.choice(last)}" for g in gender]
age = np.clip(rng.normal(38, 13, N_TRAV), 18, 78).round().astype(int)

def age_band(a):
    if a < 25: return "18-24"
    if a < 35: return "25-34"
    if a < 45: return "35-44"
    if a < 55: return "45-54"
    if a < 65: return "55-64"
    return "65+"

signup = [start + timedelta(days=int(rng.integers(0, 1200))) for _ in range(N_TRAV)]

dim_traveller = pd.DataFrame({
    "TravellerID": range(1, N_TRAV + 1),
    "TravellerName": names,
    "Gender": gender,
    "Age": age,
    "AgeBand": [age_band(a) for a in age],
    "Nationality": rng.choice(nationalities, N_TRAV, p=nat_w),
    "SignupDate": signup,
})
dim_traveller["CustomerSegment"] = rng.choice(
    ["Solo Traveller","Couple","Family","Group Tour","Business"],
    N_TRAV, p=[0.22, 0.28, 0.27, 0.15, 0.08])
# loyalty tier correlated with how long they've been signed up
tenure = np.array([(date(2026, 12, 31) - s).days for s in signup])
tier_score = tenure / 1200 + rng.normal(0, 0.25, N_TRAV)
dim_traveller["LoyaltyTier"] = pd.cut(tier_score, [-9, 0.35, 0.65, 0.9, 9],
                                      labels=["Blue","Silver","Gold","Platinum"]).astype(str)
dim_traveller["IsRepeatCustomer"] = (tenure > 500).astype(int)

# ----------------------------------------------------------------------------
# 4. DimAccommodation
# ----------------------------------------------------------------------------
acc_types = {"Luxury Hotel": (5, 2.30), "Business Hotel": (4, 1.45), "Boutique Hotel": (4, 1.30),
             "Resort": (5, 2.05), "Budget Hotel": (3, 0.80), "Homestay": (3, 0.60),
             "Hostel": (2, 0.35), "Villa": (5, 1.95), "Serviced Apartment": (4, 1.25)}
brands = ["Taj","Oberoi","Marriott","Hilton","Novotel","Radisson","Ibis","Zostel","Leela",
          "Hyatt","Accor","Sarovar","Fern","Treebo","Local Heritage","Coastal Retreat"]
acc_rows, aid = [], 1
for _, d in dim_destination.iterrows():
    chosen = rng.choice(list(acc_types.keys()), size=int(rng.integers(4, 7)), replace=False)
    for t in chosen:
        stars_base, price_idx = acc_types[t]
        stars = int(np.clip(stars_base + rng.integers(-1, 1), 1, 5))
        acc_rows.append((aid, f"{rng.choice(brands)} {d['City']}", t, stars,
                         int(d["DestinationID"]), round(price_idx * float(d["CostIndex"]), 3),
                         round(float(np.clip(rng.normal(3.4 + stars * 0.25, 0.4), 2.0, 5.0)), 1)))
        aid += 1
dim_accommodation = pd.DataFrame(acc_rows, columns=[
    "AccommodationID","AccommodationName","AccommodationType","StarRating",
    "DestinationID","PriceIndex","AvgRating"])

# ----------------------------------------------------------------------------
# 5. DimTransport
# ----------------------------------------------------------------------------
transport = [
    ("Flight","IndiGo","Economy",1.00),   ("Flight","Air India","Economy",1.10),
    ("Flight","Air India","Business",2.90),("Flight","Emirates","Economy",1.35),
    ("Flight","Emirates","Business",3.60), ("Flight","Singapore Airlines","Economy",1.40),
    ("Flight","Lufthansa","Economy",1.30), ("Flight","Qatar Airways","Business",3.40),
    ("Train","Indian Railways","AC 2-Tier",0.35),("Train","Indian Railways","AC 3-Tier",0.25),
    ("Train","Eurail","First Class",0.95), ("Train","Shinkansen","Standard",0.85),
    ("Bus","Volvo Coach","Semi-Sleeper",0.18),("Bus","State Transport","Standard",0.10),
    ("Car Rental","Zoomcar","SUV",0.55),   ("Car Rental","Hertz","Sedan",0.65),
    ("Cruise","Cordelia Cruises","Cabin",1.80),("Ferry","Makruzz","Premium",0.30),
]
dim_transport = pd.DataFrame(transport, columns=["TransportType","Carrier","TravelClass","CostFactor"])
dim_transport.insert(0, "TransportID", range(1, len(dim_transport) + 1))
dim_transport["IsInternationalCapable"] = dim_transport["TransportType"].isin(
    ["Flight","Cruise"]).astype(int)

# ----------------------------------------------------------------------------
# 6. DimBookingChannel
# ----------------------------------------------------------------------------
channels = [("Company Website","Direct",0.02),("Mobile App","Direct",0.02),
            ("Walk-in Branch","Offline",0.00),("Call Centre","Direct",0.01),
            ("MakeMyTrip","OTA",0.14),("Booking.com","OTA",0.15),
            ("Expedia","OTA",0.16),("Travel Agent","Partner",0.10),
            ("Corporate Portal","Partner",0.07)]
dim_channel = pd.DataFrame(channels, columns=["ChannelName","ChannelType","CommissionRate"])
dim_channel.insert(0, "ChannelID", range(1, len(dim_channel) + 1))

# ----------------------------------------------------------------------------
# 7. FactTrip
# ----------------------------------------------------------------------------
N_FACT = 12000

# Destination choice weighted by popularity
dest_w = dim_destination["PopularityIndex"].values.astype(float)
dest_w = dest_w / dest_w.sum()
dest_idx = rng.choice(len(dim_destination), N_FACT, p=dest_w)

# Start date weighted by seasonal demand (peak months busier) and yearly growth
month_weight = {1:0.95,2:0.85,3:0.90,4:1.25,5:1.40,6:0.80,7:0.75,8:0.80,
                9:0.85,10:1.30,11:1.25,12:1.45}
year_growth  = {2023:0.80, 2024:0.95, 2025:1.15, 2026:1.25}
w = np.array([month_weight[d.month] * year_growth[d.year] for d in days], dtype=float)
w = w / w.sum()
start_pos = rng.choice(len(days), N_FACT, p=w)
start_dates = days[start_pos]

dest = dim_destination.iloc[dest_idx].reset_index(drop=True)

# Duration: longer for long-haul / adventure
base_dur = np.where(dest["IsDomestic"].values == 1, 4.5, 8.0)
base_dur = base_dur + np.where(dest["DestinationType"].isin(["Adventure","Wildlife"]).values, 2.0, 0.0)
duration = np.clip(rng.gamma(4.0, base_dur / 4.0), 1, 28).round().astype(int)
end_dates = start_dates + pd.to_timedelta(duration, unit="D")

# Travellers
trav_idx = rng.integers(0, N_TRAV, N_FACT)
trav = dim_traveller.iloc[trav_idx].reset_index(drop=True)
seg_size = {"Solo Traveller":1, "Couple":2, "Family":4, "Group Tour":7, "Business":1}
num_trav = np.array([seg_size[s] for s in trav["CustomerSegment"]])
num_trav = np.clip(num_trav + rng.integers(-1, 2, N_FACT) * (num_trav > 2), 1, 12)

# Accommodation must belong to the chosen destination
acc_by_dest = {int(k): v["AccommodationID"].values for k, v in dim_accommodation.groupby("DestinationID")}
acc_ids = np.array([rng.choice(acc_by_dest[int(d)]) for d in dest["DestinationID"]])
acc = dim_accommodation.set_index("AccommodationID").loc[acc_ids].reset_index()

# Transport: international destinations must use international-capable transport
intl_ids  = dim_transport.loc[dim_transport["IsInternationalCapable"] == 1, "TransportID"].values
all_ids   = dim_transport["TransportID"].values
trn_ids = np.array([rng.choice(intl_ids) if dom == 0 else rng.choice(all_ids)
                    for dom in dest["IsDomestic"].values])
trn = dim_transport.set_index("TransportID").loc[trn_ids].reset_index()

# Channel
chan_w = np.array([0.13,0.12,0.05,0.06,0.16,0.15,0.13,0.12,0.08]); chan_w = chan_w/chan_w.sum()
chan_ids = rng.choice(dim_channel["ChannelID"].values, N_FACT, p=chan_w)
chan = dim_channel.set_index("ChannelID").loc[chan_ids].reset_index()

# ---- Costs (INR) ----
peak = np.isin(start_dates.month, [4, 5, 10, 11, 12]).astype(float)
peak_mult = 1.0 + 0.18 * peak

acc_cost = (2800 * acc["PriceIndex"].values * duration * np.ceil(num_trav / 2)
            * peak_mult * rng.normal(1.0, 0.12, N_FACT))
trn_cost = (9500 * trn["CostFactor"].values * num_trav
            * np.where(dest["IsDomestic"].values == 1, 1.0, 2.6)
            * peak_mult * rng.normal(1.0, 0.15, N_FACT))
act_cost = (1900 * dest["CostIndex"].values * duration * num_trav
            * rng.normal(1.0, 0.22, N_FACT)
            * np.where(dest["DestinationType"].isin(["Adventure","Wildlife"]).values, 1.5, 1.0))

acc_cost = np.clip(acc_cost, 1500, None).round(2)
trn_cost = np.clip(trn_cost, 800, None).round(2)
act_cost = np.clip(act_cost, 500, None).round(2)
gross = acc_cost + trn_cost + act_cost

tier_disc = trav["LoyaltyTier"].map({"Blue":0.00,"Silver":0.03,"Gold":0.06,"Platinum":0.10}).values
promo     = rng.choice([0.0, 0.05, 0.10, 0.15], N_FACT, p=[0.60, 0.20, 0.14, 0.06])
disc_pct  = np.clip(tier_disc + promo, 0, 0.25)
discount  = (gross * disc_pct).round(2)
revenue   = (gross - discount).round(2)
commission= (revenue * chan["CommissionRate"].values).round(2)
net_rev   = (revenue - commission).round(2)

# Booking lead time
lead = np.clip(rng.gamma(2.2, 22, N_FACT), 1, 300).round().astype(int)
book_dates = start_dates - pd.to_timedelta(lead, unit="D")

# Booking status
status = rng.choice(["Completed","Cancelled","No Show"], N_FACT, p=[0.915, 0.070, 0.015])
status = np.where(np.array([d.date() for d in start_dates]) > date(2026, 9, 14),
                  np.where(rng.random(N_FACT) < 0.93, "Confirmed", "Cancelled"), status)

# Satisfaction: driven by star rating, discount, and whether it was a peak crowd period
sat = (5.2 + 0.42 * acc["StarRating"].values - 0.55 * peak
       + 1.6 * disc_pct - 0.02 * duration + rng.normal(0, 0.85, N_FACT))
sat = np.clip(sat, 1, 10).round(1)
sat = np.where(np.isin(status, ["Cancelled","No Show","Confirmed"]), np.nan, sat)

fact = pd.DataFrame({
    "TripID": range(1, N_FACT + 1),
    "BookingReference": ["TRP" + str(100000 + i) for i in range(1, N_FACT + 1)],
    "TravellerID": trav["TravellerID"].values,
    "DestinationID": dest["DestinationID"].values,
    "AccommodationID": acc["AccommodationID"].values,
    "TransportID": trn["TransportID"].values,
    "ChannelID": chan["ChannelID"].values,
    "BookingDateKey": [int(d.strftime("%Y%m%d")) for d in book_dates],
    "StartDateKey": [int(d.strftime("%Y%m%d")) for d in start_dates],
    "EndDateKey": [int(d.strftime("%Y%m%d")) for d in end_dates],
    "DurationDays": duration,
    "NumTravellers": num_trav,
    "LeadTimeDays": lead,
    "AccommodationCost": acc_cost,
    "TransportCost": trn_cost,
    "ActivityCost": act_cost,
    "GrossAmount": gross.round(2),
    "DiscountAmount": discount,
    "Revenue": revenue,
    "ChannelCommission": commission,
    "NetRevenue": net_rev,
    "SatisfactionScore": sat,
    "BookingStatus": status,
})

# ---- Deliberate data-quality issues for the "data cleaning" section ----
# (a) missing satisfaction scores already exist for cancelled trips
# (b) a handful of duplicated bookings
dupes = fact.sample(60, random_state=7).copy()
dupes["TripID"] = range(N_FACT + 1, N_FACT + 61)
fact = pd.concat([fact, dupes], ignore_index=True)
# (c) inconsistent status casing
mask = fact.sample(frac=0.03, random_state=11).index
fact.loc[mask, "BookingStatus"] = fact.loc[mask, "BookingStatus"].str.upper()
# (d) a few negative durations (data entry errors)
bad = fact.sample(25, random_state=13).index
fact.loc[bad, "DurationDays"] = -fact.loc[bad, "DurationDays"]

# ----------------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------------
files = {
    "DimDate.csv": dim_date,
    "DimDestination.csv": dim_destination,
    "DimTraveller.csv": dim_traveller,
    "DimAccommodation.csv": dim_accommodation,
    "DimTransport.csv": dim_transport,
    "DimBookingChannel.csv": dim_channel,
    "FactTrip.csv": fact,
}
for fn, df in files.items():
    df.to_csv(f"{OUT}/{fn}", index=False)
    print(f"{fn:26s} {len(df):>7,} rows  x {len(df.columns):>2} cols")

print("\nRevenue total : Rs {:,.0f}".format(fact.loc[fact.BookingStatus.str.title()=="Completed","Revenue"].sum()))
print("Date range    :", fact.StartDateKey.min(), "-", fact.StartDateKey.max())
