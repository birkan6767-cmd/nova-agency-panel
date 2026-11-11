"""Ortak test ayarları.

Testler GERÇEK veritabanına ve gerçek yayıncı verisine asla dokunmaz:
her test geçici bir dizinde çalışır ve uygulama veritabanını orada oluşturur.
Tüm yayıncılar uydurmadır.
"""
import sqlite3
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
DB_NAME = "nova_agency_enterprise.db"

SAHTE_YAYINCILAR = [
    # (name, uid, contact_info, crystals, hours)
    ("Test Yayinci Bir", "T0001", "0500 000 00 01", 12000, 10.0),
    ("Test Yayinci Iki", "T0002", "@test_iki", 55000, 22.5),
    ("Deneme Hesabi", "T0003", "0500 000 00 03", 101000, 31.0),
]


@pytest.fixture(autouse=True)
def temiz_sunucu_bellegi():
    """Sunucu tarafı sayaçlar (st.cache_resource) testler arasında sızmasın."""
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def calistir(at: AppTest) -> AppTest:
    at.run(timeout=30)
    assert not at.exception, at.exception
    return at


@pytest.fixture
def sahte_db(tmp_path, monkeypatch):
    """Geçici dizinde şemayı oluşturur, sahte yayıncıları ekler, db yolunu döndürür."""
    monkeypatch.chdir(tmp_path)
    calistir(AppTest.from_file(APP_PATH))
    db_path = tmp_path / DB_NAME
    con = sqlite3.connect(db_path)
    con.executemany(
        "INSERT INTO publishers (name, uid, contact_info, contact_type, hours, crystals, tier, commission, status) "
        "VALUES (?, ?, ?, 'Telefon', ?, ?, 'Tier 1 (Başlangıç)', 50, 'Aktif')",
        [(n, u, c, h, cr) for (n, u, c, cr, h) in SAHTE_YAYINCILAR],
    )
    con.commit()
    con.close()
    return db_path


def sayfa_metni(at: AppTest) -> str:
    """Sayfadaki tüm görünür metinler (markdown, info, uyarı, başarı, hata, başlıklar)."""
    parcalar = []
    for tur in ("markdown", "info", "warning", "success", "error", "title", "subheader", "caption", "text"):
        parcalar += [str(getattr(e, "value", "")) for e in getattr(at, tur)]
    return "\n".join(parcalar)
