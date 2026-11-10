---
name: ponytail
description: "Buna gerçekten gerek var mı?" sorgusu. Yeni özellik, yeni bağımlılık, yeni dosya, yeni veritabanı tablosu/kolonu veya soyutlama eklemeden önce kullan. Gereksiz karmaşıklığı önler.
---

# Ponytail: Buna gerçekten gerek var mı?

Bir şey eklemeden önce aşağıdaki soruları sor. Cevapları kullanıcıya 3-5 satırda özetle, sonra karar ver.

## Sorular
1. **Problem gerçek mi?** Kullanıcı bunu istedi mi, yoksa ben mi "iyi olur" diye düşündüm?
2. **Zaten var mı?** `app.py` içinde benzer bir fonksiyon, sekme veya tablo var mı? (ör. `RewardDB`, `PenaltyDB`, `FinanceDB`, `AuditLogDB` hazır modeller.)
3. **Daha küçük çözüm var mı?** Yeni tablo yerine mevcut kolon? Yeni sayfa yerine mevcut sekme? Yeni kütüphane yerine pandas/streamlit?
4. **Bedeli ne?** Bakım yükü, şema migrasyonu, yeni bağımlılık, kullanıcının öğrenmesi gereken yeni ekran.
5. **Hiç yapmasak ne olur?** Cevap "pek bir şey olmaz" ise yapma, öner ve geç.

## Karar
- **Gerek yok** → Yapma. Nedenini bir cümleyle söyle, alternatifi öner.
- **Daha küçüğü yeter** → Küçük olanı yap, büyüğünü sadece not et.
- **Gerek var** → Devam et (büyük işse `superpowers` akışıyla).

## Kırmızı bayraklar
- "İleride lazım olabilir" diye eklenen ayarlar / parametreler.
- Tek kullanım için yazılmış yardımcı sınıflar veya katmanlar.
- Tek dosyalık bu uygulamayı gerekçesiz çok dosyaya bölmek.
- `requirements.txt`'ye tek bir fonksiyon için paket eklemek.
