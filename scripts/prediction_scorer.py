"""
Veikkausliiga 2026 - Veikkausten pisteytysjärjestelmä

Laskee pisteet osallistujien sarjataulukko- ja maalintekijäveikkauksista
verraten niitä kauden todellisiin tuloksiin.

Pisteytysjärjestelmä:
  Sarjataulukko:
    Täsmäosuma (ero 0)  → 10 pistettä
    Ero ≥ 1 sijoitusta  → 0 pistettä

  Maalintekijät:
    Pelaaja top-N listalla → 10 pistettä (in_list-bonus)
    Per maali (kaikille)   →  2 pistettä
    Per syöttö (kaikille)  →  1 piste
    Ei tilastoja           →  0 pistettä

  Huom: maalit ja syötöt lasketaan kaikille veikkatuille pelaajille,
  myös niille jotka ovat top-N listan ulkopuolella.
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
except ImportError as e:
    print(f"Varoitus (config): {e}")
    PARTICIPANTS = []
    STANDINGS_SCORING = {0: 10}
    SCORER_SCORING = {"in_list": 10, "goal": 2, "assist": 1}
    TOP_SCORERS_COUNT = 10
    TEAMS_2026 = []
    TEAM_LOGOS = {}

    def get_output_path(filename):
        return Path("output") / filename

try:
    from fetch_stats import StatsProcessor
except ImportError as e:
    print(f"Varoitus (fetch_stats): {e}")
    StatsProcessor = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PredictionScorer:
    """Laskee veikkausten pisteet"""

    # ------------------------------------------------------------------
    # Pisteytysfunktiot
    # ------------------------------------------------------------------

    def _standings_points_for_diff(self, diff):
        return STANDINGS_SCORING.get(diff, 0)

    def _resolve_player_name(self, predicted_name, name_dict):
        """Etsii pelaajan nimen hakemistosta, tukee lyhennettyjä yhdyssukunimiä.

        Yrittää ensin tarkkaa vastaavuutta, sitten tarkistaa päättyykö jokin
        todellinen nimi ennustettuun nimeen (esim. "Barbosa, Neemias" löytää
        "Benavenuto Barbosa, Neemias").

        Parameters
        ----------
        predicted_name : str  – ennustettu nimi (esim. "Barbosa, Neemias")
        name_dict      : dict – hakemisto nimi → data

        Returns
        -------
        matched_name : str | None
        """
        if predicted_name in name_dict:
            return predicted_name
        for actual_name in name_dict:
            if actual_name.endswith(predicted_name):
                return actual_name
        return None

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
            act_i_val = actual_pos.get(team)
            if act_i_val is None:
                # Joukkuetta ei löydy sarjataulukosta — ei pisteitä
                pts = 0
                diff = None
                act_display = "-"
            else:
                diff = abs(pred_i - act_i_val)
                pts = self._standings_points_for_diff(diff)
                act_display = act_i_val
            total += pts
            details.append(
                {
                    "joukkue": team,
                    "veikkausi": pred_i,
                    "toteutunut": act_display,
                    "ero": diff,
                    "pisteet": pts,
                }
            )

        return total, details

    def calculate_scorer_points(self, predicted, actual, all_players=None):
        """
        Laskee pisteet maalintekijäennusteesta.

        Parameters
        ----------
        predicted   : list[str]   – pelaajat ennustusjärjestyksessä
        actual      : list[dict]  – pelaajat top-N listan mukaan
                                    (kukin dict: pelaaja, maalit, syotot)
        all_players : dict | None – kaikki pelaajat nimi → {maalit, syotot};
                                    käytetään maalien/syöttöjen laskemiseen
                                    myös top-N listan ulkopuolisille pelaajille

        Returns
        -------
        (total_points: int, details: list[dict])
        """
        # Rakennetaan hakemisto: pelaajan nimi → {pos, maalit, syotot}
        actual_dict = {}
        for i, p in enumerate(actual, 1):
            actual_dict[p["pelaaja"]] = {
                "pos": i,
                "maalit": p["maalit"],
                "syotot": p["syotot"],
            }
        total = 0
        details = []

        for pred_i, player in enumerate(predicted, 1):
            matched_name = self._resolve_player_name(player, actual_dict)
            stats = actual_dict.get(matched_name) if matched_name else None
            if stats is None:
                # Pelaaja ei top-N listalla — tarkistetaan täydet tilastot
                full_name = self._resolve_player_name(player, all_players) if all_players else None
                full = all_players.get(full_name) if full_name else None
                if full is not None:
                    goals = full["maalit"]
                    assists = full["syotot"]
                    pts = (
                        goals * SCORER_SCORING.get("goal", 2)
                        + assists * SCORER_SCORING.get("assist", 1)
                    )
                    act_pos = "-"
                    status = f"⚠️ Top-{len(actual)}-listan ulkopuolella"
                else:
                    pts = 0
                    act_pos = "-"
                    goals = 0
                    assists = 0
                    status = "Ei listalla"
            else:
                act_pos = stats["pos"]
                goals = stats["maalit"]
                assists = stats["syotot"]
                pts = (
                    SCORER_SCORING.get("in_list", 10)
                    + goals * SCORER_SCORING.get("goal", 2)
                    + assists * SCORER_SCORING.get("assist", 1)
                )
                status = f"✅ Top-listalla (sija {act_pos})"

            total += pts
            details.append(
                {
                    "pelaaja": player,
                    "veikkausi": pred_i,
                    "toteutunut": act_pos,
                    "maalit": goals,
                    "syotot": assists,
                    "pisteet": pts,
                    "tila": status,
                }
            )

        return total, details

    # ------------------------------------------------------------------
    # Päälogiikka
    # ------------------------------------------------------------------

    def score_all(self, actual_standings, actual_scorers, all_players=None):
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
                all_players,
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

        # Osallistujat joilla on veikkaus ensin, tyhjät veikkaukset loppuun
        results.sort(
            key=lambda x: (not (x["standings_details"] or x["scorer_details"]), -x["total_points"])
        )
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
        max_standings = STANDINGS_SCORING.get(0, 10) * n_teams

        # Laske maksimipisteet maalintekijöistä: paras mahdollinen tulos jos
        # kaikki veikkaajat osuisivat top-listalle oikeiden tilastojen kanssa
        n_scorers_predicted = max(
            (len(p.get("scorers_prediction", [])) for p in PARTICIPANTS if p.get("scorers_prediction")),
            default=5,
        ) or 5
        if actual_scorers:
            max_scorers = sum(
                SCORER_SCORING.get("in_list", 10)
                + p["maalit"] * SCORER_SCORING.get("goal", 2)
                + p["syotot"] * SCORER_SCORING.get("assist", 1)
                for p in actual_scorers[:n_scorers_predicted]
            )
        else:
            max_scorers = SCORER_SCORING.get("in_list", 10) * n_scorers_predicted

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
                filled_count = sum(1 for p in PARTICIPANTS if p.get("standings_prediction", []))
                f.write("## 🥇 Pistetaulukko\n\n")
                f.write(f"*Veikkauksia jätetty: {filled_count}/{len(PARTICIPANTS)}*\n\n")
                f.write("| Sija | Osallistuja | Sarjataulukko | Maalintekijät | Yhteensä |\n")
                f.write("|:----:|-------------|:-------------:|:-------------:|:--------:|\n")
                filled_rank = 0
                for r in results:
                    is_empty = not r["standings_details"] and not r["scorer_details"]
                    if is_empty:
                        f.write(
                            f"| — | {r['name']} "
                            f"| *(ei veikkausta)* "
                            f"| *(ei veikkausta)* "
                            f"| — |\n"
                        )
                    else:
                        filled_rank += 1
                        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(filled_rank, f"{filled_rank}.")
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
                f.write(f"| 0 (täsmäosuma) | {STANDINGS_SCORING.get(0, 10)} p |\n")
                f.write(f"| ≥ 1 sijoitus | {STANDINGS_SCORING.get(1, 0)} p |\n\n")

                f.write(f"**Maalintekijät** (maks. {max_scorers} p, top-{TOP_SCORERS_COUNT} lista)\n\n")
                f.write("| Tilanne | Pisteet |\n")
                f.write("|:-------:|:-------:|\n")
                f.write(f"| ✅ Top-{TOP_SCORERS_COUNT}-listalla | {SCORER_SCORING.get('in_list', 10)} p |\n")
                f.write(f"| ⚽ Per maali (kaikille) | {SCORER_SCORING.get('goal', 2)} p |\n")
                f.write(f"| 🎯 Per syöttö (kaikille) | {SCORER_SCORING.get('assist', 1)} p |\n")
                f.write(f"| ⚠️ Top-{TOP_SCORERS_COUNT}-listan ulkopuolella | vain maalit+syötöt |\n")
                f.write("| ❌ Ei tilastoja | 0 p |\n\n")
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
                    f.write("| # | Pelaaja | M | S |\n")
                    f.write("|:-:|--------|:-:|:-:|\n")
                    for i, p in enumerate(actual_scorers, 1):
                        medal_icon = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
                        f.write(f"| {i} | {medal_icon} {p['pelaaja']} | {p['maalit']} | {p['syotot']} |\n")
                else:
                    f.write("*Maalintekijätietoja ei vielä saatavilla.*\n")
                f.write("\n---\n\n")

                # ---- Yksittäiset pisteet per osallistuja ----
                f.write("## 📝 Yksityiskohtaiset pisteet\n\n")

                for r in results:
                    has_standings = bool(r["standings_details"])
                    has_scorers = bool(r["scorer_details"])

                    if not has_standings and not has_scorers:
                        f.write(f"### {r['name']} — *(veikkaus ei vielä jätetty)*\n\n")
                        f.write("*Tämä osallistuja ei ole vielä jättänyt veikkaustaan.*\n\n")
                        f.write("---\n\n")
                        continue

                    f.write(f"### {r['name']} — {r['total_points']} pistettä\n\n")

                    # Sarjataulukko-ennuste
                    s_pct = round(r["standings_points"] / max_standings * 100) if max_standings else 0
                    f.write(
                        f"**Sarjataulukko:** {r['standings_points']}/{max_standings} p "
                        f"({s_pct}%) {pct_bar(r['standings_points'], max_standings, 15)}\n\n"
                    )
                    if has_standings:
                        f.write("| Veikkaama sija | Joukkue | Toteutunut sija | Ero | Pisteet |\n")
                        f.write("|:--------------:|---------|:---------------:|:---:|:-------:|\n")
                        for d in r["standings_details"]:
                            if d["ero"] is None:
                                diff_icon = "❌"
                                ero_display = "-"
                            elif d["ero"] == 0:
                                diff_icon = "✅"
                                ero_display = d["ero"]
                            else:
                                diff_icon = "❌"
                                ero_display = d["ero"]
                            f.write(
                                f"| {d['veikkausi']} | {team_cell(d['joukkue'])} "
                                f"| {d['toteutunut']} | {diff_icon} {ero_display} | {d['pisteet']} |\n"
                            )
                    f.write("\n")

                    # Maalintekijä-ennuste
                    g_pct = round(r["scorer_points"] / max_scorers * 100) if max_scorers else 0
                    f.write(
                        f"**Maalintekijät:** {r['scorer_points']}/{max_scorers} p "
                        f"({g_pct}%) {pct_bar(r['scorer_points'], max_scorers, 15)}\n\n"
                    )
                    if has_scorers:
                        f.write("| Veikkaama sija | Pelaaja | Toteutunut sija | Maalit | Syötöt | Pisteet | Tila |\n")
                        f.write("|:--------------:|---------|:---------------:|:------:|:------:|:-------:|------|\n")
                        for d in r["scorer_details"]:
                            f.write(
                                f"| {d['veikkausi']} | {d['pelaaja']} "
                                f"| {d['toteutunut']} | {d['maalit']} | {d['syotot']} "
                                f"| {d['pisteet']} | {d['tila']} |\n"
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

        # Todellinen maalintekijälista — haetaan kerran, johdetaan sekä
        # top-N lista (in_list-bonus) että täysi hakemisto (maalit/syötöt kaikille)
        all_player_stats, is_dummy_scorers = processor.fetch_full_player_stats()
        all_players_sorted = sorted(all_player_stats, key=lambda x: x["maalit"], reverse=True)
        actual_scorers = [
            {"pelaaja": p["pelaaja"], "maalit": p["maalit"], "syotot": p["syotot"]}
            for p in all_players_sorted[:TOP_SCORERS_COUNT]
        ]
        if not actual_scorers:
            actual_scorers = processor._create_dummy_scorers(TOP_SCORERS_COUNT)
            is_dummy_scorers = True

        # Täysi pelaajahakemisto maalien/syöttöjen tarkistamiseen top-N listan ulkopuolelta
        all_players_dict = {
            p["pelaaja"]: {"maalit": p["maalit"], "syotot": p["syotot"]}
            for p in all_player_stats
        }

        is_dummy = is_dummy_standings or is_dummy_scorers

        if not actual_standings:
            logger.error("✗ Sarjataulukko ei saatavilla")
            return False

        # Laske pisteet
        results = self.score_all(actual_standings, actual_scorers, all_players_dict)
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
