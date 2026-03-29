"""
Yksikkötestit kaikkien aikojen tilastoille (HistoricalStatsProcessor).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_historical_stats import (
    VEIKKAUSLIIGA_CHAMPIONS,
    ALL_TIME_TOP_SCORERS,
    RECORDS,
    count_championships,
)


class TestVeikkausliigaChampions(unittest.TestCase):
    """Testaa mestariluettelon johdonmukaisuuden."""

    def test_covers_full_veikkausliiga_era(self):
        """Lista kattaa koko Veikkausliiga-kauden 1990–2025."""
        years = [year for year, _ in VEIKKAUSLIIGA_CHAMPIONS]
        self.assertIn(1990, years, "Vuosi 1990 (Veikkausliigan ensimmäinen kausi) puuttuu")
        self.assertIn(2025, years, "Vuosi 2025 (viimeisin kausi) puuttuu")

    def test_no_duplicate_years(self):
        """Sama vuosi ei esiinny kahdesti."""
        years = [year for year, _ in VEIKKAUSLIIGA_CHAMPIONS]
        self.assertEqual(len(years), len(set(years)), "Listassa on vuosiduplikaatteja")

    def test_consecutive_years(self):
        """Jokaiselle vuodelle 1990–2025 on mestari."""
        years = sorted(year for year, _ in VEIKKAUSLIIGA_CHAMPIONS)
        expected = list(range(1990, 2026))
        self.assertEqual(years, expected, "Jotkin vuodet puuttuvat tai ovat väärässä järjestyksessä")

    def test_1990_champion_hjk(self):
        """1990 mestari on HJK (Veikkausliigan ensimmäinen mestari)."""
        champion_1990 = next((team for year, team in VEIKKAUSLIIGA_CHAMPIONS if year == 1990), None)
        self.assertEqual(champion_1990, "HJK")

    def test_hjk_championship_count(self):
        """HJK:lla on oikea mestaruusmäärä listalla (1990–2025)."""
        counts = dict(count_championships(VEIKKAUSLIIGA_CHAMPIONS))
        # HJK voitti 1990, 1992, 1997, 2003, 2008, 2009, 2010, 2012, 2013, 2014,
        # 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 = 18
        self.assertEqual(counts.get("HJK"), 18,
                         f"HJK:n mestaruusmäärä on väärä: {counts.get('HJK')}, odotetaan 18")

    def test_jazz_championship_count(self):
        """Jazz voitti mestaruuden kahdesti (1993 ja 1996)."""
        counts = dict(count_championships(VEIKKAUSLIIGA_CHAMPIONS))
        self.assertEqual(counts.get("Jazz"), 2)

    def test_early_champions_included(self):
        """Varhaisen Veikkausliiga-kauden mestarit (1990–1994) ovat mukana."""
        early_years = {year: team for year, team in VEIKKAUSLIIGA_CHAMPIONS if year < 1995}
        self.assertEqual(len(early_years), 5, "Vuodet 1990–1994 eivät kaikki ole listalla")
        self.assertIn(1991, early_years, "Vuosi 1991 puuttuu")
        self.assertIn(1992, early_years, "Vuosi 1992 puuttuu")
        self.assertIn(1993, early_years, "Vuosi 1993 puuttuu")
        self.assertIn(1994, early_years, "Vuosi 1994 puuttuu")


class TestRecords(unittest.TestCase):
    """Testaa ennätystaulukon johdonmukaisuuden."""

    def test_records_year_range_covers_1990(self):
        """Ennätysteksti kattaa Veikkausliiga-kauden alusta 1990."""
        mestaruus_record = next(
            (r for r in RECORDS if "mestaruuksia" in r["kuvaus"].lower()), None
        )
        self.assertIsNotNone(mestaruus_record, "Mestaruusennätys puuttuu RECORDS-listalta")
        self.assertIn("1990", mestaruus_record["kuvaus"],
                      "Ennätystekstissä pitäisi viitata vuoteen 1990")

    def test_records_hjk_count_matches_list(self):
        """RECORDS-teksti mainitsee saman mestaruusmäärän kuin laskettu arvo."""
        counts = dict(count_championships(VEIKKAUSLIIGA_CHAMPIONS))
        hjk_count = counts.get("HJK", 0)
        mestaruus_record = next(
            (r for r in RECORDS if "mestaruuksia" in r["kuvaus"].lower()), None
        )
        self.assertIsNotNone(mestaruus_record)
        self.assertIn(str(hjk_count), mestaruus_record["arvo"],
                      f"RECORDS ei mainitse HJK:n laskettua mestaruusmäärää {hjk_count}")


class TestAllTimeTopScorers(unittest.TestCase):
    """Testaa kaikkien aikojen maalintekijälistan rakenteen."""

    def test_ten_scorers(self):
        """Listassa on 10 pelaajaa."""
        self.assertEqual(len(ALL_TIME_TOP_SCORERS), 10)

    def test_scorers_sorted_descending(self):
        """Maalimäärät ovat laskevassa järjestyksessä."""
        goals = [p["maalit"] for p in ALL_TIME_TOP_SCORERS]
        self.assertEqual(goals, sorted(goals, reverse=True),
                         "Maalintekijät eivät ole laskevassa järjestyksessä")

    def test_required_fields(self):
        """Jokaisella pelaajalla on pelaaja, maalit ja joukkueet -kentät."""
        for scorer in ALL_TIME_TOP_SCORERS:
            self.assertIn("pelaaja", scorer)
            self.assertIn("maalit", scorer)
            self.assertIn("joukkueet", scorer)
            self.assertIsInstance(scorer["maalit"], int)


if __name__ == "__main__":
    unittest.main()
