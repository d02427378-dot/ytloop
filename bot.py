import os, time, sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "https://multiplayyoutube.rf.gd/?i=1"
VIDEO = os.environ.get("VIDEO_URL", "https://youtu.be/NrVpHJvtCGc?si=iXPaGaZVcvQn_-qM")
SCREENS = 24
INTERVAL = 360

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def cycle(page):
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.select_option('select[aria-label="Select grid size"]', str(SCREENS))
    page.wait_for_timeout(1200)
    try:
        page.locator('main button[aria-label="Select all screens"]').first.click(timeout=10000)
    except PWTimeout:
        log("! Select All absent")
    page.wait_for_timeout(1000)
    f = page.locator('input[placeholder="Enter YouTube URL"]')
    f.click(); f.fill(""); f.type(VIDEO, delay=15)
    page.locator('button[aria-label="Play videos"]').first.click(timeout=10000)
    try:
        page.wait_for_selector("iframe", timeout=30000)
        page.wait_for_timeout(4000)
        log(f"{page.locator('iframe').count()} lecteurs (mute par defaut)")
    except PWTimeout:
        log("! Aucun lecteur")
    try:  # aligne le minuteur interne du site
        s = page.locator('span[role="slider"]').first
        s.scroll_into_view_if_needed(); s.focus()
        cur = int(s.get_attribute("aria-valuenow") or 5)
        key = "ArrowRight" if 6 > cur else "ArrowLeft"
        for _ in range(abs(6 - cur)):
            page.keyboard.press(key); page.wait_for_timeout(80)
    except Exception:
        pass

def main():
    budget = int(sys.argv[sys.argv.index("--minutes") + 1]) * 60
    fin_globale = time.time() + budget
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/profil", headless=True,
            viewport={"width": 1920, "height": 1080},
            args=["--autoplay-policy=no-user-gesture-required", "--mute-audio",
                  "--disable-blink-features=AutomationControlled", "--no-first-run"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        n = 0
        try:
            while time.time() < fin_globale:
                n += 1; log(f"=== Cycle {n} ===")
                try: cycle(page)
                except Exception as e: log(f"! {type(e).__name__}: {e}")
                reste = min(INTERVAL, fin_globale - time.time())
                if reste <= 0: break
                log(f"Pause {int(reste)}s")
                time.sleep(reste)
                try: page.reload(wait_until="domcontentloaded", timeout=60000)
                except Exception: pass
        finally:
            ctx.close()

main()