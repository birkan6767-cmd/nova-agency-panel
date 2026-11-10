"""İndirilen tam yedeği doğrular ve geri yüklenebilirliğini test eder.

Kullanım:  python tools/yedek_dogrula.py nova_yedek_....zip

Yapılanlar (hepsi geçici bir klasörde; yedek dosyası değiştirilmez):
  1. Zip'teki veritabanı dosyasının özeti manifestle karşılaştırılır.
  2. PRAGMA integrity_check + tablo başına satır sayısı ve içerik özeti manifestle karşılaştırılır.
  3. Yedek yeni bir dosyaya geri yüklenir ve aynı kontroller tekrarlanır.
  4. (streamlit kuruluysa) Uygulama geri yüklenen KOPYA ile açılır, hata vermediği kontrol edilir.

Çıktıda yalnızca tablo adları, satır sayıları ve OK / FARK VAR yazar; kişisel veri yazmaz.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nova_yedek  # noqa: E402


def uygulama_acilis_testi(restored_db):
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        return "ATLANDI (streamlit kurulu değil)"
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(restored_db, os.path.join(tmp, nova_yedek.DB_ARCNAME))
        eski = os.getcwd()
        os.chdir(tmp)
        try:
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
            return "OK" if not at.exception else "HATA (uygulama geri yüklenen kopyayla açılmadı)"
        finally:
            os.chdir(eski)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Kullanım: python tools/yedek_dogrula.py <yedek.zip>")
    with tempfile.TemporaryDirectory() as work:
        ok, rapor, restored = nova_yedek.verify_backup_zip(sys.argv[1], work)
        print("\n".join(rapor))
        if ok:
            sonuc = uygulama_acilis_testi(restored)
            print(f"Uygulama açılış testi (geri yüklenen kopya): {sonuc}")
            ok = not sonuc.startswith("HATA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
