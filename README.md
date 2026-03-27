# Veikkausliiga 2026

## Project Description
Veikkausliiga 2026 is an advanced football league management system designed to provide comprehensive features for managing teams, players, matches, and statistics for the Finnish top division football league.

## Features
- **Team Management**: Add, update, and remove teams from the league.
- **Player Management**: Manage player profiles, statistics, and transfers.
- **Match Scheduling**: Schedule and manage fixtures for the league season.
- **Statistics and Reports**: Generate detailed reports on matches, teams, and players.
- **User Access Control**: Different access levels for administrators and regular users.

## Project Structure
```
.
├── scripts/             # Python scripts that generate reports
│   ├── main.py          # Entry point — runs all four analyzers
│   ├── config.py        # URLs, team list, request settings
│   ├── fetch_stats.py   # → output/Tilastot2026.md  (sarjataulukko)
│   ├── match_predictor.py  # → output/Ennusteet2026.md (otteluennusteet)
│   ├── attendance_analyzer.py # → output/Yleiso2026.md (yleisömäärät)
│   └── fetch_matches.py # → output/Ottelut2026.md  (otteluohjelma)
├── output/              # Generated Markdown reports (versioned)
│   ├── Tilastot2026.md  # Sarjataulukko
│   ├── Ennusteet2026.md # Otteluennusteet
│   ├── Yleiso2026.md    # Yleisömäärätilastot
│   └── Ottelut2026.md   # Otteluohjelma ja tulokset
├── .github/workflows/   # CI/CD workflow
└── README.md
```

## Output-tiedostot — mistä luvut tulevat?

Skriptit hakevat tiedot ensisijaisesti **veikkausliiga.com**-sivustolta:

| Tiedosto | Lähde | Fallback |
|---|---|---|
| `Tilastot2026.md` | `veikkausliiga.com/tilastot/2026/veikkausliiga/joukkueet/` | Kiinteä esimerkkidata |
| `Ottelut2026.md` | `veikkausliiga.com/tilastot/2026/veikkausliiga/ottelut/` | Kiinteä esimerkkidata |
| `Ennusteet2026.md` | Laskettu ottelutilastoista | Kiinteät testiprobabiliteetit |
| `Yleiso2026.md` | Yleisötilastot sivustolta | Kiinteä esimerkkidata |

> **Huom:** GitHub Copilot -agentin sandbox-ympäristö ei pysty tavoittamaan veikkausliiga.com-sivustoa palomuurirajoitusten vuoksi. Tällöin skriptit tuottavat tiedostot **esimerkkidatalla** (kiinteät arvot) ja merkitsevät sen raportin yläosaan varoituksella `⚠ Lähde: Esimerkkidata`.
>
> Oikeat tiedot saadaan, kun `python scripts/main.py` ajetaan ympäristössä, jolla on pääsy veikkausliiga.com-sivustolle (esim. paikallisesti tai sallimalla sivusto Copilot-agentin [allowlist-asetuksista](https://github.com/Linux88888/veikkausliiga2026/settings/copilot/coding_agent)).

## Miksi agentti ei voi suoraan puskea mainiin?

GitHub Copilot -koodausagentti toimii aina **feature-branchillä** (`copilot/**`) ja luo pull requestin `main`-haaraan. Tämä on GitHubin tietoturvasuunnitelma:

- `main`-haara on suojattu (branch protection) — suorat pushit estetty
- PR-malli mahdollistaa ihmisvalvonnan ennen koodin yhdistämistä
- Agentti ei voi ohittaa branch protection -sääntöjä

**CI-workflow puskee kuitenkin automaattisesti generoitujen raporttien päivitykset takaisin `copilot/**`-haaraan** jokaisen ajon jälkeen (`git push origin HEAD:"$BRANCH"`).

Jos haluat vähentää manuaalista työtä, voit ottaa käyttöön **auto-merge** PR:ssä — tällöin PR yhdistyy automaattisesti, kun CI-tarkistukset menevät läpi.

## Usage Instructions
1. Clone the repository: `git clone https://github.com/Linux88888/veikkausliiga2026.git`
2. Navigate to the project directory: `cd veikkausliiga2026`
3. Install dependencies: `pip install -r requirements.txt`
4. Generate all reports: `python scripts/main.py`
5. View reports in `output/` directory

## License
This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Author
**Linux88888** - [GitHub Profile](https://github.com/Linux88888)

## Contributions
Contributions are welcome! Please submit a pull request or open an issue for suggestions and improvements.