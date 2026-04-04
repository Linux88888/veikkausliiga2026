"""
Yksikkötestit veikkausten pisteytysjärjestelmälle (PredictionScorer)
ja ottelutietojen parsimiselle (MatchFetcher).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from prediction_scorer import PredictionScorer


class TestCalculateStandingsPoints(unittest.TestCase):
    def setUp(self):
        self.scorer = PredictionScorer()

    def test_perfect_prediction(self):
        """Täsmälleen oikea ennuste → 10 pistettä per joukkue"""
        teams = ["HJK", "KuPS", "FC Inter"]
        pts, details = self.scorer.calculate_standings_points(teams, teams)
        self.assertEqual(pts, 30)
        for d in details:
            self.assertEqual(d["pisteet"], 10)
            self.assertEqual(d["ero"], 0)

    def test_one_off_prediction(self):
        """Ero 1 sijoitus → 0 pistettä"""
        predicted = ["HJK", "KuPS", "FC Inter"]
        actual    = ["KuPS", "HJK", "FC Inter"]
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        # HJK: pred=1, act=2, ero=1 → 0p
        # KuPS: pred=2, act=1, ero=1 → 0p
        # FC Inter: pred=3, act=3, ero=0 → 10p
        self.assertEqual(pts, 10)
        self.assertEqual(details[0]["pisteet"], 0)
        self.assertEqual(details[1]["pisteet"], 0)
        self.assertEqual(details[2]["pisteet"], 10)

    def test_two_off_prediction(self):
        """Ero 2 sijoitusta → 0 pistettä"""
        predicted = ["HJK", "KuPS", "FC Inter"]
        actual    = ["FC Inter", "KuPS", "HJK"]
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        # HJK: pred=1, act=3, ero=2 → 0p
        # KuPS: pred=2, act=2, ero=0 → 10p
        # FC Inter: pred=3, act=1, ero=2 → 0p
        self.assertEqual(pts, 10)

    def test_large_error_gives_zero(self):
        """Ero ≥ 1 sijoitusta → 0 pistettä"""
        predicted = ["HJK", "KuPS", "FC Inter", "SJK"]
        actual    = ["SJK", "FC Inter", "KuPS", "HJK"]
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        # HJK: pred=1, act=4, ero=3 → 0p
        # KuPS: pred=2, act=3, ero=1 → 0p
        # FC Inter: pred=3, act=2, ero=1 → 0p
        # SJK: pred=4, act=1, ero=3 → 0p
        self.assertEqual(pts, 0)
        self.assertEqual(details[0]["pisteet"], 0)
        self.assertEqual(details[3]["pisteet"], 0)

    def test_missing_team_gives_zero_points(self):
        """Joukkue ei sarjataulukossa → ei pisteitä, ei false-positiiveja"""
        predicted = ["HJK", "KuPS", "SJK"]
        actual    = ["HJK", "KuPS"]  # SJK puuttuu
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        # HJK: pred=1, act=1, ero=0 → 10p
        # KuPS: pred=2, act=2, ero=0 → 10p
        # SJK: puuttuu → 0p
        self.assertEqual(pts, 20)
        self.assertEqual(details[2]["pisteet"], 0)
        self.assertEqual(details[2]["toteutunut"], "-")
        self.assertIsNone(details[2]["ero"])

    def test_missing_team_no_false_exact_match(self):
        """Puuttuva joukkue ei saa täsmäosumaa vaikka indeksi osuisi aiemmalla bugilla"""
        # Tämä testaa bugin korjausta: aiempi koodi käytti len(actual) positiona,
        # joka saattoi tuottaa eron 0 jos pred_i == len(actual).
        predicted = ["HJK", "KuPS", "SJK"]
        actual    = ["HJK", "KuPS"]  # len=2; SJK pred=3 sai aiemmin len(actual)=2 → ero=1 → 2p
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        sjk_detail = next(d for d in details if d["joukkue"] == "SJK")
        self.assertEqual(sjk_detail["pisteet"], 0)


class TestCalculateScorerPoints(unittest.TestCase):
    def setUp(self):
        self.scorer = PredictionScorer()

    def test_exact_scorer(self):
        """Pelaaja top-listalla → 10 p + maalit*2 + syötöt*1"""
        predicted = ["Plange, Luke", "Karjalainen, Rasmus"]
        actual = [
            {"pelaaja": "Plange, Luke",        "maalit": 3, "syotot": 1},
            {"pelaaja": "Karjalainen, Rasmus",  "maalit": 2, "syotot": 0},
        ]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # Plange: 10 + 3*2 + 1*1 = 17
        # Karjalainen: 10 + 2*2 + 0*1 = 14
        self.assertEqual(pts, 31)
        self.assertEqual(details[0]["pisteet"], 17)
        self.assertEqual(details[1]["pisteet"], 14)

    def test_in_list_scorer(self):
        """Pelaaja listalla mutta eri sijoituksessa → 10 p + maalit*2 + syötöt*1"""
        predicted = ["Plange, Luke", "Karjalainen, Rasmus"]
        actual = [
            {"pelaaja": "Karjalainen, Rasmus",  "maalit": 2, "syotot": 1},
            {"pelaaja": "Plange, Luke",         "maalit": 1, "syotot": 2},
        ]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # Plange: 10 + 1*2 + 2*1 = 14
        # Karjalainen: 10 + 2*2 + 1*1 = 15
        self.assertEqual(pts, 29)
        self.assertEqual(details[0]["pisteet"], 14)
        self.assertEqual(details[1]["pisteet"], 15)

    def test_not_in_list_scorer(self):
        """Pelaaja ei top-listalla → 0 pistettä"""
        predicted = ["Tuntematon Pelaaja"]
        actual = [
            {"pelaaja": "Plange, Luke",        "maalit": 5, "syotot": 2},
            {"pelaaja": "Karjalainen, Rasmus",  "maalit": 3, "syotot": 1},
        ]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        self.assertEqual(pts, 0)
        self.assertEqual(details[0]["pisteet"], 0)

    def test_mixed_scorer(self):
        """Yhdistelmä top-listalla ja ei listalla"""
        predicted = ["Plange, Luke", "Odutayo, Colin", "Tuntematon"]
        actual = [
            {"pelaaja": "Plange, Luke",    "maalit": 4, "syotot": 0},
            {"pelaaja": "Karjalainen, Rasmus", "maalit": 3, "syotot": 2},
            {"pelaaja": "Odutayo, Colin",  "maalit": 2, "syotot": 1},
        ]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # Plange: 10 + 4*2 + 0*1 = 18
        # Odutayo: 10 + 2*2 + 1*1 = 15
        # Tuntematon: 0
        self.assertEqual(pts, 33)

    def test_scorer_goals_assists_zero(self):
        """Pelaaja listalla mutta 0 maalia/syöttöä → vain 10 p"""
        predicted = ["Plange, Luke"]
        actual = [{"pelaaja": "Plange, Luke", "maalit": 0, "syotot": 0}]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        self.assertEqual(pts, 10)
        self.assertEqual(details[0]["pisteet"], 10)


class TestIsScoreHelper(unittest.TestCase):
    def setUp(self):
        from fetch_matches import MatchFetcher
        self.fetcher = MatchFetcher()

    def test_valid_scores(self):
        for s in ["2-1", "0-0", "3-2", "10-0", "2–1"]:
            self.assertTrue(self.fetcher._is_score(s), f"Should be valid score: {s}")

    def test_invalid_scores(self):
        for s in ["Seuranta", "-", "", "HJK", "FC Inter - VPS", "13:00", "La 4.4.2026"]:
            self.assertFalse(self.fetcher._is_score(s), f"Should NOT be valid score: {s}")


class TestMatchParsingCombinedFormat(unittest.TestCase):
    """Testaa yhdistetyn 'Koti - Vieras' -muodon parsimista"""

    def setUp(self):
        from fetch_matches import MatchFetcher
        self.fetcher = MatchFetcher()

    def test_is_score_rejects_combined_team_string(self):
        """'FC Inter - VPS' ei ole tulos"""
        self.assertFalse(self.fetcher._is_score("FC Inter - VPS"))

    def test_is_score_rejects_seuranta(self):
        """'Seuranta' ei ole tulos"""
        self.assertFalse(self.fetcher._is_score("Seuranta"))

    def test_is_score_accepts_real_score(self):
        """'2-1' on oikea tulos"""
        self.assertTrue(self.fetcher._is_score("2-1"))


if __name__ == "__main__":
    unittest.main()
