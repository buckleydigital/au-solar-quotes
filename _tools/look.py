#!/usr/bin/env python3
"""Run: python3 _tools/look.py .   (re-applies the styles; safe to re-run)
AU Solar Quotes visual refresh: dark emerald hero matching the logo,
form-first on mobile, stronger quote card. Idempotent."""
import os, re, sys

ROOT = sys.argv[1]

CSS = r"""/* @look-css */
  /* ==========================================================
     Brand refresh: near-black + emerald, matching the logo.
     Dark hero with the quote card as the focal point; form
     first on phones; rounded cards below the fold.
     ========================================================== */
  :root{
    --accent:#0a7f55; --accent-d:#086645; --go:#2ed98f; --go-d:#22c47e; --glow:46,217,142;
    --ink:#06140f; --ink2:#344841; --muted:#5f716a; --faint:#8d9b95;
    --band:#f2f7f4; --line:#dde6e1; --line2:#c8d5ce; --ok:#0b8a5a;
    --r:10px; --r-lg:16px;
  }
  body{background:#fff}
  header{background:rgba(255,255,255,.96);border-bottom:1px solid rgba(6,20,15,.08)}
  .cta{background:var(--go);color:var(--ink);font-weight:700;border-radius:999px;padding:10px 20px;box-shadow:0 6px 18px -8px rgba(var(--glow),.9)}
  .cta:hover{background:var(--go-d)}

  /* ---- dark hero (full-bleed band behind .wrap.hero) ---- */
  .hero{position:relative;isolation:isolate;padding-block:clamp(40px,6vw,76px) clamp(44px,6vw,80px);
    --ink:#fff; --ink2:rgba(255,255,255,.78); --muted:rgba(255,255,255,.6); --line:rgba(255,255,255,.14); --ok:var(--go)}
  .hero::before{content:'';position:absolute;inset:0 calc(50% - 50vw);z-index:-1;
    background:
      radial-gradient(720px 420px at 82% 18%,rgba(var(--glow),.26),transparent 62%),
      radial-gradient(560px 380px at 6% 96%,rgba(var(--glow),.12),transparent 64%),
      linear-gradient(180deg,#05110c 0%,#0a1d16 100%)}
  .hero::after{content:'';position:absolute;inset:0 calc(50% - 50vw);z-index:-1;opacity:.5;
    background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);
    background-size:44px 44px;-webkit-mask-image:radial-gradient(ellipse 70% 80% at 30% 40%,#000 20%,transparent 75%);mask-image:radial-gradient(ellipse 70% 80% at 30% 40%,#000 20%,transparent 75%)}
  .hero-grid{align-items:center}
  .hero h1{color:#fff;font-size:clamp(2.3rem,4.8vw,3.6rem);letter-spacing:-.035em}
  .hero h1 .hl{color:var(--go)}
  .hero h1 .hl::after{background:var(--go);opacity:.22;height:.2em}
  .hero .eyebrow{border-color:rgba(var(--glow),.35);background:rgba(var(--glow),.08);color:#d6f7e8}
  .hero .sub{font-size:1.08rem;max-width:540px}
  .hero .tick{color:rgba(255,255,255,.86)}
  .hero .trust-pill{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.14);color:rgba(255,255,255,.82);border-radius:999px}

  /* ---- quote card: light island on the dark hero ---- */
  .survey-card{--ink:#06140f; --ink2:#344841; --muted:#5f716a; --line:#dde6e1; --ok:#0b8a5a;
    border:none;border-radius:var(--r-lg);color:var(--ink);
    box-shadow:0 0 0 1px rgba(var(--glow),.45),0 0 70px -12px rgba(var(--glow),.45),0 34px 70px -28px rgba(0,0,0,.75)}
  .card-head{background:linear-gradient(120deg,#0a7f55 0%,#0f9a68 60%,#16b07a 100%);padding:20px 24px}
  .card-head .t{font-size:1.22rem;letter-spacing:-.02em}
  .card-head .s{opacity:.92}
  .survey-progress{padding:16px 24px 0}
  .progbar{height:6px;border-radius:99px;background:#e6eee9}
  .progbar>i{background:linear-gradient(90deg,var(--accent),var(--go));border-radius:99px}
  .card-body{padding:20px 24px 22px}
  .q{font-size:1.24rem;letter-spacing:-.02em}
  .choice-card,.choice-h{border-radius:12px;padding:16px 18px;font-size:1rem;font-weight:600;border:1.5px solid var(--line2);box-shadow:0 1px 0 rgba(6,20,15,.04);transition:transform .12s,border-color .12s,background .12s,box-shadow .12s}
  .choice-card:hover,.choice-h:hover{border-color:var(--accent);background:#f3fbf7;transform:translateY(-1px);box-shadow:0 8px 18px -12px rgba(10,127,85,.6)}
  .choice-card.selected,.choice-h.selected{border-color:var(--accent);background:#eaf8f1;box-shadow:inset 0 0 0 1px var(--accent)}
  .choice-card span{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#eef4f1;color:var(--accent)}
  .choice-card:hover span{background:var(--accent);color:#fff}
  .fld input{border-radius:10px;padding:13px 14px}
  .fld input:focus{box-shadow:0 0 0 4px rgba(var(--glow),.2)}
  .btn{background:var(--go);color:var(--ink);border-radius:12px;padding:16px;font-size:1.04rem;box-shadow:0 10px 24px -12px rgba(var(--glow),1)}
  .btn:hover{background:var(--go-d)}
  .btn:disabled{opacity:.5;box-shadow:none}
  .card-foot{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 16px;padding:12px 18px;border-top:1px solid var(--line);background:#f7faf8;font-size:.76rem;font-weight:600;color:var(--muted)}
  .card-foot span{display:inline-flex;align-items:center;gap:5px}
  .card-foot svg{width:13px;height:13px;color:var(--ok)}

  /* ---- stat rail continues the dark band ---- */
  .statrail{background:#0a1d16;border:none;border-top:1px solid rgba(255,255,255,.08)}
  .stat{border-left-color:rgba(255,255,255,.08)}
  .stat .n{color:var(--go);font-size:2rem}
  .stat .l{color:rgba(255,255,255,.66)}

  /* ---- sections: rounded cards instead of ruled boxes ---- */
  .sec.alt{background:var(--band);border:none}
  .sec-eyebrow{color:var(--accent)}
  .sec-title{letter-spacing:-.03em}
  .rail,.why-grid,.assure,.arealist{gap:14px;border:none;overflow:visible;background:none}
  .rail .r,.why-card,.ai,.arealist .ac{background:#fff;border:1px solid var(--line) !important;border-radius:var(--r-lg);box-shadow:0 12px 30px -24px rgba(6,20,15,.45)}
  .rail .num{color:var(--accent)}
  .rail .r::before{content:'';display:block;width:36px;height:4px;border-radius:4px;background:linear-gradient(90deg,var(--accent),var(--go));margin-bottom:16px}
  .why-ic{background:linear-gradient(135deg,var(--accent),#12a873);border-radius:10px;box-shadow:0 8px 18px -10px rgba(10,127,85,.8)}
  .ai{border-radius:12px}
  .dtable{border-radius:var(--r-lg);overflow:hidden;border-collapse:separate;border-spacing:0}
  .faq-q svg{color:var(--accent)}
  .cta-band{position:relative;overflow:hidden;border-radius:20px;
    background:radial-gradient(520px 260px at 90% 0%,rgba(var(--glow),.3),transparent 65%),linear-gradient(135deg,#05110c,#0c241b)}
  .cta-band a{background:var(--go);color:var(--ink);border-radius:999px;box-shadow:0 10px 26px -10px rgba(var(--glow),1)}
  footer{border-top:none}
  .mobile-cta{transition:transform .25s,opacity .25s}
  .mobile-cta.hide{transform:translateY(140%);opacity:0;pointer-events:none}
  .mobile-cta{background:var(--go) !important;color:var(--ink) !important;border-radius:999px !important}

  /* battery pages: their own sheet loads later, so these need the extra 'body' weight */
  body .bt-btn{background:var(--go);color:var(--ink) !important;border-radius:999px;box-shadow:0 10px 24px -12px rgba(var(--glow),1)}
  body .bt-btn:hover{background:var(--go-d)}
  body .bt-deadline{border-radius:var(--r-lg);border:1px solid rgba(var(--glow),.55);box-shadow:0 0 50px -18px rgba(var(--glow),.55),0 20px 40px -30px rgba(6,20,15,.5)}
  body .bt-count div{border-radius:10px}
  body .bt-stats,body .bt-steps{gap:14px;border:none;overflow:visible;background:none}
  body .bt-stats>div,body .bt-steps>div{background:#fff;border:1px solid var(--line) !important;border-radius:var(--r-lg);box-shadow:0 12px 30px -24px rgba(6,20,15,.45)}
  body .bt-steps>div::before{content:'';display:block;width:36px;height:4px;border-radius:4px;background:linear-gradient(90deg,var(--accent),var(--go));margin-bottom:16px}
  body .bt-steps .n{color:var(--accent);padding:0;border:0 !important}
  body .bt-calc{border:1px solid var(--line);border-radius:var(--r-lg);box-shadow:0 18px 40px -30px rgba(6,20,15,.5)}
  body .bt-card,body .bt-areas a{border-radius:var(--r-lg)}
  @media(max-width:960px){
    /* form first on phones: headline, one line, then the card */
    .hero-copy{display:contents}
    .hero-grid{gap:0}
    .hero .eyebrow{order:1;justify-self:start;margin-bottom:14px}
    .hero h1{order:2;font-size:clamp(2rem,8.4vw,2.6rem);margin-bottom:10px}
    .hero .sub{display:none}
    .hero h1{margin-bottom:20px}
    .survey-card{order:4}
    .hero .ticks{order:5;margin:26px 0 16px}
    .hero .trust-pills{order:6}
    .statrail .in{grid-template-columns:1fr 1fr}
    .stat:nth-child(n+3){border-top-color:rgba(255,255,255,.08)}
    .rail .r,.why-card,.ai{border-top:1px solid var(--line) !important}
  }
  @media(max-width:560px){
    .hero{padding-top:26px}
    .card-head{padding:16px 18px}
    .survey-progress{padding:14px 18px 0}
    .card-body{padding:16px 18px 18px}
  }
/* @end-look-css */
"""

