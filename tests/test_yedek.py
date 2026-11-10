"""Tam yedek / geri yükleme testleri — yalnızca sahte veri, geçici dizin."""
import hashlib
import io
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(ROOT / "app.py")
sys.path.insert(0, str(ROOT))
import nova_yedek  # noqa: E402

DB_NAME = "nova_agency_enterprise.db"
GIZLI_ISIM = "SAHTE_GIZLI_ISIM_93X"


@pytest.fixture
def sahte_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    db = tmp_path / DB_NAME
    con = sqlite3.connect(db)
    con.executemany("INSERT INTO publishers (name, uid, contact_info, hours, crystals, commission, status) VALUES (?,?,?,?,?,?,?)",
                    [(GIZLI_ISIM, "T0001", "0500 000 00 01", 1.5, 1000, 50, "Aktif"),
                     ("Test Iki", "T0002", "@test", 2.0, 30000, 58, "Aktif")])
    con.execute("INSERT INTO performance_history (publisher_uid, publisher_name, date, hours, crystals) VALUES ('T0001', ?, '2026-08-01', 3, 500)", (GIZLI_ISIM,))
    con.execute("INSERT INTO rooms (room_name, room_id, owner) VALUES ('Oda', 'R1', 'Test')")
    con.execute("INSERT INTO penalties (pub_name, publisher_uid, reason, deduction, date) VALUES ('Test Iki', 'T0002', 'gec', 10, '2026-08-02')")
    con.commit()
    con.close()
    return db


def _file_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_yedek_tum_tablolari_kapsar_ve_dogrulanir(sahte_db, tmp_path):
    data, man = nova_yedek.create_backup_zip(str(sahte_db))
    assert man["integrity_check"] == "ok"
    assert man["tables"]["publishers"]["rows"] == 2
    assert man["tables"]["performance_history"]["rows"] == 1
    assert man["tables"]["rooms"]["rows"] == 1
    assert man["tables"]["penalties"]["rows"] == 1
    work = tmp_path / "w"; work.mkdir()
    ok, rapor, restored = nova_yedek.verify_backup_zip(data, str(work))
    assert ok, rapor
    assert rapor[-1] == "SONUÇ: OK"
    con = sqlite3.connect(restored)
    assert con.execute("SELECT COUNT(*) FROM publishers WHERE uid='T0002'").fetchone()[0] == 1
    con.close()


def test_yedek_kaynak_veritabanini_degistirmez(sahte_db):
    once = _file_hash(sahte_db)
    nova_yedek.create_backup_zip(str(sahte_db))
    assert _file_hash(sahte_db) == once


def _zip_degistir(data, db_bytes=None, manifest=None):
    zin = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(nova_yedek.DB_ARCNAME, db_bytes if db_bytes is not None else zin.read(nova_yedek.DB_ARCNAME))
        z.writestr(nova_yedek.MANIFEST_ARCNAME, manifest if manifest is not None else zin.read(nova_yedek.MANIFEST_ARCNAME))
    return out.getvalue()


def test_bozuk_veya_eksik_yedek_reddedilir(sahte_db, tmp_path):
    data, man = nova_yedek.create_backup_zip(str(sahte_db))
    db_bytes = zipfile.ZipFile(io.BytesIO(data)).read(nova_yedek.DB_ARCNAME)

    bozuk = bytearray(db_bytes); bozuk[len(bozuk) // 2] ^= 0xFF
    yanlis_manifest = json.loads(json.dumps(man)); yanlis_manifest["tables"]["publishers"]["rows"] = 99
    for i, aday in enumerate([
        _zip_degistir(data, db_bytes=bytes(bozuk)),
        _zip_degistir(data, manifest=json.dumps(yanlis_manifest)),
        b"bu bir zip degil",
    ]):
        work = tmp_path / f"w{i}"; work.mkdir()
        ok, rapor, _ = nova_yedek.verify_backup_zip(aday, str(work))
        assert not ok, rapor


def test_dogrulama_araci_ok_der_ve_kisisel_veri_yazmaz(sahte_db, tmp_path):
    data, _ = nova_yedek.create_backup_zip(str(sahte_db))
    z = tmp_path / "yedek.zip"; z.write_bytes(data)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "yedek_dogrula.py"), str(z)],
                       capture_output=True, text=True, timeout=180, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SONUÇ: OK" in r.stdout
    assert "Uygulama açılış testi (geri yüklenen kopya): OK" in r.stdout
    for gizli in (GIZLI_ISIM, "0500 000 00 01", "T0001", "@test"):
        assert gizli not in r.stdout + r.stderr


def _yonetici(monkeypatch):
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    if "ADMIN_PASSWORD_HASH" in Path(APP_PATH).read_text(encoding="utf-8"):
        sifre = secrets.token_urlsafe(20)
        tuz = os.urandom(16)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", f"scrypt${tuz.hex()}${hashlib.scrypt(sifre.encode(), salt=tuz, n=2**14, r=8, p=1).hex()}")
        at.run()
        at.sidebar.radio[0].set_value("💼 Yönetim Paneli").run()
        at.text_input[0].set_value(sifre)
        at.button[0].click().run()
    else:
        at.session_state["logged_in"] = True
        at.run()
        at.sidebar.radio[0].set_value("💼 Yönetim Paneli").run()
    assert not at.exception
    return at


def test_yedek_butonu_giris_yapmayana_gorunmez(sahte_db):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.sidebar.radio[0].set_value("💼 Yönetim Paneli").run()
    assert not any(b.label == "Yedeği hazırla" for b in at.button)


def test_yonetici_yedegi_hazirlar_ve_denetim_kaydi_dusulur(sahte_db, monkeypatch):
    at = _yonetici(monkeypatch)
    btn = [b for b in at.button if b.label == "Yedeği hazırla"]
    assert btn, [b.label for b in at.button]
    btn[0].click().run()
    assert not at.exception
    assert at.session_state.backup_manifest["tables"]["publishers"]["rows"] == 2
    assert at.session_state.backup_zip[:2] == b"PK"
    con = sqlite3.connect(sahte_db)
    assert con.execute("SELECT COUNT(*) FROM audit_logs WHERE action='Tam yedek hazırlandı'").fetchone()[0] == 1
    con.close()
