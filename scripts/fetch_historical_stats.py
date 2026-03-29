"""
Veikkausliiga - Kaikkien aikojen tilastot
Generoi KaikkienAikojenTilastot.md-tiedoston historiallisista tilastoista.
"""

import logging
from datetime import datetime
from pathlib import Path

try:
    from config import get_output_path, TEAM_LOGOS
except ImportError:
    def get_output_path(filename):
        return Path("output") / filename
    TEAM_LOGOS = {}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Historiallinen data — Veikkausliiga-mestarit
# ---------------------------------------------------------------------------
VEIKKAUSLIIGA_CHAMPIONS = [
    (2025, "KuPS"),
    (2024, "KuPS"),
    (2023, "HJK"),
    (2022, "HJK"),
    (2021, "HJK"),
    (2020, "HJK"),
    (2019, "KuPS"),
    (2018, "HJK"),
    (2017, "HJK"),
    (2016, "IFK Mariehamn"),
    (2015, "SJK"),
    (2014, "HJK"),
    (2013, "HJK"),
    (2012, "HJK"),
    (2011, "HJK"),
    (2010, "HJK"),
    (2009, "HJK"),
    (2008, "FC Inter"),
    (2007, "Tampere United"),
    (2006, "Tampere United"),
    (2005, "MyPa"),
    (2004, "Haka"),
    (2003, "HJK"),
    (2002, "HJK"),
    (2001, "Tampere United"),
    (2000, "Haka"),
    (1999, "Haka"),
    (1998, "Haka"),
    (1997, "HJK"),
    (1996, "Jazz"),
    (1995, "Haka"),
    (1994, "TPV"),
    (1993, "Jazz"),
    (1992, "HJK"),
    (1991, "Kuusysi"),
    (1990, "HJK"),
]

# Mestaruusmäärät joukkueittain (laskettuna yllä olevasta listasta)
def count_championships(champions):
    counts = {}
    for _, team in champions:
        counts[team] = counts.get(team, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

# Kaikkien aikojen parhaat maalintekijät Veikkausliigassa (historialliset tiedot)
ALL_TIME_TOP_SCORERS = [
    {"pelaaja": "Valeri Popovitš",  "maalit": 166, "joukkueet": "Haka, HJK ym."},
    {"pelaaja": "Mika Aaltonen",    "maalit": 152, "joukkueet": "HJK, Haka ym."},
    {"pelaaja": "Mixu Paatelainen", "maalit": 102, "joukkueet": "Haka, TPS ym."},
    {"pelaaja": "Jonatan Johansson","maalit":  90, "joukkueet": "TPS, Jazz ym."},
    {"pelaaja": "Shefki Kuqi",      "maalit":  85, "joukkueet": "Mikkelin Palloilijat, HJK, FC Jokerit ym."},
    {"pelaaja": "Toni Lehtinen",    "maalit":  84, "joukkueet": "Tampere United ym."},
    {"pelaaja": "Aki Hyryläinen",   "maalit":  80, "joukkueet": "Haka ym."},
    {"pelaaja": "Pasi Rautiainen",  "maalit":  74, "joukkueet": "HJK ym."},
    {"pelaaja": "Sami Ristilä",     "maalit":  71, "joukkueet": "Haka, Tampere United ym."},
    {"pelaaja": "Jari Litmanen",    "maalit":  51, "joukkueet": "Reipas, HJK, MyPa, FC Lahti ym."},
]

# Ennätyksiä
RECORDS = [
    {"kuvaus": "Eniten mestaruuksia (1990–2025)",  "arvo": "HJK (17 mestaruutta 1990–2025, yli 30 kaikkiaan)"},
    {"kuvaus": "Eniten maaleja kaudella",            "arvo": "Valeri Popovitš / Kimmo Tarkkio — 23 maalia (1999)"},
    {"kuvaus": "Korkein voitto",                     "arvo": "HJK 12–1 Atlantis (1966)"},
    {"kuvaus": "Sarjan ennätysyleisö",               "arvo": "Olympiastadion, Helsinki"},
]


class HistoricalStatsProcessor:
    """Generoi kaikkien aikojen tilastot -raportin"""

    def save_report(self):
        """Tallentaa kaikkien aikojen tilastot KaikkienAikojenTilastot.md-tiedostoon"""
        try:
            report_path = get_output_path("KaikkienAikojenTilastot.md")
            championship_counts = count_championships(VEIKKAUSLIIGA_CHAMPIONS)

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# 🏅 Veikkausliiga — Kaikkien aikojen tilastot\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("*Lähde: Historialliset tilastot*\n\n")
                f.write("---\n\n")

                # Mestaruustaulukko
                f.write("## 🏆 Mestaruudet joukkueittain (1990–2025)\n\n")
                f.write("| # | Joukkue | Mestaruudet |\n")
                f.write("|:-:|---------|:-----------:|\n")
                for i, (team, count) in enumerate(championship_counts, 1):
                    logo_path = TEAM_LOGOS.get(team, "")
                    if logo_path:
                        team_cell = f'<img src="{logo_path}" width="20" height="20"> {team}'
                    else:
                        team_cell = team
                    f.write(f"| {i} | {team_cell} | **{count}** |\n")
                f.write("\n")

                # Mestarit vuosittain
                f.write("## 📅 Mestarit vuosittain (1990–2025)\n\n")
                f.write("| Vuosi | Mestari |\n")
                f.write("|:-----:|---------|\n")
                for year, team in VEIKKAUSLIIGA_CHAMPIONS:
                    logo_path = TEAM_LOGOS.get(team, "")
                    if logo_path:
                        team_cell = f'<img src="{logo_path}" width="16" height="16"> {team}'
                    else:
                        team_cell = team
                    f.write(f"| {year} | {team_cell} |\n")
                f.write("\n")

                # Kaikkien aikojen parhaat maalintekijät
                f.write("## ⚽ Kaikkien aikojen parhaat maalintekijät\n\n")
                f.write("| # | Pelaaja | Maalit | Joukkueet |\n")
                f.write("|:-:|---------|:------:|-----------|\n")
                for i, scorer in enumerate(ALL_TIME_TOP_SCORERS, 1):
                    f.write(
                        f"| {i} | {scorer['pelaaja']} | **{scorer['maalit']}** "
                        f"| {scorer['joukkueet']} |\n"
                    )
                f.write("\n")

                # Ennätykset
                f.write("## 📊 Ennätyksiä\n\n")
                f.write("| Kategoria | Ennätys |\n")
                f.write("|-----------|---------|\n")
                for rec in RECORDS:
                    f.write(f"| {rec['kuvaus']} | {rec['arvo']} |\n")
                f.write("\n")

            logger.info(f"✓ Kaikkien aikojen tilastot tallennettu: {report_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Virhe kaikkien aikojen tilastojen tallenuksessa: {e}")
            return False

    def run(self):
        """Pääfunktio"""
        logger.info("\n" + "="*60)
        logger.info("KAIKKIEN AIKOJEN TILASTOT - Veikkausliiga")
        logger.info("="*60)
        return self.save_report()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    processor = HistoricalStatsProcessor()
    success = processor.run()
    exit(0 if success else 1)
