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

## NOVA Ajan Ekibi

### Hazır ajanlar (Claude Code ile gelir)
- `Explore` — geniş kod araması (salt okunur). Kod nerede, hangi dosyada sorularında.
- `Plan` — büyük işler için uygulama planı (salt okunur).
- `general-purpose` — birden fazla adımlı araştırma/görevler.

### Nova uzman ajanları
| Ajan | Görev | Yazabildiği yer |
|---|---|---|
| `nova-satis-stok` | Satış, stok, kâr, komisyon, mükerrer kayıt kontrolü | `analiz/`, `raporlar/` |
| `nova-panel-yazilim` | Bayi/ajans paneli geliştirme ve hata düzeltme | Uygulama kodu (`app.py` ve panel kodu) |
| `nova-test-kalite` | Satış, stok, fiyat, yetki, ödeme akışı testleri | `tests/`, `requirements-dev.txt`, `pytest.ini` |
| `nova-guvenlik` | Yetki, veri güvenliği, gizli bilgi denetimi | Hiçbir yer (yalnızca inceleme) |
| `nova-web-sitesi` | Nova Medya sitesi, başvuru formu, mobil görünüm | Site dosyaları (`site/` veya site reposu) |
| `nova-icerik-marka` | Reklam, duyuru, site ve sosyal medya metinleri | `icerik/` (taslak) |

Panel reposuna özel önceki ajanlar da duruyor: `kod-inceleyici`, `guvenlik-denetcisi` (salt okunur), `test-yazici` (`tests/`), `veri-uzmani` ve `streamlit-tasarimci` (`app.py`).

### Aynı dosyada çakışmayı önleme (ana oturum için kurallar)
1. Her dosyanın tek sahibi var (yukarıdaki tablo). Sahibi olmayan ajan o dosyayı düzenlemez; değişikliği öneri/diff olarak raporlar, sahibi uygular.
2. Uygulama kodunu (`app.py`) yazabilen ajanlar — `nova-panel-yazilim`, `streamlit-tasarimci`, `veri-uzmani` — **aynı anda çalıştırılmaz**; sırayla çalışır.
3. `tests/` yazabilen ajanlar — `nova-test-kalite`, `test-yazici` — aynı anda çalıştırılmaz.
4. Yazan iki ajan paralel çalışacaksa ayrı git worktree'de başlatılır (Agent aracında `isolation: "worktree"`), sonuçlar ana oturumda tek tek birleştirilir.
5. Salt okunur ajanlar (`Explore`, `Plan`, `nova-guvenlik`, `kod-inceleyici`, `guvenlik-denetcisi`) her zaman paralel çalışabilir.

### Onay gerektiren işlemler (kullanıcıya sormadan YAPILMAZ)
- Canlıya alma / deploy, `main`'e birleştirme
- Veritabanı şeması değişikliği
- Gerçek satış veya stok kaydı oluşturma, değiştirme, silme
- Fiyat, komisyon, tier eşiği, hakediş formülü değişikliği
- Dışarıya mesaj, e-posta, DM, webhook gönderme; sosyal medyada yayın
- Yeni erişim yetkisi verme (kullanıcı, rol, API anahtarı, GitHub/servis izni)
- Dışarıdan eklenti, skill veya ajan kurma

### Veri ve gizlilik
- Testlerde gerçek müşteri/yayıncı verisi ve gerçek `*.db` kullanılmaz; uydurma veri + geçici dizin.
- Şifre, token, API anahtarı, bağlantı dizesi hiçbir çıktıya, rapora, log'a, commit'e yazılmaz; sadece `dosya:satır` ve türü belirtilir.
- Raporlarda kişisel veri maskelenir (telefon `05** *** **12`, ID son 4 hane).
