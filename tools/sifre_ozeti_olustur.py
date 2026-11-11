"""Yönetici şifresi için scrypt özeti üretir.

Kullanım:  python tools/sifre_ozeti_olustur.py
Şifre ekranda görünmeden sorulur; çıktı sadece özettir. Çıktıyı
Streamlit Cloud > App > Settings > Secrets'a (yerelde .streamlit/secrets.toml)
ADMIN_PASSWORD_HASH = "..." satırı olarak ekle. Şifrenin kendisini hiçbir yere yazma.
"""
import getpass
import hashlib
import os

sifre = getpass.getpass("Yeni yönetici şifresi (en az 16 karakter): ")
if len(sifre) < 16:
    raise SystemExit("Şifre en az 16 karakter olmalı.")
if sifre != getpass.getpass("Tekrar: "):
    raise SystemExit("Şifreler eşleşmiyor.")
tuz = os.urandom(16)
ozet = hashlib.scrypt(sifre.encode(), salt=tuz, n=2**14, r=8, p=1)
print(f'ADMIN_PASSWORD_HASH = "scrypt${tuz.hex()}${ozet.hex()}"')
