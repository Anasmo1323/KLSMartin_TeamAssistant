import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        output_dir = "offer_webapp/public/onboarding"
        
        # Go to local app
        await page.goto("http://localhost:3000", wait_until="networkidle")
        
        # Bypass onboarding
        await page.evaluate("localStorage.setItem('kls_onboarding_done', 'true')")
        await page.reload(wait_until="networkidle")
        
        # 1. Login
        await page.screenshot(path=f"{output_dir}/login.png")
        
        # 2. Enter code
        await page.fill('input[type="password"]', "8899")
        # No button to click, the code auto-submits when length === 4 usually, or there is no button. Wait, is there a button?
        # Let's wait a bit instead of clicking a button.
        await page.wait_for_timeout(1000)
        
        # 3. Navigation
        await page.screenshot(path=f"{output_dir}/navigation.png")
        
        # 4. Click a category
        cards = await page.locator('div[class*="categoryCard"]').all()
        if cards:
            await cards[0].click()
            await page.wait_for_timeout(1000)
            
            # 5. Standard Items
            await page.screenshot(path=f"{output_dir}/standard_items.png")
            
            # 6. Add items
            plus_btns = await page.locator('button:has-text("+")').all()
            for btn in plus_btns[:3]:
                await btn.click()
                
            await page.wait_for_timeout(1000)
            # 7. Checkout
            await page.screenshot(path=f"{output_dir}/checkout.png")
            
        await browser.close()

asyncio.run(main())
