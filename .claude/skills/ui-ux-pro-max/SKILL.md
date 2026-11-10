---
name: ui-ux-pro-max
description: Arayüzü şablon gibi değil, tasarımcı işi gibi gösterir. Streamlit sayfası, sekme, kart, form, dashboard veya CSS ile ilgili her işte kullan.
---

# UI UX Pro Max (Nova Agency için)

## Önce: marka sistemini koru
Uygulamanın kimliği lacivert + altın. Yeni renk uydurma, bu token'ları kullan:

| Rol | Renk |
|---|---|
| Arka plan | `#061A4A` (kart içi `#0A225C`) |
| Yüzey / kart | `#0F2D75` |
| Vurgu (altın) | `#D4AF37`, hover `#F3C643` |
| Metin | `#FFFFFF`, ikincil `rgba(255,255,255,.7)` |
| Başarı / uyarı / hata | `#2ECC71` / `#F1C40F` / `#E74C3C` |

Mevcut `.metric-card`, `.pub-card` ve `.info-card` sınıflarını tekrar kullan; yeni stil gerekiyorsa aynı `<style>` bloğuna ekle.

## Şablon görüntüsünden kaçınma kuralları
1. **Hiyerarşi:** Her ekranda tek bir ana mesaj. Büyük sayı (KPI) → kısa etiket → detay. `st.metric` ile KPI satırı, altına detay.
2. **Boşluk:** Her şeyi alt alta yığma. `st.columns` ile gruplandır, gruplar arası `st.divider()` yerine boşluk tercih et.
3. **Tutarlılık:** Kart köşe yarıçapı 12px, iç boşluk 18–20px, sol altın kenarlık sadece "öne çıkan" kartlarda.
4. **Az emoji:** Sekme başlıklarında var, içerikte her satıra emoji koyma.
5. **Boş durumlar:** Veri yoksa boş tablo gösterme; ne yapılacağını söyleyen kısa bir mesaj + aksiyon butonu.
6. **Sayı formatı:** Binlik ayırıcı (`{x:,}`), para `$12.50`, yüzde `%85`. Tablo kolonlarında `st.column_config` (ProgressColumn, NumberColumn) kullan.
7. **Geri bildirim:** Her form gönderiminde `st.success`/`st.error`; uzun işlemde `st.spinner`.
8. **Mobil:** Yayıncılar telefondan bakar. 3'ten fazla kolonu yayıncı portalında kullanma; uzun tablolar yerine kartlar.
9. **Erişilebilirlik:** Altın metni sadece koyu zeminde kullan; metin/zemin kontrastı en az 4.5:1.

## Güvenlik
`unsafe_allow_html=True` ile HTML üretirken kullanıcıdan gelen her değeri (`name`, `uid`, `contact_info`) `html.escape()` ile kaçır.

## Bitiş kontrolü
- `streamlit run app.py` ile sayfayı aç, mümkünse Playwright ile masaüstü (1280px) ve telefon (390px) ekran görüntüsü al ve kendin bak.
- Boş veri ve dolu veri durumlarını ikisini de kontrol et.
