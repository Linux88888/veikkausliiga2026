"""
Veikkausliiga - Kaikkien aikojen yleisömäärätilastot
Hakee yleisömäärätiedot vuosilta 1990–2025 ja tallentaa ne vuosittain
sekä luo top 50 -yhteenvedon YleisöHistoria.md-tiedostoon.

Lähde: https://www.veikkausliiga.com/tilastot/{vuosi}/veikkausliiga/ottelut/
"""

import re
import time
import logging
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from config import get_output_path, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
except ImportError:
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def get_output_path(filename):
        return Path("output") / filename

logger = logging.getLogger(__name__)

BASE_URL = "https://www.veikkausliiga.com/tilastot/{year}/veikkausliiga/ottelut/"
FIRST_SEASON = 1990
LAST_SEASON = 2025
TOP_N = 50

# Markkinoinnilliset havainnot raportissa (muokkaa ilman koodimuutoksia)
MARKETING_INSIGHTS = [
    (
        "**Huippuvuodet 1995–2006**",
        "Sarjan suosio oli korkeimmillaan 1990-luvun puolivälissä ja 2000-luvun alussa. "
        "Yksittäiset suurottelut (esim. HJK–MYPA 1996: 23 382 katsojaa) nostivat kauden "
        "huippulukemat merkittävästi.",
    ),
    (
        "**Lasku 2007–2014**",
        "Sarjan keskiyleisö laski useana peräkkäisenä vuotena. "
        "Kaupallinen kehitys ja stadionikapasiteettirajoitukset hillitsivät kasvua.",
    ),
    (
        "**HIFK-nousu 2015–2019**",
        "HIFK:n nousu liigaan toi HJK–HIFK-Helsingin derbyn, joka nosti otteluyleisöjä "
        "merkittävästi. Tämä osoittaa, että paikallisderbyillä on suuri vaikutus katsojamääriin.",
    ),
    (
        "**🦠 Korona 2020–2021**",
        "Pandemia romahdutti yleisömäärät. Vuonna 2020 otteluita pelattiin ensin ilman yleisöä, "
        "sitten rajatulla kapasiteetilla. Vuosi 2021 näki osittaisen palautumisen.",
    ),
    (
        "**Toipuminen 2022–2025**",
        "Yleisömäärät ovat toipuneet, mutta eivät ole vielä saavuttaneet 2015–2019-huipputasoa. "
        "Tämä tarjoaa kasvupotentiaalia markkinoinnille: Uudet kanta-asiakaskampanjat, "
        "stadionkehitys ja medianäkyvyyden lisääminen ovat avainasemassa.",
    ),
]


