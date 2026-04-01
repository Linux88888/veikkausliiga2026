"""
Yksikkötestit HistoricalAttendanceFetcher-luokan analytiikkafunktioille.
Testaa vuosikohtaisten keskiarvojen laskentaa, koronahuomion merkitsemistä
sekä trendianalyysiä.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_historical_attendance import HistoricalAttendanceFetcher, FIRST_SEASON, LAST_SEASON


def _make_matches(year_attendance_pairs):
    """Apufunktio: muodostaa ottelulistoista yksinkertaisen testidatan."""
    matches = []
    for year, attendances in year_attendance_pairs:
        for i, att in enumerate(attendances):
            matches.append({
                "year": year,
                "date": f"1.6.{year}",
                "home": "HJK",
                "away": "KuPS",
                "score": "1 — 0",
                "attendance": att,
            })
    return matches


class TestComputeYearlyStats(unittest.TestCase):
    """Testaa compute_yearly_stats()-metodia."""

    def setUp(self):
        self.fetcher = HistoricalAttendanceFetcher()

    def test_basic_average(self):
        """Yksinkertainen kolmen ottelun kausi: keskiarvo lasketaan oikein."""
        matches = _make_matches([(2019, [3000, 5000, 7000])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertIn(2019, stats)
        self.assertEqual(stats[2019]["matches"], 3)
        self.assertEqual(stats[2019]["total"], 15000)
        self.assertEqual(stats[2019]["average"], 5000)

    def test_max_min_attendance(self):
        """max_att ja min_att lasketaan oikein."""
        matches = _make_matches([(2018, [1000, 9000, 4500])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertEqual(stats[2018]["max_att"], 9000)
        self.assertEqual(stats[2018]["min_att"], 1000)

    def test_covid_flag_set_for_2020_and_2021(self):
        """Korona-lippu asetetaan vuosille 2020 ja 2021."""
        matches = _make_matches([
            (2019, [5000]),
            (2020, [2000]),
            (2021, [3000]),
            (2022, [4500]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertFalse(stats[2019]["covid"], "2019 ei ole koronavuosi")
        self.assertTrue(stats[2020]["covid"], "2020 on koronavuosi")
        self.assertTrue(stats[2021]["covid"], "2021 on koronavuosi")
        self.assertFalse(stats[2022]["covid"], "2022 ei ole koronavuosi")

    def test_multiple_years(self):
        """Useamman vuoden data lajitellaan vuosittain oikein."""
        matches = _make_matches([
            (2000, [4000, 6000]),
            (2001, [3000, 3000, 3000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertEqual(stats[2000]["average"], 5000)
        self.assertEqual(stats[2001]["average"], 3000)
        self.assertEqual(stats[2001]["matches"], 3)

    def test_empty_year_not_in_stats(self):
        """Vuosi ilman otteluita ei ole tuloksissa."""
        matches = _make_matches([(2005, [5000])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertIn(2005, stats)
        # 2004 ei ole annettu → ei pitäisi olla tilastoissa
        self.assertNotIn(2004, stats)

    def test_single_match_year(self):
        """Yhden ottelun kausi: keskiarvo = ottelun yleisömäärä."""
        matches = _make_matches([(1996, [23382])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.assertEqual(stats[1996]["average"], 23382)
        self.assertEqual(stats[1996]["max_att"], 23382)
        self.assertEqual(stats[1996]["min_att"], 23382)


class TestComputeTrends(unittest.TestCase):
    """Testaa compute_trends()-metodia."""

    def setUp(self):
        self.fetcher = HistoricalAttendanceFetcher()

    def _stats_from_matches(self, year_attendance_pairs):
        matches = _make_matches(year_attendance_pairs)
        stats = self.fetcher.compute_yearly_stats(matches)
        self.fetcher.compute_trends(stats)
        return stats

    def test_first_year_yoy_is_none(self):
        """Ensimmäisellä vuodella ei ole edellistä vuotta → yoy_change on None."""
        matches = _make_matches([(2000, [5000]), (2001, [6000])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.fetcher.compute_trends(stats)
        self.assertIsNone(stats[2000]["yoy_change"])

    def test_positive_yoy_change(self):
        """Kasvu lasketaan oikein positiivisena prosenttina."""
        matches = _make_matches([(2000, [4000]), (2001, [8000])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.fetcher.compute_trends(stats)
        self.assertAlmostEqual(stats[2001]["yoy_change"], 100.0, places=1)

    def test_negative_yoy_change(self):
        """Lasku lasketaan oikein negatiivisena prosenttina."""
        matches = _make_matches([(2019, [8000]), (2020, [2000])])
        stats = self.fetcher.compute_yearly_stats(matches)
        self.fetcher.compute_trends(stats)
        self.assertAlmostEqual(stats[2020]["yoy_change"], -75.0, places=1)

    def test_best_year_has_highest_average(self):
        """best_year on vuosi, jolla on korkein keskiarvo."""
        matches = _make_matches([
            (2000, [3000]),
            (2005, [7000]),
            (2010, [5000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        best_yr, _ = trends["best_year"]
        self.assertEqual(best_yr, 2005)

    def test_worst_year_has_lowest_average(self):
        """worst_year on vuosi, jolla on matalin keskiarvo."""
        matches = _make_matches([
            (2000, [5000]),
            (2020, [1500]),
            (2022, [4500]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        worst_yr, _ = trends["worst_year"]
        self.assertEqual(worst_yr, 2020)

    def test_pre_covid_avg_excludes_covid_years(self):
        """pre_covid_avg ei sisällä vuosia 2020 tai 2021."""
        matches = _make_matches([
            (2018, [6000]),
            (2019, [8000]),
            (2020, [2000]),
            (2021, [2500]),
            (2022, [5000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        # Pre-covid: 2018 ja 2019 → total=14000, matches=2 → avg=7000
        self.assertEqual(trends["pre_covid_avg"], 7000)

    def test_covid_avg_only_covid_years(self):
        """covid_avg sisältää vain vuodet 2020 ja 2021."""
        matches = _make_matches([
            (2019, [8000]),
            (2020, [2000, 2000]),   # total 4000, 2 matches
            (2021, [3000]),          # total 3000, 1 match
            (2022, [5000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        # COVID: total=7000, matches=3 → avg=2333
        self.assertEqual(trends["covid_avg"], 7000 // 3)

    def test_post_covid_avg_only_2022_onward(self):
        """post_covid_avg kattaa vain vuodet > 2021."""
        matches = _make_matches([
            (2020, [2000]),
            (2022, [5000]),
            (2023, [6000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        # Post-COVID: 2022+2023 → total=11000, matches=2 → avg=5500
        self.assertEqual(trends["post_covid_avg"], 5500)

    def test_recovery_pct_calculated(self):
        """recovery_pct lasketaan post-covid / pre-covid × 100."""
        matches = _make_matches([
            (2019, [8000]),
            (2020, [2000]),
            (2022, [4000]),
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        # pre=8000, post=4000 → recovery=50%
        self.assertAlmostEqual(trends["recovery_pct"], 50.0, places=1)

    def test_best_total_year(self):
        """best_total_year on vuosi, jolla on eniten katsojia yhteensä."""
        matches = _make_matches([
            (2000, [3000, 3000, 3000, 3000]),   # total 12000
            (2001, [8000]),                      # total 8000
        ])
        stats = self.fetcher.compute_yearly_stats(matches)
        trends = self.fetcher.compute_trends(stats)
        best_total_yr, _ = trends["best_total_year"]
        self.assertEqual(best_total_yr, 2000)


class TestSaveTop50ReportIntegration(unittest.TestCase):
    """Integraatiotestit: varmistaa, että raportti syntyy oikein välimuistidatasta."""

    def setUp(self):
        self.fetcher = HistoricalAttendanceFetcher()

    def test_report_contains_yearly_averages_section(self):
        """Raportti sisältää vuosikohtainen keskiarvokehitys -osion."""
        import tempfile, os
        from pathlib import Path

        # Pieni testidata: kolme vuotta
        matches = _make_matches([
            (2019, [5000, 7000]),
            (2020, [2000, 3000]),
            (2022, [4500, 6000]),
        ])

        # Ohjataan tuloste tmp-tiedostoon
        import fetch_historical_attendance as fha
        orig_fn = fha.get_output_path

        with tempfile.TemporaryDirectory() as tmpdir:
            fha.get_output_path = lambda name: Path(tmpdir) / name
            try:
                result = self.fetcher.save_top50_report(matches)
            finally:
                fha.get_output_path = orig_fn

        self.assertTrue(result)

    def test_covid_annotation_in_report(self):
        """Koronahuomio (🦠) esiintyy raportissa vuodelle 2020."""
        import tempfile
        from pathlib import Path

        matches = _make_matches([
            (2019, [5000]),
            (2020, [2000]),
            (2021, [2500]),
            (2022, [4000]),
        ])

        import fetch_historical_attendance as fha
        orig_fn = fha.get_output_path
        report_text = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "YleisöHistoria.md"
            fha.get_output_path = lambda name: out_path
            try:
                self.fetcher.save_top50_report(matches)
            finally:
                fha.get_output_path = orig_fn
            report_text = out_path.read_text(encoding="utf-8")

        self.assertIn("🦠", report_text, "Koronahuomio puuttuu raportista")
        self.assertIn("Korona", report_text, "Korona-teksti puuttuu raportista")

    def test_trend_section_in_report(self):
        """Trendianalyysi-osio on raportissa."""
        import tempfile
        from pathlib import Path

        matches = _make_matches([
            (2018, [5000]),
            (2019, [6000]),
            (2020, [1500]),
            (2021, [2000]),
            (2022, [4500]),
        ])

        import fetch_historical_attendance as fha
        orig_fn = fha.get_output_path
        report_text = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "YleisöHistoria.md"
            fha.get_output_path = lambda name: out_path
            try:
                self.fetcher.save_top50_report(matches)
            finally:
                fha.get_output_path = orig_fn
            report_text = out_path.read_text(encoding="utf-8")

        self.assertIn("Trendianalyysi", report_text)
        self.assertIn("Toipumisaste", report_text)
        self.assertIn("Aikakausivertailu", report_text)


if __name__ == "__main__":
    unittest.main()
