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

# ── Google Analytics 4 ──────────────────────────────────────────────────────
# 🔴 Keçdim üçün GA4 mülkiyyəti HƏLƏ YOXDUR. 22.08.2026-da yaratmağa cəhd edildi:
#   • `ai-agent-office@ai-agent-office-492519` SA GA hesablarını GÖRÜR
#     (Hesabli, EmlakPro, Cashera, Ucuztap), amma mülkiyyət yaratmaqda 403 —
#     onda yalnız oxu icazəsi var, Editor lazımdır.
#   • GA4 Admin API ümumiyyətlə HESAB yarada bilmir (yalnız UI).
#   • Başqa məhsulun mülkiyyətini işlətmək datanı qarışdırardı — edilmədi.
#
# Açmaq üçün İKİ yoldan biri (hər ikisi ~1 dəqiqə):
#   A) analytics.google.com → «Keçdim» hesabı + mülkiyyət yarat → Measurement ID
#      (G-XXXXXXXXXX) götür və aşağıya yaz.
#   B) Mövcud GA hesabına `ai-agent-office@ai-agent-office-492519.iam.gserviceaccount.com`
#      ünvanını **Editor** kimi əlavə et — qalanını skript özü edər.
#
# ID yazılmayana qədər səhifələrə HEÇ BİR sayğac qoyulmur (boş/sınıq teq yox).
GA_ID = ""   # məsələn: "G-XXXXXXXXXX"

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

    ga = ""
    if GA_ID:
        # Async gtag.js. GA4-də IP anonimləşdirmə standartdır; əlavə olaraq
        # reklam siqnalları söndürülür — sayt yalnız auditoriya ölçür.
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>'
              '<script>window.dataLayer=window.dataLayer||[];'
              'function gtag(){dataLayer.push(arguments)}gtag("js",new Date());'
              f'gtag("config","{GA_ID}",{{"anonymize_ip":true,"allow_google_signals":false}});</script>')

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
{ga}
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



# ── YENİ BLOQ YAZILARI ──────────────────────────────────────────────────────
# 🔴 Bunlar dizayn ixracında YOXDUR — burada yaradılır. Şablon (nav + footer)
# mövcud dizayn faylından hərfi götürülür ki, görünüş birəbir eyni olsun.
#
# 🔴 MƏZMUN QAYDASI: hər rəqəm və sitat RƏSMİ mənbədən yoxlanılıb.
#   • MİQ bal/keçid qaydası — miq.edu.az/faq (22.08.2026-da oxundu)
#   • Sürət hədləri — «Yol hərəkəti haqqında» AR Qanunu 517-IQ, Maddə 50
#     (azstand.gov.az-dan PDF endirilib, mətn hərfi köçürülüb)
# Yoxlanmamış rəqəm YAZILMIR.

def _card(inner: str) -> str:
    return ('<div style="background:#F6F8F5;border:1px solid #E2E8E1;border-radius:14px;'
            'padding:18px 22px;margin-top:22px;font:400 15px/1.75 Inter;color:#3C453F">'
            + inner + "</div>")


def _row(a: str, b: str) -> str:
    return ('<div style="display:flex;justify-content:space-between;gap:16px;padding:9px 0;'
            'border-bottom:1px solid #EEF0EC"><span>' + a
            + '</span><b style="font-family:Manrope;white-space:nowrap">' + b + "</b></div>")


