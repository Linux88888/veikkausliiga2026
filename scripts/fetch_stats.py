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
        MAX_RETRIES, RETRY_DELAY, PREDICTED_ORDER, TOP_SCORERS_COUNT,
        TEAM_LOGOS,
    )
except ImportError:
    # Fallback konfiguraatio jos config.py ei löydy
    STANDINGS_URL = "https://www.veikkausliiga.com/tilastot/2026/veikkausliiga/joukkueet/"
    PLAYERS_URL = "https://www.veikkausliiga.com/tilastot/2026/veikkausliiga/pelaajat/"
    POINT_MULTIPLIERS = {"goal": 2.0, "shot": 0.1, "assist": 0.5, "red_card": -1.0, "yellow_card": -0.2}
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    PREDICTED_ORDER = ["HJK", "Ilves", "KuPS"]
    TOP_SCORERS_COUNT = 10
    TEAM_LOGOS = {}
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
            
            logged_first_row = False
            for row in table_rows[1:]:
                cells = row.find_all('td')
                if cells and len(cells) >= 8:
                    if not logged_first_row:
                        logger.info(f"Sarjataulukkorakenne: {len(cells)} saraketta, esimerkkisolu: {[c.get_text().strip()[:15] for c in cells]}")
                        logged_first_row = True
                    standing_data = {
                        'sijoitus': cells[0].get_text().strip().rstrip('.'),
                        'joukkue': cells[1].get_text().strip(),
                        'ottelut': cells[2].get_text().strip(),
                        'voitot': cells[3].get_text().strip(),
                        'tasapelit': cells[4].get_text().strip(),
                        'tappiot': cells[5].get_text().strip(),
                        'tehdyt_maalit': cells[6].get_text().strip(),
                        'paassetyt_maalit': cells[7].get_text().strip(),
                        'maaliero': cells[8].get_text().strip() if len(cells) > 8 else '0',
                        'pisteet': cells[9].get_text().strip() if len(cells) > 9 else '0',
                    }
                    standings.append(standing_data)
            
            if standings:
                # Jos kaikki joukkueet ovat pelanneet 0 ottelua, järjestetään PREDICTED_ORDER:n mukaan
                all_zero = all(s.get('ottelut', '0') == '0' for s in standings)
                if all_zero and PREDICTED_ORDER:
                    predicted_pos = {team: i for i, team in enumerate(PREDICTED_ORDER)}
                    standings.sort(key=lambda s: predicted_pos.get(s['joukkue'], 99))
                    for i, s in enumerate(standings, 1):
                        s['sijoitus'] = str(i)
                    logger.info(f"✓ Sarjataulukko järjestetty PREDICTED_ORDER:n mukaan (ei pelejä vielä)")
                else:
                    logger.info(f"✓ Sarjataulukko haettu: {len(standings)} joukkuetta")
                return standings
            else:
                return self._create_dummy_standings()
        except Exception as e:
            logger.error(f"✗ Virhe: {e}")
            return self._create_dummy_standings()
    
    def _create_dummy_standings(self):
        """Luo testidatan jos haku epäonnistuu — sisältää kaikki 12 joukkuetta"""
        dummy_data = [
            {'sijoitus': '1',  'joukkue': 'HJK',           'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '2',  'joukkue': 'KuPS',          'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '3',  'joukkue': 'SJK',           'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '4',  'joukkue': 'FC Inter',      'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '5',  'joukkue': 'Ilves',         'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '6',  'joukkue': 'TPS',           'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '7',  'joukkue': 'FC Lahti',      'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '8',  'joukkue': 'FF Jaro',       'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '9',  'joukkue': 'AC Oulu',       'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '10', 'joukkue': 'IFK Mariehamn', 'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '11', 'joukkue': 'VPS',           'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
            {'sijoitus': '12', 'joukkue': 'IF Gnistan',    'ottelut': '0', 'voitot': '0', 'tasapelit': '0', 'tappiot': '0', 'tehdyt_maalit': '0', 'paassetyt_maalit': '0', 'maaliero': '0',  'pisteet': '0', '_is_dummy': True},
        ]
        logger.warning(f"⚠ Käytetään esimerkkidataa (veikkausliiga.com ei tavoitettavissa): {len(dummy_data)} joukkuetta")
        return dummy_data
    
    def fetch_full_player_stats(self):
        """Hakee täydelliset pelaajatilastot (maalit, syötöt, kortit, pelit).

        Returns
        -------
        (players: list[dict], is_dummy: bool)
        """
        try:
            response = self.fetch_with_retry(PLAYERS_URL)
            if not response:
                return self._create_dummy_player_stats(), True

            soup = BeautifulSoup(response.text, 'html.parser')
            players = []
            table_rows = soup.find_all('tr')

            logged_first_row = False
            for row in table_rows[1:]:
                cells = row.find_all('td')
                if cells and len(cells) >= 3:
                    if not logged_first_row:
                        logger.info(f"Pelaajataulukkorakenne: {len(cells)} saraketta, esimerkkisolu: {[c.get_text().strip()[:15] for c in cells]}")
                        logged_first_row = True
                    # Rakenne (veikkausliiga.com 2026):
                    # [0]=sijoitus, [1]=pelaaja, [2]=joukkue, [3]=O(ottelut),
                    # [4]=A(minuutit), [5]=M(maalit), [6]=S(syötöt),
                    # [7]=AK, [8]=VS, [9]=VU, [10]=R,
                    # [11]=KK(keltaiset), [12]=PK(punaiset), ...
                    def safe_int(idx):
                        try:
                            return int(cells[idx].get_text().strip()) if len(cells) > idx else 0
                        except ValueError:
                            return 0

                    player_name = cells[1].get_text().strip() if len(cells) > 1 else ''
                    team = cells[2].get_text().strip() if len(cells) > 2 else ''
                    if player_name:
                        players.append({
                            'sijoitus': cells[0].get_text().strip() if cells else '',
                            'pelaaja': player_name,
                            'joukkue': team,
                            'ottelut': safe_int(3),
                            'maalit': safe_int(5),
                            'syotot': safe_int(6),
                            'keltaiset': safe_int(11),
                            'punaiset': safe_int(12),
                        })

            if players:
                logger.info(f"✓ Pelaajatilastot haettu: {len(players)} pelaajaa")
                return players, False
            else:
                return self._create_dummy_player_stats(), True
        except Exception as e:
            logger.error(f"✗ Virhe pelaajatilastojen haussa: {e}")
            return self._create_dummy_player_stats(), True

    def fetch_top_scorers(self, count=None):
        """Hakee parhaat maalintekijät pelaajatilastoista.

        Returns
        -------
        (players: list[str], is_dummy: bool)
        """
        if count is None:
            count = TOP_SCORERS_COUNT
        players, is_dummy = self.fetch_full_player_stats()
        players_sorted = sorted(players, key=lambda x: x['maalit'], reverse=True)
        top = [p['pelaaja'] for p in players_sorted[:count]]
        if top:
            logger.info(f"✓ Maalintekijät haettu: {len(top)} pelaajaa")
            return top, is_dummy
        return self._create_dummy_scorers(count), True

    def _create_dummy_player_stats(self):
        """Luo testidatan pelaajatilastoille jos haku epäonnistuu"""
        dummy = [
            {'sijoitus': '1',  'pelaaja': 'Karjalainen, Rasmus', 'joukkue': 'KuPS',     'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '2',  'pelaaja': 'Lappalainen, Lassi',  'joukkue': 'KuPS',     'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '3',  'pelaaja': 'Engvall, Gustav',     'joukkue': 'Ilves',    'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '4',  'pelaaja': 'Borchers, Mads',      'joukkue': 'HJK',      'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '5',  'pelaaja': 'Vikström, Rudi',      'joukkue': 'AC Oulu',  'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '6',  'pelaaja': 'Toivio, Toni',        'joukkue': 'HJK',      'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '7',  'pelaaja': 'Havenaar, Mike',      'joukkue': 'SJK',      'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '8',  'pelaaja': 'Pennanen, Timi',      'joukkue': 'FC Inter', 'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '9',  'pelaaja': 'Lindström, Joni',     'joukkue': 'TPS',      'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
            {'sijoitus': '10', 'pelaaja': 'Oduya, Wisdom',       'joukkue': 'FC Lahti', 'ottelut': 0, 'maalit': 0, 'syotot': 0, 'keltaiset': 0, 'punaiset': 0},
        ]
        logger.warning(f"⚠ Käytetään esimerkkidataa pelaajatilastoille: {len(dummy)} pelaajaa")
        return dummy

    def _create_dummy_scorers(self, count=10):
        """Luo testidatan maalintekijöille jos haku epäonnistuu"""
        dummy = [
            "Karjalainen, Rasmus",
            "Lappalainen, Lassi",
            "Engvall, Gustav",
            "Borchers, Mads",
            "Vikström, Rudi",
            "Toivio, Toni",
            "Havenaar, Mike",
            "Pennanen, Timi",
            "Lindström, Joni",
            "Oduya, Wisdom",
        ]
        logger.warning(f"⚠ Käytetään esimerkkidataa maalintekijöille: {len(dummy[:count])} pelaajaa")
        return dummy[:count]

    def save_player_stats_report(self, players, is_dummy):
        """Tallentaa pelaajatilastot Pelaajatilastot2026.md-tiedostoon"""
        try:
            report_path = get_output_path("Pelaajatilastot2026.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("# ⚽ Veikkausliiga 2026 — Pelaajatilastot\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if is_dummy:
                    f.write("*⚠️ Kausi alkaa 4.4.2026 — ensimmäiset tilastot saatavilla kauden alettua*\n\n")
                else:
                    f.write(f"*Lähde: [{PLAYERS_URL}]({PLAYERS_URL})*\n\n")
                f.write("---\n\n")

                f.write("## Maalintekijätilasto\n\n")
                f.write("| # | Pelaaja | Joukkue | Ot | M | S | K | P |\n")
                f.write("|:-:|---------|---------|:--:|:-:|:-:|:-:|:-:|\n")
                for p in players:
                    logo_path = TEAM_LOGOS.get(p['joukkue'], "")
                    if logo_path:
                        team_cell = f'<img src="{logo_path}" width="16" height="16"> {p["joukkue"]}'
                    else:
                        team_cell = p['joukkue']
                    f.write(
                        f"| {p['sijoitus']} | {p['pelaaja']} | {team_cell} "
                        f"| {p['ottelut']} | **{p['maalit']}** | {p['syotot']} "
                        f"| {p['keltaiset']} | {p['punaiset']} |\n"
                    )

                f.write("\n> **Ot** = Ottelut · **M** = Maalit · **S** = Syötöt · "
                        "**K** = Keltaiset kortit · **P** = Punaiset kortit\n\n")

                # Seuratut pelaajat -osio
                watched = [p for p in players if any(
                    w.split(',')[0].strip().lower() in p['pelaaja'].lower()
                    for w in WATCHED_PLAYERS
                )]
                if watched:
                    f.write("## Seuratut pelaajat\n\n")
                    f.write("| Pelaaja | Joukkue | Ot | M | S |\n")
                    f.write("|---------|---------|:--:|:-:|:-:|\n")
                    for p in watched:
                        f.write(
                            f"| {p['pelaaja']} | {p['joukkue']} "
                            f"| {p['ottelut']} | {p['maalit']} | {p['syotot']} |\n"
                        )
                    f.write("\n")

            logger.info(f"✓ Pelaajatilastot tallennettu: {report_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Virhe pelaajatilastojen tallenuksessa: {e}")
            return False

    def save_standings_report(self, standings):
        """Tallentaa sarjataulukon raporttiin"""
        try:
            is_dummy = any(row.get('_is_dummy') for row in standings)
            report_path = get_output_path("Tilastot2026.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                # Otsikko
                f.write("# 🏆 Veikkausliiga 2026 — Sarjataulukko\n\n")
                f.write(f"*Päivitetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if is_dummy:
                    f.write("*⚠️ Kausi alkaa 4.4.2026 — ensimmäiset tilastot saatavilla kauden alettua*\n\n")
                else:
                    f.write(f"*Lähde: [{STANDINGS_URL}]({STANDINGS_URL})*\n\n")
                f.write("---\n\n")

                # Sarjataulukko logojen kanssa
                f.write("| # | Joukkue | Ot | V | T | H | TM | PM | ME | Pist |\n")
                f.write("|:-:|---------|:--:|:-:|:-:|:-:|:--:|:--:|:--:|:----:|\n")
                for row in standings:
                    team = row['joukkue']
                    logo_path = TEAM_LOGOS.get(team, "")
                    if logo_path:
                        team_cell = f'<img src="{logo_path}" width="20" height="20"> {team}'
                    else:
                        team_cell = team
                    f.write(
                        f"| {row['sijoitus']} | {team_cell} "
                        f"| {row['ottelut']} | {row['voitot']} | {row['tasapelit']} "
                        f"| {row['tappiot']} | {row['tehdyt_maalit']} "
                        f"| {row['paastetyt_maalit'] if 'paastetyt_maalit' in row else row.get('paassetyt_maalit', '0')} "
                        f"| {row.get('maaliero', '0')} | **{row.get('pisteet', '0')}** |\n"
                    )

                f.write("\n> **Ot** = Ottelut · **V** = Voitot · **T** = Tasapelit · **H** = Häviöt\n")
                f.write("> **TM** = Tehdyt maalit · **PM** = Päästetyt maalit · **ME** = Maaliero\n\n")
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

        success = True

        standings = self.fetch_standings()
        if standings:
            logger.info(f"✓ Sarjataulukko: {len(standings)} joukkuetta analysoitu")
            self.save_standings_report(standings)
        else:
            logger.error("✗ Sarjataulukon noutaminen epäonnistui")
            success = False

        players, is_dummy = self.fetch_full_player_stats()
        if players:
            logger.info(f"✓ Pelaajatilastot: {len(players)} pelaajaa analysoitu")
            self.save_player_stats_report(players, is_dummy)
        else:
            logger.error("✗ Pelaajatilastojen noutaminen epäonnistui")
            success = False

        return success

if __name__ == "__main__":
    processor = StatsProcessor()
    success = processor.run()
    exit(0 if success else 1)
