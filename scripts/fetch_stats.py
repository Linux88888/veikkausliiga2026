"""
Veikkausliiga 2026 - Fetch Statistics
Haetaan sarjataulukko ja pelaajatilastot
Parannettu versio: virheiden käsittely, logging, parempi rakenne
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import time
from pathlib import Path

try:
    from config import (
        STANDINGS_URL, PLAYERS_URL, TEAMS_2026, WATCHED_PLAYERS,
        POINT_MULTIPLIERS, get_output_path, REQUEST_TIMEOUT, 
        MAX_RETRIES, RETRY_DELAY, PREDICTED_ORDER
    )
except ImportError:
    # Fallback konfiguraatio jos config.py ei löydy
    STANDINGS_URL = "https://www.veikkausliiga.com/tilastot/2026/veikkausliiga/joukkueet/"
    POINT_MULTIPLIERS = {"goal": 2.0, "shot": 0.1, "assist": 0.5, "red_card": -1.0, "yellow_card": -0.2}
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    PREDICTED_ORDER = ["HJK", "Ilves", "KuPS"]
    def get_output_path(filename):
        return Path("output") / filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StatsProcessor:
    """Käsittelee Veikkausliigan tilastotiedot"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
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
    
    def fetch_standings(self):
        """Hakee sarjataulukon"""
        try:
            response = self.fetch_with_retry(STANDINGS_URL)
            if not response:
                return self._create_dummy_standings()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            standings = []
            table_rows = soup.find_all('tr')
            
            if not table_rows:
                return self._create_dummy_standings()
            
            for row in table_rows[1:]:
                cells = row.find_all('td')
                if cells and len(cells) >= 8:
                    standing_data = {
                        'sijoitus': cells[0].get_text().strip().rstrip('.'),
                        'joukkue': cells[1].get_text().strip(),
                        'ottelut': cells[2].get_text().strip(),
                        'voitot': cells[3].get_text().strip(),
                        'tasapelit': cells[4].get_text().strip(),
                        'tappiot': cells[5].get_text().strip(),
                        'tehdyt_maalit': cells[6].get_text().strip(),
                        'paassetyt_maalit': cells[7].get_text().strip(),
                    }
                    standings.append(standing_data)
            
            if standings:
                logger.info(f"✓ Sarjataulukko haettu: {len(standings)} joukkuetta")
                return standings
            else:
                return self._create_dummy_standings()
        except Exception as e:
            logger.error(f"✗ Virhe: {e}")
            return self._create_dummy_standings()
    
    def _create_dummy_standings(self):
        """Luo testidatan jos haku epäonnistuu"""
        dummy_data = [
            {'sijoitus': '1', 'joukkue': 'HJK', 'ottelut': '5', 'voitot': '4', 'tasapelit': '1', 'tappiot': '0', 'tehdyt_maalit': '12', 'paassetyt_maalit': '3', '_is_dummy': True},
            {'sijoitus': '2', 'joukkue': 'Ilves', 'ottelut': '5', 'voitot': '4', 'tasapelit': '0', 'tappiot': '1', 'tehdyt_maalit': '11', 'paassetyt_maalit': '5', '_is_dummy': True},
            {'sijoitus': '3', 'joukkue': 'KuPS', 'ottelut': '5', 'voitot': '3', 'tasapelit': '1', 'tappiot': '1', 'tehdyt_maalit': '10', 'paassetyt_maalit': '6', '_is_dummy': True},
        ]
        logger.warning(f"⚠ Käytetään esimerkkidataa (veikkausliiga.com ei tavoitettavissa): {len(dummy_data)} joukkuetta")
        return dummy_data
    
    def save_standings_report(self, standings):
        """Tallentaa sarjataulukon raporttiin"""
        try:
            is_dummy = any(row.get('_is_dummy') for row in standings)
            report_path = get_output_path("Tilastot2026.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# Veikkausliiga 2026 - Sarjataulukko\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if is_dummy:
                    f.write(f"*⚠ Lähde: Esimerkkidata (veikkausliiga.com ei tavoitettavissa) — luvut eivät ole oikeita*\n\n")
                else:
                    f.write(f"*Lähde: {STANDINGS_URL}*\n\n")
                f.write("| # | Joukkue | Ot | V | T | T | TM | PM |\n")
                f.write("|---|---------|----|----|----|----|----|----|-----|\n")
                for row in standings:
                    f.write(f"| {row['sijoitus']} | {row['joukkue']} | {row['ottelut']} | {row['voitot']} | {row['tasapelit']} | {row['tappiot']} | {row['tehdyt_maalit']} | {row['paassetyt_maalit']} |\n")
            logger.info(f"✓ Raportti tallennettu: {report_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Virhe raportin tallenuksessa: {e}")
            return False
    
    def run(self):
        """Pääfunktio - suorittaa kaikki analyysit"""
        logger.info("\n" + "="*60)
        logger.info("TILASTOTIETOJEN HAKU - Veikkausliiga 2026")
        logger.info("="*60)
        
        standings = self.fetch_standings()
        
        if standings:
            logger.info(f"✓ Prosessi valmis! {len(standings)} joukkuetta analysoitu")
            self.save_standings_report(standings)
            return True
        else:
            logger.error("✗ Tietojen noutaminen epäonnistui")
            return False

if __name__ == "__main__":
    processor = StatsProcessor()
    success = processor.run()
    exit(0 if success else 1)
