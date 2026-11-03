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

İşlətmə:  python3 build.py          — tam qurma (dizayn mənbəyi lazımdır) + post-proses
          python3 build.py --post   — yalnız post-proses (mənbəsiz; çıxış fayllarına)
"""
import html
import re
import datetime as dt
import shutil
from pathlib import Path

SRC = Path.home() / "Desktop" / "KEÇDİM"
# 🔴 03.11.2026: dizayn qovluğu `~/Desktop/Pro/Keçdim/`-ə köçüb. Oradakı Landing və
# 4 bloq faylı «compressed,dataless»-dir (oxuyanda `Errno 60 Operation timed out`) —
# yəni TAM qurma hazırda mümkün deyil. Canlı mənbə Claude Design layihəsidir
# (`5fbfb99f-a61e-4710-a7ea-37aad4d1b1ed`). Mənbə əlçatmazdırsa `--post` rejimi
# yalnız çıxış fayllarına post-proses qaydalarını tətbiq edir (aşağıda `post()`).
if not SRC.exists():
    SRC = Path.home() / "Desktop" / "Pro" / "Keçdim"
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
GA_ID = "G-FXBNW1V7D0"

APP_STORE = "https://apps.apple.com/az/app/ke%C3%A7dim/id6793411739"
PLAY_STORE = "https://play.google.com/store/apps/details?id=az.kecdim"

# ── Kampaniya izlənməsi (UTM) ───────────────────────────────────────────────
# 🔴 Niyə lazımdır: Play Console-un `store_performance_*_traffic_source.csv`
# hesabatında saytdan gələn BÜTÜN trafik «Other / No UTM source specified»
# kimi görünürdü — yəni saytın Play-ə neçə adam göndərdiyi ÖLÇÜLƏ BİLMİRDİ.
#
# Play: install referrer standartı — `&referrer=<utm sətri, URL-kodlanmış>`.
#       Dəyər Play Console hesabatında «UTM source / UTM campaign» sütunlarına düşür.
# Apple: App Analytics kampaniya linki — `?pt=<provider token>&ct=<kampaniya>&mt=8`.
#       🔴 `ct` TƏK BAŞINA işləmir, Apple `pt`-siz kampaniyanı qeydə almır.
#       `pt` yalnız App Store Connect UI-dan alınır (API-də YOXDUR):
#       ASC → Analytics → Acquisition → Campaigns → «Create Campaign Link» →
#       yaranan URL-dəki `pt=` rəqəmi. Onu aşağıya yazanda linklər avtomatik tamamlanır.
#       Boş qaldıqda `ct` yenə əlavə olunur (zərərsizdir, link işləyir) və Apple
#       tərəfdə ölçmə «Web Referrers → kecdim.pro-tech.az» sətri ilə qalır.
ASC_PROVIDER_TOKEN = ""          # məs. "123456789" — ASC UI-dan
UTM_SOURCE = "kecdim_site"
UTM_MEDIUM = "badge"


def store_url(store: str, campaign: str) -> str:
    """Mağaza linkini kampaniya parametrləri ilə qur.

    store: "apple" | "play" · campaign: məs. "site_hero"
    """
    from urllib.parse import quote
    if store == "play":
        ref = quote(f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}"
                    f"&utm_campaign={campaign}", safe="")
        return f"{PLAY_STORE}&referrer={ref}"
    parts = []
    if ASC_PROVIDER_TOKEN:
        parts.append(f"pt={ASC_PROVIDER_TOKEN}")
    parts.append(f"ct={campaign}")
    # 🔴 `mt=8` QƏSDƏN yoxdur: Apple onu 301 ilə atır (ölçüldü 14.09.2026) —
    # hər klikə artıq bir yönləndirmə əlavə edərdi. `ct` isə son URL-də qalır.
    return f"{APP_STORE}?" + "&".join(parts)


# Səhifədəki yerinə görə kampaniya adı: birinci cüt = hero, ikinci = aşağı CTA.
STORE_CAMPAIGNS = ["site_hero", "site_cta"]

# ── Klik ölçməsi (GA4) ──────────────────────────────────────────────────────
# 🔴 03.11.2026: əvvəl `#yukle` (ana səhifənin yükləmə bölməsinə LANGAR) da
# `app_click` sayılırdı — yəni «mağazaya getdi» ilə «ana səhifəyə keçdi» eyni
# hadisə idi və admin paneldəki «CTR → APP» şişirdilmiş çıxırdı.
# İndi:  mağaza linki (apps.apple.com / play.google.com) → `app_click` (+store, placement)
#        `#yukle` langarı                                  → `download_section_click`
# `app_click` adı QƏSDƏN saxlanılıb: `kecdim-supabase/functions/blog-stats` onu oxuyur.
# `a.href` (həll olunmuş URL) oxunur — mobil yönləndirmə skripti linki mağazaya
# çevirəndən sonra da düz sayılsın.
CLICK_JS = (
    '<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a");'
    'if(!a||!window.gtag)return;var h=a.href||"",r=a.getAttribute("href")||"",'
    'p=a.getAttribute("data-kd-store")||"",s=/apps\\.apple\\.com/.test(h)?"apple":/play\\.google\\.com/.test(h)?"play":"";'
    'if(s){gtag("event","app_click",{page_path:location.pathname,link_url:h,store:s,placement:p,transport_type:"beacon"});}'
    'else if(/#yukle$/.test(r)){gtag("event","download_section_click",{page_path:location.pathname,placement:p});}},true);</script>')

# ── səhifə xəritəsi: mənbə → (çıxış, başlıq, təsvir, növ) ───────────────────
PAGES = {
    "Keçdim Landing.dc.html": (
        "index.html",
        "Keçdim — Azərbaycanın imtahan hazırlığı platforması",
        "Sürücülük, buraxılış, Dövlət Qulluğu, MİQ, sertifikasiya və magistratura "
        "imtahanlarına real formatda hazırlaş: 2 300+ izahlı sual, sınaq imtahanları, fərdi plan.",
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

# ── Google Search Console doğrulaması ────────────────────────────────────────
# 🔴 KÖK SƏBƏB (03.09.2026): `kecdim.pro-tech.az` **GitHub Pages**-dən verilir
# (`server: GitHub.com`), Cloudflare bu host üçün yalnız DNS-dir (proxy=False).
# Yəni doğrulama faylını Cloudflare-ə qoymaq HEÇ NƏ etmir — Google onu
# `https://kecdim.pro-tech.az/...` ünvanında axtarır, oranı isə bu repo verir.
#
# İki üsuldan birini doldur, `build.py` hər ikisini avtomatik yerləşdirir və
# rebuild-də İTMİR (IndexNow açarı ilə eyni məntiq):
#   · GOOGLE_VERIFY_META — «HTML teqi» üsulundakı `content="..."` dəyəri
#   · GOOGLE_VERIFY_FILE — «HTML faylı» üsulundakı `googleXXXX.html` adı
# Boş qalsa heç nə əlavə olunmur.
GOOGLE_VERIFY_META = ""
GOOGLE_VERIFY_FILE = ""

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
    # Kampaniya adı görünmə sırasına görə verilir (hero → cta → ...).
    _seen = {"apple": 0, "play": 0}

    def _camp(store):
        i = _seen[store]
        _seen[store] += 1
        return STORE_CAMPAIGNS[i] if i < len(STORE_CAMPAIGNS) else f"site_{i + 1}"

    body = re.sub(
        r'href="#elaqe"((?:(?!</a>).)*?App Store)',
        lambda mm: f'href="{html.escape(store_url("apple", _camp("apple")), quote=False)}" '
                   f'target="_blank" rel="noopener"{mm.group(1)}',
        body, flags=re.S)
    body = re.sub(
        r'href="#elaqe"((?:(?!</a>).)*?Google Play)',
        lambda mm: f'href="{html.escape(store_url("play", _camp("play")), quote=False)}" '
                   f'target="_blank" rel="noopener"{mm.group(1)}',
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
              f'gtag("config","{GA_ID}",{{"anonymize_ip":true,"allow_google_signals":false}});</script>'
              # App-a keçid ölçülür: bloq → «Yüklə» və ya mağaza linki.
              # Bunsuz «CTR → APP» sütunu heç vaxt real ola bilməz.
              + CLICK_JS)

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
{_gverify()}<meta property="og:image" content="https://kecdim.pro-tech.az/og-image.png">
<meta property="og:image:width" content="1024">
<meta property="og:image:height" content="500">
<meta property="og:image:alt" content="Keçdim — imtahan hazırlığı tətbiqi">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://kecdim.pro-tech.az/og-image.png">
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
                      f'gtag("config","{GA_ID}",{{"anonymize_ip":true,"allow_google_signals":false}});</script>'
              # App-a keçid ölçülür: bloq → «Yüklə» və ya mağaza linki.
              # Bunsuz «CTR → APP» sütunu heç vaxt real ola bilməz.
              + CLICK_JS)
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
{_gverify()}<meta property="og:image" content="https://kecdim.pro-tech.az/og-image.png">
<meta property="og:image:width" content="1024">
<meta property="og:image:height" content="500">
<meta property="og:image:alt" content="Keçdim — imtahan hazırlığı tətbiqi">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://kecdim.pro-tech.az/og-image.png">
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



def inject_related():
    """Hər bloq yazısının sonuna «Oxşar yazılar» bloku qoyur.

    🔴 Niyə: 03.09 ölçməsi göstərdi ki, bloq səhifələrinin GA4-də baxışı SIFIRDIR.
    Səbəblərdən biri struktur idi — hər yazı dalan idi: nə bir-birinə keçid, nə də
    siyahıya qayıdış vardı. Daxili keçid həm Google-un dərinliyə enməsini, həm də
    oxucunun ikinci yazıya keçməsini asanlaşdırır.

    Blok mövcud səhifələrdən qurulur (başlıq <title>-dan oxunur) — əl ilə siyahı
    saxlanmır, yəni yeni yazı əlavə olunanda özü qoşulur.
    """
    import re as _re
    pages = sorted(OUT.glob("bloq-*.html"))
    meta = {}
    for f in pages:
        html = f.read_text(encoding="utf-8")
        m = _re.search(r"<title>(.*?)(?:\s*\|\s*Keçdim)?</title>", html, _re.S)
        meta[f.name] = (m.group(1).strip() if m else f.stem)
    names = list(meta)
    done = 0
    for i, name in enumerate(names):
        f = OUT / name
        html = f.read_text(encoding="utf-8")
        if "kd-related" in html:                      # təkrar qoşma
            html = _re.sub(r'<section class="kd-related".*?</section>', "", html, flags=_re.S)
        picks = [names[(i + k) % len(names)] for k in (1, 2, 3)][: max(0, min(3, len(names) - 1))]
        if not picks:
            continue
        cards = "".join(
            f'<a href="/{n}" style="display:block;padding:14px 16px;border:1px solid #E4E8E2;'
            f'border-radius:14px;background:#FFF;color:#1C2321;font:600 14px Inter,sans-serif;'
            f'line-height:1.45">{meta[n]}</a>' for n in picks)
        block = (
            '<section class="kd-related" style="max-width:760px;margin:8px auto 40px;padding:0 20px">'
            '<div style="font:700 15px Manrope,sans-serif;margin:0 0 12px">Oxşar yazılar</div>'
            f'<div style="display:grid;gap:10px">{cards}</div>'
            '<div style="margin-top:14px;font:500 13px Inter,sans-serif">'
            '<a href="/bloq.html">← Bütün yazılar</a> · <a href="/#yukle">Keçdim-i yüklə</a></div>'
            '</section>')
        html = html.replace("</body>", block + "\n</body>")
        f.write_text(html, encoding="utf-8")
        done += 1
    return done


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



def fix_pricing():
    """🔴 Dizayn maketindəki qiymətlər SAXTA idi (08.09.2026).

    Landing-in `#qiymet` bölməsi dizayndan olduğu kimi gəlir, dizaynda isə
    uydurma rəqəm və vədlər var idi: aylıq 6.99 ₼ (real 5.99), illik 29.99 ₼
    (real 35.99), «AI izahlar» (belə funksiya yoxdur), «4 imtahan» (əslində 6),
    «3 gün pulsuz» (trial yoxdur). Admin panelindəki 20 saxta rəqəmlə eyni sinif.

    Həqiqət mənbəyi — canlı `plus_plans` cədvəli və `app_config.plus_features` /
    `free_features`. Qiymət dəyişəndə AŞAĞIDAKI cütləri yenilə; mənbə dizayn
    yenidən ixrac olunsa da bu funksiya düzəlişi təkrar tətbiq edir.

    🔑 Hər əvəzləmə yoxlanır: gözlənilən mətn tapılmasa xəbərdarlıq verilir —
    səssiz «heç nə etmədim» halı olmasın.
    """
    f = OUT / "index.html"
    if not f.exists():
        return 0
    t = f.read_text(encoding="utf-8")
    pairs = [
        # (dizayndakı saxta mətn, real dəyər)
        ("<span>Aylıq</span><b style=\"font-family:Manrope\">6.99 ₼</b>",
         "<span>1 ay</span><b style=\"font-family:Manrope\">5.99 ₼</b>"),
        ("<span>İllik</span><b style=\"font-family:Manrope\">29.99 ₼</b>",
         "<span>1 il</span><b style=\"font-family:Manrope\">35.99 ₼</b>"),
        ("<span>✓ Limitsiz sual və sınaq</span><span>✓ AI izahlar + təhlil</span>"
         "<span>✓ Fərdi plan + 4 imtahan</span><span>✓ Reklamsız · 3 gün pulsuz</span>",
         "<span>✓ Bütün 6 imtahanda limitsiz tam sınaq</span>"
         "<span>✓ Bölmə üzrə detallı hesabat — hansı mövzuda zəifsən</span>"
         "<span>✓ Sınaq tarixçəsinin tam arxivi</span>"
         "<span>✓ Reklamsız istifadə</span>"),
        ("<span>✓ Gündəlik sual limiti</span><span>✓ 1 sınaq imtahanı / gün</span>"
         "<span>✓ Əsas statistika</span><span>✓ Qeydiyyatsız istifadə</span>",
         "<span>✓ Səhvlərin təkrarı — həmişə limitsiz</span>"
         "<span>✓ Gündəlik pulsuz sual limiti</span>"
         "<span>✓ İmtahan təqvimi və xatırlatmalar</span>"
         "<span>✓ Yol nişanları kataloqu</span>"),
        # «Pulsuz sına» ölü düymə idi: trial yoxdur, satınalma bağlıdır.
        (">Pulsuz sına</a>", ">Tətbiqi yüklə</a>"),
        # 17.09.2026: Kapital Bank production terminalı açıldı — «Satınalma hazırlanır»
        # bloku satış blokuna çevrildi (saytdan kartla alış, /plus.html).
        ("<div style=\"font:600 14px Inter;color:#1C2321\">Satınalma hazırlanır</div>\n"
         "<div style=\"font:400 13px/1.7 Inter;color:#6B7671;margin-top:6px\">Keçdim+ abunəliyi hələ satışa açılmayıb — "
         "bu müddətdə bütün funksiyalar pulsuzdur. Açılandan sonra ödəniş App Store, Google Play və bank kartı "
         "(Visa / Mastercard) ilə mümkün olacaq. Qiymətlər Azərbaycan manatı (₼) ilədir, ƏDV daxildir.</div>",
         "<div style=\"font:600 14px Inter;color:#1C2321\">Keçdim+ necə alınır?</div>\n"
         + PLUS_HOWTO_HTML + "\n"
         "<a href=\"/plus.html\" style=\"display:inline-flex;align-items:center;justify-content:center;height:44px;"
         "padding:0 22px;background:#16A34A;border-radius:12px;font:600 14px Inter;color:#FFFFFF;margin-top:14px\">Keçdim+ al</a>"),
    ]
    n = 0
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new)
            n += 1
        elif new not in t:
            print(f"   ⚠️  qiymət blokunda gözlənilən mətn tapılmadı: {old[:60]}…")
    f.write_text(t, encoding="utf-8")
    return n


# «Keçdim+ necə alınır?» mətni — 03.11.2026 qərarı: saytda kartla BİRDƏFƏLİK paket,
# tətbiqdə App Store / Google Play abunəsi (avtomatik yenilənir).
PLUS_HOWTO_HTML = (
    "<div style=\"font:400 13px/1.7 Inter;color:#6B7671;margin-top:6px\"><b>Saytda</b> — bank kartı (Visa / Mastercard) "
    "ilə birdəfəlik paket: ödəniş Kapital Bank üzərindən keçir, avtomatik yenilənmir. Tətbiqdəki e-poçtunla daxil ol "
    "(hesabın yoxdursa, yaranacaq), paketi seç, ödə — tətbiqdə eyni e-poçtla girəndə Keçdim+ avtomatik görünür. "
    "<b>Tətbiqdə</b> — App Store / Google Play abunəsi: avtomatik yenilənir, mağaza hesabından idarə və ləğv olunur. "
    "Saytda qiymətlər Azərbaycan manatı (₼) ilədir, ƏDV daxildir.</div>")

# Sabit məzmun düzəlişləri — həqiqət mənbəyi canlı baza (03.11.2026 ölçüldü):
#   exam_rules(driving): mock_total_questions=10, mock_duration_sec=900, max_mistakes=1
#   exam_rules(masters): 95 sual, 12600 s; questions.qtype aktivlərdə YALNIZ 'single'
#     (esse/açıq sual YOXDUR, «AI qiymətləndirmə» funksiyası da yoxdur)
#   exam_rules(miq): 60 sual, 9000 s, bölmələr miq_specialty(40×2, min 34) +
#     miq_pedagogy(20×1, min 6), pass_score 40 — «məntiq» bölməsi YOXDUR
#   aktiv imtahanlarda aktiv sual: 2379 → aşağı yuvarlaq «2 300+»
#     (sorğu: questions⋈topics⋈subjects⋈exams, status='active', t.is_active, e.is_active)
#   offline hamı üçündür — Plus üstünlüyü DEYİL (yalnız «Reklamsız» Plus-dadır).
# Sual sayı dəyişəndə QUESTIONS_LABEL-i yenilə (aşağı yuvarlaq, uydurma yox).
QUESTIONS_LABEL = "2 300+"

FACT_PAIRS = [
    ("20 sual · 20 dəqiqə · keçid 17. Yol nişanları, üstünlük, manevr, cərimələr.",
     "10 sual · 15 dəqiqə · ən çox 1 səhv. Yol nişanları, üstünlük, manevr, cərimələr."),
    ("Məntiq, informatika və xarici dil. Esse tapşırığı və AI qiymətləndirmə ilə.",
     "95 sual · 3 saat 30 dəqiqə. Məntiq, informatika və xarici dil üzrə qapalı test sualları."),
    ("İxtisas + metodika + məntiq. İxtisasına görə sual bazası, müsahibə həddi şkalası.",
     "60 sual · 150 dəqiqə. İxtisas + tədris metodikası, ixtisasına görə sual bazası; keçid 40 bal."),
    ('<div style="font:800 26px Manrope,sans-serif;color:#FFFFFF">2000+</div>',
     f'<div style="font:800 26px Manrope,sans-serif;color:#FFFFFF">{QUESTIONS_LABEL}</div>'),
    ("hazırlaş: 2200+ izahlı sual", f"hazırlaş: {QUESTIONS_LABEL} izahlı sual"),
    # Telefon maketi: «Günün sınağı» DYP formatındadır (10 sual)
    (">20 sual · real format<", ">10 sual · real format<"),
    (">12/20 →<", ">6/10 →<"),
    # 17.09 çıxışından qalan köhnə dəyərlər (fix_pricing-in əvvəlki «yeni» mətni)
    ("<span>✓ Reklamsız və offline istifadə</span>", "<span>✓ Reklamsız istifadə</span>"),
    ("<div style=\"font:400 13px/1.7 Inter;color:#6B7671;margin-top:6px\">Abunəlik saytdan bank kartı (Visa / Mastercard) "
     "ilə alınır — ödəniş Kapital Bank üzərindən keçir. Tətbiqdəki hesabınla daxil ol, paketi seç, ödə: Keçdim+ həmin "
     "hesabda dərhal açılır. Qiymətlər Azərbaycan manatı (₼) ilədir, ƏDV daxildir.</div>",
     PLUS_HOWTO_HTML),
]


def fix_facts():
    """Ana səhifədəki fakt səhvlərini canlı bazaya uyğunlaşdırır (bax FACT_PAIRS).
    İdempotentdir; gözlənilən mətn tapılmasa (və yeni mətn də yoxdursa) xəbərdarlıq."""
    f = OUT / "index.html"
    t = f.read_text(encoding="utf-8")
    n = 0
    for old, new in FACT_PAIRS:
        if old in t:
            t = t.replace(old, new)
            n += 1
        elif new not in t:
            print(f"   ⚠️  fakt düzəlişi: gözlənilən mətn tapılmadı: {old[:70]}…")
    f.write_text(t, encoding="utf-8")
    return n


# ── Mobil başlıq ────────────────────────────────────────────────────────────
# 🔴 03.11.2026: 360–390 px-də loqo «Keç/dim» iki sətrə bölünürdü və «Bloq» linki
# kəsilirdi — nav-da 5 link + düymə dar ekrana sığmırdı. Dizayn sabit enlidir,
# ona görə qayda bütün səhifələrə ayrıca <style id="kd-mobile"> bloku kimi
# yazılır (təkrar işlədiləndə əvəzlənir, ikiqat düşmür).
MOBILE_CSS = """
/* loqo heç vaxt bölünmür (yalnız NAV-dakı loqo — eyni şrift başqa başlıqlarda da var) */
[style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]>[style*="font:800 24px Manrope"]{white-space:nowrap;flex:none}
@media (max-width:720px){
  [style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]{gap:14px!important;padding:12px 16px!important}
  [style*="display:flex;gap:26px;font:500 14px Inter;margin-left:auto"]{gap:14px!important}
  [style*="display:flex;gap:26px;font:500 14px Inter;margin-left:auto"]>a:not([href="/bloq.html"]){display:none}
}
@media (max-width:420px){
  [style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]>[style*="font:800 24px Manrope"]{font-size:21px!important}
  [style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]>[style*="font:800 24px Manrope"] [style*="font:600 13px Inter"]{font-size:12px!important;margin-left:4px!important}
  [style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]{gap:10px!important;padding:10px 14px!important}
  [style*="padding:16px 32px;display:flex;align-items:center;gap:36px"]>a[style*="padding:11px 22px"]{padding:9px 14px!important;font-size:13px!important;white-space:nowrap;flex:none}
  [style*="display:flex;gap:26px;font:500 14px Inter;margin-left:auto"]>a{white-space:nowrap}
}
/* bloq.html: dizaynın min-width blokları və siyahı sətirləri 360–390 px-də üfüqi
   sürüşmə yaradırdı (ölçüldü: scrollWidth 486 / innerWidth 360) — mətn kənardan kəsilirdi */
