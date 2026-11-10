from PIL import Image, ImageDraw, ImageFont
import textwrap
W,H=1080,1920
NAVY=(6,26,74); NAVY2=(15,45,117); GOLD=(212,175,55); WHITE=(255,255,255); SOFT=(200,210,235)
B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def f(p,s): return ImageFont.truetype(p,s)
slaytlar=[
 ("SESLİ ODA", "Yayıncısının bir günü", "Kamera yok. Deneyim şart değil."),
 ("01", "Yayın saatini ekibinle birlikte planlarsın", None),
 ("02", "Akış hazır: konu, soru, küçük etkinlikler", None),
 ("03", "Kamera açmazsın. Sadece sesinle yayın yaparsın.", None),
 ("04", "Yayından sonra neyin işe yaradığına birlikte bakarsınız", None),
 ("TAKİP ET", "Yarın: ilk 5 dakikada odayı nasıl ısıtırsın?", "Başvuru için DM"),
]
def ciz(i,ust,ana,alt):
    im=Image.new("RGB",(W,H),NAVY); d=ImageDraw.Draw(im)
    for y in range(H):  # hafif dikey gradyan
        t=y/H; c=tuple(int(NAVY[k]*(1-t)+NAVY2[k]*t*0.6+NAVY[k]*t*0.4) for k in range(3)); d.line([(0,y),(W,y)],fill=c)
    d.rectangle([90,150,110,330],fill=GOLD)
    d.text((140,150),"NOVA MEDYA",font=f(B,46),fill=GOLD)
    d.text((140,215),"Yayıncı gelişim ajansı",font=f(R,34),fill=SOFT)
    # ilerleme çubuğu
    n=len(slaytlar); gw=(W-180-(n-1)*14)/n
    for k in range(n):
        x=90+k*(gw+14); d.rounded_rectangle([x,90,x+gw,100],radius=5,fill=GOLD if k<=i else (60,80,130))
    y=700
    big=ust.isdigit()
    d.text((90,y),ust,font=f(B,190 if big else 120),fill=GOLD); y+= 240 if big else 170
    for line in textwrap.wrap(ana,width=17):
        d.text((90,y),line,font=f(B,92),fill=WHITE); y+=118
    if alt:
        y+=40; d.text((90,y),alt,font=f(R,52),fill=SOFT)
    d.text((90,H-200),"Başvuru ücretsiz · 18 yaş ve üzeri",font=f(R,36),fill=SOFT)
    d.text((90,H-150),"Kazanç garanti edilmez",font=f(R,36),fill=SOFT)
    im.save(f"s{i}.png")
for i,s in enumerate(slaytlar): ciz(i,*s)
print(len(slaytlar))
