"""
Yksikkötestit otteluennustelaskurille (match_predictor.py).
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from match_predictor import (
    _calc_win_prob,
    _calc_over25_prob,
    _parse_date,
    _group_by_round,
    MatchPredictor,
    TEAM_STRENGTH,
)


class TestCalcWinProb(unittest.TestCase):
    """Testaa kotijoukkueen voittotodennäköisyyslaskuri."""

    def test_equal_teams_home_advantage(self):
        """Tasavahvoilla joukkueilla kotijoukkueella on etu."""
        prob = _calc_win_prob(70, 70)
        self.assertGreater(prob, 0.5, "Kotijoukkueen voittotodennäköisyys pitää olla > 0.5 tasavahvoilla")

    def test_stronger_home_team_wins_more(self):
        """Vahvempi kotijoukkue voittaa todennäköisemmin."""
        prob_strong = _calc_win_prob(85, 50)
        prob_weak = _calc_win_prob(50, 85)
        self.assertGreater(prob_strong, prob_weak)

    def test_result_clamped_to_bounds(self):
        """Tulos on aina välillä [0.15, 0.85]."""
        for home, away in [(100, 0), (0, 100), (50, 50), (85, 85)]:
            prob = _calc_win_prob(home, away)
            self.assertGreaterEqual(prob, 0.15, f"Tulos {prob} alle alarajan: home={home}, away={away}")
            self.assertLessEqual(prob, 0.85, f"Tulos {prob} yli ylärajan: home={home}, away={away}")

    def test_returns_three_decimal_float(self):
        """Palauttaa pyöristetyn desimaaliluvun."""
        prob = _calc_win_prob(70, 65)
        self.assertIsInstance(prob, float)
        # max 3 desimaalia
        self.assertEqual(prob, round(prob, 3))


class TestCalcOver25Prob(unittest.TestCase):
    """Testaa yli 2.5 maalia -todennäköisyyslaskuri."""

    def test_strong_teams_higher_over25(self):
        """Vahvat joukkueet tuottavat enemmän maaleja."""
        prob_strong = _calc_over25_prob(85, 85)
        prob_weak = _calc_over25_prob(50, 50)
        self.assertGreater(prob_strong, prob_weak)

    def test_result_clamped_to_bounds(self):
        """Tulos on aina välillä [0.35, 0.80]."""
        for home, away in [(100, 100), (0, 0), (70, 60)]:
            prob = _calc_over25_prob(home, away)
            self.assertGreaterEqual(prob, 0.35)
            self.assertLessEqual(prob, 0.80)


class TestParseDate(unittest.TestCase):
    """Testaa päivämäärän parsiminen."""

    def test_valid_date_with_weekday(self):
        """'La 4.4.2026' → date(2026, 4, 4)"""
        result = _parse_date("La 4.4.2026")
        self.assertEqual(result, date(2026, 4, 4))

    def test_valid_date_no_weekday(self):
        """'4.4.2026' → date(2026, 4, 4)"""
        result = _parse_date("4.4.2026")
        self.assertEqual(result, date(2026, 4, 4))

    def test_invalid_date_returns_original(self):
        """Virheellinen merkkijono palautetaan sellaisenaan."""
        result = _parse_date("ei päivämäärä")
        self.assertEqual(result, "ei päivämäärä")

    def test_empty_string_returns_original(self):
        """Tyhjä merkkijono palautetaan sellaisenaan."""
        result = _parse_date("")
        self.assertEqual(result, "")

    def test_two_digit_day_and_month(self):
        """'Pe 10.4.2026' → date(2026, 4, 10)"""
        result = _parse_date("Pe 10.4.2026")
        self.assertEqual(result, date(2026, 4, 10))


class TestGroupByRound(unittest.TestCase):
    """Testaa otteluiden ryhmittely kierroksittain."""

    def test_groups_by_date(self):
        """Saman päivän ottelut ryhmitellään yhteen."""
        matches = [
            {"pvm": "La 4.4.2026", "koti": "HJK", "vieras": "Ilves"},
            {"pvm": "La 4.4.2026", "koti": "KuPS", "vieras": "SJK"},
            {"pvm": "Su 5.4.2026", "koti": "TPS", "vieras": "FC Inter"},
        ]
        rounds = _group_by_round(matches)
        self.assertEqual(len(rounds), 2)
        pvm1, ottelut1 = rounds[0]
        self.assertEqual(pvm1, "La 4.4.2026")
        self.assertEqual(len(ottelut1), 2)

    def test_sorted_chronologically(self):
        """Kierrokset järjestetään aikajärjestyksessä."""
        matches = [
            {"pvm": "Su 5.4.2026", "koti": "TPS", "vieras": "FC Inter"},
            {"pvm": "La 4.4.2026", "koti": "HJK", "vieras": "Ilves"},
        ]
        rounds = _group_by_round(matches)
        dates = [r[0] for r in rounds]
        self.assertEqual(dates[0], "La 4.4.2026")
        self.assertEqual(dates[1], "Su 5.4.2026")

    def test_empty_list(self):
        """Tyhjä lista palauttaa tyhjän listan."""
        self.assertEqual(_group_by_round([]), [])


class TestMatchPredictorPredictMatch(unittest.TestCase):
    """Testaa MatchPredictor._predict_match."""

    def setUp(self):
        self.predictor = MatchPredictor()

    def test_probabilities_sum_to_one(self):
        """Koti+tasapeli+vieras = 1.0 (pyöristysvirheen sisällä)."""
        pred = self.predictor._predict_match("HJK", "Ilves")
        total = pred["koti_voitto"] + pred["tasapeli"] + pred["vieras_voitto"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_all_required_keys_present(self):
        """Ennuste sisältää kaikki tarvittavat kentät."""
        pred = self.predictor._predict_match("KuPS", "SJK")
        for key in ("koti", "vieras", "koti_voitto", "tasapeli", "vieras_voitto", "yli_25"):
            self.assertIn(key, pred)

    def test_unknown_team_uses_default_strength(self):
        """Tuntematon joukkue käyttää oletusarvoa (55) kaatumatta."""
        pred = self.predictor._predict_match("Tuntematon FC", "HJK")
        self.assertIsNotNone(pred)
        self.assertGreater(pred["koti_voitto"], 0)

    def test_all_probabilities_positive(self):
        """Kaikki todennäköisyydet ovat positiivisia."""
        pred = self.predictor._predict_match("HJK", "IF Gnistan")
        self.assertGreater(pred["koti_voitto"], 0)
        self.assertGreater(pred["tasapeli"], 0)
        self.assertGreater(pred["vieras_voitto"], 0)
        self.assertGreater(pred["yli_25"], 0)


class TestTeamStrengthData(unittest.TestCase):
    """Testaa TEAM_STRENGTH-tietorakenne."""

    def test_all_2026_teams_have_strength(self):
        """Kaikilla 2026 joukkueilla on vahvuusluokitus."""
        try:
            from config import TEAMS_2026
        except ImportError:
            TEAMS_2026 = ["HJK", "KuPS", "FC Inter", "SJK", "FC Lahti", "Ilves",
                          "FF Jaro", "VPS", "AC Oulu", "IF Gnistan", "IFK Mariehamn", "TPS"]
        for team in TEAMS_2026:
            self.assertIn(team, TEAM_STRENGTH, f"Joukkueella '{team}' ei ole vahvuusluokitusta")

    def test_strengths_in_valid_range(self):
        """Vahvuusluokitukset ovat välillä 1–100."""
        for team, strength in TEAM_STRENGTH.items():
            self.assertGreaterEqual(strength, 1, f"{team}: vahvuus {strength} alle 1")
            self.assertLessEqual(strength, 100, f"{team}: vahvuus {strength} yli 100")

    def test_hjk_is_strongest(self):
        """HJK on vahvin joukkue (historiallisesti dominoivin)."""
        max_strength = max(TEAM_STRENGTH.values())
        self.assertEqual(TEAM_STRENGTH["HJK"], max_strength)


if __name__ == "__main__":
    unittest.main()
