"""
Veikkausliiga 2026 - Otteluennusteet
Ennustaa tulevien otteluiden tuloksia joukkueiden vahvuuden perusteella
"""
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Joukkueiden vahvuusluokitukset (0–100)
# Perustuu viimeaikaisiin tuloksiin ja historialliseen menestykseen
# ---------------------------------------------------------------------------
TEAM_STRENGTH = {
    "HJK":           85,  # 17 mestaruutta, dominoiva 2009-2025
    "KuPS":          82,  # Mestari 2024 ja 2025
    "Ilves":         72,  # Tasainen kärkiryhmä
    "SJK":           70,  # Mestari 2015, vakaa kärjessä
    "FC Inter":      65,  # Vaihteleva, potentiaalia
    "FC Lahti":      60,  # Keskiluokka
    "TPS":           57,  # Noussut uudelleen liigaan
    "FF Jaro":       55,  # Keskiluokka
    "VPS":           55,  # Keskiluokka
    "AC Oulu":       52,  # Haastaja, uusi tulokas
    "IFK Mariehamn": 50,  # Mestari 2016, tasainen
    "IF Gnistan":    50,  # Uusi tulokas
}

# Kotiedun prosentuaalinen lisäys voittotodennäköisyyteen
HOME_ADVANTAGE = 0.07


def _calc_win_prob(home_strength, away_strength):
    """
    Laskee kotijoukkueen voittotodennäköisyyden joukkueiden vahvuuden perusteella.
    Palauttaa arvon välillä [0.15, 0.85].
    """
    strength_diff = (home_strength - away_strength) / 100.0
    # Perus kotijoukkueen voittotodennäköisyys on ~45% + kotiedun bonus
    prob = 0.45 + HOME_ADVANTAGE + strength_diff
    return round(min(0.85, max(0.15, prob)), 3)


def _calc_over25_prob(home_strength, away_strength):
    """
    Laskee yli 2.5 maalin todennäköisyyden ottelussa.
    Vahvemmat joukkueet tuottavat enemmän maaleja.
    """
    avg_strength = (home_strength + away_strength) / 2.0
    # Skaalaus: 50→0.55, 70→0.63, 85→0.69
    prob = 0.40 + (avg_strength / 100.0) * 0.35
    return round(min(0.80, max(0.35, prob)), 3)


def _read_upcoming_matches(output_dir: Path):
    """
    Lukee tulevat ottelut Ottelut.md-tiedostosta.
    Palauttaa listan {'pvm': ..., 'koti': ..., 'vieras': ...} -sanakirjoja.
    """
    ottelut_path = output_dir / "Ottelut.md"
    matches = []
    if not ottelut_path.exists():
        logger.warning(f"⚠ {ottelut_path} ei löydy, käytetään esimerkkidataa")
        return matches

    in_upcoming = False
    for line in ottelut_path.read_text(encoding="utf-8").splitlines():
        if "## Tulevat ottelut" in line:
            in_upcoming = True
            continue
        if in_upcoming and line.startswith("## "):
            break
        if in_upcoming and line.startswith("|") and not line.startswith("| Päivämäärä") and not line.startswith("|---"):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) >= 3:
                matches.append({
                    "pvm": parts[0],
                    "koti": parts[1],
                    "vieras": parts[2],
                })
    logger.info(f"✓ Luettu {len(matches)} tulevaa ottelua Ottelut.md:stä")
    return matches


def _parse_date(pvm_str):
    """
    Muuntaa 'La 4.4.2026' → datetime.date-olion päivämääräjärjestystä varten.
    Palauttaa datetime.date-olion onnistuessaan, alkuperäisen merkkijonon muuten.
    """
    try:
        # Ota vain päivämääräosa (esim. "4.4.2026")
        parts = pvm_str.strip().split()
        date_part = parts[-1] if len(parts) > 1 else parts[0]
        d, m, y = date_part.split(".")
        return datetime(int(y), int(m), int(d)).date()
    except Exception:
        return pvm_str


def _group_by_round(matches):
    """
    Ryhmittelee ottelut kierroksittain päivämäärän mukaan.
    Palauttaa listan (pvm, [ottelut]) järjestettynä todellisen päivämäärän mukaan.
    """
    rounds = {}
    for m in matches:
        rounds.setdefault(m["pvm"], []).append(m)
    return sorted(rounds.items(), key=lambda x: _parse_date(x[0]))