NEW_POSTS = [
    dict(
        slug="miq-kecid-bali", cat="MİQ", cat_color="#4F46E5", read="5 dəq", date="22 avqust 2026",
        emoji="🎯", tint="rgba(79,70,229,.10)", date_short="22 avqust",
        short="Ümumi 40 bal kifayət etmir — ixtisas 34, metodika 6. Nümunələrlə izah.",
        title="MİQ-də keçid balı: üç şərtin hamısı ödənməlidir",
        desc="Müəllimlərin işə qəbulu imtahanında ümumi 40 bal kifayət etmir — ixtisas və "
             "metodika üzrə ayrıca minimumlar da var. Rəsmi qayda və hesablama nümunələri.",
        body=(
            "<p>MİQ-in bal sistemi çoxlarının düşündüyündən sərtdir. «40 bal topladım, keçdim» "
            "fikri <b>yanlışdır</b> — rəsmi qaydada üç şərt var və üçü də eyni anda ödənməlidir.</p>"
            + _card(
                "<b>Rəsmi qayda (miq.edu.az):</b><br>«ümumtəhsil proqramı üzrə minimun <b>34 bal</b> "
                "və tədris metodikası üzrə minimum <b>6 bal</b> olmaqla, ümumi <b>40 bal</b> və daha "
                "yüksək nəticə göstərən namizədlər vakant yerlərin seçiminə buraxılır.»")
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">İmtahanın quruluşu</h3>"
            + _row("İxtisas (fənn) sualları", "40 sual × 2 bal = 80")
            + _row("Tədris metodikası və təlim strategiyaları", "20 sual × 1 bal = 20")
            + _row("Maksimum bal", "100")
            + _row("Müddət", "150 dəqiqə")
            + _row("Səhv cavab — ixtisas", "−0,5 bal")
            + _row("Səhv cavab — metodika", "−0,25 bal")
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">İki nümunə</h3>"
            + "<p><b>Keçir.</b> İxtisasda 22 düz, 18 səhv → 2×22 − 0,5×18 = <b>35 bal</b> (≥34 ✓). "
              "Metodikada 9 düz, 11 səhv → 9 − 0,25×11 = <b>6,25 bal</b> (≥6 ✓). "
              "Ümumi 41,25 (≥40 ✓). Hər üç şərt ödənir.</p>"
            + "<p><b>Keçmir.</b> İxtisasda yenə 35 bal, metodikada isə 8 düz, 12 səhv → "
              "8 − 0,25×12 = <b>5 bal</b>. Ümumi <b>40,0</b> — ümumi hədd ödənir, amma metodika "
              "6-dan aşağıdır. Namizəd keçmir.</p>"
            + "<p>Yəni ixtisası mükəmməl bilib metodikanı saymamaq riskli strategiyadır: "
              "cəmi bir neçə metodika sualı bütün nəticəni ləğv edə bilər.</p>"),
    ),
    dict(
        slug="miq-menfi-bal", cat="MİQ", cat_color="#4F46E5", read="4 dəq", date="22 avqust 2026",
        emoji="➖", tint="rgba(79,70,229,.10)", date_short="22 avqust",
        short="Təsadüfi təxmin sıfır gətirir, bir variantı silsən müsbətə keçir. Hesablama.",
        title="Mənfi bal: təxmin etmək nə vaxt sərfəlidir?",
        desc="MİQ-də səhv cavab bal aparır, boş buraxmaq isə aparmır. Riyazi olaraq hansı "
             "halda təxmin etmək sərfəlidir — sadə hesablama.",
        body=(
            "<p>MİQ-də cavabsız qoyulan sual <b>bal aparmır</b>, səhv cavab isə aparır: "
            "ixtisasda −0,5, metodikada −0,25. Onda sual yaranır — bilmirsənsə boş qoymaq, "
            "yoxsa təxmin etmək?</p>"
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">Tam təsadüfi seçim</h3>"
            + "<p>İxtisas sualında 5 variant var. Təsadüfi seçsən, orta gözlənilən bal:</p>"
            + _card("(1/5) × (+2) + (4/5) × (−0,5) = 0,4 − 0,4 = <b>0</b>")
            + "<p>Yəni tam təsadüfi təxmin nə qazandırır, nə itirir — <b>sıfır</b>. Sistem məhz belə "
              "qurulub, təsadüfi doldurmağın mənası yoxdur.</p>"
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">Bir variantı ata bilirsənsə</h3>"
            + _card("(1/4) × (+2) + (3/4) × (−0,5) = 0,5 − 0,375 = <b>+0,125</b>")
            + "<p>Artıq müsbətdir. İki variantı atsan gözlənilən bal +0,33-ə qalxır. "
              "<b>Nəticə:</b> heç bir fikrin yoxdursa boş qoy; bircə variantı belə əminliklə "
              "silə bilirsənsə — cavabla.</p>"
            + "<p>Metodika suallarında rəqəmlər kiçikdir (1 bal / −0,25), amma nisbət eynidir: "
              "təsadüfi seçim sıfır, eliminasiya ilə müsbət.</p>"
            + "<p>Praktik məsləhət: sualı oxuyanda dərhal açıq-aşkar yanlış variantları sil. "
              "Bu vərdiş həm vaxt qazandırır, həm də təxminləri sərfəli edir.</p>"),
    ),
    dict(
        slug="surucululuk-suret-hedleri", cat="SÜRÜCÜLÜK", cat_color="#16A34A", read="4 dəq",
        emoji="🚗", tint="rgba(22,163,74,.10)", date_short="22 avqust",
        short="60, 90, 110, 70, 50, 20 — hansı hal üçün hansı rəqəm. Qanunun tam cədvəli.",
        date="22 avqust 2026",
        title="Sürət hədləri: imtahanda ən çox qarışdırılan rəqəmlər",
        desc="Yaşayış məntəqəsində, avtomagistralda, qoşqu ilə, banında adam daşıyanda — "
             "«Yol hərəkəti haqqında» Qanunun tam sürət cədvəli.",
        body=(
            "<p>Sürücülük imtahanında sürətlə bağlı suallar demək olar həmişə olur və rəqəmlər "
            "bir-birinə oxşadığı üçün asanlıqla qarışır. Aşağıdakı cədvəl «Yol hərəkəti haqqında» "
            "Azərbaycan Respublikası Qanununun (517-IQ) <b>50-ci maddəsinə</b> əsaslanır.</p>"
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">Yaşayış məntəqəsində</h3>"
            + _row("Ümumi hədd", "60 km/saat")
            + _row("Səlahiyyətli orqan artıra bilər, amma maksimum", "90 km/saat")
            + _row("Yaşayış zonası və həyət ərazisi", "20 km/saat")
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">Yaşayış məntəqəsindən kənarda</h3>"
            + _row("Minik avtomobili · yük avtomobili ≤3,5 t — avtomagistral", "110 km/saat")
            + _row("Minik avtomobili · yük avtomobili ≤3,5 t — digər yollar", "90 km/saat")
            + _row("Şəhərlərarası və kiçik avtobuslar, motosikletlər — bütün yollar", "90 km/saat")
            + _row("Digər avtobuslar · qoşqulu minik · yük >3,5 t — avtomagistral", "90 km/saat")
            + _row("Digər avtobuslar · qoşqulu minik · yük >3,5 t — digər yollar", "70 km/saat")
            + _row("Banında adam daşıyan yük avtomobili", "50 km/saat")
            + _row("Yedəyində mexaniki nəqliyyat vasitəsi aparan", "50 km/saat")
            + _card("<b>Yadda saxlamağın asan yolu:</b> «böyük və ya yüklü» olan hər şey bir pillə "
                    "aşağı gedir. Minik 110 → böyük avtobus/ağır yük 90 → onlar adi yolda 70 → "
                    "adam daşıyan ban və yedək 50.")
            + "<p>Diqqət: bunlar <b>yuxarı hədlərdir</b>. Qanun eyni maddədə sürücünün yol və "
              "hava şəraitini nəzərə almasını da tələb edir — buzlu yolda 90 km/saat qanuni hədd "
              "daxilində olsa da, qayda pozuntusudur.</p>"),
    ),
    dict(
        slug="dq-test-merhelesi", cat="DÖVLƏT QULLUĞU", cat_color="#0D9488", read="4 dəq",
        emoji="🏛", tint="rgba(13,148,136,.10)", date_short="22 avqust",
        short="100 sual, 3 saat, alt-qruplar — və uzun imtahanda diqqəti saxlamağın yolu.",
        date="22 avqust 2026",
        title="Dövlət Qulluğu test mərhələsi: 100 sual, 3 saat",
        desc="Test imtahanının müddəti, sual sayı və vəzifə alt-qrupları — namizədin "
             "bilməli olduğu əsas parametrlər.",
        body=(
            "<p>Dövlət qulluğuna qəbulun test mərhələsi bir çox namizədin gözlədiyindən "
            "uzundur və bu, hazırlıq strategiyasını dəyişir.</p>"
            + _row("Sual sayı", "100")
            + _row("Müddət", "3 saat (180 dəqiqə)")
            + _row("Bir suala düşən orta vaxt", "≈1 dəqiqə 48 saniyə")
            + _card("<b>Mənbə:</b> DİM «Namizədin yaddaş kitabçası» (08.05.2025) — «İmtahan "
                    "müddəti 3 saatdır».")
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">Vəzifə alt-qrupları</h3>"
            + "<p>Müsabiqə vahid deyil — vəzifələr alt-qruplara bölünür: <b>AB, AC, BA, BB</b>. "
              "Alt-qrup həm tələb olunan təhsil və staj səviyyəsini, həm də seçə biləcəyin "
              "vakansiyaları müəyyən edir. Ərizə verməzdən əvvəl hansı alt-qrupa aid olduğunu "
              "dəqiqləşdir — sonradan dəyişmək mümkün olmur.</p>"
            + "<h3 style=\"font:800 20px Manrope,sans-serif;margin:32px 0 10px\">3 saat niyə vacibdir</h3>"
            + "<p>Uzun imtahanda əsas risk bilik deyil, <b>diqqətin düşməsi</b>dir. İkinci saatın "
              "sonunda səhv sayı artır. Ona görə hazırlıqda 20-30 suallıq qısa məşqlərdən əlavə "
              "ən azı bir neçə <b>tam formatda</b> sınaq keçmək lazımdır — orqanizm 3 saatlıq "
              "diqqətə öyrəşməlidir.</p>"
            + "<p>Praktik qayda: hər 30 sualdan sonra 20-30 saniyəlik fasilə ver — gözlərini "
              "ekrandan ayır, nəfəsini bərpa et. Bu, itirilən vaxtdan qat-qat çox bal qazandırır.</p>"),
    ),
]


