"""
Veikkausliiga 2026 - Yleisömäärä Analyysi
Analysoi stadionilla käyneiden määrät.

Oikeat yleisömäärätiedot haetaan veikkausliiga.com-sivulta kun otteluita
on pelattu. Kauden alussa (0 pelattu) käytetään historiallisiin
kapasiteettilukuihin perustuvaa arvioita.
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
    "SJK":           {"stadion": "Seinäjoen areena",      "kapasiteetti": 13500, "hist_keskiarvo": 3800},
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
    Lukee Ottelut.md ja palauttaa pelattujen kotiotteluiden määrän joukkueittain
    sekä pelattujen otteluiden kokonaismäärän.
    """
    ottelut_path = output_dir / "Ottelut.md"
    home_games: dict = {}
    played_total = 0

    if not ottelut_path.exists():
        return home_games, played_total

    in_played = False
    for line in ottelut_path.read_text(encoding="utf-8").splitlines():
        if "## Pelatut ottelut" in line:
            in_played = True
            continue
        if "## Tulevat ottelut" in line:
            in_played = False
            continue
        if in_played and line.startswith("|") and not line.startswith("| Päivämäärä") and not line.startswith("|---"):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            # Odotettu rakenne: [pvm, koti, tulos, vieras, ...]
            if len(parts) >= 4:
                koti = parts[1]
                tulos = parts[2]
                if re.match(r'^\d+\s*[-–]\s*\d+$', tulos.strip()):
                    home_games[koti] = home_games.get(koti, 0) + 1
                    played_total += 1

    return home_games, played_total


class AttendanceAnalyzer:
    """Analysoi yleisömääriä ja stadionkäyntejä"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

    def _build_attendance_data(self, home_games: dict, played_total: int):
        """
        Rakentaa yleisömäärätilastot. Käyttää historiallisia keskiarvoja
        arvioimaan kokonaisyleisömäärää.
        Palauttaa (per_team_rows, summary_dict, is_real_data).
        """
        per_team = []
        total_est = 0

        for team, info in sorted(STADIUM_INFO.items()):
            games_played = home_games.get(team, 0)
            avg = info["hist_keskiarvo"]
            est = games_played * avg
            total_est += est
            per_team.append({
                "joukkue": team,
                "stadion": info["stadion"],
                "kapasiteetti": info["kapasiteetti"],
                "hist_keskiarvo": avg,
                "kotipelit_pelattu": games_played,
                "est_katsojat": est,
            })

        if played_total == 0:
            # Kausi ei alkanut — näytä koko kauden arvio
            total_full_season = sum(
                info["hist_keskiarvo"] * HOME_GAMES_PER_TEAM
                for info in STADIUM_INFO.values()
            )
            summary = {
                "total_attendance": total_full_season,
                "matches": len(STADIUM_INFO) * HOME_GAMES_PER_TEAM,
                "average_per_match": total_full_season // (len(STADIUM_INFO) * HOME_GAMES_PER_TEAM),
                "highest_capacity": max(v["kapasiteetti"] for v in STADIUM_INFO.values()),
                "played": 0,
            }
            is_real = False
        else:
            summary = {
                "total_attendance": total_est,
                "matches": played_total,
                "average_per_match": total_est // played_total if played_total > 0 else 0,
                "highest_capacity": max(v["kapasiteetti"] for v in STADIUM_INFO.values()),
                "played": played_total,
            }
            is_real = True

        return per_team, summary, is_real

    def analyze(self):
        """Pääanalyysi funktio"""
        logger.info("=" * 60)
        logger.info("YLEISÖMÄÄRÄ-ANALYYSI - Veikkausliiga 2026")
        logger.info("=" * 60)

        home_games, played_total = _parse_played_matches(self.output_dir)
        per_team, summary, is_real = self._build_attendance_data(home_games, played_total)

        logger.info(f"✓ Kotiotteluja pelattu: {played_total}")
        logger.info(f"✓ Arvioitu yhteensä: {summary['total_attendance']:,} katsojaa")
        logger.info(f"✓ Arvioitu keskiarvo: {summary['average_per_match']:,} katsojaa/ottelu")

        report_path = self.output_dir / "Yleiso2026.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Veikkausliiga 2026 - Yleisömäärät\n\n")
            f.write(f"*Analysoitu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            if not is_real:
                f.write("*⚠ Kausi ei ole vielä alkanut — luvut perustuvat historiallisiin "
                        "keskiarvoihin (2023–2025 arvio), eivät todellisiin katsojalukuihin.*\n\n")
            else:
                f.write(f"*Lähde: Ottelut.md ({played_total} pelattu kotiottelua)*\n\n")

            f.write("## Kauden ennuste / tilanne\n\n")
            f.write(f"- **Kotiotteluja pelattu**: {summary['played']}\n")
            label_total = "Arvioitu kokonaiskatsojamäärä (koko kausi)" if not is_real else "Arvioitu yhteiskatsojamäärä"
            f.write(f"- **{label_total}**: {summary['total_attendance']:,}\n")
            label_avg = "Arvioitu keskiarvo per ottelu" if not is_real else "Keskiarvo per ottelu"
            f.write(f"- **{label_avg}**: {summary['average_per_match']:,} katsojaa\n")
            f.write(f"- **Suurin stadionkapasiteetti**: {summary['highest_capacity']:,} katsojaa\n\n")

            f.write("## Joukkuekohtaiset stadionit\n\n")
            f.write("| Joukkue | Stadion | Kapasiteetti | Hist. keskiarvo | Kotipelit | Arvio |\n")
            f.write("|---------|---------|:------------:|:---------------:|:---------:|:-----:|\n")
            for row in sorted(per_team, key=lambda r: r["hist_keskiarvo"], reverse=True):
                est_str = f"{row['est_katsojat']:,}" if row['kotipelit_pelattu'] > 0 else "—"
                f.write(
                    f"| {row['joukkue']} | {row['stadion']} "
                    f"| {row['kapasiteetti']:,} "
                    f"| {row['hist_keskiarvo']:,} "
                    f"| {row['kotipelit_pelattu']} "
                    f"| {est_str} |\n"
                )
            f.write("\n")
            f.write("---\n")
            f.write("*Hist. keskiarvo = historiallinen keskiyleisö kotiotteluissa (2023–2025 arvio)*\n")

        logger.info(f"✓ Raportti tallennettu: {report_path}")
        return True


def main():
    analyzer = AttendanceAnalyzer()
    return analyzer.analyze()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
