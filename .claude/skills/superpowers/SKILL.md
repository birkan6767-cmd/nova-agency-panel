---
name: superpowers
description: Kıdemli yazılımcı çalışma düzeni — Plan → Test → Kod. Yeni özellik eklerken, hata düzeltirken veya app.py'de birkaç satırdan büyük her değişiklikte kullan. Tek satırlık yazım düzeltmeleri için gerekmez.
---

# Superpowers: Plan → Test → Kod

Kod yazmaya hemen başlama. Bu üç adımı sırayla uygula.

## 1. Plan
Kodlamadan önce kısa bir plan yaz ve kullanıcıya göster:
- **Hedef:** Tek cümle; "bitti" ne demek?
- **Etkilenen yerler:** `app.py` içindeki fonksiyon/sekme/model adları (örn. `tabs[6] # FİNANS`, `FinanceDB`).
- **Adımlar:** Numaralı, her biri doğrulanabilir küçük adımlar.
- **Riskler:** Veritabanı şeması değişiyor mu? (değişiyorsa `database_migration()` güncellenmeli), mevcut veri bozulur mu?
- **Açık sorular:** Belirsiz bir şey varsa burada sor ve cevabı bekle.

Büyük veya belirsiz işlerde planı onaylatmadan kodlamaya geçme.

## 2. Test (önce)
Değişikliği yapmadan önce doğrulama yolunu kur:
- Saf mantık (ör. `tier_calculator`, `target_calculator`, hakediş hesabı) için `tests/` altında pytest testi yaz; önce **kırmızı** olduğunu gör.
- Arayüz davranışı için Streamlit'in `streamlit.testing.v1.AppTest` aracını kullan:
  ```python
  from streamlit.testing.v1 import AppTest
  at = AppTest.from_file("app.py").run()
  assert not at.exception
  ```
- Hata düzeltmede: önce hatayı tekrar üreten testi yaz.

Testler geçici bir SQLite dosyası kullanmalı; gerçek `nova_agency_enterprise.db`'ye yazmamalı.

## 3. Kod
- Planı adım adım uygula; her adımdan sonra testleri çalıştır.
- Sadece planda olan yerlere dokun.
- Bitince: `python -m py_compile app.py` + `pytest -q` (varsa) çalıştır.

## Bitiş raporu
- Ne değişti (dosya:satır).
- Hangi testler geçti — çıktı ile.
- Doğrulanamayan kısımlar (açıkça).
