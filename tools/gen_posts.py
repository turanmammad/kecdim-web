#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""posts_data.py-dakı yazıları bloq-dyp-10-sehv.html şablonundan HTML-ə çevirir,
bloq.html siyahısına və sitemap.xml-ə əlavə edir. İdempotentdir (təkrar işlədilsə ikiqat yazmır)."""
import re, html, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from posts_data import POSTS
R = Path(__file__).resolve().parent.parent
SITE = "https://kecdim.pro-tech.az"
DATE_HUMAN = "20 oktyabr 2026"; DATE_ISO = "2026-10-20"
tpl = (R / "bloq-dyp-10-sehv.html").read_text(encoding="utf-8")
CAT_COLOR = {"SÜRÜCÜLÜK":"#16A34A"}
H = lambda s: html.escape(s, quote=True)

def article_body(p):
    parts = [f'<span style="font:600 12px Inter;color:#16A34A;letter-spacing:.5px">{H(p["cat"])}</span>',
      f'<div style="font:800 34px/1.25 Manrope,sans-serif;margin-top:14px;letter-spacing:-.5px;text-wrap:pretty">{H(p["title"])}</div>',
      f'<div style="display:flex;align-items:center;gap:12px;margin-top:18px;font:500 13px Inter;color:#6B7671"><span style="width:34px;height:34px;border-radius:50%;background:rgba(22,163,74,.12);display:flex;align-items:center;justify-content:center;font:800 14px Manrope,sans-serif;color:#15803D">K</span><span>Keçdim komandası</span><span>·</span><span>{p["min"]} dəq oxu</span><span>·</span><span>{DATE_HUMAN}</span></div>',
      f'<div style="font:400 16px/1.75 Inter;color:#3C453F;margin-top:28px">{p["intro"]}</div>']
    for i,(h,t) in enumerate(p["secs"]):
        mt = 32 if i == 0 else 28
        parts.append(f'<div style="font:800 22px Manrope,sans-serif;margin-top:{mt}px">{h}</div>')
        parts.append(f'<div style="font:400 16px/1.75 Inter;color:#3C453F;margin-top:12px">{t}</div>')
    parts.append(f'<div style="background:rgba(22,163,74,.07);border-left:3px solid #16A34A;border-radius:0 14px 14px 0;padding:18px 22px;margin-top:24px;font:500 15px/1.65 Inter">{p["box"]}</div>')
    if p["disc"]:
        parts.append(f'<div style="font:400 13px/1.6 Inter;color:#6B7671;margin-top:20px">{H(p["disc"])}</div>')
    parts.append('<div style="background:radial-gradient(130% 160% at 20% 15%,#1FB25A 0%,#16A34A 62%,#149244 100%);border-radius:18px;padding:28px 32px;margin-top:36px;display:flex;align-items:center;gap:20px;flex-wrap:wrap">'
      '<div style="flex:1;min-width:240px"><div style="font:800 19px Manrope,sans-serif;color:#FFFFFF">Real formatda məşq et</div><div style="font:400 13px Inter;color:rgba(255,255,255,.85);margin-top:4px">İzahlı suallar, sınaq imtahanları, pulsuz başlanğıc.</div></div>'
      '<a href="/#yukle" style="padding:13px 26px;background:#FFFFFF;border-radius:12px;font:600 14px Inter;color:#15803D;flex:none">Tətbiqi yüklə</a></div>')
    inner = "\n".join(parts)
    return ('<!-- M1 -->\n<div id="m1" style="max-width:1120px;margin:0 auto;padding:48px 32px 0;scroll-margin-top:80px">\n'
      '<div style="background:#FFFFFF;border-radius:24px;box-shadow:0 2px 16px rgba(28,35,33,.07);padding:56px 0">\n'
      '<div style="max-width:680px;margin:0 auto;padding:0 32px">\n' + inner + '\n</div>\n</div>\n</div>\n\n\n')

def related(p):
    same = [q for q in POSTS if q is not p and q["cat"] == p["cat"]]
    other = [q for q in POSTS if q is not p and q["cat"] != p["cat"]]
    pick = (same + other)[:3]
    a = lambda u,t: f'<a href="{u}" style="display:block;padding:14px 16px;border:1px solid #E4E8E2;border-radius:14px;background:#FFF;color:#1C2321;font:600 14px Inter,sans-serif;line-height:1.45">{H(t)}</a>'
    links = "".join(a(f'/bloq-{q["slug"]}.html', q["title"]) for q in pick)
    return ('<section class="kd-related" style="max-width:760px;margin:8px auto 40px;padding:0 20px"><div style="font:700 15px Manrope,sans-serif;margin:0 0 12px">Oxşar yazılar</div><div style="display:grid;gap:10px">'
      + links + '</div><div style="margin-top:14px;font:500 13px Inter,sans-serif"><a href="/bloq.html">← Bütün yazılar</a> · <a href="/#yukle">Keçdim-i yüklə</a></div></section>')

def build(p):
    url = f'{SITE}/bloq-{p["slug"]}.html'
    s = tpl
    s = s.replace("DYP imtahanında ən çox səhv edilən 10 sual — və niyə", H(p["title"]))
    s = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1)+H(p["desc"]), s)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1)+H(p["desc"]), s)
    s = s.replace("https://kecdim.pro-tech.az/bloq-dyp-10-sehv.html", url)
    s = re.sub(r'"description":"[^"]*"', lambda m: '"description":'+__import__("json").dumps(p["desc"],ensure_ascii=False), s, count=1)
    s = s.replace('"inLanguage":"az-AZ"', f'"inLanguage":"az-AZ","datePublished":"{DATE_ISO}","dateModified":"{DATE_ISO}","author":{{"@type":"Organization","name":"Keçdim"}}',1)
    a = s.index("<!-- M1"); b = s.index("<!-- FOOTER -->")
    s = s[:a] + article_body(p) + s[b:]
    s = re.sub(r'<section class="kd-related".*?</section>', lambda m: related(p), s, flags=re.S)
    return s

# 1) yazılar
for p in POSTS:
    (R / f'bloq-{p["slug"]}.html').write_text(build(p), encoding="utf-8")

# 2) bloq.html siyahısı
bl = (R / "bloq.html").read_text(encoding="utf-8")
if "<!--NEWPOSTS-->" in bl:
    bl = re.sub(r"<!--NEWPOSTS-->.*?<!--/NEWPOSTS-->", "", bl, flags=re.S)
rows = []
for p in POSTS:
    rows.append(f'<a href="/bloq-{p["slug"]}.html" style="display:flex;align-items:center;gap:18px;padding:18px 0;color:#1C2321">'
      f'<span style="width:118px;flex:none;font:600 10.5px Inter,sans-serif;color:#16A34A;letter-spacing:.5px">{H(p["cat"])}</span>'
      f'<span style="flex:1;font:600 15px/1.4 Inter,sans-serif">{H(p["title"])}</span>'
      f'<span style="font:400 12px Inter,sans-serif;color:#9AA49D;flex:none">{p["min"]} dəq · {DATE_HUMAN}</span>'
      '<span style="color:#16A34A;font:600 15px Inter,sans-serif;flex:none">→</span></a>')
block = "<!--NEWPOSTS-->\n" + "\n".join(rows) + "\n<!--/NEWPOSTS-->\n"
m = bl.index("<!-- NEWSLETTER -->")
# siyahının bağlayıcı </div></div>-dən əvvələ qoy
close = bl.rfind("</div>", 0, m); close = bl.rfind("</div>", 0, close)
bl = bl[:close] + block + bl[close:]
(R / "bloq.html").write_text(bl, encoding="utf-8")

# 3) sitemap
sm = (R / "sitemap.xml").read_text(encoding="utf-8")
for p in POSTS:
    u = f'{SITE}/bloq-{p["slug"]}.html'
    if u not in sm:
        sm = sm.replace("</urlset>", f'  <url><loc>{u}</loc><lastmod>{DATE_ISO}</lastmod></url>\n</urlset>')
(R / "sitemap.xml").write_text(sm, encoding="utf-8")
print(len(POSTS), "yazı yazıldı")
