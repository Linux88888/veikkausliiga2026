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
            except requests.exceptions.SSLError:
                logger.warning(f"⚠ SSL-tarkistus epäonnistui, yritetään ilman tarkistusta")
                try:
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
                    response.raise_for_status()
                    logger.info(f"✓ Haku onnistui ilman SSL-tarkistusta (status {response.status_code})")
                    return response
                except requests.RequestException as e2:
                    logger.warning(f"✗ Virhe SSL-ohituksella: {e2}")
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error("✗ Kaikki yritykset epäonnistuivat")
                        return None
            except requests.RequestException as e:
                logger.warning(f"✗ Virhe: {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("✗ Kaikki yritykset epäonnistuivat")
                    return None

    @staticmethod
    def _is_score(s):
        """Palauttaa True vain oikean muotoiselle tulokselle, esim. '2-1' tai '0–0'."""
        import re
        return bool(re.match(r'^\d+\s*[-–]\s*\d+$', s.strip()))

    def fetch_matches(self):
        """Hakee ottelutiedot veikkausliigan sivuilta"""
        import re
        try:
            from config import TEAMS_2026
        except ImportError:
            TEAMS_2026 = ["HJK", "KuPS", "FC Inter", "SJK", "FC Lahti", "Ilves",
                          "FF Jaro", "VPS", "AC Oulu", "IF Gnistan", "IFK Mariehamn", "TPS"]
        try:
            response = self.fetch_with_retry(MATCHES_URL)
            if not response:
                return self._create_dummy_matches()

            soup = BeautifulSoup(response.text, 'html.parser')
            matches = []

            # Yritetään löytää ottelutaulukko sivulta eri tavoilla
            # Tapa 1: Etsi taulukon rivit data-attribuuteilla
            match_rows = (
                soup.find_all('tr', attrs={'data-match-id': True}) or
                soup.find_all('tr', class_=lambda c: c and 'match' in c.lower()) or
                soup.find_all('tr', class_=lambda c: c and 'ottelu' in c.lower())
            )

            # Tapa 2: Etsi yleiset taulukkorivit
            if not match_rows:
                match_rows = soup.find_all('tr')

            # Apufunktiot solun tyypin tunnistamiseen
            def is_time(s):
                return bool(re.match(r'^\d{1,2}:\d{2}$', s.strip()))

            def is_date_with_weekday(s):
                # Esim. "La 4.4.2026", "Pe 10.4.2026"
                return bool(re.match(r'^[A-Za-zÄÖÅäöå]{2,3}\s+\d+\.\d+\.\d{4}$', s.strip()))

            logged_rows = 0
            for row in match_rows:
                cells = row.find_all('td')
                if not cells:
                    continue

                cell_texts = [c.get_text().strip() for c in cells]

                # Kirjaa ensimmäisten rivien rakenne debuggausta varten
                if logged_rows < 3 and len(cells) >= 4:
                    logger.info(f"Rivi {logged_rows+1}: {len(cells)} saraketta: {cell_texts[:8]}")
                    logged_rows += 1

                # Tarkista onko tämä ottelurivi (cells[1]=päivä, cells[2]=aika)
                if not (len(cells) >= 4 and is_date_with_weekday(cell_texts[1]) and is_time(cell_texts[2])):
                    continue

                pvm = cell_texts[1]
                koti = None
                tulos = '-'
                vieras = None

                # Veikkausliigan ottelutaulukon rakenne (tyypillinen):
                # cells[0] = ottelu-ID (numero)
                # cells[1] = päivä+päivämäärä (esim. "La 4.4.2026")
                # cells[2] = kellonaika (esim. "13:00")
                # cells[3] = linkki ottelusivu
                # cells[4] = kotijoukkue TAI "Koti - Vieras" yhdistettynä
                # cells[5] = tulos (esim. "2-1") TAI "Seuranta" (seurantanappi)
                # cells[6] = vierasjoukkue (tai tyhjä jos yhdistetty)

                # Ensisijainen strategia: cells[4]=koti, cells[5]=tulos, cells[6]=vieras
                if len(cells) >= 5:
                    raw_koti = cell_texts[4]
                    raw_tulos = cell_texts[5] if len(cells) > 5 else ''
                    raw_vieras = cell_texts[6] if len(cells) > 6 else ''

                    # Käsittele yhdistetty "Koti - Vieras" -muoto cells[4]:ssa
                    # (verkkosivusto saattaa yhdistää joukkueet yhteen soluun)
                    if raw_koti and ' - ' in raw_koti and not self._is_score(raw_koti):
                        parts = [p.strip() for p in raw_koti.split(' - ', 1)]
                        koti = parts[0]
                        vieras = parts[1] if len(parts) > 1 else raw_vieras
                    else:
                        koti = raw_koti
                        vieras = raw_vieras

                    # Hyväksy tulos vain jos se on oikean muotoinen (esim. "2-1")
                    tulos = raw_tulos if self._is_score(raw_tulos) else '-'

                # Varastrategia: etsi joukkuenimet kaikista soluista [3+]
                # käytetään jos ensisijainen strategia tuotti päivämäärän tai kellonajan
                if not koti or not vieras or is_time(koti) or is_date_with_weekday(koti):
                    team_cells = []
                    for i in range(3, len(cell_texts)):
                        t = cell_texts[i].strip()
                        # Suodata pois tyhjät, kellonajat, päivämäärät, numerot ja monirivinen teksti
                        if (t and not is_time(t) and not is_date_with_weekday(t)
                                and not t.isdigit() and '\n' not in t
                                and not re.search(r'\d+\.\d+\.\d{4}', t)):
                            team_cells.append(t)
                    # Odotettu rakenne: [kotijoukkue, tulos, vierasjoukkue]
                    # tai vain [kotijoukkue, vierasjoukkue] jos tulosta ei ole
                    if len(team_cells) >= 3 and self._is_score(team_cells[1]):
                        koti = team_cells[0]
                        tulos = team_cells[1]
                        vieras = team_cells[2]
                    elif len(team_cells) >= 2:
                        koti = team_cells[0]
                        tulos = '-'
                        vieras = team_cells[1]

                if not koti or not vieras:
                    continue
                if not tulos:
                    tulos = '-'

                match_data = {
                    'pvm': pvm,
                    'koti': koti,
                    'tulos': tulos,
                    'vieras': vieras,
                }
                matches.append(match_data)

            if matches:
                logger.info(f"✓ Ottelutiedot haettu: {len(matches)} ottelua")
                return matches
            else:
                logger.warning("⚠ Ottelutietoja ei löydy sivun rakenteesta, käytetään esimerkkidataa")
                return self._create_dummy_matches()
        except Exception as e:
            logger.error(f"✗ Virhe: {e}")
            return self._create_dummy_matches()

    def _create_dummy_matches(self):
        """Luo esimerkkidatan jos haku epäonnistuu"""
        dummy_matches = [
            {'pvm': '2026-04-01', 'koti': 'HJK',      'tulos': '2-1', 'vieras': 'Ilves',    '_is_dummy': True},
            {'pvm': '2026-04-01', 'koti': 'KuPS',     'tulos': '1-1', 'vieras': 'FC Inter', '_is_dummy': True},
            {'pvm': '2026-04-01', 'koti': 'SJK',      'tulos': '3-0', 'vieras': 'VPS',      '_is_dummy': True},
            {'pvm': '2026-04-05', 'koti': 'FC Lahti', 'tulos': '-',   'vieras': 'HJK',      '_is_dummy': True},
            {'pvm': '2026-04-05', 'koti': 'Ilves',    'tulos': '-',   'vieras': 'KuPS',     '_is_dummy': True},
            {'pvm': '2026-04-05', 'koti': 'FF Jaro',  'tulos': '-',   'vieras': 'SJK',      '_is_dummy': True},
            {'pvm': '2026-04-08', 'koti': 'VPS',      'tulos': '-',   'vieras': 'FC Lahti', '_is_dummy': True},
            {'pvm': '2026-04-08', 'koti': 'FC Inter', 'tulos': '-',   'vieras': 'FF Jaro',  '_is_dummy': True},
            {'pvm': '2026-04-12', 'koti': 'HJK',      'tulos': '-',   'vieras': 'KuPS',     '_is_dummy': True},
            {'pvm': '2026-04-12', 'koti': 'AC Oulu',  'tulos': '-',   'vieras': 'Ilves',    '_is_dummy': True},
        ]
        logger.warning(f"⚠ Käytetään esimerkkidataa (veikkausliiga.com ei tavoitettavissa): {len(dummy_matches)} ottelua")
        return dummy_matches

    def save_matches_report(self, matches):
        """Tallentaa ottelutiedot raporttiin"""
        try:
            is_dummy = any(m.get('_is_dummy') for m in matches)
            report_path = get_output_path("Ottelut.md")
            played = [m for m in matches if m['tulos'] and m['tulos'] != '-']
            upcoming = [m for m in matches if not m['tulos'] or m['tulos'] == '-']

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# Veikkausliiga 2026 - Ottelut\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if is_dummy:
                    f.write(f"*⚠ Lähde: Esimerkkidata (veikkausliiga.com ei tavoitettavissa) — tulokset eivät ole oikeita*\n\n")
                else:
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
