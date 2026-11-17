#!/usr/bin/env python3
import argparse, asyncio, random, time
from pathlib import Path
from playwright.async_api import async_playwright

VIDEO_ID = "NrVpHJvtCGc"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}&autoplay=1"

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]
LOCALES = [("fr-FR", "Europe/Paris"), ("en-US", "America/New_York"),
           ("de-DE", "Europe/Berlin"), ("es-ES", "Europe/Madrid")]
STEALTH = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
window.chrome = window.chrome || { runtime: {} };
"""
STATS = {"views": 0, "errors": 0}

def parse_proxy(raw):
    if not raw: return None
    if "://" not in raw: raw = "http://" + raw
    scheme, rest = raw.split("://", 1)
    auth = None
    if "@" in rest: auth, rest = rest.rsplit("@", 1)
    host, _, port = rest.partition(":")
    cfg = {"server": f"{scheme}://{host}:{port or 80}"}
    if auth:
        u, _, pw = auth.partition(":")
        cfg["username"], cfg["password"] = u, pw
    return cfg

async def dismiss_consent(page):
    for label in ("Tout accepter", "Accept all", "Alle akzeptieren", "Aceptar todo"):
        try:
            b = page.get_by_role("button", name=label, exact=False).first
            if await b.is_visible(timeout=1200):
                await b.click(); return
        except Exception: pass

async def skip_ads(page):
    for sel in (".ytp-ad-skip-button", ".ytp-ad-skip-button-modern", ".ytp-skip-ad-button"):
        try:
            b = page.locator(sel).first
            if await b.is_visible(timeout=600): await b.click()
        except Exception: pass

async def start_playback(page):
    for sel in (".ytp-large-play-button", "button.ytp-play-button"):
        try:
            await page.locator(sel).first.click(timeout=4000); return True
        except Exception: pass
    try:
        await page.keyboard.press("k"); return True
    except Exception: return False

async def is_playing(page):
    try:
        return await page.evaluate("()=>{const v=document.querySelector('video');return !!v && !v.paused && v.currentTime>1;}")
    except Exception: return False

async def one_session(browser, proxy_raw, cfg):
    locale, tz = random.choice(LOCALES)
    ctx = await browser.new_context(
        proxy=parse_proxy(proxy_raw),
        user_agent=random.choice(UAS), locale=locale, timezone_id=tz,
        viewport={"width": random.choice([1366, 1440, 1920]),
                  "height": random.choice([768, 900, 1080])},
        extra_http_headers={"Accept-Language": f"{locale},en;q=0.8"},
    )
    await ctx.add_init_script(STEALTH)
    page = await ctx.new_page()
    page.set_default_timeout(20000)
    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await dismiss_consent(page)
        if not await start_playback(page): raise RuntimeError("play introuvable")
        try: await page.evaluate("()=>{const v=document.querySelector('video');if(v)v.muted=true;}")
        except Exception: pass
        for _ in range(20):
            if await is_playing(page): break
            await skip_ads(page); await asyncio.sleep(1)
        else: raise RuntimeError("lecture bloquee")
        target = random.uniform(cfg.min_watch, cfg.max_watch)
        done = 0.0
        while done < target:
            step = min(2.0, target - done)
            await asyncio.sleep(step); done += step
            await skip_ads(page)
            if not await is_playing(page): await start_playback(page)
        if target >= 30: STATS["views"] += 1
        print(f"[+] {proxy_raw or 'direct':<26} {target:5.1f}s total={STATS['views']} err={STATS['errors']}", flush=True)
    except Exception as e:
        STATS["errors"] += 1
        print(f"[!] {proxy_raw or 'direct':<26} {type(e).__name__}: {e}", flush=True)
    finally:
        try: await ctx.close()
        except Exception: pass

async def worker(wid, browser, proxies, cfg):
    i = 0
    while True:
        p = proxies[(wid + i * max(1, cfg.workers)) % len(proxies)] if proxies else None
        await one_session(browser, p, cfg)
        i += 1
        await asyncio.sleep(random.uniform(cfg.gap_min, cfg.gap_max))

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--min-watch", type=float, default=45.0)
    ap.add_argument("--max-watch", type=float, default=65.0)
    ap.add_argument("--gap-min", type=float, default=5.0)
    ap.add_argument("--gap-max", type=float, default=15.0)
    ap.add_argument("--proxies", default="")
    cfg = ap.parse_args()
    proxies = []
    if cfg.proxies and Path(cfg.proxies).exists():
        proxies = [l.strip() for l in Path(cfg.proxies).read_text().splitlines()
                   if l.strip() and not l.startswith("#")]
    print(f"{len(proxies)} proxies | workers={cfg.workers}", flush=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=[
            "--disable-blink-features=AutomationControlled",
            "--autoplay-policy=no-user-gesture-required",
            "--mute-audio", "--no-sandbox", "--disable-dev-shm-usage"])
        await asyncio.gather(*[worker(i, b, proxies, cfg) for i in range(cfg.workers)])

if __name__ == "__main__":
    asyncio.run(main())
