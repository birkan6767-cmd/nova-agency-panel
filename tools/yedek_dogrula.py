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


ACILIS_OK = "OK"
ACILIS_ATLANDI = "YAPILMADI (streamlit kurulu değil)"


def uygulama_acilis_testi(restored_db):
    """Uygulamayı geri yüklenen KOPYA ile açar. Hiçbir durumda istisna fırlatmaz.

    Dönüş: "OK", "YAPILMADI (...)" veya "HATA (...)".
    """
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        return ACILIS_ATLANDI
    eski = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(restored_db, os.path.join(tmp, nova_yedek.DB_ARCNAME))
            os.chdir(tmp)
            try:
                at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
            finally:
                os.chdir(eski)
            if at.exception:
                return "HATA (uygulama geri yüklenen kopyayla açılırken hata verdi)"
            return ACILIS_OK
    except Exception as e:  # açılış testi asla aracı çökertmemeli
        return f"HATA (açılış testi beklenmeyen şekilde durdu: {type(e).__name__})"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Kullanım: python tools/yedek_dogrula.py <yedek.zip>")
    with tempfile.TemporaryDirectory() as work:
        ok, rapor, restored = nova_yedek.verify_backup_zip(sys.argv[1], work)
        if not ok:
            print("\n".join(rapor))  # son satır zaten "SONUÇ: FARK VAR" veya "SONUÇ: GEÇERSİZ YEDEK"
            sys.exit(1)
        # Yedek ve geri yükleme geçti; nihai SONUÇ ancak açılış testinden sonra yazılır.
        print("\n".join(rapor[:-1]))
        print("Yedek ve geri yükleme kontrolleri: GEÇTİ")
        acilis = uygulama_acilis_testi(restored)
        print(f"Uygulama açılış testi (geri yüklenen kopya): {acilis}")
    if acilis == ACILIS_OK:
        print("SONUÇ: OK (tüm kontroller geçti)")
        sys.exit(0)
    if acilis == ACILIS_ATLANDI:
        print("SONUÇ: OK — DİKKAT: uygulama açılış testi YAPILMADI; yalnızca yedek ve geri yükleme doğrulandı.")
        sys.exit(0)
    print("SONUÇ: BAŞARISIZ (uygulama açılış testi geçmedi)")
    sys.exit(1)


if __name__ == "__main__":
    main()
