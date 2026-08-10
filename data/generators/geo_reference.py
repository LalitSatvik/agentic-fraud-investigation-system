"""Small curated country/city reference table used to keep geo fields internally
consistent (country <-> city <-> lat/lon), which Faker's locale providers don't
guarantee out of the box. `tier` marks a subset as higher-risk jurisdictions for
sanctions/proxy-hosting style scenarios — these are used purely as synthetic
narrative labels for this demo, not real-world risk assessments.
"""
from datetime import datetime

# Fixed "as of" reference date the whole synthetic dataset is generated/queried
# relative to (account ages, "days since signup", etc.) — shared by the
# generators and the API's enrichment endpoints so both agree on "now".
TODAY = datetime(2026, 8, 11)

# (country_code, country_name, city, lat, lon, tier)
LOCATIONS = [
    ("US", "United States", "New York", 40.7128, -74.0060, "common"),
    ("US", "United States", "Chicago", 41.8781, -87.6298, "common"),
    ("US", "United States", "Austin", 30.2672, -97.7431, "common"),
    ("GB", "United Kingdom", "London", 51.5074, -0.1278, "common"),
    ("DE", "Germany", "Berlin", 52.5200, 13.4050, "common"),
    ("FR", "France", "Paris", 48.8566, 2.3522, "common"),
    ("CA", "Canada", "Toronto", 43.6532, -79.3832, "common"),
    ("AU", "Australia", "Sydney", -33.8688, 151.2093, "common"),
    ("IN", "India", "Mumbai", 19.0760, 72.8777, "common"),
    ("IN", "India", "Bengaluru", 12.9716, 77.5946, "common"),
    ("SG", "Singapore", "Singapore", 1.3521, 103.8198, "common"),
    ("JP", "Japan", "Tokyo", 35.6762, 139.6503, "common"),
    ("BR", "Brazil", "São Paulo", -23.5505, -46.6333, "common"),
    ("MX", "Mexico", "Mexico City", 19.4326, -99.1332, "common"),
    ("ZA", "South Africa", "Johannesburg", -26.2041, 28.0473, "common"),
    ("NL", "Netherlands", "Amsterdam", 52.3676, 4.9041, "common"),
    ("AE", "United Arab Emirates", "Dubai", 25.2048, 55.2708, "elevated"),
    ("RU", "Russia", "Moscow", 55.7558, 37.6173, "elevated"),
    ("NG", "Nigeria", "Lagos", 6.5244, 3.3792, "elevated"),
    ("PA", "Panama", "Panama City", 8.9824, -79.5199, "elevated"),
    ("KY", "Cayman Islands", "George Town", 19.2869, -81.3674, "elevated"),
    ("VU", "Vanuatu", "Port Vila", -17.7333, 168.3167, "elevated"),
    ("BY", "Belarus", "Minsk", 53.9006, 27.5590, "elevated"),
    ("KP", "North Korea", "Pyongyang", 39.0392, 125.7625, "elevated"),
    ("SC", "Seychelles", "Victoria", -4.6796, 55.4920, "elevated"),
]

COMMON = [loc for loc in LOCATIONS if loc[5] == "common"]
ELEVATED = [loc for loc in LOCATIONS if loc[5] == "elevated"]

HOSTING_ISPS = [
    ("HydraNet Hosting", 64512),
    ("Nebula Cloud Colo", 64513),
    ("QuietTunnel VPN", 64514),
    ("OrbitalProxy Ltd", 64515),
    ("DarkFiber Datacenter", 64516),
]

CONSUMER_ISPS = [
    ("Comcast", 7922),
    ("AT&T", 7018),
    ("Deutsche Telekom", 3320),
    ("BT Group", 2856),
    ("Airtel", 24560),
    ("NTT Communications", 4713),
    ("Vodafone", 1273),
    ("Telstra", 1221),
]

MERCHANT_CATEGORIES = [
    ("grocery", False),
    ("electronics", False),
    ("travel", False),
    ("utilities", False),
    ("subscription", False),
    ("restaurant", False),
    ("apparel", False),
    ("gambling", True),
    ("crypto_exchange", True),
    ("cash_agent", True),
    ("money_transfer", True),
    ("peer_transfer", False),
]

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
OS_BY_DEVICE = {
    "mobile": ["iOS 18", "Android 15", "Android 14"],
    "desktop": ["Windows 11", "macOS 15", "Ubuntu 24.04"],
    "tablet": ["iPadOS 18", "Android 15"],
}
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
