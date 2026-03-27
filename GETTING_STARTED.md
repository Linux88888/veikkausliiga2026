# Veikkausliiga 2026 - Pika-opas

## ⚡ Nopea Aloitus (5 minuuttia)

### 1. Asennus

```bash
# Kloonaa repository
git clone https://github.com/Linux88888/veikkausliiga2026.git
cd veikkausliiga2026

# Asenna riippuvuudet
pip install -r requirements.txt
```

### 2. Suorita Analyysit

```bash
# Käynnistä pääskripti
python scripts/main.py
```

### 3. Tarkastele Tuloksia

```bash
# Avaa generoidut raportit
cat output/Tilastot2026.md
cat output/Yleiso2026.md
cat output/Ennusteet2026.md
```

---

## 📁 Projektirakenteen Selitys

```
veikkausliiga2026/
├── README.md                      # Pääasiakirja
├── GETTING_STARTED.md             # Tämä tiedosto
├── requirements.txt               # Python-riippuvuudet
├── config.py                      # Konfiguraatio
├── scripts/
│   ├── config.py                 # Asetukset ja vakiot
│   ├── main.py                   # Pääohjelma
│   ├── fetch_stats.py            # Tilastojen haku
│   ├── attendance_analyzer.py    # Yleisöanalyysi
│   └── match_predictor.py        # Otteluennusteet
├── output/                        # Generoidut raportit
├── data/                          # Väliaikaistiedostot
└── LICENSE                        # GPL-3.0 lisenssi
```

---

## 🎯 Jokaisen Skriptin Kuvaus

### config.py
- Määrittää joukkueet, pelaajat ja konfiguraatiot
- Asettaa URL:t ja timeout-arvot
- Valmistaa output- ja data-kansiot

### fetch_stats.py
- Hakee sarjataulukon veikkausliiga.com:sta
- Laskee pelaajien pisteet
- Vertaa ennustettua järjestystä toteutuneeseen

### main.py
- Pääohjelma joka koordinoi kaikkea
- Ajaa kaikki analyysit peräkkäin
- Tulostaa yhteenvedon

### attendance_analyzer.py
- Analysoi stadionilla käyneiden määriä
- Laskee keskiarvot ja tilastot
- Tuottaa yleisö-raportin

### match_predictor.py
- Ennustaa tulevien otteluiden tuloksia
- Laskee voittotodennäköisyydet
- Tuottaa ennuste-raportin

---

## 🚀 Edistyneet Komennot

### Jotain tiettyä skriptiä:

```bash
# Pelkästään tilastohaku
python scripts/fetch_stats.py

# Pelkästään yleisöanalyysi
python scripts/attendance_analyzer.py

# Pelkästään ennusteet
python scripts/match_predictor.py
```

### Debug-moodissa (lisää lokit):

```bash
# Muokkaa scripts/main.py:tä ja vaihda:
logging.basicConfig(level=logging.DEBUG)
```

---

## 🔧 Konfigurointi

Avaa `scripts/config.py` ja muokkaa:

```python
# Seurattavat pelaajat
WATCHED_PLAYERS = ["Pelaaja1", "Pelaaja2", ...]

# Veikattu sarjajärjestys
PREDICTED_ORDER = ["HJK", "Ilves", "KuPS", ...]

# Timeout sekunteissa
REQUEST_TIMEOUT = 10

# Uudelleenyritykset
MAX_RETRIES = 3
```

---

## 📊 Tuotetut Raportit

Analyysit tuottavat kolme markdown-raporttia:

1. **Tilastot2026.md** - Sarjataulukko ja pelaajapisteet
2. **Yleiso2026.md** - Yleisömäärät ja stadionkäynnit
3. **Ennusteet2026.md** - Tulevien otteluiden ennusteet

---

## ❓ Usein Kysytyt Kysymykset

### P: Miten päivitän tiedot?
V: Suorita `python scripts/main.py` uudelleen. Se hakee uudet tiedot automaattisesti.

### P: Voiko tätä ajaa automaattisesti?
V: Kyllä! Aseta GitHub Actions workflow tai cron-työ. Katso dokumentaatiota.

### P: Mitä jos veikkausliiga.com on alhaalla?
V: Skripti käyttää testidataa. Yritä myöhemmin uudelleen.

### P: Voiko rivien lukumäärää muuttaa?
V: Kyllä! Muokkaa `POINT_MULTIPLIERS` arvoja `config.py`:ssä.

---

## 🆘 Ongelmatilanteet

**ModuleNotFoundError: No module named 'requests'**
```bash
pip install -r requirements.txt
```

**Connection timeout**
- Tarkista internet-yhteys
- Yritä myöhemmin (sivu saattaa olla alhaalla)

**Ei output-tiedostoja**
```bash
mkdir -p output
python scripts/main.py
```

---

## 📝 Lisäresurssit

- [GitHub Repository](https://github.com/Linux88888/veikkausliiga2026)
- [README.md](README.md) - Yksityiskohtainen dokumentaatio
- [INSTALL.md](INSTALL.md) - Asennusohjeet
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Ongelmien ratkaisu

---

**Hyvää analysointia! 🎉**
