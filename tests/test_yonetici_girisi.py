"""Yönetici girişi testleri — gerçek şifre kullanılmaz, test şifresi her seferinde rastgele üretilir."""
import hashlib
import os
import secrets
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _ozet(sifre):
    tuz = os.urandom(16)
    return f"scrypt${tuz.hex()}${hashlib.scrypt(sifre.encode(), salt=tuz, n=2**14, r=8, p=1).hex()}"


def _yonetim(monkeypatch, tmp_path, ozet):
    monkeypatch.chdir(tmp_path)
    if ozet is None:
        monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    else:
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", ozet)
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.sidebar.radio[0].set_value("💼 Yönetim Paneli").run()
    return at


def _giris(at, sifre):
    at.text_input[0].set_value(sifre)
    at.button[0].click().run()
    return at


def test_dogru_sifre_ile_giris(monkeypatch, tmp_path):
    sifre = secrets.token_urlsafe(20)
    at = _giris(_yonetim(monkeypatch, tmp_path, _ozet(sifre)), sifre)
    assert at.session_state.logged_in is True


def test_yanlis_sifre_reddedilir(monkeypatch, tmp_path):
    at = _giris(_yonetim(monkeypatch, tmp_path, _ozet(secrets.token_urlsafe(20))), "yanlis-sifre")
    assert not at.session_state.logged_in
    assert any("Hatalı" in e.value for e in at.error)


def test_kodda_sabit_sifre_yok():
    assert "ADMIN_PASSWORD =" not in Path(APP_PATH).read_text(encoding="utf-8")


def test_ozet_tanimli_degilse_giris_kapali(monkeypatch, tmp_path):
    at = _giris(_yonetim(monkeypatch, tmp_path, None), "herhangi")
    assert not at.session_state.logged_in
    assert any("yapılandırılmamış" in e.value for e in at.error)


def test_bes_hatali_denemeden_sonra_kilitlenir(monkeypatch, tmp_path):
    sifre = secrets.token_urlsafe(20)
    at = _yonetim(monkeypatch, tmp_path, _ozet(sifre))
    for _ in range(5):
        _giris(at, "yanlis")
    _giris(at, sifre)  # doğru şifre bile bu oturumda reddedilmeli
    assert not at.session_state.logged_in
    assert any("Çok fazla" in e.value for e in at.error)