@media (max-width:600px){
  [style*="min-width:380px"],[style*="min-width:340px"],[style*="min-width:320px"],
  [style*="min-width:300px"]{min-width:0!important;flex-basis:100%!important;box-sizing:border-box}
  [style*="minmax(330px,1fr)"]{grid-template-columns:1fr!important}
  a[style*="display:flex;align-items:center;gap:18px;padding:18px 0"]{flex-wrap:wrap;gap:4px 12px!important}
  a[style*="display:flex;align-items:center;gap:18px;padding:18px 0"]>span[style*="width:118px"]{width:auto!important}
  a[style*="display:flex;align-items:center;gap:18px;padding:18px 0"]>span[style*="flex:1"]{flex:1 1 100%!important;order:2}
  a[style*="display:flex;align-items:center;gap:18px;padding:18px 0"]>span[style*="font:400 12px"]{order:3}
  a[style*="display:flex;align-items:center;gap:18px;padding:18px 0"]>span[style*="color:#16A34A;font:600 15px"]{display:none}
}
"""


def inject_mobile_css():
    n = 0
    block = f'<style id="kd-mobile">{MOBILE_CSS}</style>'
    for f in sorted(OUT.glob("*.html")):
        t = f.read_text(encoding="utf-8")
        if "<!-- NAV" not in t:
            continue
        out = re.sub(r'<style id="kd-mobile">.*?</style>\n?', "", t, flags=re.S)
        out = out.replace("</head>", block + "\n</head>", 1)
        if out != t:
            f.write_text(out, encoding="utf-8")
            n += 1
    return n


# ── GA klik dinləyicisi bütün səhifələrdə yeni versiyaya ─────────────────────
def inject_click_tracking():
    n = 0
    for f in sorted(OUT.glob("*.html")):
        t = f.read_text(encoding="utf-8")
        out = re.sub(r'<script>document\.addEventListener\("click",function\(e\)\{var a=e\.target\.closest.*?</script>',
                     lambda m: CLICK_JS, t, flags=re.S)
        if out != t:
            f.write_text(out, encoding="utf-8")
            n += 1
    return n


# ── Bloq «Tətbiqi yüklə» → birbaşa mağaza (cihaza görə) ─────────────────────
# 🔴 03.11.2026: bloqdakı bütün «yüklə» düymələri `/#yukle`-yə (ana səhifə) gedirdi —
# telefonda oxucu əvvəl ana səhifəyə, sonra ikinci kliklə mağazaya çatırdı.
# İndi iPhone/iPad → App Store, Android → Google Play (UTM/ct ilə); masaüstündə
# link `/#yukle` qalır (orada hər iki mağaza nişanı var, QR yoxdur).
# `data-kd-store` = yerləşmə adı → Apple `ct`, Play `utm_campaign` (+ utm_content=slug).
BLOG_STORE_PLACEMENTS = [
    # (anchor-un hərfi başlanğıcı, placement)
    ('<a href="/#yukle" style="padding:11px 22px;', "blog_nav"),
    ('<a href="/#yukle" style="padding:13px 26px;', "blog_cta"),
    ('<a href="/#yukle">Keçdim-i yüklə</a>', "blog_related"),
    ('<a href="/#yukle" style="color:#22C55E">', "blog_footer"),
]


def _store_js() -> str:
    apple = APP_STORE + "?" + (f"pt={ASC_PROVIDER_TOKEN}&" if ASC_PROVIDER_TOKEN else "") + "ct="
    return (
        '<script id="kd-store">(function(){var u=navigator.userAgent||"",'
        'ios=/iPhone|iPad|iPod/.test(u)||(/Macintosh/.test(u)&&navigator.maxTouchPoints>1),and=/Android/i.test(u);'
        'if(!ios&&!and)return;var slug=location.pathname.replace(/^\\/|\\.html$/g,"")||"index";'
        'document.querySelectorAll("a[data-kd-store]").forEach(function(a){var c=a.getAttribute("data-kd-store");'
        f'a.href=ios?"{apple}"+c:"{PLAY_STORE}&referrer="+encodeURIComponent("utm_source={UTM_SOURCE}&utm_medium=blog&utm_campaign="+c+"&utm_content="+slug);'
        'a.removeAttribute("target");});})();</script>')


def inject_store_links():
    n = 0
    js = _store_js()
    files = sorted(OUT.glob("bloq-*.html")) + [OUT / "bloq.html"]
    for f in files:
        t = f.read_text(encoding="utf-8")
        out = t
        for start, place in BLOG_STORE_PLACEMENTS:
            tagged = start.replace('<a href="/#yukle"', f'<a href="/#yukle" data-kd-store="{place}"', 1)
            out = out.replace(start, tagged)
        out = re.sub(r'<script id="kd-store">.*?</script>\n?', "", out, flags=re.S)
        if "data-kd-store=" in out:
            out = out.replace("</body>", js + "\n</body>", 1)
        if out != t:
            f.write_text(out, encoding="utf-8")
            n += 1
    return n


# ── llms.txt — AI axtarış/cavab sistemləri üçün saytın qısa xəritəsi ──────────
LLMS_TXT = """# Keçdim

