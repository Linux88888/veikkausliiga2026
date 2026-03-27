# API Dokumentaatio - Veikkausliiga 2026

## Yleiskatsaus

Veikkausliiga 2026 -projekti koostuu useista Python-moduuleista, jotka yhdessä muodostavat täydellisen analyysijärjestelmän.

---

## config.py - Konfiguraatiomoduuli

### Vakiot

#### TEAMS_2026
```python
TEAMS_2026 = [
    "HJK", "KuPS", "FC Inter", "SJK", "FC Lahti", 
    "Ilves", "FF Jaro", "VPS", "AC Oulu", 
    "IF Gnistan", "IFK Mariehamn", "TPS"
]
```
Veikkausliigan 2026 kaikki 12 joukkuetta.

#### WATCHED_PLAYERS
```python
WATCHED_PLAYERS = [
    "Coffey, Ashley Mark",
    "Moreno Ciorciari, Jaime Jose",
    "Karjalainen, Rasmus",
    "Plange, Luke Elliot",
    "Odutayo, Colin"
]
```
Seuratut pelaajat, joista kerätään yksityiskohtaiset tilastot.

#### POINT_MULTIPLIERS
```python
POINT_MULTIPLIERS = {
    "goal": 2.0,           # Piste per maali
    "shot": 0.1,           # Piste per laukaus
    "assist": 0.5,         # Piste per syöttö
    "red_card": -1.0,      # Negatiivinen piste
    "yellow_card": -0.2    # Negatiivinen piste
}
```
Pisteiden laskentakaava pelaajille.

#### Verkko-osoitteet
```python
VEIKKAUSLIIGA_BASE_URL = "https://www.veikkausliiga.com/tilastot/2026"
STANDINGS_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/joukkueet/"
PLAYERS_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/pelaajat/"
MATCHES_URL = f"{VEIKKAUSLIIGA_BASE_URL}/veikkausliiga/ottelut/"
```
Käytetyt URL-osoitteet tiedonhakuun.

#### Tekniiset Asetukset
```python
REQUEST_TIMEOUT = 10        # Sekuntia
MAX_RETRIES = 3             # Yritykset
RETRY_DELAY = 2             # Sekuntia
```
Verkkopyyntöjen asetukset.

### Funktiot

#### get_output_path(filename)
```python
path = get_output_path('Tilastot2026.md')
```
Palauttaa polun output-kansioon.

#### get_data_path(filename)
```python
path = get_data_path('temporary_data.json')
```
Palauttaa polun data-kansioon.

---

## fetch_stats.py - Tilastoprosessori

### Luokka: StatsProcessor

#### __init__()
Alustaa istunnon verkkokyselyille.

```python
processor = StatsProcessor()
```

#### fetch_with_retry(url, max_retries)
Hakee URL:n automaattisella uudelleenyrityslogiikoilla.

```python
response = processor.fetch_with_retry(
    "https://example.com/data",
    max_retries=3
)
```

**Palauttaa:** `requests.Response` tai `None`

#### fetch_standings()
Hakee sarjataulukon.

```python
standings = processor.fetch_standings()
# Palauttaa listan sanakirjoja
```

**Palauttaa:**
```python
[
    {
        'sijoitus': '1',
        'joukkue': 'HJK',
        'ottelut': '5',
        'voitot': '4',
        'tasapelit': '1',
        'tappiot': '0',
        'tehdyt_maalit': '12',
        'paastetyt_maalit': '3'
    },
    ...
]
```

#### run()
Pääfunktio - suorittaa kaikki analyysit.

```python
success = processor.run()
# Palauttaa True/False
```

---

## attendance_analyzer.py - Yleisöanalyysi

### Luokka: AttendanceAnalyzer

#### analyze()
Pääanalyysi-funktio yleisömäärille.

```python
analyzer = AttendanceAnalyzer()
success = analyzer.analyze()
```

**Tuottaa:** `output/Yleiso2026.md`

---

## match_predictor.py - Otteluennusteet

### Luokka: MatchPredictor

#### predict()
Ennustaa tulevien otteluiden tuloksia.

```python
predictor = MatchPredictor()
success = predictor.predict()
```

**Tuottaa:** `output/Ennusteet2026.md`

---

## main.py - Pääohjelma

### Funktio: main()
Koordinoi kaikkea ja suorittaa analyysit järjestyksessä.

```python
success = main()
exit(0 if success else 1)
```

**Suoritusjärjestys:**
1. Tilastohaku (fetch_stats.py)
2. Yleisöanalyysi (attendance_analyzer.py)
3. Otteluennusteet (match_predictor.py)

---

## Tulostetut Raportit

### Tilastot2026.md
- Sarjataulukko
- Pelaajien pisteet
- Ennusteiden tarkkuus

### Yleiso2026.md
- Yhteensä katsojat
- Keskiarvo per ottelu
- Stadionkohtaiset tilastot

### Ennusteet2026.md
- Tulevat ottelut
- Voittotodennäköisyydet
- Yli 2.5 maalia -todennäköisyydet

---

## Virheenkäsittely

Kaikki moduulit käyttävät loggausta ja virheiden käsittelyä:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    result = processor.run()
except Exception as e:
    logger.error(f"Virhe: {e}")
```

---

## Esimerkki: Omien Funktioiden Lisääminen

```python
# scripts/my_analyzer.py

from config import get_output_path
import logging

logger = logging.getLogger(__name__)

def my_custom_analysis():
    """Oma analyysifunktio"""
    logger.info("Suoritan omaa analyysia...")
    
    # Tee analyysi
    results = {...}
    
    # Tallenna raportti
    report_path = get_output_path('MyAnalysis.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Oma Analyysi\n\n")
        f.write(str(results))
    
    logger.info(f"✓ Raportti: {report_path}")
    return True

if __name__ == "__main__":
    my_custom_analysis()
```

Sitten kutsu se main.py:stä:

```python
from my_analyzer import my_custom_analysis

def main():
    # ... muut analyysit ...
    my_custom_analysis()
```

---

## Lisäresurssit

- [Python requests library](https://requests.readthedocs.io/)
- [BeautifulSoup4 dokumentaatio](https://www.crummy.com/software/BeautifulSoup/)
- [logging moduuli](https://docs.python.org/3/library/logging.html)
