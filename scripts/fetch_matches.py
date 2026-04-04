"""
Veikkausliiga 2026 - Ottelutiedot
Hakee otteluohjelma ja tulokset suoraan veikkausliigan sivuilta
"""

import re
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

# Kuinka monta ryhmää enintään haetaan (ryhmät 1, 2, …, MAX_GROUPS)
MAX_GROUPS = 10

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
        """Palauttaa True vain oikean muotoiselle tulokselle, esim. '2-1', '0–0' tai '0 — 0'."""
        return bool(re.match(r'^\d+\s*[-–—]\s*\d+$', s.strip()))

    @staticmethod
    def _normalize_score(s):
        """Normalisoi tuloksen muotoon '2-1' (korvaa em/en-viivamuodot tavallisella viivalla)."""
        return re.sub(r'\s*[-–—]\s*', '-', s.strip())

    @staticmethod
    def _is_time(s):
        """Palauttaa True jos merkkijono on kellonaika (esim. '13:00')."""
        return bool(re.match(r'^\d{1,2}:\d{2}$', s.strip()))

    @staticmethod
    def _is_date_with_weekday(s):
        """Palauttaa True jos merkkijono on päivämäärä viikonpäivällä (esim. 'La 4.4.2026')."""
        return bool(re.match(r'^[A-Za-zÄÖÅäöå]{2,3}\s+\d+\.\d+\.\d{4}$', s.strip()))

    def _parse_matches_from_html(self, html):
        """Parsii ottelut HTML-sisällöstä ja palauttaa ottelulistauksen."""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []

        # Tapa 1: Etsi taulukon rivit data-attribuuteilla
        match_rows = (
            soup.find_all('tr', attrs={'data-match-id': True}) or
            soup.find_all('tr', class_=lambda c: c and 'match' in c.lower()) or
            soup.find_all('tr', class_=lambda c: c and 'ottelu' in c.lower())
        )

        # Tapa 2: Etsi yleiset taulukkorivit
        if not match_rows:
            match_rows = soup.find_all('tr')

        logged_rows = 0
        last_date = None
        for row in match_rows:
            cells = row.find_all('td')
            if not cells:
                continue

            cell_texts = [c.get_text().strip() for c in cells]

            # Kirjaa ensimmäisten rivien rakenne debuggausta varten
            if logged_rows < 3 and len(cells) >= 4:
                logger.info(f"Rivi {logged_rows+1}: {len(cells)} saraketta: {cell_texts[:8]}")
                logged_rows += 1

            # Tarkista onko tämä ottelurivi (cells[2]=aika, cells[1]=päivä tai tyhjä)
            # Sivusto ryhmittelee saman päivän ottelut: vain ensimmäisellä on päivämäärä,
            # muilla cells[1] on tyhjä — käytetään viimeksi nähtyä päivämäärää.
            if not (len(cells) >= 4 and self._is_time(cell_texts[2])):
                continue

            if self._is_date_with_weekday(cell_texts[1]):
                last_date = cell_texts[1]
            elif cell_texts[1] == '' and last_date:
                pass  # käytetään last_date-arvoa
            else:
                continue

            if not last_date:
                continue

            pvm = last_date
            koti = None
            tulos = '-'
            vieras = None

            # Veikkausliigan ottelutaulukon rakenne (tyypillinen):
            # cells[0] = ottelu-ID (numero)
            # cells[1] = päivä+päivämäärä (esim. "La 4.4.2026")
            # cells[2] = kellonaika (esim. "13:00")
            # cells[3] = linkki ottelusivu
            # cells[4] = kotijoukkue TAI "Koti - Vieras" yhdistettynä
            # cells[5] = linkit (Ennakko/Seuranta/Tilastot/Raportti) TAI tulos (esim. "2-1")
            # cells[6] = tulos (esim. "0 — 0") TAI vierasjoukkue
            # cells[7] = yleisömäärä (jos yhdistetty muoto)

            # Ensisijainen strategia: cells[4]=koti, cells[5]=tulos, cells[6]=vieras
            if len(cells) >= 5:
                raw_koti = cell_texts[4]
                raw_tulos = cell_texts[5] if len(cells) > 5 else ''
                raw_vieras = cell_texts[6] if len(cells) > 6 else ''

                # Käsittele yhdistetty "Koti - Vieras" -muoto cells[4]:ssa
                if raw_koti and ' - ' in raw_koti and not self._is_score(raw_koti):
                    parts = [p.strip() for p in raw_koti.split(' - ', 1)]
                    koti = parts[0]
                    vieras = parts[1] if len(parts) > 1 else raw_vieras
                    # Kun muoto on yhdistetty, tulos on cells[6] (cells[5] on linkkipalsta)
                    if not self._is_score(raw_tulos) and self._is_score(raw_vieras):
                        raw_tulos = raw_vieras
                else:
                    koti = raw_koti
                    vieras = raw_vieras

                # Hyväksy tulos vain jos se on oikean muotoinen (esim. "2-1")
                if self._is_score(raw_tulos):
                    tulos = self._normalize_score(raw_tulos)
                else:
                    tulos = '-'

            # Varastrategia: etsi joukkuenimet kaikista soluista [3+]
            if not koti or not vieras or self._is_time(koti) or self._is_date_with_weekday(koti):
                team_cells = []
                for i in range(3, len(cell_texts)):
                    t = cell_texts[i].strip()
                    if (t and not self._is_time(t) and not self._is_date_with_weekday(t)
                            and not t.isdigit() and '\n' not in t
                            and not re.search(r'\d+\.\d+\.\d{4}', t)):
                        team_cells.append(t)
                if len(team_cells) >= 3 and self._is_score(team_cells[1]):
                    koti = team_cells[0]
                    tulos = self._normalize_score(team_cells[1])
                    vieras = team_cells[2]
                elif len(team_cells) >= 2:
                    koti = team_cells[0]
                    tulos = '-'
                    vieras = team_cells[1]

            if not koti or not vieras:
                continue
            if not tulos:
                tulos = '-'

            matches.append({
                'pvm': pvm,
                'koti': koti,
                'tulos': tulos,
                'vieras': vieras,
            })

        return matches

    def fetch_matches(self):
        """Hakee ottelutiedot kaikista ryhmistä veikkausliigan sivuilta"""
        try:
            # Poista mahdollinen vanha ?group=-parametri perus-URL:sta
            base_url = MATCHES_URL.split('?')[0].rstrip('/')
            all_matches = []

            for group_num in range(1, MAX_GROUPS + 1):
                group_url = f"{base_url}?group={group_num}"
                logger.info(f"Haetaan ryhmä {group_num}: {group_url}")
                response = self.fetch_with_retry(group_url)
                if not response:
                    logger.warning(f"⚠ Ryhmä {group_num}: vastaus puuttuu, lopetetaan")
                    break

                group_matches = self._parse_matches_from_html(response.text)
                if not group_matches:
                    logger.info(f"✓ Ryhmä {group_num}: ei otteluita, lopetetaan")
                    break

                logger.info(f"✓ Ryhmä {group_num}: {len(group_matches)} ottelua")
                all_matches.extend(group_matches)

            if all_matches:
                logger.info(f"✓ Ottelutiedot haettu: {len(all_matches)} ottelua yhteensä")
                return all_matches
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
            total = len(matches)

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# Veikkausliiga 2026 - Ottelut\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if is_dummy:
                    f.write(f"*⚠ Lähde: Esimerkkidata (veikkausliiga.com ei tavoitettavissa) — tulokset eivät ole oikeita*\n\n")
                else:
                    f.write(f"*Lähde: {MATCHES_URL}*\n\n")

                # Otteluiden tilastot
                f.write("## 📊 Tilastot\n\n")
                played_pct = f"{len(played) / total * 100:.0f}%" if total > 0 else "0%"
                f.write(f"| Pelattu | Tulossa | Yhteensä | Edistyminen |\n")
                f.write(f"|:-------:|:-------:|:--------:|:-----------:|\n")
                f.write(f"| **{len(played)}** | **{len(upcoming)}** | **{total}** | {played_pct} |\n\n")

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

                f.write(f"---\n*Yhteensä {total} ottelua "
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