> Keçdim — Azərbaycanda imtahanlara hazırlıq tətbiqi (iOS və Android). Real formatda sınaq
> imtahanları, izahlı suallar, səhvlərin təkrarı və imtahan təqvimi. Azərbaycan dilində.
> Keçdim müstəqil hazırlıq tətbiqidir — DİM, DYP və dövlət qurumları ilə rəsmi əlaqəsi yoxdur.
> Məhsul sahibi: Protech (PROTECH SOLUTIONS GROUP, MMC), Bakı.

## İmtahanlar (tətbiqdəki sınaq formatı)

- Sürücülük · DYP nəzəri imtahanı — 10 sual, 15 dəqiqə, ən çox 1 səhv
- Dövlət Qulluğu — 100 sual, 3 saat; qanunvericilik, məntiq, informatika, Azərbaycan dili
- MİQ (müəllimlərin işə qəbulu) — 60 sual, 150 dəqiqə; ixtisas + tədris metodikası; keçid 40 bal (ixtisas ≥34, metodika ≥6)
- Müəllim sertifikasiyası — 60 sual, 120 dəqiqə; keçid 30 bal
- Magistratura — 95 sual, 3 saat 30 dəqiqə; məntiq, informatika, xarici dil (qapalı test sualları)
- Buraxılış (11-ci sinif) — 56 sual, 3 saat; Azərbaycan dili, xarici dil, riyaziyyat

