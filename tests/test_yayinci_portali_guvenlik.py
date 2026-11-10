"""Yayıncı portalı güvenlik testleri (sadece sahte veri)."""
import pytest

from conftest import yayinci_kartlari


@pytest.mark.parametrize("sorgu", [".", ".*", "T", "test", "yayinci", "0"])
def test_kismi_veya_joker_arama_baskalarinin_verisini_gostermez(app, sorgu):
    at = app.ara(sorgu)
    assert yayinci_kartlari(at) == [], f"'{sorgu}' araması yayıncı verisi döktü"


@pytest.mark.parametrize("sorgu", ["(", "[", "*", "\\"])
def test_ozel_karakterler_uygulamayi_cokertmez(app, sorgu):
    app.ara(sorgu)  # _calistir istisna olmadığını doğrular


def test_tam_id_eslesmesi_tek_kayit_gosterir(app):
    kartlar = yayinci_kartlari(app.ara("T0002"))
    assert len(kartlar) == 1
    assert "T0002" in kartlar[0]


def test_id_bas_son_bosluk_ve_buyuk_kucuk_harf_toleransi(app):
    assert len(yayinci_kartlari(app.ara("  t0002 "))) == 1


def test_isim_ile_arama_kart_gostermez(app):
    assert yayinci_kartlari(app.ara("Test Yayinci Iki")) == []


def test_iletisim_bilgisi_portalda_gosterilmez(app):
    kart = yayinci_kartlari(app.ara("T0001"))[0]
    assert "0500 000 00 01" not in kart


ZARARLI = '<img src=x onerror="document.title=1">'


def test_yayinci_adindaki_html_kacirilir(app):
    app.ekle([(ZARARLI, "T0666", "x", 0, 0.0)])
    kart = yayinci_kartlari(app.ara("T0666"))[0]
    assert "<img" not in kart
    assert "&lt;img" in kart


def test_basvuru_formundan_gelen_html_kacirilir(app):
    """Saldırgan herkese açık başvuru formuna zararlı isim girer; kart kaçırılmış göstermeli."""
    from streamlit.testing.v1 import AppTest
    from conftest import APP_PATH, _calistir

    at = _calistir(AppTest.from_file(APP_PATH))
    # Başvuru formu alanları: Ad Soyad, Catchii ID, Telefon/Instagram (arama kutusundan sonra)
    at.text_input[1].set_value(ZARARLI)
    at.text_input[2].set_value("T0777")
    at.text_input[3].set_value("0500 000 00 77")
    at.button[0].click()
    _calistir(at)
    assert any("başarıyla" in s.value for s in at.success)

    kart = yayinci_kartlari(app.ara("T0777"))[0]
    assert "<img" not in kart
