#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keçdim veb saytı — dizayn fayllarından statik sayt qurur.

Mənbə: ~/Desktop/KEÇDİM/*.dc.html (Claude Design ixracı)
Hədəf: bu qovluq (GitHub Pages → kecdim.pro-tech.az)

🔴 Niyə skript, əl ilə redaktə deyil: dizayn yenidən ixrac oluna bilər. Əl ilə
düzəlişlər növbəti ixracda itərdi. Bu skript hər dəfə eyni qaydaları tətbiq edir:

  1. `<x-dc>` / `<helmet>` qabığını açır — bunlar dizayn alətinin runtime-ıdır
     (`support.js`), real saytda yeri yoxdur. `helmet` məzmunu `<head>`-ə keçir.
  2. Hər səhifəyə ƏSL `<head>` verir: başlıq, təsvir, canonical, OG/Twitter,
     favicon, dil. Dizayn faylında bunların heç biri yoxdur.
  3. Daxili linkləri çevirir: «Keçdim Landing.dc.html» → «/» və s.
  4. 🔴 Mağaza düymələrini REAL linklərlə əvəz edir — dizaynda hamısı «#elaqe»
     saxtasına gedirdi, yəni yükləmə düyməsi işləmirdi.
  5. Mobil üçün responsiv düzəlişlər əlavə edir (dizayn sabit eni işlədir).
  6. Bloq yazılarına Article strukturlaşdırılmış datası qoşur.

İşlətmə:  python3 build.py
"""
import html
import re
import shutil
from pathlib import Path

SRC = Path.home() / "Desktop" / "KEÇDİM"
OUT = Path(__file__).resolve().parent
SITE = "https://kecdim.pro-tech.az"

APP_STORE = "https://apps.apple.com/az/app/ke%C3%A7dim/id6793411739"
PLAY_STORE = "https://play.google.com/store/apps/details?id=az.kecdim"

# ── səhifə xəritəsi: mənbə → (çıxış, başlıq, təsvir, növ) ───────────────────
PAGES = {
    "Keçdim Landing.dc.html": (
        "index.html",
        "Keçdim — Azərbaycanın imtahan hazırlığı platforması",
        "Sürücülük, buraxılış, Dövlət Qulluğu, MİQ, sertifikasiya və magistratura "
        "imtahanlarına real formatda hazırlaş: 2200+ izahlı sual, sınaq imtahanları, fərdi plan.",
        "website"),
    "Keçdim Bloq.dc.html": (
        "bloq.html",
        "Bloq — imtahana hazırlıq strategiyaları | Keçdim",
        "Sürücülükdən magistraturaya: keçmək üçün lazım olan strategiyalar, qaydalar "
        "və məsləhətlər. Hamısı Azərbaycan dilində.",
        "website"),
    "bloq-dyp-10-sehv.dc.html": (
        "bloq-dyp-10-sehv.html",
        "DYP imtahanında ən çox səhv edilən 10 sual — və niyə | Keçdim",
        "«Dayanmaq» və «durmaq» fərqindən dəmiryolu keçidindəki məsafələrə qədər — "
        "namizədlərin ən çox büdrədiyi suallar izahları ilə.",
        "article"),
    "bloq-dq-alt-qruplar.dc.html": (
        "bloq-dq-alt-qruplar.html",
        "AA-dan BB-yə: Dövlət Qulluğu alt-qrupları arasındakı fərq | Keçdim",
        "Dövlət Qulluğu imtahanının AA, AB, AC, BA və BB alt-qrupları: sual bölgüsü, "
        "müddət və keçid həddi necə fərqlənir.",
        "article"),
    "bloq-5-verdis.dc.html": (
        "bloq-5-verdis.html",
        "İlk dəfədən keçənlərin 5 vərdişi | Keçdim",
        "İmtahandan ilk cəhddə keçən namizədlərin ortaq hazırlıq vərdişləri — "
        "praktik və təkrarlana bilən strategiya.",
        "article"),
    "bloq-vaxt-bolgusu.dc.html": (
        "bloq-vaxt-bolgusu.html",
        "İmtahan günü vaxtı necə bölməli: sual-vaxt düsturu | Keçdim",
        "Sual sayına görə vaxt bölgüsü, hansı suala nə qədər vaxt ayırmaq və "
        "ilişəndə nə etmək lazımdır.",
        "article"),
    "bloq-mentiq-taktika.dc.html": (
        "bloq-mentiq-taktika.html",
        "Məntiq bölməsində vaxt itirməmək: 3 sual tipi, 3 taktika | Keçdim",
        "Məntiq suallarının əsas tipləri və hər biri üçün ən sürətli həll yolu.",
        "article"),
    "bloq-miq-metodika.dc.html": (
        "bloq-miq-metodika.html",
        "Metodika sualları: kurikulumun 7 açar anlayışı | Keçdim",
        "MİQ və sertifikasiya imtahanlarının metodika bölməsində təkrarlanan "
        "kurikulum anlayışları.",
        "article"),
    "bloq-yol-nisanlari.dc.html": (
        "bloq-yol-nisanlari.html",
        "Yol nişanlarını yadda saxlamağın asan yolu: qruplarla öyrən | Keçdim",
        "Xəbərdarlıq, qadağan, məcburi və məlumatverici nişanlar — forma və rəngə "
        "görə qruplaşdıraraq yadda saxla.",
        "article"),
}

# ── link çevirmələri ────────────────────────────────────────────────────────
LINKS = {
    "Keçdim Landing.dc.html": "/",
    "Keçdim Bloq.dc.html": "/bloq.html",
    "https://kecdim.pro-tech.az/privacy": "/privacy.html",
    "https://kecdim.pro-tech.az/terms": "/terms.html",
}

RESPONSIVE = """
/* Dizayn masaüstü üçün sabit ölçülərlə qurulub; telefonda daralsın. */
@media (max-width:820px){
  [style*="padding:88px 32px"],[style*="padding:64px 32px"],[style*="padding:16px 32px"],
  [style*="padding:40px 32px"],[style*="padding:0 32px"]{padding-left:20px!important;padding-right:20px!important}
  [style*="font:800 58px"]{font-size:38px!important;line-height:1.12!important}
  [style*="font:800 44px"]{font-size:32px!important}
  [style*="font:800 36px"]{font-size:27px!important}
  [style*="font:800 34px"]{font-size:26px!important}
  [style*="font:800 32px"]{font-size:25px!important}
  [style*="min-width:380px"],[style*="min-width:340px"],[style*="min-width:320px"],
  [style*="min-width:300px"]{min-width:100%!important}
  [style*="padding:64px 48px"]{padding:40px 22px!important}
  [style*="padding:44px 44px 44px"]{padding:28px 22px!important}
}
@media (max-width:600px){
  nav a,[style*="gap:26px"]{gap:14px!important}
  [style*="width:340px"]{width:100%!important}
}
/* Klaviatura ilə gəzənlər üçün görünən fokus — dizaynda yox idi. */
a:focus-visible{outline:3px solid #16A34A;outline-offset:3px;border-radius:6px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

FAVICON = (
    '<link rel="icon" href="data:image/svg+xml,'
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%2316A34A'/%3E"
    "%3Cpath d='M8 17l5 5L24 10' stroke='white' stroke-width='4' fill='none' "
    "stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\">"
)


def convert(src_name: str) -> str:
    out_name, title, desc, kind = PAGES[src_name]
    raw = (SRC / src_name).read_text(encoding="utf-8")

    # 1) helmet məzmununu ayır, x-dc qabığını at
    helmet = ""
    m = re.search(r"<helmet>(.*?)</helmet>", raw, re.S)
    if m:
        helmet = m.group(1).strip()
        raw = raw.replace(m.group(0), "")
    body = re.search(r"<x-dc>(.*?)</x-dc>", raw, re.S)
    body = body.group(1).strip() if body else raw

    # 2) daxili linkləri çevir (uzun adlar əvvəl — qismən uyğunluq olmasın)
    for old, new in sorted(LINKS.items(), key=lambda kv: -len(kv[0])):
        body = body.replace(f'href="{old}"', f'href="{new}"')
        body = body.replace(f'href="{old}#', f'href="{new}#')
    body = re.sub(r'href="bloq-([a-z0-9-]+)\.dc\.html"', r'href="/bloq-\1.html"', body)
    # «/#yukle» kimi qalıqları düzəlt
    body = body.replace('href="/#', 'href="/#')

    # 3a) 🔴 Apple loqosu: dizaynda U+F8FF () işlədilib — bu, Apple-a məxsus
    #     şəxsi istifadə simvoludur və YALNIZ Apple cihazlarında görünür.
    #     Android/Windows brauzerlərində düymə boş qalırdı. SVG ilə əvəz olunur.
    # Dizaynda bu span BOŞ buraxılıb (Apple loqosu qoyulmayıb) — düymə «Yüklə /
    # App Store» yazısı ilə loqosuz görünürdü. Rəsmi Apple loqosu ora yerləşdirilir.
    body = body.replace(
        '<span style="font-size:22px"></span>',
        '<svg width="20" height="24" viewBox="0 0 384 512" fill="currentColor" aria-hidden="true">'
        '<path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7'
        '-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2'
        '25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2'
        'c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/></svg>')
    # Google Play üçün rəsmi üçbucaq loqo (dizaynda sadə «▶» idi)
    body = body.replace(
        '<span style="font-size:20px">▶</span>',
        '<svg width="20" height="22" viewBox="0 0 512 512" aria-hidden="true">'
        '<path fill="#EA4335" d="M48 59.5v393c0 5.7 6.5 9.2 11.3 6.1l204.6-196.4-204.6-208.8C54.5 50.3 48 53.8 48 59.5z"/>'
        '<path fill="#FBBC04" d="M389.5 226.5l-79.7-45.7-89.4 85.4 89.4 85.8 79.7-45.7c22.4-12.8 22.4-67 0-79.8z"/>'
        '<path fill="#4285F4" d="M59.3 52.4l250.5 128.4-89.4 85.4z"/>'
        '<path fill="#34A853" d="M59.3 459.6l161.1-193.4 89.4 85.8z"/></svg>')

    # 3) 🔴 mağaza düymələri: dizaynda hamısı «#elaqe»yə gedirdi
    body = re.sub(
        r'href="#elaqe"((?:(?!</a>).)*?App Store)',
        lambda mm: f'href="{APP_STORE}" target="_blank" rel="noopener"{mm.group(1)}',
        body, flags=re.S)
    body = re.sub(
        r'href="#elaqe"((?:(?!</a>).)*?Google Play)',
        lambda mm: f'href="{PLAY_STORE}" target="_blank" rel="noopener"{mm.group(1)}',
        body, flags=re.S)

    canonical = SITE + ("/" if out_name == "index.html" else "/" + out_name)
    ld = ""
    if kind == "article":
        ld = (
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Article",'
            f'"headline":{html.escape(title.split(" | ")[0])!r},'.replace("'", '"')
            + f'"description":"{desc}","inLanguage":"az-AZ",'
            f'"mainEntityOfPage":"{canonical}",'
            '"publisher":{"@type":"Organization","name":"Protech LLC",'
            '"url":"https://pro-tech.az"}}</script>'
        )
    else:
        ld = (
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"MobileApplication",'
            '"name":"Keçdim","applicationCategory":"EducationalApplication",'
            '"operatingSystem":"iOS, Android","inLanguage":"az-AZ",'
            f'"description":"{desc}",'
            f'"downloadUrl":["{APP_STORE}","{PLAY_STORE}"],'
            '"offers":{"@type":"Offer","price":"0","priceCurrency":"AZN"},'
            '"publisher":{"@type":"Organization","name":"Protech LLC",'
            '"url":"https://pro-tech.az"}}</script>'
        )

    head = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#16A34A">
{FAVICON}
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="Keçdim">
<meta property="og:locale" content="az_AZ">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
{helmet}
<style>{RESPONSIVE}</style>
{ld}"""

    return f"""<!DOCTYPE html>
<html lang="az">
<head>
{head}
</head>
<body>
{body}
</body>
</html>
"""


def main() -> None:
    written = []
    for src in PAGES:
        if not (SRC / src).exists():
            raise SystemExit(f"🔴 mənbə yoxdur: {src}")
        out = PAGES[src][0]
        (OUT / out).write_text(convert(src), encoding="utf-8")
        written.append(out)

    # sitemap + robots
    urls = [SITE + "/"] + [
        SITE + "/" + p[0] for p in PAGES.values() if p[0] != "index.html"
    ] + [SITE + "/privacy.html", SITE + "/support.html", SITE + "/terms.html"]
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (OUT / "sitemap.xml").write_text(sm, encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    print(f"✅ {len(written)} səhifə quruldu: {', '.join(written)}")
    print(f"   + sitemap.xml ({len(urls)} URL) + robots.txt")


if __name__ == "__main__":
    main()
