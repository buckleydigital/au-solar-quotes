#!/usr/bin/env python3
"""
Tighten the solar quote pages (home, state and city pages).

    python3 _tools/tighten_solar.py

  * hero      - shorter headline and intro, three short ticks, no trust pills
  * sections  - drops "How the incentives usually work" and "Everything a
                good quote should be" (generic, repeated on every page);
                "What it costs" keeps only the sizing table
  * order     - the page's own local section and local FAQ move up, right
                after "How it works"
  * nav/CTA   - "Rebates" link removed; shorter closing call to action

Idempotent: pages already tightened are left alone. Run it before
battery_pages.py, which builds the battery pages from these.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TICK = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="3">'
        '<path d="M20 6 9 17l-5-5"/></svg>')


def sub1(pat, repl, s, label):
    out, n = re.subn(pat, repl, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('not found: %s' % label)
    return out


def cut(block_re, s, label):
    return sub1(block_re, '', s, label)


def tighten(h, path):
    # ---- nav ----
    h = sub1(r'\n\s*<a href="#rebates">Rebates</a>', '', h, 'nav rebates link')

    # ---- hero ----
    m = re.search(r'<h1><span class="hl">([^<]+)</span> solar quotes, done properly\.</h1>', h)
    if m:
        region = m.group(1)
        h1 = '<h1><span class="hl">%s</span> solar quotes from one local installer.</h1>' % region
        sub = ("Answer four quick questions and we'll match you with the accredited %s installer "
               "who covers your postcode. Your details go to them and no one else." % region)
    else:
        h1 = '<h1>Solar quotes from <span class="hl">one local installer</span>.</h1>'
        sub = ("Answer four quick questions and we'll match you with the accredited installer "
               "who covers your postcode. Your details go to them and no one else.")
    h = sub1(r'<h1>.*?</h1>', h1.replace('\\', r'\\'), h, 'h1')
    h = sub1(r'<p class="sub">.*?</p>', '<p class="sub">%s</p>' % sub, h, 'sub')
    ticks = ['One installer per postcode - never resold',
             'Accredited installers and licensed electricians only',
             'Free and obligation-free']
    h = sub1(r'<div class="ticks">.*?</div>\n\s*</div>\n\s*<div class="trust-pills">.*?</div>\n',
             '<div class="ticks">' + ''.join('\n        <div class="tick">%s %s</div>' % (TICK, t) for t in ticks)
             + '\n      </div>\n', h, 'ticks + trust pills')
    h = h.replace('<div class="s">Under a minute - matched to your area</div>',
                  '<div class="s">About 60 seconds - matched to your postcode</div>', 1)

    # ---- how it works ----
    h = sub1(r'(<section class="sec" id="how"><div class="wrap">).*?(</div></section>)',
             r'''\1
  <div class="sec-head">
    <div class="sec-eyebrow">How it works</div>
    <h2 class="sec-title">Matched in three steps</h2>
    <p class="sec-sub">Most quote sites sell your number to several installers. We match you with one.</p>
  </div>
  <div class="rail">
    <div class="r"><div class="num">Step 01</div><h3>Answer four questions</h3><p>Ownership, your power bill, your timing and your postcode. No account needed.</p></div>
    <div class="r"><div class="num">Step 02</div><h3>We find your installer</h3><p>We check which accredited installer covers your postcode. If nobody does yet, we tell you straight away.</p></div>
    <div class="r"><div class="num">Step 03</div><h3>Get your free quote</h3><p>They contact you, usually within one business day, with an obligation-free quote.</p></div>
  </div>
\2''', h, 'how section')

    # ---- costs: sizing table only ----
    h = sub1(r'(<section class="sec alt" id="costs"><div class="wrap">\s*<div class="sec-head">\s*<div class="sec-eyebrow">)What it costs(</div>\s*)<h2 class="sec-title">.*?</h2>\s*<p class="sec-sub">.*?</p>',
             r'\1What size system?\2<h2 class="sec-title">What size system fits your bill</h2>\n'
             r'    <p class="sec-sub">Typical starting points. Your installer confirms the right size for your roof and usage.</p>', h, 'costs head')
    h = sub1(r'\s*<caption>.*?</caption>', '', h, 'costs caption')
    h = sub1(r'\n  <div style="margin-top:26px;[^"]*" class="assure">.*?\n  </div>\n(</div></section>)', r'\n\1', h, 'costs factor cards')

    # ---- cut generic sections ----
    h = cut(r'<!-- REBATES \(depth\) -->\n<section class="sec" id="rebates">.*?</div></section>\n\n', h, 'rebates section')
    h = cut(r'<!-- WHY -->\n<section class="sec alt">.*?</div></section>\n\n', h, 'why section')

    # ---- closing CTA ----
    h = sub1(r'(<div class="cta-band">\s*<div>\s*)<h2>.*?</h2>\s*<p>.*?</p>',
             r'\1<h2>Get your free solar quote</h2>\n      <p>About 60 seconds. One local installer. Never resold.</p>', h, 'cta band')

    # ---- local sections move up, right after "How it works" ----
    lm = re.search(r'<!-- @local -->.*?<!-- @end-local -->\n\n?', h, re.S)
    if lm:
        block = lm.group(0)
        h = h.replace(block, '', 1)
        # bands still alternate: how, local (alt), local FAQ, costs (alt), FAQ
        h = sub1(r'(<!-- WHAT DRIVES THE COST \(depth\) -->)', lambda m: block.rstrip('\n') + '\n\n' + m.group(1), h, 'local insert point')
    return h


def main():
    n = 0
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if not d.startswith(('.', '_')) and d != 'battery']
        for fn in fns:
            if fn != 'index.html':
                continue
            p = os.path.join(dp, fn)
            h = open(p, encoding='utf-8').read()
            if 'id="quote"' not in h or 'id="rebates"' not in h:
                continue    # not a solar quote page, or already tightened
            open(p, 'w', encoding='utf-8').write(tighten(h, p))
            n += 1
    print('tightened %d solar pages' % n)


if __name__ == '__main__':
    main()