def _chrome():
    """NAV və FOOTER bloklarını mövcud dizayn faylından HƏRFİ götür —
    yeni yazılar köhnələrdən bir piksel də fərqlənməsin."""
    raw = (SRC / "bloq-5-verdis.dc.html").read_text(encoding="utf-8")
    body = re.search(r"<x-dc>(.*?)</x-dc>", raw, re.S).group(1)
    nav = body[body.index("<!-- NAV"):body.index("<!-- M4")]
    foot = body[body.index("<!-- FOOTER"):]
    return nav, foot


def build_new_posts():
    nav, foot = _chrome()
    made = []
    for post in NEW_POSTS:
        art = (
            '<div style="max-width:1120px;margin:0 auto;padding:48px 32px 0">'
            '<div style="background:#FFFFFF;border-radius:24px;box-shadow:0 2px 16px rgba(28,35,33,.07);padding:56px 0">'
            '<div style="max-width:680px;margin:0 auto;padding:0 32px">'
            f'<span style="font:600 12px Inter;color:{post["cat_color"]};letter-spacing:.5px">{post["cat"]}</span>'
            f'<div style="font:800 34px/1.25 Manrope,sans-serif;margin-top:14px;letter-spacing:-.5px;text-wrap:pretty">{post["title"]}</div>'
            '<div style="display:flex;align-items:center;gap:12px;margin-top:18px;font:500 13px Inter;color:#6B7671">'
            '<span style="width:34px;height:34px;border-radius:50%;background:rgba(22,163,74,.10);display:flex;'
            'align-items:center;justify-content:center;font:800 14px Manrope,sans-serif;color:#16A34A">K</span>'
            f'<span>Keçdim komandası</span><span>·</span><span>{post["read"]} oxu</span><span>·</span><span>{post["date"]}</span></div>'
            f'<div style="font:400 16px/1.9 Inter;color:#3C453F;margin-top:28px">{post["body"]}</div>'
            '<div style="background:radial-gradient(130% 160% at 20% 15%,#1FB25A 0%,#16A34A 62%,#149244 100%);'
            'border-radius:18px;padding:28px 32px;margin-top:36px;display:flex;align-items:center;gap:20px;flex-wrap:wrap">'
            '<div style="flex:1;min-width:240px"><div style="font:800 19px Manrope,sans-serif;color:#FFFFFF">'
            'Bu qaydaları Keçdim özü tətbiq edir</div>'
            '<div style="font:400 13px Inter;color:rgba(255,255,255,.85);margin-top:4px">'
            'Real format, rəsmi bal hesablanması, izahlı suallar.</div></div>'
            '<a href="/#yukle" style="padding:13px 26px;background:#FFFFFF;border-radius:12px;'
            'font:600 14px Inter;color:#15803D;flex:none">Tətbiqi yüklə</a></div>'
            "</div></div></div>")
        inner = nav + '<div style="max-width:1120px;margin:0 auto;padding:28px 32px 0">' \
                '<a href="/bloq.html" style="font:600 14px Inter,sans-serif;color:#16A34A">' \
                "‹ Bütün məqalələr</a></div>" + art + foot
        for old, new in sorted(LINKS.items(), key=lambda kv: -len(kv[0])):
            inner = inner.replace(f'href="{old}"', f'href="{new}"').replace(f'href="{old}#', f'href="{new}#')
        inner = re.sub(r'href="bloq-([a-z0-9-]+)\.dc\.html"', r'href="/bloq-\1.html"', inner)

        out = f"bloq-{post['slug']}.html"
        canonical = SITE + "/" + out
        ga_tag = ""
        if GA_ID:
            ga_tag = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>'
                      '<script>window.dataLayer=window.dataLayer||[];'
                      'function gtag(){dataLayer.push(arguments)}gtag("js",new Date());'
                      f'gtag("config","{GA_ID}",{{"anonymize_ip":true,"allow_google_signals":false}});</script>')
        head = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{post['title']} | Keçdim</title>
