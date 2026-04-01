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
    ALL_TIME_TOP_ATTENDANCES,
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
        # HJK voitti 1990, 1992, 1997, 2002, 2003, 2009, 2010, 2011, 2012, 2013, 2014,
        # 2017, 2018, 2020, 2021, 2022, 2023 = 17
        self.assertEqual(counts.get("HJK"), 17,
                         f"HJK:n mestaruusmäärä on väärä: {counts.get('HJK')}, odotetaan 17")

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

    def test_rafael_included(self):
        """Rafael on mukana listalla (kaikkien aikojen toiseksi paras maalintekijä)."""
        names = [p["pelaaja"] for p in ALL_TIME_TOP_SCORERS]
        self.assertIn("Rafael", names, "Rafael puuttuu kaikkien aikojen maalintekijälistalta")

    def test_popovits_is_top_scorer(self):
        """Valeri Popovitš on kaikkien aikojen paras maalintekijä (166 maalia)."""
        top = ALL_TIME_TOP_SCORERS[0]
        self.assertEqual(top["pelaaja"], "Valeri Popovitš")
        self.assertEqual(top["maalit"], 166)


class TestAllTimeTopAttendances(unittest.TestCase):
    """Testaa kaikkien aikojen yleisömäärälistan oikeellisuuden."""

    def test_ten_entries(self):
        """Listassa on täsmälleen 10 merkintää."""
        self.assertEqual(len(ALL_TIME_TOP_ATTENDANCES), 10,
                         f"Yleisömäärälistassa pitää olla 10 merkintää, löytyi {len(ALL_TIME_TOP_ATTENDANCES)}")

    def test_required_fields(self):
        """Jokaisella merkinnällä on vaaditut kentät oikeilla tyypeillä."""
        for entry in ALL_TIME_TOP_ATTENDANCES:
            self.assertIn("sija", entry)
            self.assertIn("pvm", entry)
            self.assertIn("ottelu", entry)
            self.assertIn("yleiso", entry)
            self.assertIn("stadion", entry)
            self.assertIsInstance(entry["yleiso"], int,
                                  f"Yleisömäärän pitää olla kokonaisluku, saatiin {type(entry['yleiso'])}")

    def test_unique_attendances(self):
        """Jokainen yleisömäärä on uniikki — ei sama luku useammassa ennätyksessä."""
        counts = [entry["yleiso"] for entry in ALL_TIME_TOP_ATTENDANCES]
        self.assertEqual(
            len(counts), len(set(counts)),
            f"Yleisömäärissä on duplikaatteja: {counts}"
        )

    def test_attendances_strictly_descending(self):
        """Yleisömäärät ovat aidosti laskevassa järjestyksessä (1. suurin, 10. pienin)."""
        counts = [entry["yleiso"] for entry in ALL_TIME_TOP_ATTENDANCES]
        for i in range(len(counts) - 1):
            self.assertGreater(
                counts[i], counts[i + 1],
                f"Sija {i+1} yleisömäärä ({counts[i]}) ei ole suurempi kuin sija {i+2} ({counts[i+1]})"
            )

    def test_top_attendance_is_hjk_hifk_1999(self):
        """Kaikkien aikojen yleisöennätys on HJK–HIFK 25.9.1999 (34 130 katsojaa)."""
        top = ALL_TIME_TOP_ATTENDANCES[0]
        self.assertEqual(top["yleiso"], 34130,
                         f"Yleisöennätyksen pitää olla 34130, saatiin {top['yleiso']}")
        self.assertEqual(top["sija"], 1)

    def test_rankings_match_order(self):
        """Sija-kenttä vastaa listan järjestystä (1–10)."""
        for i, entry in enumerate(ALL_TIME_TOP_ATTENDANCES, 1):
            self.assertEqual(
                entry["sija"], i,
                f"Listan kohta {i}: sija-kenttä on {entry['sija']}, pitäisi olla {i}"
            )


if __name__ == "__main__":
    unittest.main()
