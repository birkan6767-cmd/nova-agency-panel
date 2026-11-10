"""Ortak test ayarları.

Testler GERÇEK veritabanına ve gerçek yayıncı verisine asla dokunmaz:
her test geçici bir dizinde çalışır ve uygulama veritabanını orada oluşturur.
Tüm yayıncılar uydurmadır.
"""
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
DB_NAME = "nova_agency_enterprise.db"

SAHTE_YAYINCILAR = [
    # (name, uid, contact_info, crystals, hours)
    ("Test Yayinci Bir", "T0001", "0500 000 00 01", 12000, 10.0),
    ("Test Yayinci Iki", "T0002", "@test_iki", 55000, 22.5),
    ("Deneme Hesabi", "T0003", "0500 000 00 03", 101000, 31.0),
]


def _calistir(at: AppTest) -> AppTest:
    at.run(timeout=30)
    assert not at.exception, at.exception
    return at


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Geçici dizinde, sahte verilerle doldurulmuş uygulama döndürür."""
    monkeypatch.chdir(tmp_path)
    _calistir(AppTest.from_file(APP_PATH))  # şemayı oluşturur
    db_path = tmp_path / DB_NAME
    assert db_path.exists()

    def ekle(rows):
        con = sqlite3.connect(db_path)
        con.executemany(
            "INSERT INTO publishers (name, uid, contact_info, contact_type, hours, crystals, tier, commission, status) "
            "VALUES (?, ?, ?, 'Telefon', ?, ?, 'Tier 1 (Başlangıç)', 50, 'Aktif')",
            [(n, u, c, h, cr) for (n, u, c, cr, h) in rows],
        )
        con.commit()
        con.close()

    ekle(SAHTE_YAYINCILAR)

    class Uygulama:
        def __init__(self):
            self.ekle = ekle

        def ara(self, sorgu: str) -> AppTest:
            at = _calistir(AppTest.from_file(APP_PATH))
            at.text_input[0].set_value(sorgu)
            return _calistir(at)

    return Uygulama()


def yayinci_kartlari(at: AppTest):
    return [m.value for m in at.markdown if 'class="pub-card"' in m.value]
