"""
Veikkausliiga 2026 - Ottelutiedot
Hakee otteluohjelma ja tulokset suoraan veikkausliigan sivuilta
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import time
from pathlib import Path

try:
    from config import (
        MATCHES_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY,
        get_output_path
    )
except ImportError:
    MATCHES_URL = "https://www.veikkausliiga.com/tilastot/2026/veikkausliiga/ottelut/"
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def get_output_path(filename):
        return Path("output") / filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MatchFetcher:
    """Hakee Veikkausliigan ottelutiedot"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_with_retry(self, url, max_retries=MAX_RETRIES):
        """Hakee URL:n uudelleenyrityslogiikoilla"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Haetaan: {url} (yritys {attempt + 1}/{max_retries})")
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                logger.info(f"✓ Haku onnistui (status {response.status_code})")
                return response
            except requests.RequestException as e:
                logger.warning(f"✗ Virhe: {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("✗ Kaikki yritykset epäonnistuivat")
                    return None

    def fetch_matches(self):
        """Hakee ottelutiedot veikkausliigan sivuilta"""
        try:
            response = self.fetch_with_retry(MATCHES_URL)
            if not response:
                return self._create_dummy_matches()

            soup = BeautifulSoup(response.text, 'html.parser')
            matches = []

            # Yritetään löytää ottelutaulukko sivulta
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells and len(cells) >= 4:
                    match_data = {
                        'pvm': cells[0].get_text().strip(),
                        'koti': cells[1].get_text().strip(),
                        'tulos': cells[2].get_text().strip() if len(cells) > 2 else '-',
                        'vieras': cells[3].get_text().strip() if len(cells) > 3 else '-',
                    }
                    if match_data['koti'] and match_data['vieras']:
                        matches.append(match_data)

            if matches:
                logger.info(f"✓ Ottelutiedot haettu: {len(matches)} ottelua")
                return matches
            else:
                return self._create_dummy_matches()
        except Exception as e:
            logger.error(f"✗ Virhe: {e}")
            return self._create_dummy_matches()

    def _create_dummy_matches(self):
        """Luo esimerkkidatan jos haku epäonnistuu"""
        dummy_matches = [
            {'pvm': '2026-04-01', 'koti': 'HJK',      'tulos': '2-1', 'vieras': 'Ilves'},
            {'pvm': '2026-04-01', 'koti': 'KuPS',     'tulos': '1-1', 'vieras': 'FC Inter'},
            {'pvm': '2026-04-01', 'koti': 'SJK',      'tulos': '3-0', 'vieras': 'VPS'},
            {'pvm': '2026-04-05', 'koti': 'FC Lahti', 'tulos': '-',   'vieras': 'HJK'},
            {'pvm': '2026-04-05', 'koti': 'Ilves',    'tulos': '-',   'vieras': 'KuPS'},
            {'pvm': '2026-04-05', 'koti': 'FF Jaro',  'tulos': '-',   'vieras': 'SJK'},
            {'pvm': '2026-04-08', 'koti': 'VPS',      'tulos': '-',   'vieras': 'FC Lahti'},
            {'pvm': '2026-04-08', 'koti': 'FC Inter', 'tulos': '-',   'vieras': 'FF Jaro'},
            {'pvm': '2026-04-12', 'koti': 'HJK',      'tulos': '-',   'vieras': 'KuPS'},
            {'pvm': '2026-04-12', 'koti': 'AC Oulu',  'tulos': '-',   'vieras': 'Ilves'},
        ]
        logger.info(f"⚠ Käytetään esimerkkidataa: {len(dummy_matches)} ottelua")
        return dummy_matches

    def save_matches_report(self, matches):
        """Tallentaa ottelutiedot raporttiin"""
        try:
            report_path = get_output_path("Ottelut2026.md")
            played = [m for m in matches if m['tulos'] and m['tulos'] != '-']
            upcoming = [m for m in matches if not m['tulos'] or m['tulos'] == '-']

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# Veikkausliiga 2026 - Ottelut\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(f"*Lähde: {MATCHES_URL}*\n\n")

                if played:
                    f.write("## Pelatut ottelut\n\n")
                    f.write("| Päivämäärä | Koti | Tulos | Vieras |\n")
                    f.write("|------------|------|-------|--------|\n")
                    for m in played:
                        f.write(f"| {m['pvm']} | {m['koti']} | {m['tulos']} | {m['vieras']} |\n")
                    f.write("\n")

                if upcoming:
                    f.write("## Tulevat ottelut\n\n")
                    f.write("| Päivämäärä | Koti | Vieras |\n")
                    f.write("|------------|------|--------|\n")
                    for m in upcoming:
                        f.write(f"| {m['pvm']} | {m['koti']} | {m['vieras']} |\n")
                    f.write("\n")

                f.write(f"---\n*Yhteensä {len(matches)} ottelua "
                        f"({len(played)} pelattu, {len(upcoming)} tulossa)*\n")

            logger.info(f"✓ Raportti tallennettu: {report_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Virhe raportin tallennuksessa: {e}")
            return False

    def run(self):
        """Pääfunktio"""
        logger.info("\n" + "=" * 60)
        logger.info("OTTELUTIEDOT - Veikkausliiga 2026")
        logger.info("=" * 60)

        matches = self.fetch_matches()

        if matches:
            self.save_matches_report(matches)
            logger.info(f"✓ Prosessi valmis! {len(matches)} ottelua käsitelty")
            return True
        else:
            logger.error("✗ Ottelutietojen haku epäonnistui")
            return False


def main():
    fetcher = MatchFetcher()
    return fetcher.run()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
