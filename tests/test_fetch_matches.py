"""
Yksikkötestit ottelutietojen hakijalle (fetch_matches.py).

Testaa erityisesti, että kaikki ryhmät (group=1, group=2, …) haetaan
ja yhdistetään oikein, eikä vain ensimmäinen ryhmä.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_matches import MatchFetcher, MAX_GROUPS


# ---------------------------------------------------------------------------
# HTML-apufunktiot
# ---------------------------------------------------------------------------

def _make_match_row(ottelu_id, pvm, klo, koti, tulos, vieras):
    """Luo HTML-taulukkorivi yhdelle ottelulle."""
    return (
        f"<tr>"
        f"<td>{ottelu_id}</td>"
        f"<td>{pvm}</td>"
        f"<td>{klo}</td>"
        f"<td><a href='#'>Katso</a></td>"
        f"<td>{koti}</td>"
        f"<td>{tulos}</td>"
        f"<td>{vieras}</td>"
        f"</tr>"
    )


def _make_html_page(rows):
    """Kääri rivit minimaalisen HTML-sivun sisään."""
    rows_html = "\n".join(rows)
    return f"<html><body><table>{rows_html}</table></body></html>"


# ---------------------------------------------------------------------------
# Esimerkkidata
# ---------------------------------------------------------------------------

GROUP1_ROWS = [
    _make_match_row("101", "La 4.4.2026",  "13:00", "FC Inter",  "-",   "VPS"),
    _make_match_row("102", "Pe 10.4.2026", "18:30", "TPS",       "-",   "FC Lahti"),
    _make_match_row("103", "La 11.4.2026", "15:00", "KuPS",      "-",   "IF Gnistan"),
]

GROUP2_ROWS = [
    _make_match_row("201", "La 2.5.2026",  "13:00", "SJK",       "-",   "Ilves"),
    _make_match_row("202", "Ma 4.5.2026",  "18:00", "HJK",       "-",   "FC Lahti"),
]

GROUP3_ROWS = [
    _make_match_row("301", "La 6.6.2026",  "15:00", "FF Jaro",   "-",   "IFK Mariehamn"),
]

GROUP1_HTML = _make_html_page(GROUP1_ROWS)
GROUP2_HTML = _make_html_page(GROUP2_ROWS)
GROUP3_HTML = _make_html_page(GROUP3_ROWS)
EMPTY_HTML  = _make_html_page([])

PLAYED_ROW  = _make_match_row("001", "La 28.3.2026", "15:00", "HJK", "2-1", "KuPS")
PLAYED_HTML = _make_html_page([PLAYED_ROW])


# ---------------------------------------------------------------------------
# Testit
# ---------------------------------------------------------------------------

class TestParseMatchesFromHtml(unittest.TestCase):
    """Testaa _parse_matches_from_html suoraan."""

    def setUp(self):
        self.fetcher = MatchFetcher()

    def test_parses_upcoming_match(self):
        """Tuleva ottelu parsitaan oikein (tulos = '-')."""
        html = _make_html_page([
            _make_match_row("1", "La 4.4.2026", "13:00", "FC Inter", "-", "VPS")
        ])
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        m = matches[0]
        self.assertEqual(m["pvm"],    "La 4.4.2026")
        self.assertEqual(m["koti"],   "FC Inter")
        self.assertEqual(m["tulos"],  "-")
        self.assertEqual(m["vieras"], "VPS")

    def test_parses_played_match(self):
        """Pelattu ottelu parsitaan oikein (tulos on luku)."""
        matches = self.fetcher._parse_matches_from_html(PLAYED_HTML)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["tulos"], "2-1")

    def test_rejects_seuranta_as_score(self):
        """'Seuranta'-teksti solussa 5 ei tallennu tulokseksi."""
        html = _make_html_page([
            _make_match_row("2", "Su 5.4.2026", "16:00", "HJK", "Seuranta", "Ilves")
        ])
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["tulos"], "-")

    def test_empty_html_returns_empty_list(self):
        """Tyhjältä sivulta ei saada otteluita."""
        matches = self.fetcher._parse_matches_from_html(EMPTY_HTML)
        self.assertEqual(matches, [])

    def test_multiple_rows_parsed(self):
        """Kaikki rivit sivulta parsitaan."""
        matches = self.fetcher._parse_matches_from_html(GROUP1_HTML)
        self.assertEqual(len(matches), 3)

    def test_required_fields_present(self):
        """Jokaisessa ottelussa on pvm, koti, tulos ja vieras."""
        matches = self.fetcher._parse_matches_from_html(GROUP1_HTML)
        for m in matches:
            self.assertIn("pvm",    m)
            self.assertIn("koti",   m)
            self.assertIn("tulos",  m)
            self.assertIn("vieras", m)

    def test_combined_home_away_format(self):
        """'Koti - Vieras' -muoto yhdessä solussa parsitaan oikein."""
        html = _make_html_page([
            _make_match_row("3", "Ma 6.4.2026", "19:00", "HJK - Ilves", "", "")
        ])
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["koti"],   "HJK")
        self.assertEqual(matches[0]["vieras"], "Ilves")


class TestFetchMatchesMultipleGroups(unittest.TestCase):
    """Testaa, että fetch_matches hakee kaikki ryhmät."""

    def setUp(self):
        self.fetcher = MatchFetcher()

    def _make_response(self, html):
        resp = MagicMock()
        resp.text = html
        return resp

    def test_fetches_all_non_empty_groups(self):
        """Kaikki kolme ryhmää haetaan ja yhdistetään."""
        side_effects = [
            self._make_response(GROUP1_HTML),  # group=1 → 3 ottelua
            self._make_response(GROUP2_HTML),  # group=2 → 2 ottelua
            self._make_response(GROUP3_HTML),  # group=3 → 1 ottelu
            self._make_response(EMPTY_HTML),   # group=4 → tyhjä → lopetetaan
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects):
            matches = self.fetcher.fetch_matches()

        self.assertEqual(len(matches), 6, "Kaikkien ryhmien ottelut pitäisi yhdistää")

    def test_stops_at_first_empty_group(self):
        """Haku lopetetaan, kun ryhmä palauttaa tyhjän sivun."""
        side_effects = [
            self._make_response(GROUP1_HTML),  # group=1 → 3 ottelua
            self._make_response(EMPTY_HTML),   # group=2 → tyhjä → lopetetaan
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects):
            matches = self.fetcher.fetch_matches()

        self.assertEqual(len(matches), 3, "Haku pitäisi loppua tyhjään ryhmään")

    def test_stops_when_group_response_fails(self):
        """Haku lopetetaan, kun ryhmän vastaus epäonnistuu (None)."""
        side_effects = [
            self._make_response(GROUP1_HTML),  # group=1 → 3 ottelua
            None,                              # group=2 → virhe → lopetetaan
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects):
            matches = self.fetcher.fetch_matches()

        self.assertEqual(len(matches), 3)

    def test_uses_dummy_data_when_all_groups_fail(self):
        """Jos kaikki ryhmät epäonnistuvat, palautetaan esimerkkidata."""
        with patch.object(self.fetcher, 'fetch_with_retry', return_value=None):
            matches = self.fetcher.fetch_matches()

        self.assertGreater(len(matches), 0, "Esimerkkidata ei saa olla tyhjä")
        self.assertTrue(all(m.get('_is_dummy') for m in matches),
                        "Esimerkkidatan merkintöjen pitäisi sisältää '_is_dummy'")

    def test_group_urls_include_group_parameter(self):
        """Haettujen URL:ien pitäisi sisältää ?group=<numero>."""
        side_effects = [
            self._make_response(GROUP1_HTML),
            self._make_response(EMPTY_HTML),
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects) as mock_fetch:
            self.fetcher.fetch_matches()

        called_urls = [c.args[0] for c in mock_fetch.call_args_list]
        self.assertTrue(any("?group=1" in u for u in called_urls),
                        f"group=1 puuttuu haettuista URL:eista: {called_urls}")
        self.assertTrue(any("?group=2" in u for u in called_urls),
                        f"group=2 puuttuu haettuista URL:eista: {called_urls}")

    def test_does_not_exceed_max_groups(self):
        """Haku ei ylitä MAX_GROUPS-rajaa edes jos kaikki sivut sisältävät otteluita."""
        always_has_match = self._make_response(GROUP1_HTML)  # aina 3 ottelua
        with patch.object(self.fetcher, 'fetch_with_retry', return_value=always_has_match):
            matches = self.fetcher.fetch_matches()

        # MAX_GROUPS ryhmää × 3 ottelua/ryhmä
        self.assertEqual(len(matches), MAX_GROUPS * 3,
                         f"Haettujen otteluiden määrä pitää vastata MAX_GROUPS ({MAX_GROUPS})")

    def test_single_group_still_works(self):
        """Yhdenkin ryhmän ottelut palautetaan oikein."""
        side_effects = [
            self._make_response(GROUP1_HTML),
            self._make_response(EMPTY_HTML),
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects):
            matches = self.fetcher.fetch_matches()

        self.assertEqual(len(matches), 3)
        teams = {m["koti"] for m in matches}
        self.assertIn("FC Inter", teams)

    def test_contains_both_played_and_upcoming(self):
        """Tulos on '-' tuleville ja oikea numero pelatuille otteluille."""
        mixed_html = _make_html_page([
            _make_match_row("1", "La 28.3.2026", "15:00", "HJK",      "2-1", "KuPS"),
            _make_match_row("2", "La 4.4.2026",  "13:00", "FC Inter", "-",   "VPS"),
        ])
        side_effects = [
            self._make_response(mixed_html),
            self._make_response(EMPTY_HTML),
        ]
        with patch.object(self.fetcher, 'fetch_with_retry', side_effect=side_effects):
            matches = self.fetcher.fetch_matches()

        played   = [m for m in matches if m["tulos"] != "-"]
        upcoming = [m for m in matches if m["tulos"] == "-"]
        self.assertEqual(len(played),   1)
        self.assertEqual(len(upcoming), 1)


class TestCreateDummyMatches(unittest.TestCase):
    """Testaa _create_dummy_matches-fallback."""

    def setUp(self):
        self.fetcher = MatchFetcher()

    def test_returns_non_empty_list(self):
        matches = self.fetcher._create_dummy_matches()
        self.assertGreater(len(matches), 0)

    def test_all_marked_as_dummy(self):
        matches = self.fetcher._create_dummy_matches()
        for m in matches:
            self.assertTrue(m.get('_is_dummy'),
                            f"Puuttuva '_is_dummy'-kenttä: {m}")

    def test_required_fields_present(self):
        matches = self.fetcher._create_dummy_matches()
        for m in matches:
            self.assertIn("pvm",    m)
            self.assertIn("koti",   m)
            self.assertIn("tulos",  m)
            self.assertIn("vieras", m)


class TestIsScoreAndHelpers(unittest.TestCase):
    """Testaa apumetodit _is_score, _is_time ja _is_date_with_weekday."""

    def setUp(self):
        self.fetcher = MatchFetcher()

    def test_is_score_valid(self):
        # "2\u20131" käyttää ajatusviivaa tavuviivan sijaan (veikkausliiga.com käyttää molempia)
        for s in ["2-1", "0-0", "3-2", "10-0", "2\u20131"]:
            self.assertTrue(self.fetcher._is_score(s))

    def test_is_score_invalid(self):
        for s in ["Seuranta", "-", "", "HJK", "FC Inter - VPS", "13:00", "La 4.4.2026"]:
            self.assertFalse(self.fetcher._is_score(s))

    def test_is_time_valid(self):
        for s in ["13:00", "9:30", "18:45"]:
            self.assertTrue(self.fetcher._is_time(s))

    def test_is_time_invalid(self):
        for s in ["2-1", "HJK", "La 4.4.2026", ""]:
            self.assertFalse(self.fetcher._is_time(s))

    def test_is_date_with_weekday_valid(self):
        for s in ["La 4.4.2026", "Pe 10.4.2026", "Su 1.1.2026"]:
            self.assertTrue(self.fetcher._is_date_with_weekday(s))

    def test_is_date_with_weekday_invalid(self):
        for s in ["13:00", "HJK", "2-1", "", "4.4.2026"]:
            self.assertFalse(self.fetcher._is_date_with_weekday(s))


if __name__ == "__main__":
    unittest.main()
