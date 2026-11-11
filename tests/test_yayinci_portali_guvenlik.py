"""Yayıncı portalı (Aşama 0) güvenlik testleri — yalnızca sahte veri."""
import sqlite3

from streamlit.testing.v1 import AppTest

from conftest import APP_PATH, SAHTE_YAYINCILAR, calistir, sayfa_metni


def test_portalda_sorgu_kutusu_yok_ve_hicbir_yayinci_bilgisi_gorunmez(sahte_db):
    at = calistir(AppTest.from_file(APP_PATH))
    # Portalda yalnızca başvuru formu alanları var (Ad, ID, İletişim) — sorgu kutusu yok.
    assert [t.label for t in at.text_input] == ["Ad Soyad *", "Catchii ID *", "Telefon / Instagram *"]
    metin = sayfa_metni(at)
    for name, uid, contact, crystals, hours in SAHTE_YAYINCILAR:
        for alan in (name, uid, contact, f"{crystals:,}", str(crystals)):
            assert alan not in metin, alan
    assert "geçici olarak kapalı" in metin


def _basvur(ad, uid, iletisim):
    at = calistir(AppTest.from_file(APP_PATH))
    at.text_input[0].set_value(ad)
    at.text_input[1].set_value(uid)
    at.text_input[2].set_value(iletisim)
    at.button[0].click()
    return calistir(at)


def test_yeni_ve_tekrar_basvuru_ayni_mesaji_verir_kayit_cogalmaz(sahte_db):
    yeni = _basvur("Yeni Aday", "T0999", "0500 000 00 99")
    tekrar = _basvur("Baska Biri", "T0001", "0500 000 00 98")  # T0001 zaten kayıtlı
    assert [s.value for s in yeni.success] == [s.value for s in tekrar.success]
    assert len(yeni.success) == 1
    assert not tekrar.error
    con = sqlite3.connect(sahte_db)
    assert con.execute("SELECT COUNT(*) FROM publishers WHERE uid='T0001'").fetchone()[0] == 1
    assert con.execute("SELECT name, contact_info FROM publishers WHERE uid='T0001'").fetchone() == ("Test Yayinci Bir", "0500 000 00 01")
    assert con.execute("SELECT COUNT(*) FROM publishers WHERE uid='T0999'").fetchone()[0] == 1
    con.close()


def test_eksik_alanli_basvuru_kayit_olusturmaz(sahte_db):
    at = _basvur("", "T0888", "")
    assert at.error
    con = sqlite3.connect(sahte_db)
    assert con.execute("SELECT COUNT(*) FROM publishers WHERE uid='T0888'").fetchone()[0] == 0
    con.close()


def test_html_iceren_basvuru_yonetici_tablosunda_duz_metin(sahte_db):
    """Başvurudaki HTML hiçbir yerde unsafe_allow_html ile basılmamalı."""
    zararli = '<img src=x onerror="document.title=1">'
    _basvur(zararli, "T0666", "x")
    at = calistir(AppTest.from_file(APP_PATH))
    for m in at.markdown:
        assert zararli not in m.value
