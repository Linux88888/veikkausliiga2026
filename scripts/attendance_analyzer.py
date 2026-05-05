"""
Veikkausliiga 2026 - Yleisömäärä Analyysi
Analysoi stadionilla käyneiden määrät.

Oikeat yleisömäärätiedot haetaan Ottelut.md-tiedostosta (Yleisö-sarake),
jonka fetch_matches.py täyttää veikkausliiga.com-sivulta. Kauden alussa tai
kun todellisia lukuja ei ole saatavilla käytetään historiallisiin
kapasiteettilukuihin perustuvaa arviota.
"""
import logging
import re
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Stadionkapasiteetti ja historiallinen keskiyleisö joukkueittain (2023–2025 keskiarvo)
STADIUM_INFO = {
    "HJK":           {"stadion": "Bolt Arena",           "kapasiteetti": 10770, "hist_keskiarvo": 5800},
    "KuPS":          {"stadion": "Väre Arena",            "kapasiteetti": 5000,  "hist_keskiarvo": 3000},
    "FC Inter":      {"stadion": "Veritas Stadion",       "kapasiteetti": 9300,  "hist_keskiarvo": 2800},
    "SJK":           {"stadion": "OmaSP Stadion",          "kapasiteetti": 6075,  "hist_keskiarvo": 3800},
    "FC Lahti":      {"stadion": "Lahden stadion",        "kapasiteetti": 14000, "hist_keskiarvo": 2200},
    "Ilves":         {"stadion": "Tammelan stadion",      "kapasiteetti": 8000,  "hist_keskiarvo": 3600},
    "FF Jaro":       {"stadion": "Centralplan",           "kapasiteetti": 3000,  "hist_keskiarvo": 1800},
    "VPS":           {"stadion": "Hietalahden stadion",   "kapasiteetti": 5500,  "hist_keskiarvo": 1500},
    "AC Oulu":       {"stadion": "Raatti",                "kapasiteetti": 6000,  "hist_keskiarvo": 2000},
    "IF Gnistan":    {"stadion": "Helsingfors stadion",   "kapasiteetti": 3000,  "hist_keskiarvo": 1200},
    "IFK Mariehamn": {"stadion": "Wiklöf Holding Arena",  "kapasiteetti": 3000,  "hist_keskiarvo": 1600},
    "TPS":           {"stadion": "Veritas Stadion",       "kapasiteetti": 9300,  "hist_keskiarvo": 2500},
}

# Kotiotteluiden määrä koko kauden lopussa (12 joukkuetta, 22 kierrosta = 11 kotipeliä/joukkue)
HOME_GAMES_PER_TEAM = 11


def _parse_played_matches(output_dir: Path):
    """
    Lukee Ottelut.md ja palauttaa pelattujen kotiotteluiden yleisömäärät
    joukkueittain sekä pelattujen otteluiden kokonaismäärän.

    Palauttaa (home_games, played_total, match_rows) missä
    home_games = {joukkue: [att1, att2, ...]} ja att=0 jos ei tietoa,
    match_rows = lista diktejä {pvm, koti, vieras, tulos, yleiso}.
    """
    ottelut_path = output_dir / "Ottelut.md"
    home_games: dict = {}
    played_total = 0
    match_rows: list = []

    if not ottelut_path.exists():
        return home_games, played_total, match_rows

    in_played = False
    yleiso_col_idx = -1  # sarakeindeksi Yleisö-sarakkeelle (-1 = ei löydy)
    header_parts: list = []

    for line in ottelut_path.read_text(encoding="utf-8").splitlines():
        if "## Pelatut ottelut" in line:
            in_played = True
            yleiso_col_idx = -1
            header_parts = []
            continue
        if "## Tulevat ottelut" in line:
            in_played = False
            continue
        if not (in_played and line.startswith("|")):
            continue

        parts = [p.strip() for p in line.strip().strip("|").split("|")]

        # Otsikkorivi: etsi Yleisö-sarakkeen indeksi
        if "Koti" in parts:
            header_parts = parts
            _fi_table = str.maketrans("äÄöÖ", "aAoO")
            for i, p in enumerate(parts):
                if p.translate(_fi_table).lower() in ("yleiso", "katsojat", "yleisomr"):
                    yleiso_col_idx = i
                    break
            continue

        # Erotinrivi
        if parts and parts[0].startswith("---"):
            continue

        # Datarivi
        if len(parts) >= 4:
            pvm = parts[0] if len(parts) > 0 else ""
            koti = parts[1]
            tulos = parts[2]
            vieras = parts[3] if len(parts) > 3 else ""
            if re.match(r'^\d+\s*[-–]\s*\d+$', tulos.strip()):
                att = 0
                if yleiso_col_idx >= 0 and len(parts) > yleiso_col_idx:
                    # Poista tuhanneserottimet (välilyönti, piste, pilkku, narrow no-break space)
                    att_str = re.sub(r'[^\d]', '', parts[yleiso_col_idx])
                    if att_str:
                        att = int(att_str)
                home_games.setdefault(koti, []).append(att)
                played_total += 1
                match_rows.append({
                    "pvm": pvm,
                    "koti": koti,
                    "vieras": vieras,
                    "tulos": tulos,
                    "yleiso": att,
                })

    return home_games, played_total, match_rows


