"""
Yksikkötestit konfiguraatiolle (config.py) ja
tyhjien veikkausten käsittelylle (PredictionScorer).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from config import PARTICIPANTS, TEAMS_2026, TEAM_LOGOS
from prediction_scorer import PredictionScorer


class TestParticipantsConfig(unittest.TestCase):
    """Testaa PARTICIPANTS-listan rakenne ja osallistujamäärä."""

    def test_exactly_three_participants(self):
        """PARTICIPANTS-listassa on täsmälleen 3 osallistujaa."""
        self.assertEqual(len(PARTICIPANTS), 3, f"Odotetaan 3 osallistujaa, löytyi {len(PARTICIPANTS)}")

    def test_participants_have_required_keys(self):
        """Jokaisella osallistujalla on name, standings_prediction ja scorers_prediction."""
        for p in PARTICIPANTS:
            self.assertIn("name", p, "Osallistujalta puuttuu 'name'-kenttä")
            self.assertIn("standings_prediction", p, f"{p.get('name')}: puuttuu 'standings_prediction'")
            self.assertIn("scorers_prediction", p, f"{p.get('name')}: puuttuu 'scorers_prediction'")

    def test_participant_names_are_unique(self):
        """Jokaisella osallistujalla on uniikki nimi."""
        names = [p["name"] for p in PARTICIPANTS]
        self.assertEqual(len(names), len(set(names)), "Osallistujilla on duplikaattinimiä")

    def test_filled_prediction_has_all_teams(self):
        """Jos sarjataulukkoennuste on täytetty, siinä on kaikki 12 joukkuetta."""
        for p in PARTICIPANTS:
            pred = p.get("standings_prediction", [])
            if pred:
                self.assertEqual(
                    len(pred), 12,
                    f"{p['name']}: ennusteessa {len(pred)} joukkuetta, odotetaan 12"
                )

    def test_filled_prediction_teams_are_valid(self):
        """Täytetyssä ennusteessa olevat joukkueet kuuluvat Veikkausliigaan 2026."""
        for p in PARTICIPANTS:
            pred = p.get("standings_prediction", [])
            for team in pred:
                self.assertIn(
                    team, TEAMS_2026,
                    f"{p['name']}: joukkue '{team}' ei kuulu TEAMS_2026-listaan"
                )

    def test_filled_scorers_prediction_has_five_players(self):
        """Jos maalintekijäennuste on täytetty, siinä on 5 pelaajaa."""
        for p in PARTICIPANTS:
            pred = p.get("scorers_prediction", [])
            if pred:
                self.assertEqual(
                    len(pred), 5,
                    f"{p['name']}: maalintekijäennusteessa {len(pred)} pelaajaa, odotetaan 5"
                )

    def test_no_duplicate_teams_in_filled_prediction(self):
        """Täytetyssä ennusteessa ei ole samaa joukkuetta kahdesti."""
        for p in PARTICIPANTS:
            pred = p.get("standings_prediction", [])
            if pred:
                self.assertEqual(
                    len(pred), len(set(pred)),
                    f"{p['name']}: ennusteessa on duplikaattijoukkueita: {pred}"
                )

    def test_at_least_one_filled_prediction(self):
        """Ainakin yhdellä osallistujalla on täytetty veikkaus."""
        filled = [p for p in PARTICIPANTS if p.get("standings_prediction")]
        self.assertGreater(len(filled), 0, "Yhdessäkään osallistujassa ei ole täytettyä veikkausta")

    def test_all_teams_have_logos(self):
        """Kaikilla TEAMS_2026-joukkueilla on logo TEAM_LOGOS-sanakirjassa."""
        for team in TEAMS_2026:
            self.assertIn(team, TEAM_LOGOS, f"Joukkueelle '{team}' ei ole logoa TEAM_LOGOS:issa")


class TestEmptyPredictionHandling(unittest.TestCase):
    """Testaa tyhjien veikkausten käsittely PredictionScorer:issa."""

    def setUp(self):
        self.scorer = PredictionScorer()
        self.actual_standings = ["HJK", "KuPS", "FC Inter", "SJK", "Ilves",
                                  "VPS", "FF Jaro", "FC Lahti", "IFK Mariehamn",
                                  "IF Gnistan", "AC Oulu", "TPS"]
        self.actual_scorers = [
            {"pelaaja": "Plange, Luke",        "joukkue": "HJK", "maalit": 5, "syotot": 2, "sijoitus": "1"},
            {"pelaaja": "Karjalainen, Rasmus", "joukkue": "KuPS", "maalit": 4, "syotot": 3, "sijoitus": "2"},
            {"pelaaja": "Odutayo, Colin",      "joukkue": "SJK", "maalit": 3, "syotot": 1, "sijoitus": "3"},
        ]

    def test_empty_standings_prediction_gives_zero_points(self):
        """Tyhjä sarjataulukkoennuste tuottaa 0 pistettä."""
        pts, details = self.scorer.calculate_standings_points([], self.actual_standings)
        self.assertEqual(pts, 0)
        self.assertEqual(details, [])

    def test_empty_scorers_prediction_gives_zero_points(self):
        """Tyhjä maalintekijäennuste tuottaa 0 pistettä."""
        pts, details = self.scorer.calculate_scorer_points([], self.actual_scorers)
        self.assertEqual(pts, 0)
        self.assertEqual(details, [])

    def test_score_all_handles_empty_predictions(self):
        """score_all käsittelee tyhjät veikkaukset ilman virheitä."""
        results = self.scorer.score_all(self.actual_standings, self.actual_scorers)
        self.assertEqual(len(results), len(PARTICIPANTS))
        for r in results:
            self.assertIn("name", r)
            self.assertIn("total_points", r)
            self.assertGreaterEqual(r["total_points"], 0)

    def test_empty_predictions_sorted_last(self):
        """Tyhjät veikkaukset näkyvät pistelistalla viimeisenä."""
        results = self.scorer.score_all(self.actual_standings, self.actual_scorers)
        filled = [r for r in results if r["standings_details"] or r["scorer_details"]]
        empty = [r for r in results if not r["standings_details"] and not r["scorer_details"]]
        # Tarkista järjestys: kaikki täytetyt tulevat ennen tyhjiä
        filled_indices = [results.index(r) for r in filled]
        empty_indices = [results.index(r) for r in empty]
        if filled_indices and empty_indices:
            self.assertLess(
                max(filled_indices), min(empty_indices),
                "Tyhjät veikkaukset eivät ole pistelistalla viimeisenä"
            )


if __name__ == "__main__":
    unittest.main()
