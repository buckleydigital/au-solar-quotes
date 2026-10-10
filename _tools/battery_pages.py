#!/usr/bin/env python3
"""
Generate the /battery/ pages on all three solar funnel sites.

    python3 _tools/battery_pages.py            # from au-solar-quotes, siblings alongside

Each battery page is built FROM that brand's own solar page for the same
region, so it keeps the brand's CSS, header, footer, tracking and the lead
form plumbing exactly as they are. What changes:

  * head      - title/description/canonical/JSON-LD rewritten for battery
  * hero      - battery copy, 6-step form (adds "do you already have solar?")
  * body      - rebate education, countdown, calculator, local battery notes
  * links     - nearby-area and footer links point at /battery/<slug>/
  * script    - NICHE='battery' so submit-lead routes to battery engines,
                plus has_solar / battery_project (land in leads.extra)

The rebate figures are the Cheaper Home Batteries Program schedule as of
October 2026: STC factor 6.8 until 31 Dec 2026, 5.7 from 1 Jan 2027, 5.2 from
1 Jul 2027; full rate on the first 14 kWh, 60% on 14-28 kWh, 15% on 28-50 kWh.
Dollar figures assume ~$37 per STC. When the schedule moves, change RATES
below and re-run. Time-sensitive headlines also swap themselves client-side
once 1 Jan 2027 passes (data-bt-after), so the pages never claim a cut that
has already happened is still coming.

This directory starts with an underscore, so GitHub Pages (Jekyll) does not
publish it.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

STC_PRICE = 37          # AUD per certificate, approximate market value
FACTOR_NOW = 6.8        # 1 May - 31 Dec 2026
FACTOR_JAN = 5.7        # 1 Jan - 30 Jun 2027
FACTOR_JUL = 5.2        # 1 Jul - 31 Dec 2027
CUT_DATE_ISO = '2027-01-01T00:00:00+11:00'   # midnight AEDT
CUT_JUL_ISO = '2027-07-01T00:00:00+10:00'

BRANDS = {
    'au-solar-quotes': dict(domain='ausolarquotes.com.au', name='AU Solar Quotes', radius='4px'),
    'clear-solar-quotes': dict(domain='clearsolarquotes.com.au', name='Clear Solar Quotes', radius='14px'),
    'premium-solar-quotes': dict(domain='premiumsolarquotes.com.au', name='Premium Solar Quotes', radius='2px'),
}

STATES = {
    'Queensland': ('QLD', 'queensland'),
    'New South Wales': ('NSW', 'new-south-wales'),
    'Victoria': ('VIC', 'victoria'),
    'Western Australia': ('WA', 'western-australia'),
    'South Australia': ('SA', 'south-australia'),
    'Australian Capital Territory': ('ACT', 'australian-capital-territory'),
}

# slug: (display name, state, network)
REGIONS = {
    'brisbane': ('Brisbane', 'Queensland', 'Energex'),
    'gold-coast': ('Gold Coast', 'Queensland', 'Energex'),
    'sunshine-coast': ('Sunshine Coast', 'Queensland', 'Energex'),
    'toowoomba': ('Toowoomba', 'Queensland', 'Ergon Energy'),
    'cairns': ('Cairns', 'Queensland', 'Ergon Energy'),
    'rockhampton': ('Rockhampton', 'Queensland', 'Ergon Energy'),
    'bundaberg': ('Bundaberg', 'Queensland', 'Ergon Energy'),
    'hervey-bay': ('Hervey Bay', 'Queensland', 'Ergon Energy'),
    'queensland': ('Queensland', 'Queensland', 'Energex in the south-east, Ergon Energy everywhere else'),
    'sydney': ('Sydney', 'New South Wales', 'Ausgrid or Endeavour Energy, depending on your suburb'),
    'central-coast': ('Central Coast', 'New South Wales', 'Ausgrid'),
    'newcastle': ('Newcastle', 'New South Wales', 'Ausgrid'),
    'wollongong': ('Wollongong', 'New South Wales', 'Endeavour Energy'),
    'albury-wodonga': ('Albury/Wodonga', 'New South Wales', 'Essential Energy on the Albury side, AusNet Services on the Wodonga side'),
    'coffs-harbour': ('Coffs Harbour', 'New South Wales', 'Essential Energy'),
    'port-macquarie': ('Port Macquarie', 'New South Wales', 'Essential Energy'),
    'tamworth': ('Tamworth', 'New South Wales', 'Essential Energy'),
    'new-south-wales': ('New South Wales', 'New South Wales', 'Ausgrid, Endeavour Energy or Essential Energy'),
    'melbourne': ('Melbourne', 'Victoria', 'CitiPower, Jemena, United Energy, AusNet Services or Powercor, depending on your suburb'),
    'dandenong': ('Dandenong', 'Victoria', 'United Energy or AusNet Services, depending on your street'),
    'frankston-mornington-peninsula': ('Frankston / Mornington Peninsula', 'Victoria', 'United Energy'),
    'geelong': ('Geelong', 'Victoria', 'Powercor'),
    'ballarat': ('Ballarat', 'Victoria', 'Powercor'),
    'bendigo': ('Bendigo', 'Victoria', 'Powercor'),
    'mildura': ('Mildura', 'Victoria', 'Powercor'),
    'shepparton': ('Shepparton', 'Victoria', 'Powercor'),
    'warragul': ('Warragul', 'Victoria', 'AusNet Services'),
    'victoria': ('Victoria', 'Victoria', 'one of five distribution networks'),
    'perth': ('Perth', 'Western Australia', 'Western Power (Synergy is the retailer)'),
    'mandurah': ('Mandurah', 'Western Australia', 'Western Power (Synergy is the retailer)'),
    'bunbury': ('Bunbury', 'Western Australia', 'Western Power (Synergy is the retailer)'),
    'western-australia': ('Western Australia', 'Western Australia', 'Western Power on the main grid, Horizon Power in regional towns'),
    'adelaide': ('Adelaide', 'South Australia', 'SA Power Networks'),
    'south-australia': ('South Australia', 'South Australia', 'SA Power Networks'),
    'canberra': ('Canberra', 'Australian Capital Territory', 'Evoenergy'),
    'australian-capital-territory': ('Australian Capital Territory', 'Australian Capital Territory', 'Evoenergy'),
}
STATE_SLUGS = {v[1] for v in STATES.values()}


# ─────────────────────────────── rebate maths ───────────────────────────────
def rebate(kwh, factor):
    band = min(kwh, 14) + 0.6 * max(0, min(kwh, 28) - 14) + 0.15 * max(0, min(kwh, 50) - 28)
    return band * factor * STC_PRICE


def money(v):
    return '${:,}'.format(int(round(v / 10.0) * 10))


PER_KWH_NOW = '$' + str(int(round(FACTOR_NOW * STC_PRICE)))
PER_KWH_JAN = '$' + str(int(round(FACTOR_JAN * STC_PRICE)))
CUT_PCT = int(round((1 - FACTOR_JAN / FACTOR_NOW) * 100))
EX = {k: (rebate(k, FACTOR_NOW), rebate(k, FACTOR_JAN)) for k in (10, 13.5, 20)}


def ex_line(k):
    a, b = EX[k]
    return '%s kWh: about %s now, about %s from 1 January - roughly %s less' % (
        ('%g' % k), money(a), money(b), money(a - b))


# ─────────────────────────────── shared bits ────────────────────────────────
TICK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>'
TICK_OK = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>'
PLUS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'


def esc(s):
    return html.escape(s, quote=True)


def faq_item(q, a):
    return ('<div class="faq-item"><button class="faq-q" type="button" aria-expanded="false" '
            'onclick="toggleFaq(this)">%s%s</button><div class="faq-a"><div>%s</div></div></div>' % (q, PLUS, a))


def ai(strong, text):
    return '<div class="ai">%s<span><strong>%s</strong> %s</span></div>' % (TICK, strong, text)


BT_CSS = r"""
<style id="bt-css">
  /* battery pages: components layered on the brand's own tokens */
  :root{ --bt-r:__RADIUS__; --bt-card:var(--card,var(--paper,#fff)); --bt-band:color-mix(in srgb,var(--accent) 6%,var(--bt-card)); }
  .bt-banner{background:var(--accent);color:#fff;font-size:.86rem;font-weight:600;text-align:center;padding:9px 16px;line-height:1.4}
  .bt-banner a{color:#fff;text-decoration:underline;text-underline-offset:2px}
  .bt-banner b{font-variant-numeric:tabular-nums}
  .bt-band{background:var(--bt-band);border-block:1px solid var(--line)}
  .bt-deadline{display:grid;grid-template-columns:auto 1fr auto;gap:clamp(18px,3vw,36px);align-items:center;background:var(--bt-card);border:1.5px solid var(--accent);border-radius:var(--bt-r);padding:clamp(20px,3vw,30px);box-shadow:0 18px 40px -26px rgba(0,0,0,.35);color:var(--ink);text-align:left}
  .bt-count{display:flex;gap:10px}
  .bt-count div{min-width:64px;text-align:center;border:1px solid var(--line);border-radius:var(--bt-r);padding:10px 6px;background:var(--bt-band)}
  .bt-count b{display:block;font-size:1.9rem;line-height:1;color:var(--accent);font-variant-numeric:tabular-nums}
  .bt-count span{display:block;font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-top:5px}
  .bt-deadline h2{font-size:clamp(1.2rem,2.2vw,1.55rem);margin-bottom:6px}
  .bt-deadline p{color:var(--ink2);font-size:.93rem;margin:0}
  .bt-btn{display:inline-block;background:var(--accent);color:#fff !important;border-radius:var(--bt-r);padding:14px 22px;font-weight:700;font-size:.97rem;white-space:nowrap;text-decoration:none;text-align:center}
  .bt-btn:hover{background:var(--accent-d,var(--accent))}
  .bt-stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);border-radius:var(--bt-r);overflow:hidden;background:var(--bt-card);margin-top:18px}
  .bt-stats div{padding:18px 16px;border-left:1px solid var(--line)}
  .bt-stats div:first-child{border-left:none}
  .bt-stats b{display:block;font-size:1.45rem;color:var(--accent);line-height:1.1;font-variant-numeric:tabular-nums}
  .bt-stats span{display:block;font-size:.8rem;color:var(--muted);margin-top:5px}
  .bt-timeline{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border:1px solid var(--line);border-radius:var(--bt-r);overflow:hidden;background:var(--bt-card);text-align:left}
  .bt-timeline .t{padding:20px 18px;border-left:1px solid var(--line);position:relative}
  .bt-timeline .t:first-child{border-left:none}
  .bt-timeline .t.now{background:var(--bt-band);box-shadow:inset 0 3px 0 var(--accent)}
  .bt-timeline .d{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
  .bt-timeline .f{font-size:1.6rem;font-weight:700;color:var(--ink);line-height:1;font-variant-numeric:tabular-nums}
  .bt-timeline .f small{font-size:.75rem;font-weight:600;color:var(--muted);margin-left:4px}
  .bt-timeline .k{font-size:.86rem;color:var(--ink2);margin-top:8px}
  .bt-timeline .tag{display:inline-block;font-size:.66rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:var(--accent);color:#fff;border-radius:3px;padding:2px 7px;margin-bottom:8px}
  .bt-prose{max-width:760px;margin:26px auto 0;color:var(--ink2);text-align:left}
  .bt-prose p{margin-bottom:13px}
  .bt-prose strong{color:var(--ink)}
  .bt-callout{border-left:3px solid var(--accent);background:var(--bt-band);padding:14px 18px;border-radius:0 var(--bt-r) var(--bt-r) 0;margin:18px 0;color:var(--ink)}
  .bt-calc{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1.5px solid var(--ink);border-radius:var(--bt-r);overflow:hidden;background:var(--bt-card);text-align:left}
  .bt-calc .in{padding:clamp(20px,3vw,30px);border-right:1px solid var(--line)}
  .bt-calc .out{padding:clamp(20px,3vw,30px);background:var(--bt-band)}
  .bt-calc label{display:block;font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin-bottom:10px}
  .bt-calc .size{font-size:2.3rem;font-weight:700;color:var(--ink);line-height:1;margin-bottom:12px;font-variant-numeric:tabular-nums}
  .bt-calc .size small{font-size:.95rem;color:var(--muted);font-weight:600}
  .bt-calc input[type=range]{width:100%;accent-color:var(--accent);height:28px}
  .bt-calc .presets{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}
  .bt-calc .presets button{border:1px solid var(--line2);background:var(--bt-card);color:var(--ink2);border-radius:100px;padding:6px 12px;font-size:.8rem;font-weight:600;cursor:pointer;font-family:inherit}
  .bt-calc .presets button.on,.bt-calc .presets button:hover{border-color:var(--accent);color:var(--accent)}
  .bt-calc .row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);font-size:.93rem;color:var(--ink2)}
  .bt-calc .row b{font-size:1.25rem;color:var(--ink);font-variant-numeric:tabular-nums}
  .bt-calc .row.loss b{color:var(--err)}
  .bt-calc .note{font-size:.75rem;color:var(--muted);margin-top:12px;line-height:1.5}
  .bt-table{width:100%;border-collapse:collapse;font-size:.92rem;border:1px solid var(--line);background:var(--bt-card);text-align:left}
  .bt-table caption{text-align:left;font-size:.82rem;color:var(--muted);padding-bottom:10px}
  .bt-table th,.bt-table td{padding:13px 15px;border-bottom:1px solid var(--line);vertical-align:top}
  .bt-table thead th{font-size:.76rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink2);background:var(--bt-band)}
  .bt-table td:first-child{font-weight:700;color:var(--ink)}
  .bt-table td{color:var(--ink2);font-variant-numeric:tabular-nums}
  .bt-two{display:grid;grid-template-columns:1fr 1fr;gap:18px;text-align:left}
  .bt-card{background:var(--bt-card);border:1px solid var(--line);border-radius:var(--bt-r);padding:22px 22px 10px}
  .bt-card h3{font-size:1.06rem;margin-bottom:12px}
  .bt-card ul{list-style:none;margin:0;padding:0}
  .bt-card li{display:flex;gap:10px;align-items:flex-start;font-size:.9rem;color:var(--ink2);margin-bottom:12px}
  .bt-card li svg{flex:0 0 auto;margin-top:4px;color:var(--accent)}
  .bt-card.no li svg{color:var(--muted)}
  .bt-areas{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:left}
  .bt-areas a{display:block;border:1px solid var(--line);border-radius:var(--bt-r);padding:12px 14px;background:var(--bt-card);color:var(--ink);font-weight:600;font-size:.92rem}
  .bt-areas a:hover{border-color:var(--accent);color:var(--accent)}
  .bt-areas a span{display:block;font-size:.76rem;color:var(--muted);font-weight:500}
  .bt-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border:1px solid var(--line);border-radius:var(--bt-r);overflow:hidden;background:var(--bt-card);text-align:left}
  .bt-steps div{padding:24px 22px;border-left:1px solid var(--line)}
  .bt-steps div:first-child{border-left:none}
  .bt-steps .n{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:10px}
  .bt-steps h3{font-size:1.04rem;margin-bottom:7px}
  .bt-steps p{font-size:.89rem;color:var(--muted)}
  .bt-sec-cta{text-align:center;margin-top:28px}
  .faq-item.open .faq-a{max-height:1100px}
  @media(max-width:900px){
    .bt-deadline{grid-template-columns:1fr;text-align:left}
    .bt-stats{grid-template-columns:1fr 1fr}
    .bt-stats div:nth-child(3){border-left:none}
    .bt-stats div:nth-child(n+3){border-top:1px solid var(--line)}
    .bt-timeline{grid-template-columns:1fr 1fr}
    .bt-timeline .t:nth-child(3){border-left:none}
    .bt-timeline .t:nth-child(n+3){border-top:1px solid var(--line)}
    .bt-calc,.bt-two,.bt-steps{grid-template-columns:1fr}
    .bt-calc .in{border-right:none;border-bottom:1px solid var(--line)}
    .bt-steps div{border-left:none;border-top:1px solid var(--line)}
    .bt-steps div:first-child{border-top:none}
    .bt-areas{grid-template-columns:1fr 1fr}
    .bt-table{font-size:.86rem}
    .bt-table th,.bt-table td{padding:10px 10px}
  }
  @media(max-width:520px){ .bt-count div{min-width:0;flex:1} .bt-areas{grid-template-columns:1fr} .bt-timeline{grid-template-columns:1fr} .bt-timeline .t{border-left:none !important;border-top:1px solid var(--line)} .bt-timeline .t:first-child{border-top:none} }
</style>
"""

BT_JS = r"""
/* ─── battery: countdown, after-deadline copy swap, rebate calculator ─── */
var BT_CUT = new Date('__CUT__').getTime(), BT_JUL = new Date('__JUL__').getTime();
var BT_STC = __STC__, BT_F_NOW = __FNOW__, BT_F_JAN = __FJAN__, BT_F_JUL = __FJUL__;
(function(){
  var now = Date.now();
  // After 1 Jan 2027 the "it drops on 1 January" copy is wrong; swap to the
  // alternate wording carried on the element, and count to 1 July instead.
  if(now >= BT_CUT){
    document.querySelectorAll('[data-bt-after]').forEach(function(el){ el.innerHTML = el.getAttribute('data-bt-after'); });
    BT_F_NOW = BT_F_JAN; BT_F_JAN = BT_F_JUL; BT_CUT = BT_JUL;
  }
  function tick(){
    var ms = Math.max(0, BT_CUT - Date.now());
    var d = Math.floor(ms/864e5), h = Math.floor(ms%864e5/36e5), m = Math.floor(ms%36e5/6e4);
    document.querySelectorAll('[data-bt-days]').forEach(function(el){ el.textContent = d; });
    var H = document.getElementById('bt-h'), M = document.getElementById('bt-m'), D = document.getElementById('bt-d');
    if(D) D.textContent = d; if(H) H.textContent = h; if(M) M.textContent = m;
  }
  tick(); setInterval(tick, 30000);
})();
function btRebate(k, f){
  var band = Math.min(k,14) + 0.6*Math.max(0, Math.min(k,28)-14) + 0.15*Math.max(0, Math.min(k,50)-28);
  return band * f * BT_STC;
}
function btMoney(v){ return '$' + (Math.round(v/10)*10).toLocaleString('en-AU'); }
function btCalc(k){
  k = parseFloat(k); var r = document.getElementById('bt-range'); if(!r) return;
  r.value = k;
  document.getElementById('bt-size').textContent = (k % 1 ? k.toFixed(1) : k);
  var a = btRebate(k, BT_F_NOW), b = btRebate(k, BT_F_JAN);
  document.getElementById('bt-now').textContent = '~' + btMoney(a);
  document.getElementById('bt-jan').textContent = '~' + btMoney(b);
  document.getElementById('bt-loss').textContent = '~' + btMoney(a - b);
  document.querySelectorAll('.bt-calc .presets button').forEach(function(x){ x.classList.toggle('on', parseFloat(x.getAttribute('data-k')) === k); });
}
function btCalcUsed(){ if(!window._btCalcUsed){ window._btCalcUsed = 1; track('rebate_calculator', { action:'used' }); } }
btCalc(13.5);
"""

# ─────────────────────────────── per-state copy ─────────────────────────────
def state_local(state, R, net):
    """Return (intro, assure items, faq list) for the local section."""
    in_R = R
    if state == 'Queensland':
        incentive = ("Queensland's own battery rebate (the Battery Booster) has closed, so the federal discount is the incentive that "
                     "matters here. Some retailers pay a sign-up credit for joining their virtual power plant - worth asking about, "
                     "but compare it against the plan's rates rather than taking the credit at face value.")
        items = [
            ai('Exports are worth very little.', 'Feed-in tariffs on most Queensland plans have fallen to single-digit cents, while power bought back in the evening costs several times that. A battery earns its keep by storing the midday surplus instead of selling it cheap.'),
            ai('Storm season and outages.', 'Summer storms knock power out across %s. A battery only keeps the lights on in a blackout if it is installed with backup - many are not by default. Ask whether the quote covers essential circuits or the whole home.' % in_R),
            ai('Heat shortens battery life.', 'Most batteries throttle in high heat. A shaded wall or garage beats a west-facing wall in full afternoon sun, and a good installer will say where it should go and why.'),
            ai('Network rules.', 'Your network is %s. Export limits and any dynamic-export requirement are set at connection, so they belong on the quote, not discovered after.' % net),
        ]
    elif state == 'New South Wales':
        incentive = ("NSW stacks a state incentive on top of the federal discount through the Peak Demand Reduction Scheme, paid when "
                     "your battery is connected to an approved virtual power plant. It is commonly quoted at up to around $1,500, with "
                     "the net amount depending on the provider. Ask your installer whether it applies to the battery and VPP being quoted.")
        items = [
            ai('Stacked incentives.', 'The federal discount plus the NSW VPP incentive can both apply to one install - but only if the battery and VPP meet both sets of rules. Get both itemised on the quote.'),
            ai('Exporting is getting less attractive.', 'Feed-in tariffs have fallen to a few cents on many NSW plans, and some networks have introduced two-way tariffs on certain plans that can charge for midday exports. Storing beats selling.'),
            ai('Evening peak pricing.', 'Time-of-use plans charge the most between late afternoon and evening - exactly when a battery charged by your panels does its work.'),
            ai('Network rules.', 'Your network is %s. Export limits and connection approval come from the network, so ask the installer to confirm what applies at your address.' % net),
        ]
    elif state == 'Victoria':
        incentive = ("Victoria's state battery rebate under Solar Homes has closed, so the federal discount is the main incentive for "
                     "%s homes - which makes its 1 January step-down matter more here than in states that still stack a second rebate." % in_R)
        items = [
            ai('Feed-in tariffs are close to nothing.', "Victoria's minimum feed-in tariff has been cut to a few cents or less, so the gap between exporting a kilowatt-hour and buying one back in the evening is wide."),
            ai('Size for winter, not just summer.', 'Victorian winters cut solar output hard. A battery sized to fill on a January afternoon may never fill in June, so a good quote shows both seasons.'),
            ai('Going all-electric.', 'Households swapping gas for heat pumps and induction lift their evening use - which is when a battery pays its way.'),
            ai('Network rules.', 'Your network is %s. Export limits are set by the network, so ask what applies at your address before agreeing on a size.' % net),
        ]
    elif state == 'Western Australia':
        incentive = ("WA adds its own Residential Battery Scheme on top of the federal discount. Synergy customers have been able to "
                     "claim a state rebate (reported at up to $1,300), Horizon Power customers more, provided the battery joins the "
                     "approved virtual power plant - and interest-free loans have been offered to eligible households. Terms change, so "
                     "your installer should confirm what is open when you sign.")
        items = [
            ai('Two rebates, one condition.', 'The WA rebate requires VPP enrolment and a compatible battery. Check both before you choose a brand, not after.'),
            ai('Evening exports pay more.', "Synergy's buyback pays more for exports in the late-afternoon-to-evening window than in the middle of the day, which suits a battery that charges at noon and discharges later."),
            ai('Heat placement.', 'Perth-region summers are hard on batteries. Shade and airflow matter, and the installer should say where it is going and why.'),
            ai('Network rules.', 'Your network is %s. Connection approval and any export limits come from the network.' % net),
        ]
    elif state == 'South Australia':
        incentive = ("South Australia has no state battery rebate at the moment, so the federal discount is the incentive to catch. "
                     "What SA does have is the most developed virtual power plant market in the country - VPP offers here can be "
                     "genuinely worth comparing, as long as the plan's rates hold up too.")
        items = [
            ai('Some of the highest prices in the country.', 'SA evening electricity prices are among the steepest in Australia, which is exactly the power a battery replaces.'),
            ai('Very high solar penetration.', 'With so much rooftop solar, midday exports are worth little and export limits are common. Storing your own surplus is the better use of it.'),
            ai('Mature VPP market.', 'Multiple VPPs compete for SA batteries. The federal discount requires a VPP-capable battery, so you keep that option open whichever brand you choose.'),
            ai('Network rules.', 'Your network is %s, which has been rolling out flexible exports. Ask the installer what applies at your address.' % net),
        ]
    else:  # ACT
        incentive = ("Canberra households can pair the federal discount with the ACT's Sustainable Household Scheme, which has offered "
                     "low- and zero-interest loans for batteries, solar and electrification. Check the current loan terms - and the "
                     "federal step-down still applies to the battery itself.")
        items = [
            ai('Cold-climate evenings.', 'Canberra winters push all-electric homes into heavy evening heating loads, which is exactly when a battery discharges.'),
            ai('Electrification.', 'With the ACT moving homes off gas, a battery helps run heat pumps and induction on your own solar rather than evening grid power.'),
            ai('Finance can cover it.', 'Spreading the cost with a scheme loan means the federal discount is captured now without paying the whole price upfront.'),
            ai('Network rules.', 'Your network is %s. Export limits and connection approval come from the network.' % net),
        ]
    faqs = [
        ('Can I get the battery rebate in %s?' % R,
         'Yes. The federal Cheaper Home Batteries discount applies Australia-wide to eligible on-grid homes, installed by an accredited installer. ' + incentive),
        ('What size battery do %s homes usually get?' % R,
         'Most households land between 10 and 16 kWh of usable capacity. The first 14 kWh earn the full federal rate, which is why so many quotes sit just under it. '
         'The right size depends on your evening usage and how much solar you have to fill it - a quote should show the maths for your bills, not a one-size answer.'),
    ]
    return incentive, items, faqs


# ─────────────────────────────── content blocks ─────────────────────────────
def hero_copy(brand, R, national):
    where = 'Australian' if national else R
    if brand == 'au-solar-quotes':
        h1 = ('Home battery quotes, <span class="hl">before the rebate drops</span>.' if national
              else '<span class="hl">%s</span> battery quotes, before the rebate drops.' % R)
        h1_after = ('Home battery quotes, <span class="hl">done properly</span>.' if national
                    else '<span class="hl">%s</span> battery quotes, done properly.' % R)
    elif brand == 'clear-solar-quotes':
        h1 = ('Battery quotes, <span class="hl">priced before the rebate cut</span>.' if national
              else 'Battery quotes in <span class="hl">%s</span>, priced before the rebate cut.' % R)
        h1_after = ('Clear, honest <span class="hl">battery quotes</span>.' if national
                    else 'Clear, honest battery quotes in <span class="hl">%s</span>.' % R)
    else:
        h1 = ('Premium home batteries, <span class="hl">installed before the rebate steps down</span>.' if national
              else 'Premium home batteries for <span class="hl">%s</span>, installed before the rebate steps down.' % R)
        h1_after = ('Premium home batteries, <span class="hl">quoted properly</span>.' if national
                    else 'Premium home batteries for <span class="hl">%s</span>, quoted properly.' % R)
    sub = ('The federal battery discount falls about %d%% on 1 January 2027, and the rate you get is set by the day your battery is '
           'installed - not the day you sign. Answer five quick questions and we&#39;ll match you with one accredited %s battery '
           'installer who can quote now and install while the current rate applies.' % (CUT_PCT, where))
    sub_after = ('The federal battery discount steps down every six months until 2030. Answer five quick questions and we&#39;ll '
                 'match you with one accredited %s battery installer for an itemised quote.' % where)
    eyebrow = 'Federal battery discount drops 1 January 2027'
    eyebrow_after = 'Federal battery discount steps down again 1 July 2027'
    return dict(h1=h1, h1_after=h1_after, sub=sub, sub_after=sub_after, eyebrow=eyebrow, eyebrow_after=eyebrow_after)


STEPS_HTML = r"""<!-- STEP 1: OWNERSHIP -->
        <div class="step active" id="step1">
          <div class="q">Do you own your home?</div>
          <div class="qs">The battery discount and installer quotes need the owner's go-ahead.</div>
          <div id="step1-inner">
            <button class="choice-card" onclick="pickOwner(true,'owner',this)">Yes, I own it <span>&rarr;</span></button>
            <button class="choice-card" onclick="pickOwner(false,'renter',this)">No, I'm renting <span>&rarr;</span></button>
          </div>
          <div id="renter-msg" style="display:none;padding:16px 2px;font-size:.9rem;color:var(--ink2)">
            No problem. A battery needs the owner's sign-off. If you can involve them, come back any time - ideally before 1 January.
          </div>
        </div>

        <!-- STEP 2: EXISTING SOLAR -->
        <div class="step" id="step2">
          <button class="backlink" onclick="goToStep(2,1)">&larr; Back</button>
          <div class="q">Do you already have solar panels?</div>
          <div class="qs">Adding to existing solar and installing both are quoted differently.</div>
          <button class="choice-h" onclick="pickSolar(this,'yes','Add a battery to existing solar')">Yes - add a battery to my solar</button>
          <button class="choice-h" onclick="pickSolar(this,'no','Solar and battery together')">No - I want solar and a battery</button>
          <button class="choice-h" onclick="pickSolar(this,'unsure','Not sure yet')">Not sure yet</button>
        </div>

        <!-- STEP 3: BILL -->
        <div class="step" id="step3">
          <button class="backlink" onclick="goToStep(3,2)">&larr; Back</button>
          <div class="q">Roughly what's your quarterly power bill?</div>
          <div class="qs">Helps your installer size the battery to your evening use.</div>
          <button class="choice-h" onclick="pickBill(this,'Under $300')">Under $300</button>
          <button class="choice-h" onclick="pickBill(this,'$300 - $600')">$300 - $600</button>
          <button class="choice-h" onclick="pickBill(this,'$600 - $1,000')">$600 - $1,000</button>
          <button class="choice-h" onclick="pickBill(this,'Over $1,000')">Over $1,000</button>
        </div>

        <!-- STEP 4: TIMELINE -->
        <div class="step" id="step4">
          <button class="backlink" onclick="goToStep(4,3)">&larr; Back</button>
          <div class="q">When would you like it installed?</div>
          <div class="qs" data-bt-after="So the right installer prioritises your quote.">The current discount applies to batteries installed by 31 December.</div>
          <button class="choice-h" onclick="pickTimeline(this,'ASAP - next 30 days')" data-bt-after="ASAP, next 30 days">Before 1 January - lock in the current rate</button>
          <button class="choice-h" onclick="pickTimeline(this,'1 - 3 months')">1 - 3 months</button>
          <button class="choice-h" onclick="pickTimeline(this,'3 - 6 months')">3 - 6 months</button>
          <button class="choice-h" onclick="pickTimeline(this,'Just researching')">Just researching</button>
        </div>

        <!-- STEP 5: POSTCODE -->
        <div class="step" id="step5">
          <button class="backlink" onclick="goToStep(5,4)">&larr; Back</button>
          <div class="q">What's your postcode?</div>
          <div class="qs">We check which battery installer covers your area.</div>
          <div class="fld">
            <input id="postcode" type="tel" inputmode="numeric" maxlength="4" placeholder="e.g. 2000" oninput="onPostcodeTyping()">
            <div class="err" id="err-postcode"></div>
          </div>
          <div class="suburb-chip" id="suburb-chip"><span id="suburb-text"></span></div>
          <button class="btn" id="postcodeBtn" style="margin-top:12px" onclick="submitPostcode()">Find my battery installer</button>
        </div>

        <!-- STEP 6: CONTACT -->
        <div class="step" id="step6">
          <button class="backlink" onclick="goToStep(6,5)">&larr; Back</button>
          <div class="q">Where should <span id="buyerName">your installer</span> send your quote?</div>
          <div class="qs">Shared only with your one matched installer.</div>
          <!-- honeypot: hidden from humans; bots fill it and get silently dropped -->
          <input id="website" name="website" type="text" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0">
          <div class="grid2">
            <div class="fld"><label>First name</label><input id="firstName" oninput="validateContact()"><div class="err" id="err-firstName">Required</div></div>
            <div class="fld"><label>Last name</label><input id="lastName" oninput="validateContact()"><div class="err" id="err-lastName">Required</div></div>
          </div>
          <div class="fld"><label>Email</label><input id="email" type="email" oninput="validateContact()"><div class="err" id="err-email">Enter a valid email</div></div>
          <div class="fld"><label>Mobile</label><input id="phone" type="tel" inputmode="numeric" placeholder="04xx xxx xxx" oninput="validateContact()"><div class="err" id="err-phone">Enter a valid AU mobile</div></div>
          <div class="consent-wrap">
            <input type="checkbox" id="consent" onchange="validateContact()">
            <label for="consent">I agree to be contacted by <strong id="consentBuyerName">my matched accredited installer</strong> about my solar battery enquiry. My details are shared only with that one installer. I've read the <a href="https://__DOMAIN__/privacy-policy.html">Privacy Policy</a> &amp; <a href="https://__DOMAIN__/terms.html">Terms</a>.</label>
          </div>
          <button class="btn" id="submitBtn" disabled onclick="submitForm()">Get my free battery quote</button>
          <div class="err" id="err-form" style="text-align:center;margin-top:10px"></div>
        </div>

        """


def body_sections(brand, slug, R, state, net, national, region_links):
    pull = ' pull-up' if brand == 'clear-solar-quotes' else ''
    a13, b13 = EX[13.5]
    dl_h2 = 'The battery discount drops on 1 January 2027'
    dl_h2_after = 'The battery discount steps down again on 1 July 2027'
    dl_p = ('From 1 January the federal discount falls from about %s to about %s per kWh of usable capacity. On a typical 13.5 kWh battery '
            'that is roughly %s less. The rate is set by your <strong>installation date</strong>, and installers book out in the run-up to Christmas.'
            % (PER_KWH_NOW, PER_KWH_JAN, money(a13 - b13)))
    dl_p_after = ('The discount steps down every six months until the program ends in 2030. The rate is set by your <strong>installation '
                  'date</strong>, so the sooner your battery is in, the more of it you keep.')
    out = []
    # 1. deadline card + stats
    out.append('''<!-- DEADLINE -->
<section class="sec%s" id="deadline"><div class="wrap">
  <div class="bt-deadline">
    <div class="bt-count" aria-label="Time until the rebate changes">
      <div><b id="bt-d">--</b><span>days</span></div><div><b id="bt-h">--</b><span>hours</span></div><div><b id="bt-m">--</b><span>mins</span></div>
    </div>
    <div>
      <h2 data-bt-after="%s">%s</h2>
      <p data-bt-after="%s">%s</p>
    </div>
    <a href="#quote" class="bt-btn">Get my battery quote</a>
  </div>
  <div class="bt-stats">
    <div><b>~%d%%</b><span>smaller federal discount from 1 Jan 2027</span></div>
    <div><b>14 kWh</b><span>usable capacity earns the full rate</span></div>
    <div><b>1</b><span>accredited installer per postcode, never resold</span></div>
    <div><b>$0</b><span>cost to you for the quote, always</span></div>
  </div>
</div></section>''' % (pull, esc(dl_h2_after), dl_h2, esc(dl_p_after), dl_p, CUT_PCT))

    # 2. rebate education
    out.append('''<!-- REBATE EXPLAINED -->
<section class="sec bt-band" id="rebate"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">The battery rebate, explained - October 2026</div>
    <h2 class="sec-title">How the federal battery discount works, and why January matters</h2>
    <p class="sec-sub">The Cheaper Home Batteries Program has been taking thousands off home batteries since July 2025. It was reshaped on 1 May 2026 and now steps down every six months. Here is what that means if you are thinking about a battery.</p>
  </div>
  <div class="bt-timeline">
    <div class="t"><div class="d">Jul 2025 - Apr 2026</div><div class="f">8.4<small>STCs/kWh</small></div><div class="k">Program launched at a flat rate per usable kWh.</div></div>
    <div class="t now"><span class="tag" data-bt-after="Ended">Now</span><div class="d">1 May - 31 Dec 2026</div><div class="f">%s<small>STCs/kWh</small></div><div class="k">About %s per kWh on the first 14 kWh, tapering above that.</div></div>
    <div class="t"><span class="tag" data-bt-after="Now" style="background:var(--err)">Next</span><div class="d">1 Jan - 30 Jun 2027</div><div class="f">%s<small>STCs/kWh</small></div><div class="k">About %s per kWh - roughly %d%% less on every battery.</div></div>
    <div class="t"><div class="d">1 Jul 2027 onwards</div><div class="f">%s<small>STCs/kWh</small></div><div class="k">Keeps stepping down every six months until the program ends in 2030.</div></div>
  </div>
  <div class="bt-prose">
    <p><strong>It comes off the price, not back to you later.</strong> The discount is created as small-scale technology certificates (STCs) for each kWh of usable battery capacity. Your installer claims them and takes the value off your quote upfront - a good quote shows it as its own line.</p>
    <p><strong>Bigger batteries get a tapering rate.</strong> Since 1 May 2026 the first 14 kWh earns the full rate, capacity between 14 and 28 kWh earns 60%%, and 28 to 50 kWh earns 15%%. Nothing above 50 kWh counts. That is why so many home quotes now sit at or just under 14 kWh.</p>
    <p><strong>Your installation date sets the rate.</strong> Not the date you get a quote, sign a contract or pay a deposit. A battery quoted in November but installed on 5 January gets the January rate.</p>
    <div class="bt-callout" data-bt-after="With the discount stepping down every six months, the practical move is the same: get an itemised quote early, check the installation date the installer can commit to, and make sure the discount on the quote matches the rate on that date."><strong>The practical upshot for October 2026:</strong> with about <b data-bt-days>--</b> days left, the homeowners who keep the higher rate are the ones who get a quote now, give themselves time to compare it properly, and lock an installation date before the Christmas shutdown. Ask any installer to put the installation date - and the discount at that date - in writing.</div>
    <p><strong>What makes a battery eligible.</strong> The home must be connected to the grid, the battery must be on the approved product list and capable of joining a virtual power plant (you do not have to join one), and it must be installed by an accredited installer. Every installer we match you with meets that bar.</p>
  </div>
</div></section>''' % (FACTOR_NOW, PER_KWH_NOW, FACTOR_JAN, PER_KWH_JAN, CUT_PCT, FACTOR_JUL))

    # 3. calculator
    out.append('''<!-- CALCULATOR -->
<section class="sec" id="calc"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">Rebate calculator</div>
    <h2 class="sec-title" data-bt-after="What the next step-down costs on your battery">What waiting until January costs on your battery</h2>
    <p class="sec-sub">Pick a usable battery size. These are estimates of the federal discount only - your installer confirms the exact figure on the quote.</p>
  </div>
  <div class="bt-calc">
    <div class="in">
      <label for="bt-range">Usable battery capacity</label>
      <div class="size"><span id="bt-size">13.5</span> <small>kWh</small></div>
      <input type="range" id="bt-range" min="5" max="40" step="0.5" value="13.5" oninput="btCalc(this.value);btCalcUsed()" aria-label="Battery size in kWh">
      <div class="presets">
        <button type="button" data-k="10" onclick="btCalc(10);btCalcUsed()">10 kWh</button>
        <button type="button" data-k="13.5" onclick="btCalc(13.5);btCalcUsed()">13.5 kWh</button>
        <button type="button" data-k="16" onclick="btCalc(16);btCalcUsed()">16 kWh</button>
        <button type="button" data-k="20" onclick="btCalc(20);btCalcUsed()">20 kWh</button>
        <button type="button" data-k="30" onclick="btCalc(30);btCalcUsed()">30 kWh</button>
      </div>
    </div>
    <div class="out">
      <div class="row"><span data-bt-after="Installed before 1 July 2027">Installed by 31 Dec 2026</span><b id="bt-now">-</b></div>
      <div class="row"><span data-bt-after="Installed from 1 July 2027">Installed from 1 Jan 2027</span><b id="bt-jan">-</b></div>
      <div class="row loss"><span>Discount lost by waiting</span><b id="bt-loss">-</b></div>
      <a href="#quote" class="bt-btn" style="display:block;margin-top:18px">Lock in my quote now</a>
      <p class="note">Estimate assumes a certificate value of about $%d and the tiered schedule (100%% to 14 kWh, 60%% to 28 kWh, 15%% to 50 kWh). Certificate prices move, and installers pass them through differently, so the figure on your quote is the one that counts. State incentives are extra and not included.</p>
    </div>
  </div>
</div></section>''' % STC_PRICE)

    # 4. is it worth it + sizing
    out.append('''<!-- WORTH IT -->
<section class="sec bt-band" id="worth"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">Straight talk</div>
    <h2 class="sec-title">Is a battery actually worth it for your home?</h2>
    <p class="sec-sub">A deadline is a reason to get a quote, not a reason to buy the wrong battery. Here is who tends to come out ahead, and who should think harder.</p>
  </div>
  <div class="bt-two">
    <div class="bt-card"><h3>A battery usually stacks up if...</h3><ul>
      <li>%s<span>You export a lot of solar in the middle of the day for a few cents per kWh.</span></li>
      <li>%s<span>Most of your power is used in the evening - cooking, heating or cooling, kids home after school.</span></li>
      <li>%s<span>You are on (or can move to) a time-of-use plan with an expensive evening peak.</span></li>
      <li>%s<span>You want backup through outages, an EV charged on your own sun, or to go all-electric.</span></li>
    </ul></div>
    <div class="bt-card no"><h3>Think harder if...</h3><ul>
      <li>%s<span>Your solar system is small and barely covers daytime use - there is little left to store.</span></li>
      <li>%s<span>Someone is home all day and already uses most of the solar as it is made.</span></li>
      <li>%s<span>You are planning to sell within a couple of years.</span></li>
      <li>%s<span>A quote is pushing a big battery without showing your usage - bigger is not automatically better under the tiered rate.</span></li>
    </ul></div>
  </div>
  <div style="margin-top:30px;overflow-x:auto">
  <table class="bt-table">
    <caption>Typical starting points. Your installer sizes the battery to your actual interval data and solar system.</caption>
    <thead><tr><th scope="col">Quarterly bill</th><th scope="col">Usable battery often discussed</th><th scope="col">Notes</th></tr></thead>
    <tbody>
      <tr><td>Under $300</td><td>5 - 10 kWh</td><td>Smaller households. Check the payback carefully - the saving is smaller too.</td></tr>
      <tr><td>$300 - $600</td><td>10 - 14 kWh</td><td>The sweet spot for most family homes, and it all earns the full federal rate.</td></tr>
      <tr><td>$600 - $1,000</td><td>13.5 - 20 kWh</td><td>Larger homes, ducted air, pools. Capacity over 14 kWh earns 60%% of the rate.</td></tr>
      <tr><td>Over $1,000</td><td>20 kWh+</td><td>EVs, all-electric homes, three-phase supply. Often paired with more solar.</td></tr>
    </tbody>
  </table>
  </div>
  <h3 style="margin:34px 0 12px;text-align:left">What a good battery quote shows - deadline or not</h3>
  <div class="assure">
    %s
    %s
    %s
    %s
    %s
    %s
  </div>
</div></section>''' % ((TICK,) * 8 + (
        ai('Usable capacity, not nominal.', 'The discount is calculated on usable kWh. If the quote only lists a headline number, ask.'),
        ai('The federal discount as its own line.', 'And the installation date it was calculated for.'),
        ai('Backup, spelled out.', 'None, essential circuits, or whole home - they are very different installs.'),
        ai('Warranty in years and throughput.', 'A 10-year warranty with a low energy-throughput cap can end early.'),
        ai('Approved product, accredited installer.', 'Both are conditions of the discount - get the model and accreditation number in writing.'),
        ai('Any state incentive or VPP terms.', 'What you are signing up to, what it pays, and whether you can leave.'),
    )))

    # 5. how it works
    out.append('''<!-- HOW -->
<section class="sec" id="how"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">How it works</div>
    <h2 class="sec-title">One installer, one honest battery quote</h2>
    <p class="sec-sub">Most quote sites sell your number to whoever pays. We match you to one accredited battery installer and stop there.</p>
  </div>
  <div class="bt-steps">
    <div><div class="n">Step 01</div><h3>Five quick questions</h3><p>Whether you own the home, if you already have solar, your bill, your timing and your postcode. No account, no upload.</p></div>
    <div><div class="n">Step 02</div><h3>Matched to one installer</h3><p>We check which accredited battery installer covers your postcode and match you to that one business. Nobody else gets your details.</p></div>
    <div><div class="n">Step 03</div><h3>Quote with the rebate itemised</h3><p>Your installer contacts you, usually within one business day, with a quote showing the discount and the installation date it applies to.</p></div>
  </div>
  <div class="bt-sec-cta"><a href="#quote" class="bt-btn">Start my battery quote</a></div>
</div></section>''')

    # 6. local
    if national:
        cards = ''.join('<a href="/battery/%s/">%s<span>%s</span></a>' % (STATES[s][1], s, STATES[s][0]) for s in STATES)
        out.append('''<!-- STATES -->
<section class="sec bt-band" id="local"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">By state</div>
    <h2 class="sec-title">State incentives on top of the federal discount</h2>
    <p class="sec-sub">The federal discount applies everywhere. Some states add their own incentive or finance; others have closed theirs. Pick your state for the local detail.</p>
  </div>
  <div class="bt-prose" style="margin-top:0">
    <p><strong>NSW</strong> - a Peak Demand Reduction Scheme incentive for connecting your battery to a virtual power plant, stacked on the federal discount.</p>
    <p><strong>WA</strong> - the Residential Battery Scheme rebate for Synergy and Horizon Power customers who join the approved VPP, plus interest-free loans for eligible households.</p>
    <p><strong>ACT</strong> - Sustainable Household Scheme loans that can cover batteries.</p>
    <p><strong>VIC, QLD and SA</strong> - state battery rebates have closed, so the federal discount is the one to catch.</p>
    <p style="font-size:.85rem;color:var(--muted)">State programs change at short notice. Your installer confirms what is open when you sign.</p>
  </div>
  <div class="bt-areas" style="margin-top:22px">%s</div>
</div></section>''' % cards)
        local_faqs = []
    else:
        incentive, items, local_faqs = state_local(state, R, net)
        out.append('''<!-- @local -->
<section class="sec bt-band" id="local"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">Batteries in %s</div>
    <h2 class="sec-title">What&#39;s different about a battery in %s</h2>
    <p class="sec-sub">%s</p>
  </div>
  <div class="assure">
    %s
  </div>
</div></section>''' % (R, R, incentive, '\n    '.join(items)))

    # 7. FAQ
    faqs = general_faqs() + local_faqs
    out.append('''<!-- FAQ -->
<section class="sec" id="faq"><div class="wrap">
  <div class="sec-head mid">
    <div class="sec-eyebrow">FAQ</div>
    <h2 class="sec-title">Battery questions, answered</h2>
  </div>
  <div class="faq-wrap">
    %s
  </div>
</div></section>''' % '\n    '.join(faq_item(q, a) for q, a in faqs))

    # 8. CTA
    out.append('''<!-- CLOSING CTA -->
<section class="sec" style="padding-top:0"><div class="wrap">
  <div class="cta-band">
    <div>
      <h2 data-bt-after="Ready for a straight-up battery quote?">Get your battery quote in before 1 January</h2>
      <p>One short form, one accredited local installer, the discount itemised on the quote.</p>
    </div>
    <a href="#quote">Get my free battery quote</a>
  </div>
</div></section>
''')
    return '\n\n'.join(out), faqs


def general_faqs():
    return [
        ('When exactly does the battery rebate drop?',
         'On 1 January 2027 the federal discount falls from %s to %s certificates per kWh of usable capacity - about %d%% less. It steps down again to %s on 1 July 2027 and keeps falling every six months until the program ends in 2030. '
         'The rate is set by the date your battery is <strong>installed</strong>, not the date you sign.' % (FACTOR_NOW, FACTOR_JAN, CUT_PCT, FACTOR_JUL)),
        ('How much do I lose if my battery goes in after 1 January?',
         'Roughly, using a certificate value of about $%d: %s; %s; %s. Your installer confirms the exact discount on the quote.' % (
             STC_PRICE, ex_line(10), ex_line(13.5), ex_line(20))),
        ('Do I need solar panels to get the battery discount?',
         'No - the federal discount does not require existing solar. But a battery earns most when it is charged by your own panels, so most people either add one to existing solar or install both together. The form asks which, so your installer quotes the right job.'),
        ('Is the rebate paid to me?',
         'No. The discount is created as certificates that your installer claims, and the value comes off your price upfront. Check that the quote shows it as a separate line and states the installation date it was calculated for.'),
        ('Do I have to join a virtual power plant?',
         'Not for the federal discount - the battery has to be VPP-capable, but joining is your choice. Some state incentives do require joining one, so read the terms before you sign up.'),
        ('Can I still get a battery installed before 1 January?',
         'Often yes, but not always. Many installers book out in the run-up to Christmas and shut down over the break, and some installs need network approval first. Getting a quote now gives you the best chance - ask the installer to commit to an installation date in writing.'),
        ('Is this really free? What is the catch?',
         'Free for homeowners. We are paid by the installer you are matched with, not by you, and it never changes the price you are quoted. Your details go to one installer only and are never resold.'),
        ('What if nobody covers my postcode yet?',
         'We still take your details and match you as soon as an accredited battery installer covers your area. We will not pass your number around to fill the gap.'),
    ]


def jsonld(brand, domain, brand_name, slug, R, state, faqs, national):
    base = 'https://%s/' % domain
    url = base + ('battery/' if national else 'battery/%s/' % slug)
    crumbs = [('Home', base), ('Home batteries', base + 'battery/')]
    if not national:
        if slug not in STATE_SLUGS:
            crumbs.append((state, base + 'battery/%s/' % STATES[state][1]))
        crumbs.append((R, url))
    strip = lambda s: re.sub(r'<[^>]+>', '', s)
    g = [
        {"@type": "Organization", "logo": base + brand + "-og.png", "name": brand_name, "url": base,
         "description": "Free solar and battery quote matching. One accredited local installer per postcode, never shared or resold.", "areaServed": "AU"},
        {"@type": "WebSite", "name": brand_name, "url": base},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]},
        {"@type": "Service", "name": "Solar battery quote matching" + ('' if national else ' in ' + R),
         "serviceType": "Solar battery quote matching",
         "provider": {"@type": "Organization", "name": brand_name, "url": base},
         "areaServed": {"@type": "Place", "name": 'Australia' if national else R}, "url": url},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in faqs]},
    ]
    return url, '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@graph": g}, ensure_ascii=False, separators=(',', ':'))


# ─────────────────────────────── transform ──────────────────────────────────
def sub1(pattern, repl, s, flags=re.S, count=1, label=None):
    new, n = re.subn(pattern, repl, s, count=count, flags=flags)
    if n == 0:
        raise SystemExit('pattern not found: %s' % (label or pattern[:70]))
    return new


def rep(old, new, s, count=1, label=None):
    if old not in s:
        raise SystemExit('text not found: %s' % (label or old[:70]))
    return s.replace(old, new, count) if count else s.replace(old, new)


def build(brand, src_html, slug, national):
    cfg = BRANDS[brand]
    domain, bname = cfg['domain'], cfg['name']
    if national:
        R, state, net = 'Australia', None, None
    else:
        R, state, net = REGIONS[slug]
    h = src_html

    # ---- body content first (need the FAQs for JSON-LD) ----
    body, faqs = body_sections(brand, slug, R, state, net, national, None)
    url, ld = jsonld(brand, domain, bname, slug, R, state, faqs, national)

    # ---- head ----
    if national:
        title = 'Home Battery Quotes Before the 1 January Rebate Cut | %s' % bname
        desc = ('Get a free home battery quote from one accredited local installer before the federal battery discount drops on 1 January 2027. '
                'Rebate explained, calculator, never resold.')
    else:
        title = '%s Battery Quotes Before the Rebate Cut | %s' % (R, bname)
        desc = ('%s solar battery quotes from one accredited local installer. The federal battery discount drops about %d%% on 1 January 2027 - '
                'get quoted and installed first. Free, never resold.' % (R, CUT_PCT))
    ogdesc = 'One accredited local battery installer for your postcode. Beat the 1 January 2027 rebate cut. Free and obligation-free.'
    h = sub1(r'<title>.*?</title>', '<title>%s</title>' % esc(title), h)
    h = sub1(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % esc(desc), h)
    h = sub1(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % esc(title), h)
    h = sub1(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % esc(ogdesc), h)
    h = sub1(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url, h)
    h = sub1(r'<meta name="twitter:title" content="[^"]*">', '<meta name="twitter:title" content="%s">' % esc(title), h)
    h = sub1(r'<meta name="twitter:description" content="[^"]*">', '<meta name="twitter:description" content="%s">' % esc(ogdesc), h)
    h = sub1(r'<script type="application/ld\+json">.*?</script>', lambda m: ld, h)
    h = sub1(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url, h)
    h = rep('</head>', BT_CSS.replace('__RADIUS__', cfg['radius']) + '</head>', h)

    # ---- header nav + banner ----
    h = sub1(r'<nav class="navlinks">.*?</nav>',
             '<nav class="navlinks">\n      <a href="#rebate">The rebate</a>\n      <a href="#calc">Calculator</a>\n'
             '      <a href="#worth">Worth it?</a>\n      <a href="#faq">FAQ</a>\n      <a href="/">Solar quotes</a>\n    </nav>', h)
    banner = ('<div class="bt-banner" data-bt-after="The federal battery discount steps down again on 1 July 2027. '
              '&lt;a href=&quot;#quote&quot;&gt;Get an itemised quote&lt;/a&gt;">'
              'Federal battery discount drops ~%d%% on 1 January 2027 - <b data-bt-days>--</b> days left. '
              '<a href="#quote">Get your quote</a></div>' % CUT_PCT)
    h = rep('</header>', '</header>\n' + banner, h)

    # ---- hero copy ----
    hc = hero_copy(brand, R, national)
    h = sub1(r'(<span class="eyebrow"><span class="dot"></span>)[^<]*(</span>)',
             lambda m: m.group(1).replace('<span class="eyebrow">', '<span class="eyebrow" data-bt-after="%s">' % esc('<span class="dot"></span> ' + hc['eyebrow_after'])) + ' ' + hc['eyebrow'] + m.group(2), h)
    h = sub1(r'<h1>.*?</h1>', lambda m: '<h1 data-bt-after="%s">%s</h1>' % (esc(hc['h1_after']), hc['h1']), h)
    h = sub1(r'<p class="sub">.*?</p>', lambda m: '<p class="sub" data-bt-after="%s">%s</p>' % (esc(hc['sub_after']), hc['sub']), h)
    ticks = [
        'Lock in the current federal discount - it is set by your installation date',
        'One accredited battery installer for your postcode, never resold',
        'Free, obligation-free quote with the rebate itemised',
    ]
    h = sub1(r'(<div class="ticks">)(.*?)(\n\s*</div>\n\s*<div class="trust-pills">)',
             lambda m: m.group(1) + ''.join('\n        <div class="tick">%s %s</div>' % (TICK_OK, t) for t in ticks) + m.group(3), h)
    h = sub1(r'(<div class="card-head">\s*<div class="t">)[^<]*(</div>\s*<div class="s">)[^<]*(</div>)',
             lambda m: m.group(1) + 'Get your free battery quote' + m.group(2).replace('<div class="s">', '<div class="s" data-bt-after="Under a minute - matched to your area">') + 'Under a minute - before the 1 January rebate cut' + m.group(3), h)
    h = rep('Step 1 of 5', 'Step 1 of 6', h)
    h = sub1(r'<!-- STEP 1: OWNERSHIP -->.*?(<!-- SUCCESS -->)', lambda m: STEPS_HTML.replace('__DOMAIN__', domain) + m.group(1), h)

    # ---- body: everything between </main> (and clear's hero wrapper) and the areas block ----
    h = sub1(r'(</main>\n(?:</div>\n)?).*?(<!-- @tier1-areas -->)', lambda m: m.group(1) + '\n' + body + '\n' + m.group(2), h)

    # ---- nearby areas + footer directory -> battery pages ----
    def relink(block):
        block = re.sub(r'href="/([a-z-]+)/"', lambda m: 'href="/battery/%s/"' % m.group(1) if m.group(1) in REGIONS else m.group(0), block)
        return block.replace('<a href="/">Every area we cover</a>', '<a href="/battery/">Every area we cover</a>')
    if national:
        cards = ''.join('<a href="/battery/%s/">%s<span>%s</span></a>' % (s, REGIONS[s][0], STATES[REGIONS[s][1]][0])
                        for s in sorted(REGIONS, key=lambda x: (REGIONS[x][1], REGIONS[x][0])) if s not in STATE_SLUGS)
        h = sub1(r'<!-- @tier1-areas -->.*?<!-- @end-tier1-areas -->',
                 lambda m: '<!-- @tier1-areas -->\n<section class="sec"><div class="wrap">\n  <div class="sec-head mid">\n'
                           '    <div class="sec-eyebrow">Areas</div>\n    <h2 class="sec-title">Battery quotes by area</h2>\n'
                           '    <p class="sec-sub">Pick your area for local network, incentive and installer detail.</p>\n  </div>\n'
                           '  <div class="bt-areas">%s</div>\n</div></section>\n<!-- @end-tier1-areas -->' % cards, h)
    else:
        h = sub1(r'<!-- @tier1-areas -->.*?<!-- @end-tier1-areas -->', lambda m: relink(m.group(0)), h)
    h = sub1(r'<!-- @tier1-footer -->.*?<!-- @end-tier1-footer -->', lambda m: relink(m.group(0)), h)
    if '<a href="/battery/">Battery quotes</a>' not in h:
        h = rep('<a href="/">Home</a>', '<a href="/">Home</a>\n          <a href="/battery/">Battery quotes</a>', h)
    h = sub1(r'(<p class="fine">[^<]*?)(Rebate and incentive|Payback and incentive|Guidance on installation quality and cost)( information)?[^<]*?(</p>\s*</div>\s*</footer>)',
             lambda m: m.group(1) + 'Battery rebate figures are general estimates based on the federal Cheaper Home Batteries Program schedule as published in October 2026 and an approximate certificate value; the discount that applies is set by your installation date and confirmed by your installer on the quote. State incentives change and are confirmed at the time of sale.' + m.group(4), h, label='footer fine print')

    # ---- script ----
    h = rep("var NICHE             = 'solar';", "var NICHE             = 'battery';", h)
    h = rep('var TOTAL_STEPS = 5;', 'var TOTAL_STEPS = 6;', h)
    h = rep("var STEP_NAMES = {1:'ownership',2:'quarterly_bill',3:'timeline',4:'postcode',5:'contact'};",
            "var STEP_NAMES = {1:'ownership',2:'existing_solar',3:'quarterly_bill',4:'timeline',5:'postcode',6:'contact'};", h)
    h = sub1(r"/\* ─── STEP 2/3 ─── \*/\nfunction pickBill.*?\nfunction pickTimeline[^\n]*\n",
             "/* ─── STEP 2/3/4 ─── */\n"
             "function pickSolar(el,v,label){ document.querySelectorAll('#step2 .choice-h').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); fd.has_solar=v; fd.battery_project=label; setTimeout(()=>goToStep(2,3),260); }\n"
             "function pickBill(el,v){ document.querySelectorAll('#step3 .choice-h').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); fd.avg_quarterly_bill=v; setTimeout(()=>goToStep(3,4),260); }\n"
             "function pickTimeline(el,v){ document.querySelectorAll('#step4 .choice-h').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); fd.purchase_timeline=v; setTimeout(()=>goToStep(4,5),260); }\n", h)
    h = rep('/* ─── STEP 4: POSTCODE + LOOKUP ─── */', '/* ─── STEP 5: POSTCODE + LOOKUP ─── */', h)
    if h.count('goToStep(4,5),450)') != 3:
        raise SystemExit('expected three postcode advances in %s/%s' % (brand, slug))
    h = h.replace('goToStep(4,5),450)', 'goToStep(5,6),450)')
    h = rep('/* ─── STEP 5: VALIDATION ─── */', '/* ─── STEP 6: VALIDATION ─── */', h)
    h = rep("' about my solar enquiry. My details are shared only with that one installer.'",
            "' about my solar battery enquiry. My details are shared only with that one installer.'", h)
    h = rep("avg_quarterly_bill:fd.avg_quarterly_bill||null, purchase_timeline:fd.purchase_timeline||null,",
            "avg_quarterly_bill:fd.avg_quarterly_bill||null, purchase_timeline:fd.purchase_timeline||null,\n"
            "    has_solar:fd.has_solar||null, battery_project:fd.battery_project||null,", h)
    h = rep("document.getElementById('step5').classList.remove('active');", "document.getElementById('step6').classList.remove('active');", h)
    h = sub1(r"No pressure, just a clear, honest quote\.", "They&#39;ll quote your battery with the federal discount itemised - ask them to confirm the installation date in writing.", h)
    js = (BT_JS.replace('__CUT__', CUT_DATE_ISO).replace('__JUL__', CUT_JUL_ISO).replace('__STC__', str(STC_PRICE))
          .replace('__FNOW__', str(FACTOR_NOW)).replace('__FJAN__', str(FACTOR_JAN)).replace('__FJUL__', str(FACTOR_JUL)))
    h = sub1(r'(function toggleFaq\(el\)\{.*?\n\}\n)(</script>)', lambda m: m.group(1) + js + m.group(2), h)
    h = rep('Get my free quote &rarr;</a>', 'Get my battery quote &rarr;</a>', h)

    # sanity
    for bad in ("NICHE             = 'solar'", 'id="step5">\n          <button class="backlink" onclick="goToStep(5,4)">&larr; Back</button>\n          <div class="q">Where'):
        if bad in h:
            raise SystemExit('leftover solar wiring in %s/%s' % (brand, slug))
    return h


def main():
    written = []
    for brand in BRANDS:
        site = os.path.join(ROOT, brand)
        for slug in REGIONS:
            src = open(os.path.join(site, slug, 'index.html'), encoding='utf-8').read()
            out_dir = os.path.join(site, 'battery', slug)
            os.makedirs(out_dir, exist_ok=True)
            open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(build(brand, src, slug, False))
            written.append(out_dir)
        src = open(os.path.join(site, 'brisbane', 'index.html'), encoding='utf-8').read()
        open(os.path.join(site, 'battery', 'index.html'), 'w', encoding='utf-8').write(build(brand, src, 'brisbane', True))
        written.append(os.path.join(site, 'battery'))
    print('wrote %d pages' % len(written))


if __name__ == '__main__':
    main()
