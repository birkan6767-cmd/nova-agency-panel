"""İndirilen tam yedeği doğrular ve geri yüklenebilirliğini test eder.

Kullanım:  python tools/yedek_dogrula.py nova_yedek_....zip

Yapılanlar (hepsi geçici bir klasörde; yedek dosyası değiştirilmez):
  1. Zip'teki veritabanı dosyasının özeti manifestle karşılaştırılır.
  2. PRAGMA integrity_check + tablo başına satır sayısı ve içerik özeti manifestle karşılaştırılır.
  3. Yedek yeni bir dosyaya geri yüklenir ve aynı kontroller tekrarlanır.
  4. (streamlit kuruluysa) Uygulama geri yüklenen KOPYA ile açılır, hata vermediği kontrol edilir.

Çıktıda yalnızca tablo adları, satır sayıları ve sonuç yazar; kişisel veri yazmaz.
Uygulama açılış testi sırasında uygulamanın kendi çıktıları (stdout, stderr, günlükler,
uyarılar, hata dökümleri) tamamen susturulur; yalnızca "OK/HATA" ve hata türü raporlanır.

Çıkış kodları:
  0  Tüm kontroller geçti (yedek + geri yükleme + uygulama açılışı).
  1  Başarısız: yedek geçersiz/farklı veya uygulama geri yüklenen kopyayla açılmadı.
  2  Kısmi: yedek ve geri yükleme geçti, ama uygulama açılış testi YAPILAMADI.
"""
import contextlib
import io
import logging
import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nova_yedek  # noqa: E402


KOD_OK, KOD_BASARISIZ, KOD_KISMI = 0, 1, 2
ACILIS_OK = "OK"
ACILIS_ATLANDI = "YAPILMADI (streamlit kurulu değil)"


@contextlib.contextmanager
def _sessiz():
    """İçerideki her çıktıyı yutar: Python düzeyi (print, sys.stderr, logging, warnings)
    ve süreç düzeyi (dosya tanımlayıcı 1 ve 2). Çıkarken her şeyi eski haline getirir."""
    sys.stdout.flush()
    sys.stderr.flush()
    eski_out, eski_err = os.dup(1), os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                warnings.catch_warnings():
            warnings.simplefilter("ignore")
            logging.disable(logging.CRITICAL)
            try:
                yield
            finally:
                logging.disable(logging.NOTSET)
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os.dup2(eski_out, 1)
            os.dup2(eski_err, 2)
            for fd in (eski_out, eski_err, devnull):
                os.close(fd)


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
                with _sessiz():
                    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
                    hata_var = bool(at.exception)
            finally:
                os.chdir(eski)
            if hata_var:
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
            sys.exit(KOD_BASARISIZ)
        # Yedek ve geri yükleme geçti; nihai SONUÇ ancak açılış testinden sonra yazılır.
        print("\n".join(rapor[:-1]))
        print("Yedek ve geri yükleme kontrolleri: GEÇTİ")
        acilis = uygulama_acilis_testi(restored)
        print(f"Uygulama açılış testi (geri yüklenen kopya): {acilis}")
    if acilis == ACILIS_OK:
        print("SONUÇ: OK (tüm kontroller geçti)")
        sys.exit(KOD_OK)
    if acilis == ACILIS_ATLANDI:
        print("SONUÇ: KISMİ — uygulama açılış testi YAPILMADI; yalnızca yedek ve geri yükleme doğrulandı (çıkış kodu 2).")
        sys.exit(KOD_KISMI)
    print("SONUÇ: BAŞARISIZ (uygulama açılış testi geçmedi)")
    sys.exit(KOD_BASARISIZ)


if __name__ == "__main__":
    main()
