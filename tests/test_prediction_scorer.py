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
        """Ero ≥ 1 sijoitus → 0 pistettä"""
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
        actual    = ["HJK", "KuPS"]  # len=2; SJK pred=3 sai aiemmin len(actual)=2 → ero=1 → 0p
        pts, details = self.scorer.calculate_standings_points(predicted, actual)
        sjk_detail = next(d for d in details if d["joukkue"] == "SJK")
        self.assertEqual(sjk_detail["pisteet"], 0)


class TestCalculateScorerPoints(unittest.TestCase):
    def setUp(self):
        self.scorer = PredictionScorer()

    def _make_scorer_data(self, players_goals_assists):
        """Apufunktio: luo maalintekijädatan listasta (nimi, maalit, syötöt)."""
        return [
            {"pelaaja": name, "joukkue": "HJK", "maalit": goals, "syotot": assists, "sijoitus": str(i + 1)}
            for i, (name, goals, assists) in enumerate(players_goals_assists)
        ]

    def test_perfect_prediction_with_stats(self):
        """Pelaaja top-5:ssä + maalit + syötöt → oikeat pisteet"""
        actual = self._make_scorer_data([
            ("Plange, Luke", 10, 3),      # sija 1
            ("Karjalainen, Rasmus", 8, 5), # sija 2
        ])
        predicted = ["Plange, Luke", "Karjalainen, Rasmus"]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # Plange: 10*2 + 3*1 + 10 = 33
        # Karjalainen: 8*2 + 5*1 + 10 = 31
        self.assertEqual(pts, 64)
        self.assertEqual(details[0]["pisteet"], 33)
        self.assertEqual(details[1]["pisteet"], 31)

    def test_in_list_but_not_top5(self):
        """Pelaaja listalla mutta sija > 5 → ei top-5 bonusta, vain maalit/syötöt"""
        actual = self._make_scorer_data([
            ("P1", 5, 0),  # sija 1
            ("P2", 4, 0),  # sija 2
            ("P3", 3, 0),  # sija 3
            ("P4", 3, 0),  # sija 4
            ("P5", 2, 0),  # sija 5
            ("P6", 2, 3),  # sija 6 – ei top-5 bonusta
        ])
        predicted = ["P6"]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # P6: 2*2 + 3*1 + 0 (ei top-5) = 7
        self.assertEqual(pts, 7)
        self.assertEqual(details[0]["pisteet"], 7)

    def test_not_in_list_scorer(self):
        """Pelaaja ei top-listalla → 0 pistettä"""
        actual = self._make_scorer_data([("Plange, Luke", 5, 2)])
        predicted = ["Tuntematon Pelaaja"]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        self.assertEqual(pts, 0)
        self.assertEqual(details[0]["pisteet"], 0)

    def test_mixed_scorer(self):
        """Yhdistelmä: top-5, listalla (>5), ei listalla"""
        actual = self._make_scorer_data([
            ("Plange, Luke", 6, 2),        # sija 1, top-5
            ("Karjalainen, Rasmus", 5, 1), # sija 2, top-5
            ("P3", 4, 0),                  # sija 3
            ("P4", 3, 0),                  # sija 4
            ("P5", 2, 0),                  # sija 5
            ("Odutayo, Colin", 2, 4),      # sija 6, ei top-5
        ])
        predicted = ["Plange, Luke", "Odutayo, Colin", "Tuntematon"]
        pts, details = self.scorer.calculate_scorer_points(predicted, actual)
        # Plange: 6*2 + 2*1 + 10 = 24
        # Odutayo: 2*2 + 4*1 + 0 = 8
        # Tuntematon: 0
        self.assertEqual(pts, 32)
        self.assertEqual(details[0]["pisteet"], 24)
        self.assertEqual(details[1]["pisteet"], 8)
        self.assertEqual(details[2]["pisteet"], 0)


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
