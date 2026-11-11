"""Platform kalıcılık testi — CANLI UYGULAMADAN AYRI, tek kullanımlık bir test uygulaması.

Streamlit Community Cloud'da (veya başka bir sunucuda) bu dosyayı AYRI bir uygulama
olarak yayınla (Main file path: tools/kalicilik_testi.py). Gerçek veri içermez.

Ekranda iki değer görünür:
  - Test dosyası oluşturulma zamanı: dosya silinirse değişir.
  - Sunucu süreci başlangıç zamanı: uygulama yeniden başlarsa değişir.

Sırayla şu işlemleri yap, her birinden sonra sayfayı yenileyip iki değeri not et:
  1. Bu dosyada bir yorum satırını değiştirip GitHub'a gönder (kod güncellemesi).
  2. Test uygulamasının Settings > Secrets bölümüne TEST = "1" ekle (Secrets değişikliği).
  3. Manage app > Reboot (yeniden başlatma).
Sonuç, canlı uygulamada hangi işlemin veritabanını silebileceğini gösterir.
Test bitince test uygulamasını sil.
"""
import sqlite3
from datetime import datetime, timezone

import streamlit as st

DOSYA = "kalicilik_testi.db"  # .gitignore'daki *.db kuralıyla repoya girmez


@st.cache_resource
def surec_baslangici():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


con = sqlite3.connect(DOSYA)
con.execute("CREATE TABLE IF NOT EXISTS t (olusturma TEXT, sayac INTEGER)")
if con.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0:
    con.execute("INSERT INTO t VALUES (?, 0)", (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
    con.commit()

st.title("Kalıcılık testi")
if st.button("Sayaç +1"):
    con.execute("UPDATE t SET sayac = sayac + 1")
    con.commit()
olusturma, sayac = con.execute("SELECT olusturma, sayac FROM t").fetchone()
con.close()

st.write(f"**Test dosyası oluşturulma zamanı (UTC):** {olusturma}")
st.write(f"**Sayaç:** {sayac}")
st.write(f"**Sunucu süreci başlangıç zamanı (UTC):** {surec_baslangici()}")
st.caption("Oluşturulma zamanı veya sayaç sıfırlandıysa dosya silinmiş demektir.")
