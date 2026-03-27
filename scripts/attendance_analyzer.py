"""
Veikkausliiga 2026 - Yleisömäärä Analyysi
Analysoi stadionilla käyneiden määrät
"""
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttendanceAnalyzer:
    """Analysoi yleisömääriä ja stadionkäyntejä"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)
    
    def analyze(self):
        """Pääanalyysi funktio"""
        logger.info("="*60)
        logger.info("YLEISÖMÄÄRÄ-ANALYYSI - Veikkausliiga 2026")
        logger.info("="*60)
        
        # Testidataa
        attendance_data = {
            'total_attendance': 850000,
            'matches': 180,
            'average_per_match': 4722,
            'highest_attendance': 15000,
            'lowest_attendance': 1200,
        }
        
        logger.info(f"✓ Yhteensä katsojia: {attendance_data['total_attendance']:,}")
        logger.info(f"✓ Otteluja: {attendance_data['matches']}")
        logger.info(f"✓ Keskiarvo per ottelu: {attendance_data['average_per_match']:,}")
        
        # Tallenna raportti
        report_path = self.output_dir / "Yleiso2026.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Veikkausliiga 2026 - Yleisömäärät\n\n")
            f.write(f"*Analysoitu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"## Tilastot\n\n")
            f.write(f"- **Yhteensä katsojia**: {attendance_data['total_attendance']:,}\n")
            f.write(f"- **Otteluja**: {attendance_data['matches']}\n")
            f.write(f"- **Keskiarvo**: {attendance_data['average_per_match']:,} katsojaa/ottelu\n")
            f.write(f"- **Korkein**: {attendance_data['highest_attendance']:,} katsojaa\n")
            f.write(f"- **Matalin**: {attendance_data['lowest_attendance']:,} katsojaa\n")
        
        logger.info(f"✓ Raportti tallennettu: {report_path}")
        return True

def main():
    analyzer = AttendanceAnalyzer()
    return analyzer.analyze()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
