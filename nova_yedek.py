"""Tutarlı SQLite yedeği ve doğrulaması — yalnızca standart kütüphane.

- create_backup_zip: Çalışan veritabanının SQLite çevrimiçi yedek API'siyle alınan
  tek, tutarlı anlık görüntüsü + manifest (bütünlük, tablo başına satır sayısı ve
  içerik özeti) içeren bir .zip üretir. Kaynağı salt-okunur açar.
- verify_backup_zip: Zip'i açar, dosya özetini, bütünlüğü ve manifesti doğrular,
  ardından yedeği yeni bir dosyaya geri yükleyip aynı kontrolleri tekrarlar.

Raporlar yalnızca tablo adı ve sayı içerir; satır içeriği asla yazılmaz.
"""
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone

DB_ARCNAME = "nova_agency_enterprise.db"
MANIFEST_ARCNAME = "manifest.json"


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_manifest(con):
    """Bütünlük sonucu + her tablo için kolonlar, satır sayısı ve içerik özeti."""
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    names = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    tables = {}
    for name in names:
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{name}")')]
        h = hashlib.sha256()
        rows = 0
        for row in con.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
            h.update(json.dumps(row, default=str, ensure_ascii=False).encode("utf-8"))
            h.update(b"\n")
            rows += 1
        tables[name] = {"rows": rows, "columns": cols, "sha256": h.hexdigest()}
    return {"integrity_check": integrity, "tables": tables}


def create_backup_zip(db_path):
    """(zip_bytes, manifest) döndürür. Kaynak veritabanına yazmaz."""
    if not os.path.exists(db_path):
        raise FileNotFoundError("Veritabanı dosyası bulunamadı.")
    with tempfile.TemporaryDirectory() as tmp:
        snap = os.path.join(tmp, DB_ARCNAME)
        src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        dst = sqlite3.connect(snap)
        try:
            src.backup(dst)
            manifest = table_manifest(dst)
        finally:
            dst.close()
            src.close()
        manifest["created_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest["sqlite_file_sha256"] = _file_sha256(snap)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(snap, DB_ARCNAME)
            z.writestr(MANIFEST_ARCNAME, json.dumps(manifest, indent=2, ensure_ascii=False))
    return buf.getvalue(), manifest


def _compare(expected, actual, label, report):
    ok = True
    if actual["integrity_check"] != "ok":
        report.append(f"[{label}] Bütünlük kontrolü BAŞARISIZ")
        ok = False
    exp_t, act_t = expected["tables"], actual["tables"]
    if set(exp_t) != set(act_t):
        report.append(f"[{label}] Tablo listesi farklı: eksik={sorted(set(exp_t) - set(act_t))} fazla={sorted(set(act_t) - set(exp_t))}")
        ok = False
    for name in sorted(set(exp_t) & set(act_t)):
        e, a = exp_t[name], act_t[name]
        if e != a:
            report.append(f"[{label}] {name}: FARK VAR (beklenen {e['rows']} satır, bulunan {a['rows']} satır)")
            ok = False
    return ok


GECERSIZ = "SONUÇ: GEÇERSİZ YEDEK"


def _gecersiz(*mesajlar):
    return False, list(mesajlar) + [GECERSIZ], None


def manifest_hatasi(manifest):
    """Manifest beklenen yapıda değilse açık bir hata mesajı, uygunsa None döndürür."""
    if not isinstance(manifest, dict):
        return "Manifest geçersiz: JSON nesnesi değil."
    if not isinstance(manifest.get("sqlite_file_sha256"), str):
        return "Manifest geçersiz: veritabanı dosya özeti (sqlite_file_sha256) eksik."
    tables = manifest.get("tables")
    if not isinstance(tables, dict) or not tables:
        return "Manifest geçersiz: 'tables' bölümü eksik veya boş."
    for name, t in tables.items():
        if not isinstance(t, dict):
            return f"Manifest geçersiz: '{name}' tablosunun kaydı bozuk."
        rows = t.get("rows")
        if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
            return f"Manifest geçersiz: '{name}' tablosunun satır sayısı eksik veya hatalı."
        if not isinstance(t.get("sha256"), str) or not isinstance(t.get("columns"), list):
            return f"Manifest geçersiz: '{name}' tablosunun özet veya kolon bilgisi eksik."
    return None


def verify_backup_zip(zip_source, workdir):
    """(ok, rapor_satirlari, geri_yuklenen_db_yolu) döndürür. Hiçbir girdide istisna fırlatmaz.

    zip_source: dosya yolu veya bytes. workdir: geçici çalışma dizini.
    Geçersiz/bozuk yedekte ok=False, son satır "SONUÇ: GEÇERSİZ YEDEK" ve yol None olur.
    """
    try:
        return _verify(zip_source, workdir)
    except Exception as e:  # doğrulayıcı asla çökmemeli; ayrıntı yerine hata türü yazılır
        return _gecersiz(f"Beklenmeyen doğrulama hatası ({type(e).__name__}); yedek güvenilir sayılmamalı.")


def _verify(zip_source, workdir):
    report = []
    if isinstance(zip_source, (bytes, bytearray)):
        data = bytes(zip_source)
    else:
        try:
            with open(zip_source, "rb") as f:
                data = f.read()
        except OSError:
            return _gecersiz("Yedek dosyası okunamadı (yol yanlış veya erişim yok).")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            if not {DB_ARCNAME, MANIFEST_ARCNAME} <= names:
                return _gecersiz("Zip içinde veritabanı veya manifest dosyası eksik.")
            try:
                manifest = json.loads(z.read(MANIFEST_ARCNAME).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return _gecersiz("Manifest geçersiz: okunabilir JSON değil.")
            hata = manifest_hatasi(manifest)
            if hata:
                return _gecersiz(hata)
            extracted = os.path.join(workdir, "yedekten_cikan.db")
            with z.open(DB_ARCNAME) as src, open(extracted, "wb") as dst:
                shutil.copyfileobj(src, dst)
    except zipfile.BadZipFile:
        return _gecersiz("Zip dosyası okunamadı veya bozuk.")

    ok = True
    if _file_sha256(extracted) != manifest["sqlite_file_sha256"]:
        report.append("Veritabanı dosyasının özeti manifestle eşleşmiyor.")
        ok = False

    con = sqlite3.connect(f"file:{extracted}?mode=ro", uri=True)
    try:
        ok &= _compare(manifest, table_manifest(con), "yedek", report)
    except sqlite3.DatabaseError:
        return _gecersiz(*report, "Veritabanı dosyası açılamadı (SQLite dosyası değil veya bozuk).")
    finally:
        con.close()

    restored = os.path.join(workdir, DB_ARCNAME)
    src = sqlite3.connect(f"file:{extracted}?mode=ro", uri=True)
    dst = sqlite3.connect(restored)
    try:
        src.backup(dst)
        ok &= _compare(manifest, table_manifest(dst), "geri yükleme", report)
    finally:
        dst.close()
        src.close()

    total = sum(t["rows"] for t in manifest["tables"].values())
    header = [
        f"Yedek zamanı (UTC): {manifest.get('created_at_utc', '?')}",
        f"Tablo sayısı: {len(manifest['tables'])}, toplam satır: {total}",
    ] + [f"  - {name}: {t['rows']} satır" for name, t in sorted(manifest["tables"].items())]
    report = header + report + ["SONUÇ: OK" if ok else "SONUÇ: FARK VAR"]
    return ok, report, (restored if ok else None)