class HistoricalAttendanceFetcher:
    """Hakee ja tallentaa Veikkausliigan kaikkien aikojen yleisömäärätilastot."""

    def __init__(self):
        self.cache_dir = Path(__file__).parent.parent / "output" / "yleiso_historia"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
        else:
            self.session = None

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _get(self, url):
        """Tekee HTTP GET -pyynnön uudelleenyrityslogiikalla."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"Yritys {attempt + 1}/{MAX_RETRIES} epäonnistui: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        return None

    def fetch_year(self, year):
        """Hakee yhden kauden yleisömäärätiedot verkkosivulta.

        Palauttaa listan sanakirjoista muodossa:
          {'year': int, 'date': str, 'home': str, 'away': str,
           'score': str, 'attendance': int}
        """
        if not REQUESTS_AVAILABLE or self.session is None:
            return []

        url = BASE_URL.format(year=year)
        response = self._get(url)
        if not response:
            logger.error(f"✗ Vuoden {year} haku epäonnistui")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        matches = []
        current_date = ""

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            texts = [c.get_text().strip() for c in cells]

            # Viimeinen solu = yleisömäärä (kokonaisluku)
            att_raw = texts[-1].replace("\xa0", "").replace(" ", "").replace(",", "")
            if not att_raw.isdigit():
                continue
            attendance = int(att_raw)
            if attendance <= 0:
                continue

            # Sarakkeiden paikat vaihtelevat versioittain (7 tai 8 saraketta)
            # 7 saraketta: [id, pvm, aika+pvm, joukkueet, linkit, tulos, yleisö]
            # 8 saraketta: [id, pvm, aika, aika+pvm, joukkueet, linkit, tulos, yleisö]
            if len(cells) == 7:
                date_str = texts[1]
                teams_str = texts[3]
                score_str = texts[5]
            elif len(cells) == 8:
                date_str = texts[1]
                teams_str = texts[4]
                score_str = texts[6]
            else:
                continue

            # Seuraa juoksevaa päivämäärää (tyhjä = sama kuin edellinen)
            if date_str:
                m = re.search(r"(\d+\.\d+\.\d{4})", date_str)
                if m:
                    current_date = m.group(1)

            if " - " not in teams_str or not current_date:
                continue

            parts = teams_str.split(" - ", 1)
            matches.append({
                "year": year,
                "date": current_date,
                "home": parts[0].strip(),
                "away": parts[1].strip(),
                "score": score_str.strip(),
                "attendance": attendance,
            })

        logger.info(f"✓ Vuosi {year}: {len(matches)} ottelua haettu")
        return matches

    # ------------------------------------------------------------------
    # Caching (per-year Markdown files)
    # ------------------------------------------------------------------

    def _cache_path(self, year):
        return self.cache_dir / f"{year}.md"

    def load_from_cache(self, year):
        """Lukee vuoden tiedot välimuistista (.md-tiedostosta).

        Palauttaa listan sanakirjoja tai tyhjän listan jos tiedostoa ei ole.
        """
        path = self._cache_path(year)
        if not path.exists():
            return []

        matches = []
        for line in path.read_text(encoding="utf-8").splitlines():
            # Taulukkorivit: | pvm | koti | vieras | tulos | yleisö |
            if not line.startswith("|") or line.startswith("| Pvm"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 5:
                continue
            try:
                attendance = int(parts[4].replace(",", "").replace("\xa0", "").replace(" ", ""))
                matches.append({
                    "year": year,
                    "date": parts[0],
                    "home": parts[1],
                    "away": parts[2],
                    "score": parts[3],
                    "attendance": attendance,
                })
            except (ValueError, IndexError):
                continue
        return matches

    def save_year_cache(self, year, matches):
        """Tallentaa vuoden tiedot välimuistiin (.md-tiedostoon)."""
        path = self._cache_path(year)
        sorted_matches = sorted(matches, key=lambda x: x["attendance"], reverse=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Veikkausliiga {year} — yleisömäärät\n\n")
            f.write(f"*Haettu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"*Lähde: {BASE_URL.format(year=year)}*\n\n")
            total = sum(m["attendance"] for m in matches)
            avg = total // len(matches) if matches else 0
            f.write(f"**Otteluja:** {len(matches)} | ")
            f.write(f"**Yhteensä:** {total:,} | ")
            f.write(f"**Keskiarvo:** {avg:,}\n\n")
            f.write("| Pvm | Koti | Vieras | Tulos | Yleisö |\n")
            f.write("|-----|------|--------|------:|-------:|\n")
            for m in sorted_matches:
                f.write(
                    f"| {m['date']} | {m['home']} | {m['away']} "
                    f"| {m['score']} | {m['attendance']:,} |\n"
                )

        logger.info(f"✓ Vuosi {year} tallennettu: {path}")

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------

    def get_all_matches(self, force_refresh=False):
        """Palauttaa kaikki ottelutiedot 1990–2025.

        Lukee ensin välimuistista; hakee verkosta jos tiedot puuttuvat.
        """
        all_matches = []
        for year in range(FIRST_SEASON, LAST_SEASON + 1):
            if not force_refresh:
                cached = self.load_from_cache(year)
                if cached:
                    all_matches.extend(cached)
                    logger.info(f"✓ Vuosi {year}: {len(cached)} ottelua välimuistista")
                    continue

            fetched = self.fetch_year(year)
            if fetched:
                self.save_year_cache(year, fetched)
                all_matches.extend(fetched)
            else:
                logger.warning(f"⚠ Vuosi {year}: ei dataa")

            time.sleep(0.3)

        return all_matches

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------

    COVID_YEARS = {2020, 2021}

    def compute_yearly_stats(self, all_matches):
        """Laskee vuosikohtaiset yleisötilastot.

        Palauttaa sanakirjan {year: stats_dict} jossa stats_dict sisältää:
          matches, total, average, max_att, min_att, covid
        """
        from collections import defaultdict

        year_buckets = defaultdict(list)
        for m in all_matches:
            year_buckets[m["year"]].append(m["attendance"])

        stats = {}
        for year in range(FIRST_SEASON, LAST_SEASON + 1):
            attendances = year_buckets.get(year, [])
            if not attendances:
                continue
            total = sum(attendances)
            avg = total // len(attendances)
            stats[year] = {
                "matches": len(attendances),
                "total": total,
                "average": avg,
                "max_att": max(attendances),
                "min_att": min(attendances),
                "covid": year in self.COVID_YEARS,
            }
        return stats

    def compute_trends(self, yearly_stats):
        """Laskee trendiluvut vuosikohtaisista tilastoista.

        Lisää jokaiselle vuodelle yoy_change (%-muutos edellisestä vuodesta)
        sekä palauttaa kokonaistrendikuvauksen.
        """
        years = sorted(yearly_stats.keys())
        prev_avg = None
        for year in years:
            if prev_avg is not None and prev_avg > 0:
                yearly_stats[year]["yoy_change"] = (
                    (yearly_stats[year]["average"] - prev_avg) / prev_avg * 100
                )
            else:
                yearly_stats[year]["yoy_change"] = None
            prev_avg = yearly_stats[year]["average"]

        # Era averages
        pre_covid = [s for y, s in yearly_stats.items() if y < 2020]
        covid_era = [s for y, s in yearly_stats.items() if y in self.COVID_YEARS]
        post_covid = [s for y, s in yearly_stats.items() if y > 2021]

        def era_avg(era_list):
            if not era_list:
                return 0
            total = sum(s["total"] for s in era_list)
            matches = sum(s["matches"] for s in era_list)
            return total // matches if matches else 0

        trends = {
            "pre_covid_avg": era_avg(pre_covid),
            "covid_avg": era_avg(covid_era),
            "post_covid_avg": era_avg(post_covid),
            "best_year": max(yearly_stats.items(), key=lambda x: x[1]["average"]),
            "worst_year": min(yearly_stats.items(), key=lambda x: x[1]["average"]),
            "best_total_year": max(yearly_stats.items(), key=lambda x: x[1]["total"]),
        }

        # Post-COVID recovery ratio vs pre-COVID
        if trends["pre_covid_avg"] > 0:
            trends["recovery_pct"] = (
                trends["post_covid_avg"] / trends["pre_covid_avg"] * 100
            )
        else:
            trends["recovery_pct"] = 0.0

        return trends

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def save_top50_report(self, all_matches):
        """Tallentaa top 50 -raportin YleisöHistoria.md-tiedostoon."""
        report_path = get_output_path("YleisöHistoria.md")

        if not all_matches:
            logger.error("✗ Ei dataa top 50 -raporttia varten")
            return False

        top50 = sorted(all_matches, key=lambda x: x["attendance"], reverse=True)[:TOP_N]
        yearly_stats = self.compute_yearly_stats(all_matches)
        trends = self.compute_trends(yearly_stats)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 👥 Veikkausliiga — Top 50 kaikkien aikojen yleisömäärät\n\n")
            f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"*Lähde: veikkausliiga.com (kaudet {FIRST_SEASON}–{LAST_SEASON})*\n\n")
            f.write("---\n\n")
            f.write(f"## 🏟️ Top {TOP_N} suurinta yleisömäärää\n\n")
            f.write("| # | Päivämäärä | Koti | Vieras | Tulos | Yleisö | Kausi |\n")
            f.write("|:-:|-----------|------|--------|------:|-------:|:-----:|\n")
            for i, m in enumerate(top50, 1):
                f.write(
                    f"| {i} | {m['date']} | {m['home']} | {m['away']} "
                    f"| {m['score']} | **{m['attendance']:,}** | {m['year']} |\n"
                )
            f.write("\n")

            # Vuosikohtaiset ennätykset
            f.write("## 📅 Kauden yleisöennätys vuosittain\n\n")
            f.write("| Kausi | Päivämäärä | Ottelu | Tulos | Yleisö |\n")
            f.write("|:-----:|-----------|--------|------:|-------:|\n")
            for year in range(FIRST_SEASON, LAST_SEASON + 1):
                year_matches = [m for m in all_matches if m["year"] == year]
                if not year_matches:
                    continue
                best = max(year_matches, key=lambda x: x["attendance"])
                f.write(
                    f"| {year} | {best['date']} | {best['home']} – {best['away']} "
                    f"| {best['score']} | **{best['attendance']:,}** |\n"
                )
            f.write("\n")

            # --- UUSI: Vuosikohtainen keskiarvo-taulukko ---
            f.write("## 📈 Vuosikohtainen keskiarvokehitys\n\n")
            f.write(
                "| Kausi | Otteluja | Katsojia yht. | Keskiarvo | "
                "Muutos ed. vuoteen | Huomio |\n"
            )
            f.write(
                "|:-----:|---------:|--------------:|----------:|"
                "-------------------:|--------|\n"
            )
            for year in range(FIRST_SEASON, LAST_SEASON + 1):
                s = yearly_stats.get(year)
                if not s:
                    continue
                yoy = s["yoy_change"]
                if yoy is None:
                    yoy_str = "—"
                elif yoy >= 0:
                    yoy_str = f"+{yoy:.1f} %"
                else:
                    yoy_str = f"{yoy:.1f} %"
                note = "🦠 **Korona**" if s["covid"] else ""
                f.write(
                    f"| {year} | {s['matches']} | {s['total']:,} | "
                    f"**{s['average']:,}** | {yoy_str} | {note} |\n"
                )
            f.write("\n")

            # --- UUSI: Trendianalyysi ---
            f.write("## 🔍 Trendianalyysi ja markkinoinnillinen näkymä\n\n")

            best_yr, best_s = trends["best_year"]
            worst_yr, worst_s = trends["worst_year"]
            best_total_yr, best_total_s = trends["best_total_year"]

            f.write("### Aikakausivertailu\n\n")
            f.write("| Aikakausi | Vuodet | Keskiarvo/ottelu |\n")
            f.write("|-----------|--------|------------------:|\n")
            f.write(f"| Ennen koronaa | 1990–2019 | **{trends['pre_covid_avg']:,}** |\n")
            f.write(f"| 🦠 Koronavuodet | 2020–2021 | **{trends['covid_avg']:,}** |\n")
            f.write(f"| Koronan jälkeen | 2022–2025 | **{trends['post_covid_avg']:,}** |\n")
            f.write("\n")

            f.write("### Koronaromahdus ja toipuminen\n\n")
            drop_pct = 0.0
            if trends["pre_covid_avg"] > 0:
                drop_pct = (
                    (trends["covid_avg"] - trends["pre_covid_avg"])
                    / trends["pre_covid_avg"] * 100
                )
            f.write(
                f"Korona pudotti keskimääräisen otteluyleisön **{drop_pct:.1f} %** "
                f"(ennen koronaa: {trends['pre_covid_avg']:,} → koronavuosina: "
                f"{trends['covid_avg']:,} katsojaa/ottelu).\n\n"
            )
            f.write(
                f"Toipumisaste koronan jälkeen (2022–2025) verrattuna ennen-koronaa-tasoon: "
                f"**{trends['recovery_pct']:.1f} %**.\n\n"
            )

            f.write("### Parhaat ja heikoimmat vuodet\n\n")
            f.write("| Tilasto | Vuosi | Arvo |\n")
            f.write("|---------|:-----:|-----:|\n")
            f.write(
                f"| 🥇 Korkein keskiarvo/ottelu | {best_yr} | "
                f"**{best_s['average']:,}** |\n"
            )
            f.write(
                f"| 📉 Matalin keskiarvo/ottelu | {worst_yr} | "
                f"**{worst_s['average']:,}** |\n"
            )
            f.write(
                f"| 🏟️ Eniten katsojia yhteensä | {best_total_yr} | "
                f"**{best_total_s['total']:,}** |\n"
            )
            f.write("\n")

            f.write("### Markkinoinnilliset havainnot\n\n")
            for title, body in MARKETING_INSIGHTS:
                f.write(f"- {title}: {body}\n")
            f.write("\n")

            # Yhteenveto
            total_matches = len(all_matches)
            total_attendance = sum(m["attendance"] for m in all_matches)
            avg_attendance = total_attendance // total_matches if total_matches else 0
            max_att = top50[0]["attendance"] if top50 else 0

            f.write(f"## 📊 Yhteenveto ({FIRST_SEASON}–{LAST_SEASON})\n\n")
            f.write("| Tilasto | Arvo |\n")
            f.write("|---------|------|\n")
            f.write(f"| Otteluja yhteensä | **{total_matches:,}** |\n")
            f.write(f"| Katsojia yhteensä | **{total_attendance:,}** |\n")
            f.write(f"| Keskiarvo per ottelu | **{avg_attendance:,}** |\n")
            f.write(f"| Kaikkien aikojen ennätys | **{max_att:,}** |\n")
            f.write("\n")

        logger.info(f"✓ Top {TOP_N} yleisömääräraportti tallennettu: {report_path}")
        return True

    def run(self, force_refresh=False):
        """Pääfunktio."""
        logger.info("\n" + "=" * 60)
        logger.info("KAIKKIEN AIKOJEN YLEISÖMÄÄRÄTILASTOT - Veikkausliiga")
        logger.info("=" * 60)

        if not REQUESTS_AVAILABLE and not any(
            self._cache_path(y).exists() for y in range(FIRST_SEASON, LAST_SEASON + 1)
        ):
            logger.error("✗ requests/BeautifulSoup ei asennettuna eikä välimuistia")
            return False

        all_matches = self.get_all_matches(force_refresh=force_refresh)
        if not all_matches:
            logger.error("✗ Ei ottelutietoja")
            return False

        logger.info(f"✓ Yhteensä {len(all_matches)} ottelua käsitelty")
        return self.save_top50_report(all_matches)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="Hae Veikkausliigan yleisömäärätilastot")
    parser.add_argument("--refresh", action="store_true", help="Pakota uudelleenhaku verkosta")
    args = parser.parse_args()

    fetcher = HistoricalAttendanceFetcher()
    success = fetcher.run(force_refresh=args.refresh)
    exit(0 if success else 1)