CARD_FOOT = ('\n    <div class="card-foot">'
             '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>Free, no obligation</span>'
             '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>One installer only</span>'
             '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>Never resold</span>'
             '</div>')

JS = ("<script>/* @look-js: hide the floating quote button while the quote card is on screen */"
      "(function(){var c=document.getElementById('quote'),m=document.querySelector('.mobile-cta');"
      "if(!c||!m||!('IntersectionObserver' in window))return;"
      "new IntersectionObserver(function(e){m.classList.toggle('hide',e[0].isIntersecting)},{threshold:.15}).observe(c)})();</script>\n")

n = 0
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if not d.startswith(('.', '_'))]
    for fn in fns:
        if not fn.endswith('.html'):
            continue
        p = os.path.join(dp, fn)
        h = open(p, encoding='utf-8').read()
        if 'AU SOLAR QUOTES - "national grid"' not in h:
            continue
        h = re.sub(r'/\* @look-css \*/.*?/\* @end-look-css \*/\n', '', h, flags=re.S)
        i = h.index('</style>')          # first <style> = the shared sheet
        h = h[:i] + CSS + h[i:]
        if 'class="hero-grid"' in h:
            h = h.replace('<div class="hero-grid">\n    <div>', '<div class="hero-grid">\n    <div class="hero-copy">', 1)
            assert 'class="hero-copy"' in h, p
            if 'class="card-foot"' not in h:
                # card-foot goes right after the card-body closes, inside the card
                h, k = re.subn(r'(<div class="step" id="stepDone"></div>\n      </div>)', r'\1' + CARD_FOOT.replace('\\', r'\\'), h, count=1)
                assert k == 1, p
        if '<a href="#quote" class="mobile-cta"' in h and '@look-js' not in h:
            h, k = re.subn(r'(<a href="#quote" class="mobile-cta"[^\n]*</a>\n)', lambda m: m.group(1) + JS, h, count=1)
            assert k == 1, p
        open(p, 'w', encoding='utf-8').write(h)
        n += 1
print('styled', n, 'pages')
