# CLAUDE.md — Nova Agency Panel

Bu dosya Claude'un bu repoda nasıl çalışacağını belirler (Karpathy tarzı "tek dosya" kuralları).

## Proje
- Tek dosyalık Streamlit uygulaması: `app.py` (SQLAlchemy + SQLite, pandas, openpyxl).
- Çalıştırma: `pip install -r requirements.txt && streamlit run app.py` (port 8501).
- Veritabanı: `nova_agency_enterprise.db` (ilk çalıştırmada `database_migration()` oluşturur). Bu dosyayı commit etme.
- Arayüz dili Türkçe. Kullanıcıya Türkçe cevap ver.

## Çalışma kuralları

### 1. Kodlamadan önce düşün
- Varsayımlarını açıkça yaz. Emin değilsen tahmin etme, sor.
- Birden fazla yorum varsa seçenekleri göster; sessizce birini seçme.
- Daha basit bir yol varsa söyle.

### 2. Önce sadelik
- İsteneni çözen en az kodu yaz. İstenmeyen özellik, soyutlama veya "ileride lazım olur" ayarı ekleme.
- 200 satırlık çözüm 50 satıra iniyorsa yeniden yaz.
- Yeni kütüphane eklemeden önce mevcutlarla (streamlit, pandas, sqlalchemy) yapılabiliyor mu bak.

### 3. Cerrahi değişiklik
- Sadece görevle ilgili satırlara dokun. Komşu kodu "iyileştirme", yeniden biçimlendirme.
- Mevcut stile uy (Türkçe etiketler, emoji'li sekme başlıkları, `get_db()` + `try/finally db.close()` deseni).
- Senin değişikliğinin yarattığı kullanılmayan kodu temizle; önceden var olan ölü kodu sadece söyle.

### 4. Hedef odaklı çalış ve doğrula
- Görevi doğrulanabilir hedefe çevir: "X'i düzelt" → "X'i tekrar üreten adım + düzeldiğini gösteren kontrol".
- Her değişiklikten sonra en azından `python -m py_compile app.py` çalıştır; mümkünse `streamlit run app.py` ile sayfayı aç ve ilgili sekmeyi dene.
- "Bitti" demeden önce neyi doğruladığını, neyi doğrulayamadığını açıkça yaz.

## Güvenlik notları
- Sırları (şifre, API anahtarı) koda yazma; `st.secrets` veya ortam değişkeni kullan.
- Kullanıcı girdisini `unsafe_allow_html=True` olan HTML'e koymadan önce `html.escape` ile kaçır.

## Skill'ler (`.claude/skills/`)
- `superpowers` — her özellik/hata için Plan → Test → Kod akışı.
- `ponytail` — kod yazmadan önce "buna gerçekten gerek var mı?" sorgusu.
- `ui-ux-pro-max` — arayüz işlerinde şablon değil, tasarımcı işi gibi görünen ekranlar.
- `caveman` — `/caveman` ile çok kısa cevap modu (token tasarrufu).

## Ajanlar (`.claude/agents/`)
- `kod-inceleyici` — commit öncesi hata/sadelik incelemesi (salt okunur).
- `guvenlik-denetcisi` — sırlar, HTML enjeksiyonu, kişisel veri sızıntısı denetimi (salt okunur).
- `test-yazici` — pytest + Streamlit AppTest; testler gerçek veritabanına yazmaz.
- `veri-uzmani` — Excel içe/dışa aktarma, pandas, şema migrasyonu.
- `streamlit-tasarimci` — boş sekmeleri ve ekranları `ui-ux-pro-max` kurallarıyla tasarlar.

Önerilen akış: `superpowers` planı → `test-yazici` → kod (`veri-uzmani` / `streamlit-tasarimci`) → `kod-inceleyici` + `guvenlik-denetcisi`.