class MatchPredictor:
    """Ennustaa ottelun tuloksia joukkueiden vahvuuden perusteella"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

    def _predict_match(self, koti, vieras):
        """Ennustaa yksittäisen ottelun"""
        home_str = TEAM_STRENGTH.get(koti, 55)
        away_str = TEAM_STRENGTH.get(vieras, 55)
        home_win = _calc_win_prob(home_str, away_str)
        draw_base = 0.28 - abs(home_str - away_str) * 0.002
        draw = round(max(0.10, min(0.30, draw_base)), 3)
        away_win = round(max(0.05, 1.0 - home_win - draw), 3)
        # Korjaa pyöristysvirhe
        total = home_win + draw + away_win
        home_win = round(home_win / total, 3)
        draw = round(draw / total, 3)
        away_win = round(1.0 - home_win - draw, 3)
        over25 = _calc_over25_prob(home_str, away_str)
        return {
            "koti": koti,
            "vieras": vieras,
            "koti_voitto": home_win,
            "tasapeli": draw,
            "vieras_voitto": away_win,
            "yli_25": over25,
        }

    def predict(self):
        """Pääennuste funktio"""
        logger.info("=" * 60)
        logger.info("OTTELUENNUSTEET - Veikkausliiga 2026")
        logger.info("=" * 60)

        upcoming = _read_upcoming_matches(self.output_dir)

        # Vararatkaisu jos Ottelut.md ei löydy
        if not upcoming:
            upcoming = [
                {"pvm": "La 4.4.2026",  "koti": "HJK",      "vieras": "Ilves"},
                {"pvm": "La 4.4.2026",  "koti": "KuPS",     "vieras": "FC Inter"},
                {"pvm": "La 4.4.2026",  "koti": "SJK",      "vieras": "VPS"},
                {"pvm": "La 4.4.2026",  "koti": "FC Lahti", "vieras": "FF Jaro"},
                {"pvm": "La 4.4.2026",  "koti": "AC Oulu",  "vieras": "IFK Mariehamn"},
                {"pvm": "Su 5.4.2026",  "koti": "TPS",      "vieras": "IF Gnistan"},
            ]

        rounds = _group_by_round(upcoming)
        total_predictions = len(upcoming)
        logger.info(f"✓ Ennusteet laskettu: {total_predictions} ottelulle")

        report_path = self.output_dir / "Ennusteet2026.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Veikkausliiga 2026 - Otteluennusteet\n\n")
            f.write(f"*Analysoitu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("*Ennusteet perustuvat joukkueiden historialliseen menestykseen ja "
                    "vahvuusluokituksiin — eivät pelaaja- tai loukkaantumistietoihin.*\n\n")

            f.write("## Joukkueiden vahvuusluokitukset\n\n")
            f.write("| Joukkue | Vahvuus |\n")
            f.write("|---------|:-------:|\n")
            for team, strength in sorted(TEAM_STRENGTH.items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {team} | {strength} |\n")
            f.write("\n")

            f.write("## Ennustetut ottelut\n\n")
            for pvm, round_matches in rounds:
                f.write(f"### {pvm}\n\n")
                f.write("| Koti | Vieras | Koti-% | Tasapeli-% | Vieras-% | Yli 2.5 % |\n")
                f.write("|------|--------|:------:|:----------:|:--------:|:---------:|\n")
                for m in round_matches:
                    pred = self._predict_match(m["koti"], m["vieras"])
                    koti_icon = " ⭐" if pred["koti_voitto"] > 0.50 else ""
                    vieras_icon = " ⭐" if pred["vieras_voitto"] > pred["koti_voitto"] else ""
                    f.write(
                        f"| {m['koti']}{koti_icon} | {m['vieras']}{vieras_icon} "
                        f"| {pred['koti_voitto']*100:.0f}% "
                        f"| {pred['tasapeli']*100:.0f}% "
                        f"| {pred['vieras_voitto']*100:.0f}% "
                        f"| {pred['yli_25']*100:.0f}% |\n"
                    )
                f.write("\n")

            f.write("---\n")
            f.write(f"*Yhteensä {total_predictions} ennustetta*\n")

        logger.info(f"✓ Ennusteet tallennettu: {report_path}")
        return True


def main():
    predictor = MatchPredictor()
    return predictor.predict()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
