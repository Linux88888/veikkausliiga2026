"""
Veikkausliiga 2026 - Konfiguraatiotiedosto
Sisältää joukkueet, URL-osoitteet ja asetukset
"""

import json
import logging
from pathlib import Path

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Veikkausliiga 2026 joukkueet (päivitetty uusilla joukkueilla)
TEAMS_2026 = [
    "HJK",
    "KuPS",
    "FC Inter",
    "SJK",
    "FC Lahti",
    "Ilves",
    "FF Jaro",
    "VPS",
    "AC Oulu",
    "IF Gnistan",
    "IFK Mariehamn",
    "TPS"
]

# Seuratut pelaajat (päivitetty vuodelle 2026)
WATCHED_PLAYERS = [
    "Coffey, Ashley Mark",
    "Moreno Ciorciari, Jaime Jose",
    "Karjalainen, Rasmus",
    "Plange, Luke Elliot",
    "Odutayo, Colin"
]

# URL-osoitteet
VEIKKAUSLIIGA_BASE_URL = "https://www.veikkausliiga.com/tilastot/2026"
STANDINGS_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/joukkueet/"
PLAYERS_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/pelaajat/"
MATCHES_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/ottelut/?group=1"

# Konfiguraation tallennuspaikka
CONFIG_DIR = Path(__file__).parent.parent
OUTPUT_DIR = CONFIG_DIR / "output"
DATA_DIR = CONFIG_DIR / "data"

# Luo kansiot tarvittaessa
try:
    OUTPUT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    logger.info(f"✓ Output directory: {OUTPUT_DIR}")
    logger.info(f"✓ Data directory: {DATA_DIR}")
except Exception as e:
    logger.error(f"✗ Error creating directories: {e}")

# Analysointiparametrit
POINT_MULTIPLIERS = {
    "goal": 2.0,
    "shot": 0.1,
    "assist": 0.5,
    "red_card": -1.0,
    "yellow_card": -0.2
}

# Timeout ja retry-asetukset
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2

# Veikattu sarjajärjestys
PREDICTED_ORDER = [
    "HJK",
    "Ilves",
    "KuPS",
    "FC Inter",
    "SJK",
    "VPS",
    "FF Jaro",
    "FC Lahti",
    "IFK Mariehamn",
    "IF Gnistan",
    "AC Oulu",
    "TPS"
]

# ---------------------------------------------------------------------------
# Veikkausten pisteytysjärjestelmä
# ---------------------------------------------------------------------------

# Sarjataulukkoennuste: ero veikkaukseen (sijoituksia) → pisteet
STANDINGS_SCORING = {
    0: 3,  # Täsmälleen oikein
    1: 2,  # 1 sijoitus väärin
    2: 1,  # 2 sijoitusta väärin
    # >= 3 sijoitusta väärin: 0 pistettä
}

# Maalintekijäennuste
SCORER_SCORING = {
    "exact": 5,    # Täsmälleen oikea sijoitus
    "in_list": 2,  # Pelaaja top-listalla mutta väärässä sijoituksessa
}

# Kuinka monen parhaan maalintekijän lista otetaan huomioon
TOP_SCORERS_COUNT = 10

# ---------------------------------------------------------------------------
# Osallistujien veikkaukset
# ---------------------------------------------------------------------------
# Muokkaa tätä listaa lisäämällä omat veikkauksesi.
# standings_prediction: joukkueet sijoitusjärjestyksessä (1. → 12.)
# scorers_prediction:   pelaajat maalintekijäjärjestyksessä (1. → 5.)
PARTICIPANTS = [
    {
        "name": "Veikkaaja 1",
        "standings_prediction": [
            "HJK", "Ilves", "KuPS", "FC Inter", "SJK",
            "VPS", "FF Jaro", "FC Lahti", "IFK Mariehamn",
            "IF Gnistan", "AC Oulu", "TPS",
        ],
        "scorers_prediction": [
            "Plange, Luke",
            "Karjalainen, Rasmus",
            "Odutayo, Colin",
            "Coffey, Ashley",
            "Moreno, Jaime",
        ],
    },
    {
        "name": "Veikkaaja 2",
        "standings_prediction": [
            "KuPS", "HJK", "Ilves", "SJK", "FC Inter",
            "FF Jaro", "VPS", "TPS", "AC Oulu",
            "FC Lahti", "IF Gnistan", "IFK Mariehamn",
        ],
        "scorers_prediction": [
            "Karjalainen, Rasmus",
            "Odutayo, Colin",
            "Plange, Luke",
            "Moreno, Jaime",
            "Coffey, Ashley",
        ],
    },
    {
        "name": "Veikkaaja 3",
        "standings_prediction": [
            "Ilves", "HJK", "SJK", "KuPS", "FC Inter",
            "VPS", "FC Lahti", "FF Jaro", "AC Oulu",
            "TPS", "IF Gnistan", "IFK Mariehamn",
        ],
        "scorers_prediction": [
            "Odutayo, Colin",
            "Plange, Luke",
            "Moreno, Jaime",
            "Karjalainen, Rasmus",
            "Coffey, Ashley",
        ],
    },
]

def get_output_path(filename):
    """Palauttaa polun output-tiedostoon."""
    return OUTPUT_DIR / filename

def get_data_path(filename):
    """Palauttaa polun data-tiedostoon."""
    return DATA_DIR / filename
