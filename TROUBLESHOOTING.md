# Ongelmien Ratkaisu - Veikkausliiga 2026

Löysitkö ongelman? Tämä opas auttaa sinua ratkaisemaan tavallisimmat ongelmat.

---

## 🔴 YLEISIMMÄT ONGELMAT

### 1. ModuleNotFoundError: No module named 'requests'

**Oireet:**
```
ModuleNotFoundError: No module named 'requests'
```

**Ratkaisu:**
```bash
# Asenna kaikki riippuvuudet
pip install -r requirements.txt

# Tai asenna yksittäin
pip install requests beautifulsoup4 lxml
```

**Varmista:**
- Käytät oikeaa Python-versiota (3.8+)
- Asennuspolku on oikea

---

### 2. Connection Timeout Errors

**Oireet:**
```
requests.exceptions.ConnectionError: 
requests.exceptions.ConnectTimeout
requests.exceptions.ReadTimeout
```

**Ratkaisut:**

a) **Tarkista internet-yhteys**
```bash
ping google.com
```

b) **Tarkista, että sivu on saatavilla**
Avaa https://www.veikkausliiga.com/tilastot/2026 selaimella

c) **Odota ja yritä myöhemmin**
Sivu saattaa olla väliaikaisesti alhaalla

d) **Muuta timeout-arvo**
Muokkaa `scripts/config.py`:tä:
```python
REQUEST_TIMEOUT = 20  # Nostaa 20 sekuntiin
MAX_RETRIES = 5       # Kokeilee 5 kertaa
```

e) **Käytä VPN:ää**
Jos verkkoyhteys on heikko, kokeile VPN:ää

---

### 3. FileNotFoundError: [Errno 2] No such file or directory

**Oireet:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'output/Tilastot2026.md'
```

**Ratkaisu:**

Varmista, että olet oikeassa kansiossa:
```bash
# Tarkista sijainti
pwd

# Pitäisi näyttää: .../veikkausliiga2026

# Jos ei, siirry sinne
cd veikkausliiga2026

# Luo puuttuvat kansiot
mkdir -p output data

# Nyt kokeile uudelleen
python scripts/main.py
```

---

### 4. ImportError: No module named 'config'

**Oireet:**
```
ImportError: No module named 'config'
ModuleNotFoundError: No module named 'config'
```

**Ratkaisu:**

Suorita skriptit oikeasta sijainnista:
```bash
# ❌ Väärä tapa
cd veikkausliiga2026/scripts
python main.py

# ✅ Oikea tapa
cd veikkausliiga2026
python scripts/main.py
```

---

### 5. Raportteja ei luoda

**Oireet:**
```
✓ Process complete
(mutta output-kansioon ei ilmesty tiedostoja)
```

**Ratkaisut:**

a) **Luo output-kansio:**
```bash
mkdir -p output
python scripts/main.py
```

b) **Tarkista oikeudet:**
```bash
# Linux/macOS
chmod -R 755 output

# Yritä uudelleen
python scripts/main.py
```

c) **Poista väliaikaistiedostot:**
```bash
rm -rf output/ data/
mkdir -p output data
python scripts/main.py
```

---

### 6. Koodi ei päivity käyttäessä import

**Oireet:**
```python
# Otat muutoksen, mutta koodi ei kuuntele
from fetch_stats import StatsProcessor
```

**Ratkaisu:**

Tyhjennä Python cache:
```bash
# Poista __pycache__ kansiot
find . -type d -name __pycache__ -exec rm -r {} +

# Tai yksitellen
rm -rf scripts/__pycache__

# Nyt kokeile uudelleen
python scripts/main.py
```

---

### 7. Memory Leak - Ohjelma käyttää liikaa muistia

**Oireet:**
```
MemoryError
Process killed (out of memory)
```

**Ratkaisut:**

a) **Pienennä WATCHED_PLAYERS lista:**
```python
# scripts/config.py
WATCHED_PLAYERS = [
    "Coffey, Ashley Mark",
    "Moreno Ciorciari, Jaime Jose",
    # Poista loput
]
```

b) **Pienennä TEAMS_2026 lista (vain testaamista varten):**
```python
TEAMS_2026 = ["HJK", "Ilves", "KuPS"]
```

c) **Tarkista järjestelmän muisti:**
```bash
# macOS/Linux
top -n 1 | grep Mem

