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
        get_output_path,
    )
    from fetch_stats import StatsProcessor
except ImportError as e:
    print(f"Varoitus: {e}")
    PARTICIPANTS = []
    STANDINGS_SCORING = {0: 3, 1: 2, 2: 1}
    SCORER_SCORING = {"exact": 5, "in_list": 2}
    TOP_SCORERS_COUNT = 10
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

        # Käytetään ensimmäisen osallistujan ennustaman joukkuemäärää maksimipisteiden laskuun
        # (tai todellista joukkuemäärää, jos se on suurempi) – tyypillisesti 12 joukkuetta
        n_teams = max(
            len(PARTICIPANTS[0].get("standings_prediction", [])) if PARTICIPANTS else 0,
            len(actual_standings),
        ) or 12
        # Max pisteet sarjataulukosta: jokainen joukkue täsmäosumana
        max_standings = STANDINGS_SCORING.get(0, 3) * n_teams
        # Max pisteet maalintekijöistä: jokainen täsmäosuma
        max_scorers = SCORER_SCORING.get("exact", 5) * TOP_SCORERS_COUNT

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# Veikkausliiga 2026 — Veikkausten Pisteet\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

                if is_dummy:
                    f.write(
                        "*⚠ Huom: Tilastot perustuvat esimerkkidataan — pisteet ovat simuloituja.*\n\n"
                    )

                # ---- Pisteytysjärjestelmän selitys ----
                f.write("## Pisteytysjärjestelmä\n\n")
                f.write("### Sarjataulukko\n\n")
                f.write("| Ero sijoituksissa | Pisteet |\n")
                f.write("|-------------------|---------|\n")
                for diff, pts in sorted(STANDINGS_SCORING.items()):
                    f.write(f"| {diff} sijoitusta | {pts} p |\n")
                f.write(f"| ≥ 3 sijoitusta | 0 p |\n")
                f.write(f"\n*Maksimi sarjataulukosta: {max_standings} pistettä*\n\n")

                f.write("### Maalintekijät\n\n")
                f.write("| Tilanne | Pisteet |\n")
                f.write("|---------|----------|\n")
                f.write(f"| Täsmäosuma (oikea sijoitus) | {SCORER_SCORING.get('exact', 5)} p |\n")
                f.write(f"| Pelaaja top-{TOP_SCORERS_COUNT}-listalla | {SCORER_SCORING.get('in_list', 2)} p |\n")
                f.write("| Ei top-listalla | 0 p |\n")
                f.write(f"\n*Maksimi maalintekijöistä: {max_scorers} pistettä (top-{TOP_SCORERS_COUNT})*\n\n")

                # ---- Pistetaulukko (leaderboard) ----
                f.write("## 🏆 Pistetaulukko\n\n")
                f.write("| Sijoitus | Osallistuja | Sarjataulukko | Maalintekijät | Yhteensä |\n")
                f.write("|:--------:|-------------|:-------------:|:-------------:|:--------:|\n")
                for rank, r in enumerate(results, 1):
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
                    f.write(
                        f"| {medal} | {r['name']} "
                        f"| {r['standings_points']} / {max_standings} "
                        f"| {r['scorer_points']} / {max_scorers} "
                        f"| **{r['total_points']}** |\n"
                    )
                f.write("\n")

                # ---- Toteutunut sarjataulukko ----
                f.write("## Toteutunut sarjataulukko\n\n")
                f.write("| # | Joukkue |\n")
                f.write("|---|--------|\n")
                for i, team in enumerate(actual_standings, 1):
                    f.write(f"| {i} | {team} |\n")
                f.write("\n")

                # ---- Toteutuneet maalintekijät ----
                f.write("## Toteutuneet maalintekijät (top)\n\n")
                if actual_scorers:
                    f.write("| # | Pelaaja |\n")
                    f.write("|---|--------|\n")
                    for i, player in enumerate(actual_scorers, 1):
                        f.write(f"| {i} | {player} |\n")
                else:
                    f.write("*Maalintekijätietoja ei vielä saatavilla.*\n")
                f.write("\n")

                # ---- Yksittäiset pisteet per osallistuja ----
                f.write("## Yksityiskohtaiset pisteet\n\n")

                for r in results:
                    f.write(f"### {r['name']} — {r['total_points']} pistettä\n\n")

                    # Sarjataulukko-ennuste
                    f.write(f"**Sarjataulukkoennuste** ({r['standings_points']} / {max_standings} p)\n\n")
                    f.write("| Veikkaama sija | Joukkue | Toteutunut sija | Ero | Pisteet |\n")
                    f.write("|:--------------:|---------|:---------------:|:---:|:-------:|\n")
                    for d in r["standings_details"]:
                        f.write(
                            f"| {d['veikkausi']} | {d['joukkue']} "
                            f"| {d['toteutunut']} | {d['ero']} | {d['pisteet']} |\n"
                        )
                    f.write("\n")

                    # Maalintekijä-ennuste
                    f.write(f"**Maalintekijäennuste** ({r['scorer_points']} / {max_scorers} p)\n\n")
                    f.write("| Veikkaama sija | Pelaaja | Toteutunut sija | Pisteet | Tila |\n")
                    f.write("|:--------------:|---------|:---------------:|:-------:|------|\n")
                    for d in r["scorer_details"]:
                        f.write(
                            f"| {d['veikkausi']} | {d['pelaaja']} "
                            f"| {d['toteutunut']} | {d['pisteet']} | {d['tila']} |\n"
                        )
                    f.write("\n---\n\n")

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
