"""Yönetici girişi (Aşama 0) testleri — gerçek şifre yok; test şifreleri rastgele üretilir,
zaman sahte saatle ilerletilir."""
import hashlib
import os
import secrets
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH, calistir


def _ozet(sifre):
    tuz = os.urandom(16)
    return f"scrypt${tuz.hex()}${hashlib.scrypt(sifre.encode(), salt=tuz, n=2**14, r=8, p=1).hex()}"


class Saat:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t

    def ilerle(self, saniye):
        self.t += saniye


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    saat = Saat()
    monkeypatch.setattr(time, "time", saat)
    sifre = secrets.token_urlsafe(20)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", _ozet(sifre))
    return {"sifre": sifre, "saat": saat, "mp": monkeypatch}


def yeni_oturum():
    """Her çağrı ayrı bir tarayıcı oturumu gibidir (ayrı session_state)."""
    at = calistir(AppTest.from_file(APP_PATH))
    at.sidebar.radio[0].set_value("💼 Yönetim Paneli")
    return calistir(at)


def giris(at, sifre):
    at.text_input[0].set_value(sifre)
    at.button[0].click()
    return calistir(at)


def girdi_mi(at):
    return bool(at.session_state["logged_in"]) if "logged_in" in at.session_state else False


def hatalar(at):
    return " ".join(e.value for e in at.error)


def test_dogru_sifre_ile_giris(ortam):
    assert girdi_mi(giris(yeni_oturum(), ortam["sifre"]))


def test_yanlis_sifre_reddedilir(ortam):
    at = giris(yeni_oturum(), "yanlis")
    assert not girdi_mi(at)
    assert "Hatalı" in hatalar(at)


def test_kodda_sabit_sifre_yok():
    assert "ADMIN_PASSWORD =" not in Path(APP_PATH).read_text(encoding="utf-8")


def test_ozet_tanimli_degilse_giris_kapali(ortam):
    ortam["mp"].delenv("ADMIN_PASSWORD_HASH")
    at = giris(yeni_oturum(), "herhangi")
    assert not girdi_mi(at)
    assert "yapılandırılmamış" in hatalar(at)


def test_yeni_oturum_acmak_deneme_sinirini_asmaz(ortam):
    for _ in range(5):
        giris(yeni_oturum(), "yanlis")  # her deneme ayrı oturumdan
    at = giris(yeni_oturum(), ortam["sifre"])  # doğru şifre, yine yeni oturum
    assert not girdi_mi(at)
    assert "kilitli" in hatalar(at)


def test_kilit_suresi_dolunca_giris_acilir_ve_sure_ikiye_katlanir(ortam):
    saat = ortam["saat"]
    for _ in range(5):
        giris(yeni_oturum(), "yanlis")
    saat.ilerle(61)  # ilk kilit 60 sn
    for _ in range(5):
        giris(yeni_oturum(), "yanlis")  # ikinci kilit 120 sn olmalı
    saat.ilerle(61)
    assert not girdi_mi(giris(yeni_oturum(), ortam["sifre"]))  # hâlâ kilitli
    saat.ilerle(60)
    assert girdi_mi(giris(yeni_oturum(), ortam["sifre"]))


def test_kilit_suresi_15_dakikayi_gecmez(ortam):
    saat = ortam["saat"]
    for _ in range(8):  # 1, 2, 4, 8, 15, 15 ... dk
        for _ in range(5):
            giris(yeni_oturum(), "yanlis")
        saat.ilerle(15 * 60 + 1)
    assert girdi_mi(giris(yeni_oturum(), ortam["sifre"]))


def test_ozet_degisince_kilit_kalkar(ortam):
    for _ in range(5):
        giris(yeni_oturum(), "yanlis")
    yeni = secrets.token_urlsafe(20)
    ortam["mp"].setenv("ADMIN_PASSWORD_HASH", _ozet(yeni))
    assert girdi_mi(giris(yeni_oturum(), yeni))


def test_acik_yonetici_oturumu_kilitten_etkilenmez(ortam):
    yonetici = giris(yeni_oturum(), ortam["sifre"])
    assert girdi_mi(yonetici)
    for _ in range(5):
        giris(yeni_oturum(), "yanlis")  # saldırgan başka oturumdan kilitler
    calistir(yonetici)  # yönetici sayfayı yeniler
    assert girdi_mi(yonetici)
    assert any(t.value == "⭐ Nova Agency Enterprise" for t in yonetici.title)


def test_basarili_giriste_hatali_deneme_uyarisi(ortam):
    for _ in range(3):
        giris(yeni_oturum(), "yanlis")
    at = giris(yeni_oturum(), ortam["sifre"])
    assert any("3 hatalı giriş denemesi" in w.value for w in at.warning)


def test_30_dk_hareketsizlikte_oturum_kapanir(ortam):
    at = giris(yeni_oturum(), ortam["sifre"])
    ortam["saat"].ilerle(29 * 60)
    calistir(at)
    assert girdi_mi(at)
    ortam["saat"].ilerle(31 * 60)
    calistir(at)
    assert not girdi_mi(at)
    assert any("sona erdi" in w.value for w in at.warning)


def test_ozet_degisince_acik_oturum_kapanir(ortam):
    at = giris(yeni_oturum(), ortam["sifre"])
    ortam["mp"].setenv("ADMIN_PASSWORD_HASH", _ozet(secrets.token_urlsafe(20)))
    calistir(at)
    assert not girdi_mi(at)


def test_cikis_oturumu_kapatir(ortam):
    at = giris(yeni_oturum(), ortam["sifre"])
    [b for b in at.button if b.label == "🔒 Çıkış"][0].click()
    calistir(at)
    assert not girdi_mi(at)
