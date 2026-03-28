"""
Veikkausliiga 2026 - Veikkausten pisteytysjärjestelmä

Laskee pisteet osallistujien sarjataulukko- ja maalintekijäveikkauksista
verraten niitä kauden todellisiin tuloksiin.

Pisteytysjärjestelmä:
  Sarjataulukko:
    Ero 0 (täsmäosuma)  → 3 pistettä
    Ero 1 sijoitus      → 2 pistettä
    Ero 2 sijoitusta    → 1 piste
    Ero ≥ 3 sijoitusta  → 0 pistettä

  Maalintekijät:
    Täsmäosuma (oikea sijoitus) → 5 pistettä
    Pelaaja top-listalla        → 2 pistettä
    Ei top-listalla             → 0 pistettä
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import (
        PARTICIPANTS,
        STANDINGS_SCORING,
        SCORER_SCORING,
        TOP_SCORERS_COUNT,
        TEAMS_2026,
        TEAM_LOGOS,
        get_output_path,
    )
    from fetch_stats import StatsProcessor
except ImportError as e:
    print(f"Varoitus: {e}")
    PARTICIPANTS = []
    STANDINGS_SCORING = {0: 3, 1: 2, 2: 1}
    SCORER_SCORING = {"exact": 5, "in_list": 2}
    TOP_SCORERS_COUNT = 10
    TEAMS_2026 = []
    TEAM_LOGOS = {}
    StatsProcessor = None

    def get_output_path(filename):
        return Path("output") / filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PredictionScorer:
    """Laskee veikkausten pisteet"""

    # ------------------------------------------------------------------
    # Pisteytysfunktiot
    # ------------------------------------------------------------------

    def _standings_points_for_diff(self, diff):
        return STANDINGS_SCORING.get(diff, 0)

    def calculate_standings_points(self, predicted, actual):
        """
        Laskee pisteet sarjataulukkoennusteesta.

        Parameters
        ----------
        predicted : list[str]  – joukkueet ennustusjärjestyksessä
        actual    : list[str]  – joukkueet toteutuneen taulukon mukaan

        Returns
        -------
        (total_points: int, details: list[dict])
        """
        actual_pos = {team: i + 1 for i, team in enumerate(actual)}
        total = 0
        details = []

        for pred_i, team in enumerate(predicted, 1):
            act_i = actual_pos.get(team, len(actual))
            diff = abs(pred_i - act_i)
            pts = self._standings_points_for_diff(diff)
            total += pts
            details.append(
                {
                    "joukkue": team,
                    "veikkausi": pred_i,
                    "toteutunut": act_i,
                    "ero": diff,
                    "pisteet": pts,
                }
            )

        return total, details

    def calculate_scorer_points(self, predicted, actual):
        """
        Laskee pisteet maalintekijäennusteesta.

        Parameters
        ----------
        predicted : list[str]  – pelaajat ennustusjärjestyksessä
        actual    : list[str]  – pelaajat toteutuneen maalimäärän mukaan

        Returns
        -------
        (total_points: int, details: list[dict])
        """
        actual_pos = {player: i + 1 for i, player in enumerate(actual)}
        total = 0
        details = []

        for pred_i, player in enumerate(predicted, 1):
            act_i = actual_pos.get(player)
            if act_i is None:
                pts = 0
                status = "Ei top-listalla"
            elif act_i == pred_i:
                pts = SCORER_SCORING.get("exact", 5)
                status = f"✅ Täsmäosuma! (sija {act_i})"
            else:
                pts = SCORER_SCORING.get("in_list", 2)
                status = f"🔸 Top-listalla (sija {act_i})"

            total += pts
            details.append(
                {
                    "pelaaja": player,
                    "veikkausi": pred_i,
                    "toteutunut": act_i if act_i is not None else "-",
                    "pisteet": pts,
                    "tila": status,
                }
            )

        return total, details

    # ------------------------------------------------------------------
    # Päälogiikka
    # ------------------------------------------------------------------

    def score_all(self, actual_standings, actual_scorers):
        """Laskee pisteet kaikille osallistujille"""
        results = []

        for participant in PARTICIPANTS:
            s_pts, s_details = self.calculate_standings_points(
                participant.get("standings_prediction", []),
                actual_standings,
            )
            g_pts, g_details = self.calculate_scorer_points(
                participant.get("scorers_prediction", []),
                actual_scorers,
            )
            results.append(
                {
                    "name": participant["name"],
                    "standings_points": s_pts,
                    "scorer_points": g_pts,
                    "total_points": s_pts + g_pts,
                    "standings_details": s_details,
                    "scorer_details": g_details,
                }
            )

        results.sort(key=lambda x: x["total_points"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Raportointi
    # ------------------------------------------------------------------

    def save_report(self, results, actual_standings, actual_scorers, is_dummy):
        """Tallentaa pisteytysraportin Markdown-muodossa"""
        report_path = get_output_path("Veikkaukset2026.md")

        n_teams = max(
            len(PARTICIPANTS[0].get("standings_prediction", [])) if PARTICIPANTS else 0,
            len(actual_standings),
        ) or 12
        max_standings = STANDINGS_SCORING.get(0, 3) * n_teams
        max_scorers = SCORER_SCORING.get("exact", 5) * TOP_SCORERS_COUNT

        def team_cell(team):
            """Palauttaa taulukkosolu joukkueen logolla ja nimellä."""
            logo = TEAM_LOGOS.get(team, "")
            if logo:
                return f'<img src="{logo}" width="18" height="18"> {team}'
            return team

        def pct_bar(pts, max_pts, width=10):
            """Luo yksinkertainen edistyspalkki."""
            if max_pts == 0:
                return "░" * width
            filled = round(pts / max_pts * width)
            return "█" * filled + "░" * (width - filled)

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                # ---- Otsikko ----
                f.write("# 🏆 Veikkausliiga 2026 — Veikkaukset\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

                if is_dummy:
                    f.write(
                        "> ⚠️ **Huom:** Tilastot perustuvat esimerkkidataan — pisteet ovat simuloituja.\n\n"
                    )

                f.write("---\n\n")

                # ---- Pistetaulukko (leaderboard) ----
                f.write("## 🥇 Pistetaulukko\n\n")
                f.write("| Sija | Osallistuja | Sarjataulukko | Maalintekijät | Yhteensä |\n")
                f.write("|:----:|-------------|:-------------:|:-------------:|:--------:|\n")
                for rank, r in enumerate(results, 1):
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
                    s_bar = pct_bar(r["standings_points"], max_standings)
                    g_bar = pct_bar(r["scorer_points"], max_scorers)
                    f.write(
                        f"| {medal} | **{r['name']}** "
                        f"| {r['standings_points']}/{max_standings} {s_bar} "
                        f"| {r['scorer_points']}/{max_scorers} {g_bar} "
                        f"| 🎯 **{r['total_points']}** |\n"
                    )
                f.write("\n")

                # ---- Pisteytysjärjestelmä ----
                f.write("<details>\n<summary>📋 Pisteytysjärjestelmä</summary>\n\n")
                f.write("**Sarjataulukko** (maks. " + str(max_standings) + " p)\n\n")
                f.write("| Ero sijoituksissa | Pisteet |\n")
                f.write("|:-----------------:|:-------:|\n")
                for diff, pts in sorted(STANDINGS_SCORING.items()):
                    f.write(f"| {diff} sijoitusta | {pts} p |\n")
                f.write(f"| ≥ 3 sijoitusta | 0 p |\n\n")

                f.write(f"**Maalintekijät** (maks. {max_scorers} p, top-{TOP_SCORERS_COUNT} lista)\n\n")
                f.write("| Tilanne | Pisteet |\n")
                f.write("|:-------:|:-------:|\n")
                f.write(f"| ✅ Täsmäosuma | {SCORER_SCORING.get('exact', 5)} p |\n")
                f.write(f"| 🔸 Top-listalla | {SCORER_SCORING.get('in_list', 2)} p |\n")
                f.write("| ❌ Ei listalla | 0 p |\n\n")
                f.write("</details>\n\n")

                f.write("---\n\n")

                # ---- Toteutunut sarjataulukko ----
                f.write("## 📊 Toteutunut sarjataulukko\n\n")
                f.write("| # | Joukkue |\n")
                f.write("|:-:|--------|\n")
                for i, team in enumerate(actual_standings, 1):
                    f.write(f"| {i} | {team_cell(team)} |\n")
                f.write("\n")

                # ---- Toteutuneet maalintekijät ----
                f.write("## ⚽ Toteutuneet maalintekijät (top)\n\n")
                if actual_scorers:
                    f.write("| # | Pelaaja |\n")
                    f.write("|:-:|--------|\n")
                    for i, player in enumerate(actual_scorers, 1):
                        medal_icon = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
                        f.write(f"| {i} | {medal_icon} {player} |\n")
                else:
                    f.write("*Maalintekijätietoja ei vielä saatavilla.*\n")
                f.write("\n---\n\n")

                # ---- Yksittäiset pisteet per osallistuja ----
                f.write("## 📝 Yksityiskohtaiset pisteet\n\n")

                for r in results:
                    f.write(f"### {r['name']} — {r['total_points']} pistettä\n\n")

                    # Sarjataulukko-ennuste
                    s_pct = round(r["standings_points"] / max_standings * 100) if max_standings else 0
                    f.write(
                        f"**Sarjataulukko:** {r['standings_points']}/{max_standings} p "
                        f"({s_pct}%) {pct_bar(r['standings_points'], max_standings, 15)}\n\n"
                    )
                    f.write("| Veikkaama sija | Joukkue | Toteutunut sija | Ero | Pisteet |\n")
                    f.write("|:--------------:|---------|:---------------:|:---:|:-------:|\n")
                    for d in r["standings_details"]:
                        diff_icon = "✅" if d["ero"] == 0 else ("🟡" if d["ero"] <= 2 else "❌")
                        f.write(
                            f"| {d['veikkausi']} | {team_cell(d['joukkue'])} "
                            f"| {d['toteutunut']} | {diff_icon} {d['ero']} | {d['pisteet']} |\n"
                        )
                    f.write("\n")

                    # Maalintekijä-ennuste
                    g_pct = round(r["scorer_points"] / max_scorers * 100) if max_scorers else 0
                    f.write(
                        f"**Maalintekijät:** {r['scorer_points']}/{max_scorers} p "
                        f"({g_pct}%) {pct_bar(r['scorer_points'], max_scorers, 15)}\n\n"
                    )
                    f.write("| Veikkaama sija | Pelaaja | Toteutunut sija | Pisteet | Tila |\n")
                    f.write("|:--------------:|---------|:---------------:|:-------:|------|\n")
                    for d in r["scorer_details"]:
                        f.write(
                            f"| {d['veikkausi']} | {d['pelaaja']} "
                            f"| {d['toteutunut']} | {d['pisteet']} | {d['tila']} |\n"
                        )
                    f.write("\n---\n\n")

                # ---- Lisää oma veikkaus -ohje ----
                f.write("## ✏️ Lisää oma veikkauksesi\n\n")
                f.write(
                    "Haluatko osallistua? Lisää oma veikkauksesi muokkaamalla `scripts/config.py`-tiedostoa.\n\n"
                )
                f.write("**1.** Avaa `scripts/config.py` omalla koodieditorillasi.\n\n")
                f.write("**2.** Etsi `PARTICIPANTS`-lista ja lisää oma lohkosi:\n\n")
                f.write("```python\n")
                f.write("{\n")
                f.write('    "name": "Sinun Nimi",\n')
                f.write('    "standings_prediction": [\n')
                f.write('        "HJK",           # Veikkaat 1. sijaksi\n')
                f.write('        "KuPS",          # 2. sija\n')
                f.write('        "FC Inter",      # 3. sija\n')
                f.write('        "SJK",           # 4. sija\n')
                f.write('        "Ilves",         # 5. sija\n')
                f.write('        "FC Lahti",      # 6. sija\n')
                f.write('        "FF Jaro",       # 7. sija\n')
                f.write('        "VPS",           # 8. sija\n')
                f.write('        "IFK Mariehamn", # 9. sija\n')
                f.write('        "IF Gnistan",    # 10. sija\n')
                f.write('        "AC Oulu",       # 11. sija\n')
                f.write('        "TPS",           # 12. sija\n')
                f.write('    ],\n')
                f.write('    "scorers_prediction": [\n')
                f.write('        "Plange, Luke",         # 1. maalintekijä\n')
                f.write('        "Karjalainen, Rasmus",  # 2. maalintekijä\n')
                f.write('        "Odutayo, Colin",       # 3. maalintekijä\n')
                f.write('        "Coffey, Ashley",       # 4. maalintekijä\n')
                f.write('        "Moreno, Jaime",        # 5. maalintekijä\n')
                f.write('    ],\n')
                f.write('},\n')
                f.write("```\n\n")
                f.write("**3.** Aja `python scripts/main.py` — pisteet päivittyvät automaattisesti! 🚀\n\n")

            logger.info(f"✓ Veikkausraportti tallennettu: {report_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Virhe raportin tallennuksessa: {e}")
            return False

    # ------------------------------------------------------------------
    # Pääfunktio
    # ------------------------------------------------------------------

    def run(self):
        """Pääfunktio — hakee tilastot ja laskee veikkausten pisteet"""
        logger.info("\n" + "=" * 60)
        logger.info("VEIKKAUSTEN PISTEYTYSJÄRJESTELMÄ - Veikkausliiga 2026")
        logger.info("=" * 60)

        if not PARTICIPANTS:
            logger.warning("⚠ Ei osallistujia config.py:ssä. Lisää PARTICIPANTS-listaan.")

        if StatsProcessor is None:
            logger.error("✗ StatsProcessor ei saatavilla")
            return False

        processor = StatsProcessor()

        # Todellinen sarjataulukko
        standings = processor.fetch_standings()
        actual_standings = [s["joukkue"] for s in standings]
        is_dummy_standings = any(s.get("_is_dummy") for s in standings)

        # Todellinen maalintekijälista
        actual_scorers, is_dummy_scorers = processor.fetch_top_scorers(count=TOP_SCORERS_COUNT)

        is_dummy = is_dummy_standings or is_dummy_scorers

        if not actual_standings:
            logger.error("✗ Sarjataulukko ei saatavilla")
            return False

        # Laske pisteet
        results = self.score_all(actual_standings, actual_scorers)
        logger.info(f"✓ Pisteet laskettu: {len(results)} osallistujaa")
        for r in results:
            logger.info(f"   {r['name']}: {r['total_points']} pistettä "
                        f"(sarjat {r['standings_points']}, maalit {r['scorer_points']})")

        # Tallenna raportti
        return self.save_report(results, actual_standings, actual_scorers, is_dummy)


def main():
    scorer = PredictionScorer()
    return scorer.run()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