Sual bazası: {questions} izahlı sual. Formatlar Keçdim-də modelləşdirilir; rəsmi qaydalar dəyişə bilər.

## Qiymət

- Pulsuz: tətbiq qeydiyyatsız işləyir, gündəlik pulsuz sual limiti, səhvlərin təkrarı həmişə pulsuz, offline həll.
- Keçdim+ (saytda bank kartı ilə, birdəfəlik, avtomatik yenilənmir): {plans}.
- Keçdim+ tətbiqdə: App Store / Google Play abunəsi, avtomatik yenilənir; qiymət mağazada göstərilir.

## Əsas səhifələr

- [Ana səhifə]({site}/): imtahanlar, xüsusiyyətlər, qiymət
- [Keçdim+ al]({site}/plus.html): saytda kartla birdəfəlik alış
- [Abunə və ödəniş şərtləri]({site}/odenis.html)
- [İstifadə şərtləri]({site}/terms.html)
- [Məxfilik siyasəti]({site}/privacy.html)
- [Dəstək]({site}/support.html)
- [Bloq]({site}/bloq.html)

## Tətbiq

- [App Store]({apple})
- [Google Play]({play})

## Bloq yazıları

{posts}
"""

# plus_plans cədvəlinin 03.11.2026 canlı dəyərləri (db: code, title, months, price_azn).
PLUS_PLANS_TEXT = "1 ay — 5,99 ₼ · 3 ay — 14,99 ₼ · 1 il — 35,99 ₼"


def write_llms_txt():
    posts = []
    for f in sorted(OUT.glob("bloq-*.html")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"<title>(.*?)(?:\s*\|\s*Keçdim)?</title>", t, re.S)
        title = html.unescape(m.group(1).strip()) if m else f.stem
        posts.append(f"- [{title}]({SITE}/{f.name})")
    body = LLMS_TXT.format(questions=QUESTIONS_LABEL, plans=PLUS_PLANS_TEXT, site=SITE,
                           apple=APP_STORE, play=PLAY_STORE, posts="\n".join(posts))
    (OUT / "llms.txt").write_text(body, encoding="utf-8")
    return len(posts)


# Sitemap-a düşən statik səhifələr (bloq yazıları qovluqdan avtomatik yığılır).
# 🔴 confirmed.html / odenis-netice.html QƏSDƏN yoxdur — axın səhifələridir.
SITEMAP_STATIC = ["plus.html", "odenis.html", "privacy.html", "support.html", "terms.html"]


def write_sitemap():
    # 🔴 03.11.2026: əvvəl siyahı yalnız PAGES + NEW_POSTS-dan qurulurdu — tools/gen_posts.py
    # ilə əlavə olunan 20 yazı və plus.html ora düşmürdü. İndi bloq-*.html faylları
    # qovluqdan yığılır.
    urls = [SITE + "/", SITE + "/bloq.html"] \
        + [SITE + "/" + f.name for f in sorted(OUT.glob("bloq-*.html"))] \
        + [SITE + "/" + n for n in SITEMAP_STATIC if (OUT / n).exists()]
    # 🔴 `lastmod` (04.09.2026): tarix faylın ÖZ dəyişmə vaxtındandır — uydurulmur.
    def _lastmod(u: str) -> str:
        f = OUT / (u.rsplit("/", 1)[-1] or "index.html")
        if not f.exists():
            f = OUT / "index.html"
        return dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).date().isoformat()

    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc><lastmod>{_lastmod(u)}</lastmod></url>\n" for u in urls)
          + "</urlset>\n")
    (OUT / "sitemap.xml").write_text(sm, encoding="utf-8")
    return len(urls)


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
    for name in ("privacy.html", "support.html", "terms.html", "odenis.html", "odenis-netice.html", "plus.html", "confirmed.html"):
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


def _gverify() -> str:
    """GSC meta teqi — token yoxdursa boş sətir (heç nə əlavə olunmur)."""
    if not GOOGLE_VERIFY_META:
        return ""
    return f'<meta name="google-site-verification" content="{GOOGLE_VERIFY_META}">\n'


def post() -> None:
    """Çıxış fayllarına post-proses qaydaları — dizayn mənbəyi lazım DEYİL.

    Tam qurmadan sonra `main()` bunu çağırır; mənbə əlçatmaz olanda (bax SRC
    qeydi) və ya `tools/gen_posts.py`-dan sonra `python3 build.py --post` ilə
    tək işlədilir. Hər addım idempotentdir.
    """
    inject_ga_static()
    fx = fix_facts()        # əvvəl: köhnə çıxış mətnlərini yeni dəyərlərə köçürür
    px = fix_pricing()
    ck = inject_click_tracking()
    st = inject_store_links()
    mb = inject_mobile_css()
    nurl = write_sitemap()
    nl = write_llms_txt()
    # IndexNow açarı — Bing/Yandex-ə yeni URL-ləri dərhal bildirmək üçün.
    # 🔴 Google IndexNow-u DƏSTƏKLƏMİR (onun sitemap ping-i də 2023-də ləğv olundu),
    # ona görə Google tərəfi Search Console ilə gedir.
    INDEXNOW_KEY = "b94b7b1f07f2d56218179b68ae0496ad"
    (OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")

    # Google «HTML faylı» üsulu — məzmun faylın öz adından ibarətdir.
    if GOOGLE_VERIFY_FILE:
        (OUT / GOOGLE_VERIFY_FILE).write_text(
            f"google-site-verification: {GOOGLE_VERIFY_FILE}\n", encoding="utf-8")
        print(f"   + GSC doğrulama faylı: {GOOGLE_VERIFY_FILE}")

    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    print(f"   + qiymət bloku: {px} əvəzləmə · fakt düzəlişi: {fx} əvəzləmə")
    print(f"   + klik ölçməsi yeniləndi: {ck} səhifə · bloq mağaza linkləri: {st} səhifə")
    print(f"   + mobil başlıq CSS: {mb} səhifə")
    print(f"   + sitemap.xml ({nurl} URL) + robots.txt + llms.txt ({nl} yazı)")


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
    rel = inject_related()
    print(f"   ↳ {n} yeni yazı bloq siyahısına əlavə edildi")
    print(f"✅ {len(written)} səhifə quruldu: {', '.join(written)}")
    print(f"   + «Oxşar yazılar» bloku: {rel} səhifə")
    print("   🔴 tools/gen_posts.py yazıları üçün: python3 tools/gen_posts.py && python3 build.py --post")
    post()


if __name__ == "__main__":
    import sys
    if "--post" in sys.argv:
        post()
    else:
        main()
