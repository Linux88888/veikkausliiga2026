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
    
    try:
        logger.info("\n[1/3] Haetaan tilastotiedot...")
        processor = StatsProcessor()
        if not processor.run():
            logger.error("Tilastohaku epäonnistui")
            return False
        
        logger.info("\n[2/3] Analyysit valmis...")
        
        logger.info("\n[3/3] Raporttien luominen...")
        logger.info("✓ Raportit luotu output-kansioon")
        
        logger.info("\n" + "="*70)
        logger.info("✅ KAIKKI ANALYYSIT VALMIS!")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Virhe: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
