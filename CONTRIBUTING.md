# Osallistuminen Veikkausliiga 2026 -projektiin

Kiitos kiinnostuksestasi! Olemme iloisia, että haluat osallistua projektiin. 🎉

---

## 📋 Ennen kuin Aloitat

1. **Tarkista olemassa olevat issuet** - Niin et tee turhaa työtä
2. **Lue README.md** - Ymmärrä projektin tarkoitus
3. **Asenna kehitysympäristö** - Seuraa GETTING_STARTED.md:tä

---

## 🚀 Osallistumisen Prosessi

### 1. Forkkaa Repository

Klikkaa GitHub-sivulla "Fork"-nappia oikeassa yläkulmassa.

### 2. Kloonaa Forkisi

```bash
git clone https://github.com/YOUR_USERNAME/veikkausliiga2026.git
cd veikkausliiga2026
```

### 3. Luo Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Käytä kuvaavaa nimeä:
- `feature/better-stats-parsing`
- `fix/timeout-handling`
- `docs/add-examples`

### 4. Tee Muutokset

Muokkaa tarvittavat tiedostot ja testaa paikallisesti:

```bash
python scripts/main.py
```

### 5. Commitoi Muutokset

```bash
git add .
git commit -m "Lisää ominaisuus: lyhyt kuvaus"
```

**Commit-viestien muoto:**
```
feat: Lisää uusi ominaisuus
fix: Korjaa bugi
docs: Päivitä dokumentaatiota
style: Muokkaa koodin tyyliä
refactor: Uudelleenjärjestä koodia
test: Lisää testejä
```

### 6. Pushaa Branch

```bash
git push origin feature/your-feature-name
```

### 7. Avaa Pull Request

1. Mene GitHubiin forkkauksellesi
2. Klikkaa "New Pull Request"
3. Valitse main branch
4. Täytä kuvaus ja klikkaa "Create Pull Request"

---

## 📝 Pull Request -kuvaus

Kirjoita selkeä kuvaus:

```markdown
## Kuvaus

Tämä PR lisää/korjaa [mitä tekee].

## Muutokset

- [ ] Lisäys 1
- [ ] Lisäys 2
- [ ] Korjaus 1

## Testattu

- [ ] Paikallisesti testattu
- [ ] Ei rikkoa olemassa olevia ominaisuuksia
- [ ] Uusien ominaisuuksien testit sisällytetty

## Liittyvät issuet

Fixes #123
Closes #456
```

---

## 💻 Koodausohjeistus

### Python-tyyli

Seuraa PEP 8 standardia:

```bash
pip install black
black scripts/
```

### Docstrings

```python
def analyze_standings(standings):
    """
    Analysoi sarjataulukkoa ja palauttaa yhteenvedon.
    
    Args:
        standings (list): Lista sarjataulukon riveistä
        
    Returns:
        dict: Yhteenveto tiedot
        
    Raises:
        ValueError: Jos data on virheellinen
    """
    pass
```

### Loggaus

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Informatiivinen viesti")
logger.warning("Varoitus")
logger.error("Virhe")
```

---

## 🧪 Testaus

### Testaa paikallisesti ennen PullRequestia:

```bash
# Asenna riippuvuudet
pip install -r requirements.txt

# Suorita analyysit
python scripts/main.py

# Tarkista output
ls -la output/
cat output/Tilastot2026.md
```

### Testaa uusia ominaisuuksia:

```python
# scripts/test_my_feature.py

def test_my_feature():
    from my_feature import my_function
    result = my_function()
    assert result is not None
    print("✓ Testi läpäistyi!")

if __name__ == "__main__":
    test_my_feature()
```

---

## 📚 Dokumentaation Päivittäminen

Jos lisäät ominaisuuden, päivitä myös:

1. **README.md** - Yleiskuvaus
2. **GETTING_STARTED.md** - Käyttöohjeet
3. **API.md** - API-dokumentaatio

---

## 🐛 Bugiraportointi

Avaa Issue ja täytä:

```markdown
## Bugin kuvaus

Lyhyt kuvaus mitä on vialla.

## Toistamisen vaiheet

1. Tee tämä
2. Sitten tämä
3. Bugi tapahtuu

## Odotettu käytös

Mitä pitäisi tapahtua.

## Todellinen käytös

Mitä todellisuudessa tapahtui.

## Ympäristö

- OS: [esim. macOS 12.1]
- Python: [esim. 3.9.2]
- Versio: [git commit hash]
```

---

## ✅ Koodin Tarkistuslistaa

Ennen Pull Requestia, tarkista:

- [ ] Koodi seuraa PEP 8 -standardia
- [ ] Lisäsit docstringsit uusille funktioille
- [ ] Käytit loggausta virheiden raportointiin
- [ ] Testasin paikallisesti
- [ ] Ei riko olemassa olevia testejä
- [ ] Päivitin dokumentaation
- [ ] Commit-viestit ovat selkeät
- [ ] Ei lisää unnecessary dependencies

---

## 🎯 Osallistumisen Alueet

### Olemme kiinnostuneita:

- 📊 Parannetut analyysialgoritmit
- 🔍 Parempi data parsing
- 📈 Uudet analysointiominaisuudet
- 📚 Dokumentaation parannukset
- 🧪 Kattavammat testit
- 🚀 Suorituskyvyn optimointi
- 🐛 Bugikorjaukset

---

## ❓ Kysymyksiä?

Avaa GitHub Discussion:
https://github.com/Linux88888/veikkausliiga2026/discussions

Tai lähetä sähköpostia ylläpitäjälle.

---

## 📖 Lisäresurssit

- [Git ohjeita](https://git-scm.com/book/en/v2)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)

---

**Kiitos osallistumisesta! 🙌**