class AttendanceAnalyzer:
    """Analysoi yleisömääriä ja stadionkäyntejä"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

    def _build_attendance_data(self, home_games: dict, played_total: int):
        """
        Rakentaa yleisömäärätilastot.

        home_games = {joukkue: [att1, att2, ...]} missä att=0 tarkoittaa
        'ei tietoa'. Käyttää historiallisia keskiarvoja arvioimaan pelejä
        joista todellinen katsojaluku puuttuu tai kautta joita ei ole pelattu.

        Palauttaa (per_team_rows, summary_dict, is_real_data).
        """
        per_team = []
        total_real = 0
        total_estimated = 0
        real_matches_total = 0

        # Onko yhtään todellista (> 0) katsojalukua?
        has_real_data = any(
            att > 0
            for atts in home_games.values()
            for att in atts
        )

        for team, info in sorted(STADIUM_INFO.items()):
            attendances = home_games.get(team, [])
            games_played = len(attendances)
            hist_avg = info["hist_keskiarvo"]

            real_atts = [a for a in attendances if a > 0]
            est_games = games_played - len(real_atts)  # pelit ilman todellista lukua

            team_real = sum(real_atts)
            team_est = est_games * hist_avg
            team_played_total = team_real + team_est

            total_real += team_real
            total_estimated += team_est
            real_matches_total += len(real_atts)

            # Todellinen keskiarvo per peli (jos dataa saatavilla)
            actual_avg = round(team_real / len(real_atts)) if real_atts else 0

            # Korkein ja matalin yleisö kotipeleissä
            max_att = max(real_atts) if real_atts else 0
            min_att = min(real_atts) if real_atts else 0

            # Täyttöaste (%) todellisen keskiarvon perusteella
            fill_pct = round(actual_avg / info["kapasiteetti"] * 100, 1) if actual_avg > 0 else 0.0

            # Koko kauden arvio: todelliset + estimoidut + jäljellä olevat
            # Jäljellä oleviin käytetään todellista keskiarvoa jos saatavilla, muuten hist.
            games_remaining = HOME_GAMES_PER_TEAM - games_played
            proj_avg = actual_avg if actual_avg > 0 else hist_avg
            season_est = team_played_total + games_remaining * proj_avg

            per_team.append({
                "joukkue": team,
                "stadion": info["stadion"],
                "kapasiteetti": info["kapasiteetti"],
                "hist_keskiarvo": hist_avg,
                "kotipelit_pelattu": games_played,
                "real_katsojat": team_real,
                "real_peli_maara": len(real_atts),
                "actual_avg": actual_avg,
                "max_att": max_att,
                "min_att": min_att,
                "fill_pct": fill_pct,
                "arvio_katsojat": team_played_total,
                "kausi_arvio": season_est,
            })

        if played_total == 0:
            # Kausi ei alkanut — näytä koko kauden arvio
            total_full_season = sum(
                info["hist_keskiarvo"] * HOME_GAMES_PER_TEAM
                for info in STADIUM_INFO.values()
            )
            summary = {
                "total_attendance": total_full_season,
                "real_total": 0,
                "real_matches": 0,
                "matches": len(STADIUM_INFO) * HOME_GAMES_PER_TEAM,
                "average_per_match": total_full_season // (len(STADIUM_INFO) * HOME_GAMES_PER_TEAM),
                "highest_capacity": max(v["kapasiteetti"] for v in STADIUM_INFO.values()),
                "played": 0,
            }
            is_real = False
        else:
            total_combined = total_real + total_estimated
            avg = total_combined // played_total if played_total > 0 else 0
            summary = {
                "total_attendance": total_combined,
                "real_total": total_real,
                "real_matches": real_matches_total,
                "matches": played_total,
                "average_per_match": avg,
                "highest_capacity": max(v["kapasiteetti"] for v in STADIUM_INFO.values()),
                "played": played_total,
            }
            is_real = has_real_data

        return per_team, summary, is_real

    def analyze(self):
        """Pääanalyysi funktio"""
        logger.info("=" * 60)
        logger.info("YLEISÖMÄÄRÄ-ANALYYSI - Veikkausliiga 2026")
        logger.info("=" * 60)

        home_games, played_total, match_rows = _parse_played_matches(self.output_dir)
        per_team, summary, is_real = self._build_attendance_data(home_games, played_total)

        logger.info(f"✓ Kotiotteluja pelattu: {played_total}")
        if is_real:
            logger.info(
                f"✓ Todelliset katsojat: {summary['real_total']:,} "
                f"({summary['real_matches']} ottelussa)"
            )
        logger.info(f"✓ Arvioitu yhteensä: {summary['total_attendance']:,} katsojaa")
        logger.info(f"✓ Arvioitu keskiarvo: {summary['average_per_match']:,} katsojaa/ottelu")

        report_path = self.output_dir / "Yleiso2026.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Veikkausliiga 2026 - Yleisömäärät\n\n")
            f.write(f"*Analysoitu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            if played_total == 0:
                f.write(
                    "*⚠ Kausi ei ole vielä alkanut — luvut perustuvat historiallisiin "
                    "keskiarvoihin (2023–2025 arvio), eivät todellisiin katsojalukuihin.*\n\n"
                )
            elif not is_real:
                f.write(
                    f"*Lähde: Ottelut.md ({played_total} pelattu kotiottelua) — "
                    "todellisia katsojalukuja ei vielä saatavilla, käytetään historiallisia arvioita.*\n\n"
                )
            else:
                real_matches = summary['real_matches']
                f.write(
                    f"*Lähde: Ottelut.md ({played_total} pelattu kotiottelua, "
                    f"{real_matches} todellisella katsojaluvulla)*\n\n"
                )

            f.write("## Kauden ennuste / tilanne\n\n")
            f.write(f"- **Kotiotteluja pelattu**: {summary['played']}\n")
            if is_real and summary['real_matches'] > 0:
                f.write(
                    f"- **Todelliset katsojat** ({summary['real_matches']} ottelussa): "
                    f"{summary['real_total']:,}\n"
                )
            label_total = (
                "Arvioitu kokonaiskatsojamäärä (koko kausi)"
                if played_total == 0
                else "Arvioitu yhteiskatsojamäärä (todelliset + estimoidut)"
            )
            f.write(f"- **{label_total}**: {summary['total_attendance']:,}\n")
            label_avg = "Arvioitu keskiarvo per ottelu" if not is_real else "Keskiarvo per ottelu"
            f.write(f"- **{label_avg}**: {summary['average_per_match']:,} katsojaa\n")
            f.write(f"- **Suurin stadionkapasiteetti**: {summary['highest_capacity']:,} katsojaa\n\n")

            # --- Joukkuekohtainen taulukko ---
            f.write("## Joukkuekohtaiset stadionit\n\n")
            if is_real and played_total > 0:
                f.write(
                    "| Joukkue | Stadion | Kapasiteetti | Ennuste ka. "
                    "| Kotipelit | Toteutunut ka. | Ero ennusteesta | Todelliset katsojat | Kausiarvio |\n"
                )
                f.write(
                    "|---------|---------|:------------:|:-----------:"
                    "|:---------:|:--------------:|:---------------:|:--------------------:|:----------:|\n"
                )
                for row in sorted(per_team, key=lambda r: r["real_katsojat"] if r["real_katsojat"] > 0 else r["hist_keskiarvo"] * r["kotipelit_pelattu"], reverse=True):
                    real_str = (
                        f"{row['real_katsojat']:,}"
                        if row['real_peli_maara'] > 0
                        else "—"
                    )
                    actual_avg_str = (
                        f"{row['actual_avg']:,}"
                        if row['actual_avg'] > 0
                        else "—"
                    )
                    if row['actual_avg'] > 0:
                        diff = row['actual_avg'] - row['hist_keskiarvo']
                        sign = "+" if diff >= 0 else ""
                        diff_str = f"{sign}{diff:,}"
                    else:
                        diff_str = "—"
                    season_str = f"{int(row['kausi_arvio']):,}"
                    f.write(
                        f"| {row['joukkue']} | {row['stadion']} "
                        f"| {row['kapasiteetti']:,} "
                        f"| {row['hist_keskiarvo']:,} "
                        f"| {row['kotipelit_pelattu']} "
                        f"| {actual_avg_str} "
                        f"| {diff_str} "
                        f"| {real_str} "
                        f"| {season_str} |\n"
                    )
            else:
                f.write(
                    "| Joukkue | Stadion | Kapasiteetti | Ennuste ka. | Kotipelit | Kausiarvio |\n"
                )
                f.write("|---------|---------|:------------:|:-----------:|:---------:|:----------:|\n")
                for row in sorted(per_team, key=lambda r: r["hist_keskiarvo"], reverse=True):
                    season_str = f"{int(row['kausi_arvio']):,}"
                    f.write(
                        f"| {row['joukkue']} | {row['stadion']} "
                        f"| {row['kapasiteetti']:,} "
                        f"| {row['hist_keskiarvo']:,} "
                        f"| {row['kotipelit_pelattu']} "
                        f"| {season_str} |\n"
                    )

            # --- Katsojasuosio-ranking joukkueittain ---
            ranked = [r for r in per_team if r["actual_avg"] > 0]
            if ranked:
                ranked_sorted = sorted(ranked, key=lambda r: r["actual_avg"], reverse=True)
                f.write("\n## Katsojasuosio joukkueittain\n\n")
                f.write(
                    "| # | Joukkue | Toteutunut ka. | Korkein | Matalin | Täyttöaste | Kotipelit |\n"
                )
                f.write(
                    "|:-:|---------|:--------------:|:-------:|:-------:|:----------:|:---------:|\n"
                )
                for rank, row in enumerate(ranked_sorted, start=1):
                    max_str = f"{row['max_att']:,}" if row["max_att"] > 0 else "—"
                    min_str = f"{row['min_att']:,}" if row["min_att"] > 0 else "—"
                    fill_str = f"{row['fill_pct']:.1f} %"
                    f.write(
                        f"| {rank} | {row['joukkue']} "
                        f"| {row['actual_avg']:,} "
                        f"| {max_str} "
                        f"| {min_str} "
                        f"| {fill_str} "
                        f"| {row['real_peli_maara']} |\n"
                    )

            # --- Ottelukohtainen yleisölistaus ---
            played_with_att = [m for m in match_rows if m["yleiso"] > 0]
            if played_with_att:
                f.write("\n## Pelattujen otteluiden yleisömäärät\n\n")
                f.write("| Päivämäärä | Koti | Tulos | Vieras | Yleisö |\n")
                f.write("|------------|------|-------|--------|-------:|\n")
                for m in match_rows:
                    att_str = f"{m['yleiso']:,}" if m["yleiso"] > 0 else "—"
                    f.write(
                        f"| {m['pvm']} | {m['koti']} | {m['tulos']} "
                        f"| {m['vieras']} | {att_str} |\n"
                    )

            f.write("\n")
            f.write("---\n")
            f.write(
                "*Ennuste ka. = historiallinen keskiyleisö kotiotteluissa (2023–2025 arvio). "
                "Kausiarvio = todelliset katsojat + jäljellä olevien otteluiden arvio "
                "(käytetään toteutunutta keskiarvoa jos saatavilla, muuten ennustetta).*\n"
            )

        logger.info(f"✓ Raportti tallennettu: {report_path}")
        return True


def main():
    analyzer = AttendanceAnalyzer()
    return analyzer.analyze()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