# Windows
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory
```

---

## 🔧 DEBUG-MOODISSA AJAMINEN

Ota yksityiskohtaiset lokit näkyviin:

### Vaihtoehto 1: Muokkaa config.py

```python
# scripts/config.py - lisää tämä loppuun
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Vaihtoehto 2: Aseta ympäristömuuttuja

```bash
# Linux/macOS
PYTHONPATH=. DEBUG=1 python scripts/main.py

# Windows
set DEBUG=1 && python scripts/main.py
```

### Vaihtoehto 3: Muokkaa main.py

```python
# scripts/main.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='debug.log'
)
```

Sitten tarkista logs:
```bash
cat debug.log
```

---

## 📊 VERKON DIAGNOSTIIKKA

Kun yhteys epäonnistuu, tarkista:

### 1. Verkko-yhteys

```bash
# Tarkista pingssi
ping -c 5 8.8.8.8

# Tarkista DNS
nslookup www.veikkausliiga.com

# Tarkista route
traceroute www.veikkausliiga.com
```

### 2. SSL/TLS ongelmat

```bash
# Testaa SSL-sertifikaatti
python -c "import ssl; ssl.create_default_context().check_hostname = False"

# Tarkista requests
python -c "import requests; r = requests.get('https://www.veikkausliiga.com'); print(r.status_code)"
```

### 3. Proxy ongelmat

Jos käytät proxy:tä, konfiguroi se:

```python
# scripts/fetch_stats.py - lisää __init__:iin
proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080',
}
self.session.proxies.update(proxies)
```

---

## 🐛 BUGIN RAPORTOINTI

Jos ongelma jatkuu, avaa GitHub Issue:

1. **Otsikko:** Lyhyt kuvaus
   ```
   "Timeout-virhe veikkausliiga.com:n haussa"
   ```

2. **Kuvaus:** Täydellinen raportti
   ```markdown
   ## Bugin kuvaus
   
   [Lyhyt kuvaus]
   
   ## Toistamisen vaiheet
   1. Asenna
   2. Suorita
   3. Näe virhe
   
   ## Virheviesti
   ```
   [Liitä täsmällinen virhe]
   ```
   
   ## Ympäristö
   - OS: macOS 12.1
   - Python: 3.9.2
   - requests: 2.28.0
   ```

---

## 💡 VINKKEJÄ

### Nopea Testaus
```bash
# Testaa vain fetch_stats.py
python scripts/fetch_stats.py

# Testaa vain yleisöanalyysia
python scripts/attendance_analyzer.py

# Testaa vain ennusteita
python scripts/match_predictor.py
```

### Tarkista Konfiguraatio
```bash
# Näytä käytetyt asetukset
python -c "from scripts.config import *; print(f'Teams: {TEAMS_2026}'); print(f'Timeout: {REQUEST_TIMEOUT}')"
```

### Kotiuttaa Lokit
```bash
# Tallenna kaikki lokit tiedostoon
python scripts/main.py 2>&1 | tee output.log

# Tarkista lokit myöhemmin
less output.log
```

---

## 📞 LISÄTUKI

Jos ongelmasi ei ole listalla:

1. **Tarkista dokumentaatio:**
   - [README.md](README.md)
   - [GETTING_STARTED.md](GETTING_STARTED.md)
   - [API.md](API.md)

2. **Avaa GitHub Discussion**
   https://github.com/Linux88888/veikkausliiga2026/discussions

3. **Avaa GitHub Issue**
   https://github.com/Linux88888/veikkausliiga2026/issues

---

**Toivottavasti tämä auttoi! 🎉**