<meta name="description" content="{post['desc']}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#16A34A">
{FAVICON}
<meta property="og:type" content="article">
<meta property="og:site_name" content="Keçdim">
<meta property="og:locale" content="az_AZ">
<meta property="og:title" content="{post['title']}">
<meta property="og:description" content="{post['desc']}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600&family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#FAFAF7;font-family:Inter,system-ui,sans-serif;color:#1C2321}}
a{{color:#16A34A;text-decoration:none}}a:hover{{color:#15803D}}html{{scroll-behavior:smooth}}
h3{{color:#1C2321}}p{{margin:0 0 14px}}{RESPONSIVE}</style>
{ga_tag}
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article",
"headline":"{post['title']}","description":"{post['desc']}","inLanguage":"az-AZ",
"datePublished":"2026-08-22","mainEntityOfPage":"{canonical}",
"publisher":{{"@type":"Organization","name":"Protech LLC","url":"https://pro-tech.az"}}}}</script>"""
        (OUT / out).write_text(
            f"<!DOCTYPE html>\n<html lang=\"az\">\n<head>\n{head}\n</head>\n<body>\n{inner}\n</body>\n</html>\n",
            encoding="utf-8")
        made.append(out)
    return made



def inject_index_cards():
    """Yeni yazıları bloq siyahısına əlavə et — yetim səhifə qalmasın.
    Markup mövcud kartlardan hərfi kopyalanır (yalnız məzmun dəyişir)."""
    f = OUT / "bloq.html"
    s = f.read_text(encoding="utf-8")

    cards, rows = "", ""
    for p in NEW_POSTS:
        cards += (
            f'<a href="/bloq-{p["slug"]}.html" style="background:#FFFFFF;border-radius:20px;'
            'overflow:hidden;box-shadow:0 2px 12px rgba(28,35,33,.06);color:#1C2321;'
            'display:flex;flex-direction:column">\n'
            f'<div style="height:150px;background:{p["tint"]};display:flex;align-items:center;'
            f'justify-content:center;font-size:44px">{p["emoji"]}</div>\n'
            '<div style="padding:22px 24px 24px;display:flex;flex-direction:column;gap:10px;flex:1">\n'
            f'<span style="font:600 11px Inter;color:{p["cat_color"]};letter-spacing:.5px">{p["cat"]}</span>\n'
            f'<div style="font:800 18px/1.35 Manrope,sans-serif;text-wrap:pretty">{p["title"]}</div>\n'
            f'<div style="font:400 13px/1.6 Inter;color:#6B7671">{p["short"]}</div>\n'
            f'<div style="font:500 12px Inter;color:#9AA49D;margin-top:auto">{p["read"]} oxu · {p["date_short"]}</div>\n'
            "</div>\n</a>\n")
        rows += (
            f'<a href="/bloq-{p["slug"]}.html" style="display:flex;align-items:center;gap:18px;'
            'padding:18px 0;border-bottom:1px solid #F0F2EE;color:#1C2321">\n'
            f'<span style="width:118px;flex:none;font:600 10.5px Inter,sans-serif;color:{p["cat_color"]};'
            f'letter-spacing:.5px">{p["cat"]}</span>\n'
            f'<span style="flex:1;font:600 15px/1.4 Inter,sans-serif">{p["title"]}</span>\n'
            f'<span style="font:400 12px Inter,sans-serif;color:#9AA49D;flex:none">{p["read"]} · {p["date"]}</span>\n'
            '<span style="color:#16A34A;font:600 15px Inter,sans-serif;flex:none">→</span>\n</a>\n')

    grid = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:20px">\n'
    if grid not in s:
        raise SystemExit("🔴 bloq.html: grid konteyneri tapılmadı — inject dayandırıldı")
    s = s.replace(grid, grid + cards, 1)

    lst = '<div style="background:#FFFFFF;border-radius:20px;box-shadow:0 2px 12px rgba(28,35,33,.06);margin-top:20px;padding:6px 28px">\n'
    if lst not in s:
        raise SystemExit("🔴 bloq.html: «Bütün məqalələr» konteyneri tapılmadı")
    s = s.replace(lst, lst + rows, 1)

    f.write_text(s, encoding="utf-8")
    return len(NEW_POSTS)



def inject_ga_static():
    """privacy/support/terms/confirmed əl ilə yazılmış statik fayllardır —
    onlar həm də ÇIXIŞ faylıdır, ona görə injektor iki tərəfli olmalıdır:
    GA_ID varsa köhnə bloku əvəzlə, boşdursa tamamilə SİL.
    (Əks halda GA_ID-ni boşaltmaq köhnə tagı fayllarda qoyub gedir.)"""
    tag = ""
    if GA_ID:
        tag = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>\n'
               '<script>window.dataLayer=window.dataLayer||[];'
               'function gtag(){dataLayer.push(arguments)}gtag("js",new Date());'
               f'gtag("config","{GA_ID}",{{"anonymize_ip":true,"allow_google_signals":false}});</script>\n')
    n = 0
    for name in ("privacy.html", "support.html", "terms.html", "confirmed.html"):
        f = OUT / name
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        cleaned = re.sub(
            r'<script async src="https://www\.googletagmanager\.com/gtag/js\?id=[^"]*"></script>\n?'
            r'<script>window\.dataLayer.*?</script>\n?', "", t, flags=re.S)
        out = cleaned.replace("</head>", tag + "</head>", 1) if tag else cleaned
        if out != t:
            f.write_text(out, encoding="utf-8")
            n += 1
    return n


def main() -> None:
    written = []
    for src in PAGES:
        if not (SRC / src).exists():
            raise SystemExit(f"🔴 mənbə yoxdur: {src}")
        out = PAGES[src][0]
        (OUT / out).write_text(convert(src), encoding="utf-8")
        written.append(out)

    written += build_new_posts()
    n = inject_index_cards()
    inject_ga_static()

    # sitemap + robots
    urls = [SITE + "/"] + [
        SITE + "/" + p[0] for p in PAGES.values() if p[0] != "index.html"
    ] + [SITE + f"/bloq-{p['slug']}.html" for p in NEW_POSTS] \
      + [SITE + "/privacy.html", SITE + "/support.html", SITE + "/terms.html"]
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (OUT / "sitemap.xml").write_text(sm, encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    print(f"   ↳ {n} yeni yazı bloq siyahısına əlavə edildi")
    print(f"✅ {len(written)} səhifə quruldu: {', '.join(written)}")
    print(f"   + sitemap.xml ({len(urls)} URL) + robots.txt")


if __name__ == "__main__":
    main()
