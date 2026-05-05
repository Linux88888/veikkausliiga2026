"""
Yksikkötestit AttendanceAnalyzer-luokalle ja apufunktioille.

Testaa Ottelut.md-parsintaa, yleisömäärätilastojen laskentaa sekä
raportin generointia.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from attendance_analyzer import (
    AttendanceAnalyzer,
    STADIUM_INFO,
    HOME_GAMES_PER_TEAM,
    _parse_played_matches,
)


# ---------------------------------------------------------------------------
# Apufunktiot testitiedostojen luomiseen
# ---------------------------------------------------------------------------

def _write_ottelut(tmp_path: Path, played: list, upcoming: list = None) -> Path:
    """Kirjoittaa Ottelut.md-tiedoston annettuun hakemistoon."""
    upcoming = upcoming or []
    lines = ["# Veikkausliiga 2026 - Ottelut\n\n"]

    if played:
        has_yleiso = any("yleiso" in m for m in played)
        lines.append("## Pelatut ottelut\n\n")
        if has_yleiso:
            lines.append("| Päivämäärä | Koti | Tulos | Vieras | Yleisö |\n")
            lines.append("|------------|------|-------|--------|--------|\n")
            for m in played:
                att = m.get("yleiso", 0)
                att_str = str(att) if att > 0 else "—"
                lines.append(
                    f"| {m['pvm']} | {m['koti']} | {m['tulos']} | {m['vieras']} | {att_str} |\n"
                )
        else:
            lines.append("| Päivämäärä | Koti | Tulos | Vieras |\n")
            lines.append("|------------|------|-------|--------|\n")
            for m in played:
                lines.append(
                    f"| {m['pvm']} | {m['koti']} | {m['tulos']} | {m['vieras']} |\n"
                )
        lines.append("\n")

    if upcoming:
        lines.append("## Tulevat ottelut\n\n")
        lines.append("| Päivämäärä | Koti | Vieras |\n")
        lines.append("|------------|------|--------|\n")
        for m in upcoming:
            lines.append(f"| {m['pvm']} | {m['koti']} | {m['vieras']} |\n")

    (tmp_path / "Ottelut.md").write_text("".join(lines), encoding="utf-8")
    return tmp_path / "Ottelut.md"


# ---------------------------------------------------------------------------
# TestParsePlayedMatches
# ---------------------------------------------------------------------------

class TestParsePlayedMatches(unittest.TestCase):
    """Testaa _parse_played_matches-apufunktiota."""

    def test_no_file_returns_empty(self):
        """Tiedosto puuttuu → tyhjä dict, played=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home_games, total = _parse_played_matches(Path(tmpdir))
        self.assertEqual(home_games, {})
        self.assertEqual(total, 0)

    def test_empty_file_returns_empty(self):
        """Tyhjä tiedosto → tyhjä dict, played=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Ottelut.md").write_text("", encoding="utf-8")
            home_games, total = _parse_played_matches(Path(tmpdir))
        self.assertEqual(home_games, {})
        self.assertEqual(total, 0)

    def test_no_played_section_returns_empty(self):
        """Tiedosto olemassa, mutta ei 'Pelatut ottelut' -osiota → tyhjä."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Ottelut.md").write_text(
                "## Tulevat ottelut\n\n| Päivämäärä | Koti | Vieras |\n",
                encoding="utf-8",
            )
            home_games, total = _parse_played_matches(Path(tmpdir))
        self.assertEqual(home_games, {})
        self.assertEqual(total, 0)

    def test_old_format_counts_home_games(self):
        """Vanha muoto (ilman Yleisö-saraketta) laskee kotipelit oikein, att=0."""
        played = [
            {"pvm": "La 4.4.2026",  "koti": "HJK",   "tulos": "3-0", "vieras": "SJK"},
            {"pvm": "La 4.4.2026",  "koti": "KuPS",  "tulos": "1-1", "vieras": "Ilves"},
            {"pvm": "Pe 10.4.2026", "koti": "HJK",   "tulos": "2-1", "vieras": "FC Inter"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ottelut(Path(tmpdir), played)
            home_games, total = _parse_played_matches(Path(tmpdir))

        self.assertEqual(total, 3)
        self.assertEqual(len(home_games["HJK"]), 2)
        self.assertEqual(len(home_games["KuPS"]), 1)
        self.assertEqual(home_games["HJK"], [0, 0])  # ei att-dataa

    def test_new_format_parses_attendance(self):
        """Uusi muoto (Yleisö-sarake) parsii katsojaluvut oikein."""
        played = [
            {"pvm": "La 4.4.2026",  "koti": "HJK",   "tulos": "3-0", "vieras": "SJK",
             "yleiso": 5041},
            {"pvm": "La 4.4.2026",  "koti": "KuPS",  "tulos": "1-1", "vieras": "Ilves",
             "yleiso": 2100},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ottelut(Path(tmpdir), played)
            home_games, total = _parse_played_matches(Path(tmpdir))

        self.assertEqual(total, 2)
        self.assertEqual(home_games["HJK"], [5041])
        self.assertEqual(home_games["KuPS"], [2100])

    def test_dash_attendance_stored_as_zero(self):
        """Yleisö-sarakkeen '—' tai tyhjä tallennetaan arvona 0."""
        played = [
            {"pvm": "La 4.4.2026", "koti": "HJK", "tulos": "2-1", "vieras": "Ilves",
             "yleiso": 0},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ottelut(Path(tmpdir), played)
            home_games, total = _parse_played_matches(Path(tmpdir))

        self.assertEqual(total, 1)
        self.assertEqual(home_games["HJK"], [0])

    def test_ignores_upcoming_section(self):
        """Tulevat ottelut -osiota ei lasketa pelattuihin."""
        played = [
            {"pvm": "La 4.4.2026", "koti": "HJK", "tulos": "2-1", "vieras": "Ilves"},
        ]
        upcoming = [
            {"pvm": "La 11.4.2026", "koti": "HJK", "vieras": "KuPS"},
            {"pvm": "La 11.4.2026", "koti": "SJK", "vieras": "Ilves"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ottelut(Path(tmpdir), played, upcoming)
            home_games, total = _parse_played_matches(Path(tmpdir))

        self.assertEqual(total, 1)
        self.assertIn("HJK", home_games)
        self.assertNotIn("SJK", home_games)

    def test_multiple_games_per_team(self):
        """Joukkueella on useita kotipelejä → lista on oikean pituinen."""
        played = [
            {"pvm": "La 4.4.2026",  "koti": "HJK", "tulos": "2-1", "vieras": "KuPS",
             "yleiso": 4000},
            {"pvm": "Pe 10.4.2026", "koti": "HJK", "tulos": "1-0", "vieras": "SJK",
             "yleiso": 6000},
            {"pvm": "La 18.4.2026", "koti": "HJK", "tulos": "3-2", "vieras": "Ilves",
             "yleiso": 5500},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ottelut(Path(tmpdir), played)
            home_games, total = _parse_played_matches(Path(tmpdir))

        self.assertEqual(total, 3)
        self.assertEqual(len(home_games["HJK"]), 3)
        self.assertEqual(sum(home_games["HJK"]), 15500)


# ---------------------------------------------------------------------------
# TestBuildAttendanceData
# ---------------------------------------------------------------------------

class TestBuildAttendanceData(unittest.TestCase):
    """Testaa AttendanceAnalyzer._build_attendance_data-metodia."""

    def setUp(self):
        self.analyzer = AttendanceAnalyzer()

    def test_no_games_full_season_estimate(self):
        """Kautta ei ole pelattu → koko kauden arvio, is_real=False."""
        per_team, summary, is_real = self.analyzer._build_attendance_data({}, 0)

        self.assertFalse(is_real)
        self.assertEqual(summary["played"], 0)
        expected_total = sum(
            info["hist_keskiarvo"] * HOME_GAMES_PER_TEAM
            for info in STADIUM_INFO.values()
        )
        self.assertEqual(summary["total_attendance"], expected_total)

    def test_with_real_attendance_is_real_true(self):
        """Todellisia katsojalukuja löytyy → is_real=True."""
        home_games = {"HJK": [5041, 4200], "KuPS": [2100]}
        per_team, summary, is_real = self.analyzer._build_attendance_data(home_games, 3)

        self.assertTrue(is_real)
        self.assertEqual(summary["real_total"], 5041 + 4200 + 2100)
        self.assertEqual(summary["real_matches"], 3)

    def test_with_unknown_attendance_only_is_real_false(self):
        """Kaikki att=0 (ei todellisia tietoja) → is_real=False."""
        home_games = {"HJK": [0, 0], "KuPS": [0]}
        per_team, summary, is_real = self.analyzer._build_attendance_data(home_games, 3)

        self.assertFalse(is_real)
        self.assertEqual(summary["real_total"], 0)
        self.assertEqual(summary["real_matches"], 0)

    def test_all_12_teams_present_in_output(self):
        """Kaikki 12 joukkuetta ovat per_team-listassa."""
        per_team, _, _ = self.analyzer._build_attendance_data({}, 0)
        team_names = {r["joukkue"] for r in per_team}
        self.assertEqual(team_names, set(STADIUM_INFO.keys()))

    def test_played_total_returned_correctly(self):
        """played-arvo vastaa annettua played_total-parametria."""
        home_games = {"HJK": [5000]}
        _, summary, _ = self.analyzer._build_attendance_data(home_games, 1)
        self.assertEqual(summary["played"], 1)

    def test_average_per_match_calculation(self):
        """Keskiarvo lasketaan oikein: yhteensä / pelattu."""
        home_games = {"HJK": [4000], "KuPS": [2000]}
        # played_total = 2, total = 4000+2000 = 6000 (no est games)
        _, summary, _ = self.analyzer._build_attendance_data(home_games, 2)
        self.assertEqual(summary["average_per_match"], 3000)

    def test_estimated_attendance_uses_hist_avg(self):
        """Pelattu ottelu ilman att-dataa käyttää historiallista keskiarvoa."""
        home_games = {"HJK": [0]}  # att=0 → käytetään hist_avg
        per_team, summary, is_real = self.analyzer._build_attendance_data(home_games, 1)
        hjk_row = next(r for r in per_team if r["joukkue"] == "HJK")
        expected_est = STADIUM_INFO["HJK"]["hist_keskiarvo"]
        self.assertEqual(hjk_row["arvio_katsojat"], expected_est)

    def test_highest_capacity_is_correct(self):
        """Suurin kapasiteetti vastaa STADIUM_INFO:n maksimiarvoa."""
        _, summary, _ = self.analyzer._build_attendance_data({}, 0)
        expected = max(v["kapasiteetti"] for v in STADIUM_INFO.values())
        self.assertEqual(summary["highest_capacity"], expected)

    def test_mixed_real_and_estimated(self):
        """Joukkueella on sekä todellisia (>0) että tuntemattomia (0) pelejä."""
        home_games = {"HJK": [6000, 0]}  # 1 todellinen, 1 estimoitu
        per_team, summary, is_real = self.analyzer._build_attendance_data(home_games, 2)
        self.assertTrue(is_real)
        hjk_row = next(r for r in per_team if r["joukkue"] == "HJK")
        self.assertEqual(hjk_row["real_katsojat"], 6000)
        self.assertEqual(hjk_row["real_peli_maara"], 1)
        expected_arvio = 6000 + STADIUM_INFO["HJK"]["hist_keskiarvo"]
        self.assertEqual(hjk_row["arvio_katsojat"], expected_arvio)


# ---------------------------------------------------------------------------
# TestAnalyzeIntegration
# ---------------------------------------------------------------------------

class TestAnalyzeIntegration(unittest.TestCase):
    """Integraatiotestit: varmistaa, että analyze() luo kelvollisen raportin."""

    def _run_analyze(self, ottelut_content: str = "") -> str:
        """Ajaa analyze() väliaikaisessa hakemistossa ja palauttaa raporttitekstin."""
        import attendance_analyzer as aa_mod
        orig_init = AttendanceAnalyzer.__init__

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            if ottelut_content:
                (tmp_path / "Ottelut.md").write_text(ottelut_content, encoding="utf-8")

            # Paikallista output_dir väliaikaiseen hakemistoon
            def patched_init(self_inner):
                self_inner.output_dir = tmp_path

            AttendanceAnalyzer.__init__ = patched_init
            try:
                analyzer = AttendanceAnalyzer()
                result = analyzer.analyze()
            finally:
                AttendanceAnalyzer.__init__ = orig_init

            report = (tmp_path / "Yleiso2026.md").read_text(encoding="utf-8")

        return result, report

    def test_returns_true_on_success(self):
        """analyze() palauttaa True onnistuessaan."""
        result, _ = self._run_analyze()
        self.assertTrue(result)

    def test_creates_output_file(self):
        """analyze() luo Yleiso2026.md-tiedoston."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            orig_init = AttendanceAnalyzer.__init__

            def patched_init(self_inner):
                self_inner.output_dir = tmp_path

            AttendanceAnalyzer.__init__ = patched_init
            try:
                analyzer = AttendanceAnalyzer()
                analyzer.analyze()
            finally:
                AttendanceAnalyzer.__init__ = orig_init

            self.assertTrue((tmp_path / "Yleiso2026.md").exists())

    def test_report_has_required_headings(self):
        """Raportti sisältää pakolliset otsikot."""
        _, report = self._run_analyze()
        self.assertIn("# Veikkausliiga 2026 - Yleisömäärät", report)
        self.assertIn("## Kauden ennuste / tilanne", report)
        self.assertIn("## Joukkuekohtaiset stadionit", report)

    def test_report_pre_season_warning_shown(self):
        """Ilman pelatttuja otteluita raportissa näkyy ennakkovaroitus."""
        _, report = self._run_analyze("")
        self.assertIn("⚠", report)

    def test_report_with_played_games_no_warning(self):
        """Kun otteluita on pelattu, ennakkovaroitusta ei näy."""
        content = (
            "## Pelatut ottelut\n\n"
            "| Päivämäärä | Koti | Tulos | Vieras | Yleisö |\n"
            "|------------|------|-------|--------|--------|\n"
            "| La 4.4.2026 | HJK | 3-0 | SJK | 5041 |\n"
        )
        _, report = self._run_analyze(content)
        self.assertNotIn("⚠", report)

    def test_report_shows_real_katsojat_column_when_data_available(self):
        """Kun todellisia tietoja on, taulukossa näkyy 'Todelliset katsojat'."""
        content = (
            "## Pelatut ottelut\n\n"
            "| Päivämäärä | Koti | Tulos | Vieras | Yleisö |\n"
            "|------------|------|-------|--------|--------|\n"
            "| La 4.4.2026 | HJK | 3-0 | SJK | 5041 |\n"
        )
        _, report = self._run_analyze(content)
        self.assertIn("Todelliset katsojat", report)

    def test_report_no_real_katsojat_column_without_data(self):
        """Ilman todellisia tietoja (att=0) taulukossa ei ole 'Todelliset katsojat'."""
        content = (
            "## Pelatut ottelut\n\n"
            "| Päivämäärä | Koti | Tulos | Vieras |\n"
            "|------------|------|-------|--------|\n"
            "| La 4.4.2026 | HJK | 3-0 | SJK |\n"
        )
        _, report = self._run_analyze(content)
        self.assertNotIn("Todelliset katsojat", report)

    def test_all_stadium_info_teams_in_report(self):
        """Kaikki 12 joukkuetta esiintyvät raportissa."""
        _, report = self._run_analyze()
        for team in STADIUM_INFO:
            self.assertIn(team, report, f"Joukkue '{team}' puuttuu raportista")

    def test_report_contains_hist_footer(self):
        """Raportin lopussa on historialliset tiedot selitys."""
        _, report = self._run_analyze()
        self.assertIn("Hist. keskiarvo", report)


# ---------------------------------------------------------------------------
# TestFetchMatchesAttendanceParsing
# ---------------------------------------------------------------------------

class TestFetchMatchesAttendanceParsing(unittest.TestCase):
    """Testaa, että fetch_matches.py parsii yleisömäärän oikein HTML:stä."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from fetch_matches import MatchFetcher
        self.fetcher = MatchFetcher()

    def _make_8col_html(self, score, attendance):
        return (
            "<html><body><table>"
            "<tr>"
            "<td>1</td>"
            "<td>La 4.4.2026</td>"
            "<td>13:00</td>"
            "<td>La 4.4.2026<br>13:00</td>"
            f"<td>HJK - SJK</td>"
            "<td>Ennakko\nSeuranta\nTilastot</td>"
            f"<td>{score}</td>"
            f"<td>{attendance}</td>"
            "</tr>"
            "</table></body></html>"
        )

    def test_attendance_parsed_from_8col_played(self):
        """Yleisömäärä parsitaan pelatun 8-sarakeisen ottelun soluista."""
        html = self._make_8col_html("3 \u2014 0", "5041")
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["yleiso"], 5041)

    def test_attendance_zero_when_not_played(self):
        """Tulevalla ottelulla (tulos='-') yleisö on 0."""
        html = self._make_8col_html("-", "-")
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["yleiso"], 0)

    def test_attendance_zero_in_7col_format(self):
        """7-sarakkeisessa muodossa (ei att-solua) yleisö on 0."""
        html = (
            "<html><body><table>"
            "<tr>"
            "<td>1</td>"
            "<td>La 4.4.2026</td>"
            "<td>13:00</td>"
            "<td><a href='#'>Katso</a></td>"
            "<td>HJK</td>"
            "<td>2-1</td>"
            "<td>KuPS</td>"
            "</tr>"
            "</table></body></html>"
        )
        matches = self.fetcher._parse_matches_from_html(html)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].get("yleiso", 0), 0)

    def test_yleiso_field_present_in_all_matches(self):
        """Jokainen parsittu ottelu sisältää 'yleiso'-kentän."""
        html = self._make_8col_html("2 \u2014 1", "3401")
        matches = self.fetcher._parse_matches_from_html(html)
        for m in matches:
            self.assertIn("yleiso", m)


if __name__ == "__main__":
    unittest.main()
