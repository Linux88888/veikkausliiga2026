"""
Veikkausliiga 2026 - Pääskripti
Ajaa kaikki analyysit
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fetch_stats import StatsProcessor
except ImportError as e:
    print(f"Varoitus: {e}")
    StatsProcessor = None

try:
    from match_predictor import MatchPredictor
except ImportError as e:
    print(f"Varoitus: {e}")
    MatchPredictor = None

try:
    from attendance_analyzer import AttendanceAnalyzer
except ImportError as e:
    print(f"Varoitus: {e}")
    AttendanceAnalyzer = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Pääfunktio - käynnistää kaikki analyysit"""
    logger.info("="*70)
    logger.info("VEIKKAUSLIIGA 2026 - TIETOJEN PÄIVITYS")
    logger.info("="*70)
    
    success = True

    try:
        logger.info("\n[1/3] Haetaan tilastotiedot (Tilastot2026.md)...")
        if StatsProcessor:
            processor = StatsProcessor()
            if not processor.run():
                logger.error("Tilastohaku epäonnistui")
                success = False
        else:
            logger.error("StatsProcessor ei saatavilla")
            success = False
    except Exception as e:
        logger.error(f"❌ Virhe tilastohaussa: {e}", exc_info=True)
        success = False

    try:
        logger.info("\n[2/3] Lasketaan otteluennusteet (Ennusteet2026.md)...")
        if MatchPredictor:
            predictor = MatchPredictor()
            if not predictor.predict():
                logger.error("Otteluennusteet epäonnistui")
                success = False
        else:
            logger.error("MatchPredictor ei saatavilla")
            success = False
    except Exception as e:
        logger.error(f"❌ Virhe ennusteissa: {e}", exc_info=True)
        success = False

    try:
        logger.info("\n[3/3] Analysoidaan yleisömäärät (Yleiso2026.md)...")
        if AttendanceAnalyzer:
            analyzer = AttendanceAnalyzer()
            if not analyzer.analyze():
                logger.error("Yleisöanalyysi epäonnistui")
                success = False
        else:
            logger.error("AttendanceAnalyzer ei saatavilla")
            success = False
    except Exception as e:
        logger.error(f"❌ Virhe yleisöanalyysissä: {e}", exc_info=True)
        success = False

    if success:
        logger.info("\n" + "="*70)
        logger.info("✅ KAIKKI ANALYYSIT VALMIS!")
        logger.info("="*70)
    else:
        logger.error("\n" + "="*70)
        logger.error("❌ OSA ANALYYSEISTA EPÄONNISTUI!")
        logger.error("="*70)

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
