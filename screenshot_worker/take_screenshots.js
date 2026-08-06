const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ defaultViewport: { width: 1280, height: 800 } });
  const page = await browser.newPage();
  
  const outputDir = '../offer_webapp/public/onboarding';

  // Navigate to local app
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle2' });
  
  // 1. Screenshot of the login overlay
  await page.screenshot({ path: `${outputDir}/login.png` });
  
  // 2. Login as 8899 to unlock all
  await page.type('input[type="text"]', '8899');
  await page.click('button');
  await new Promise(r => setTimeout(r, 1000));
  
  // 3. Screenshot of Categories
  await page.screenshot({ path: `${outputDir}/navigation.png` });
  
  // 4. Click first category to see sets
  const categoryCards = await page.$$('div[class*="categoryCard"]');
  if (categoryCards.length > 0) {
    await categoryCards[0].click();
    await new Promise(r => setTimeout(r, 1000));
    
    // 5. Screenshot of standard items (scroll a bit if needed)
    await page.screenshot({ path: `${outputDir}/standard_items.png` });
    
    // 6. Add some items to cart
    // Since plus buttons are hard to target, we just use evaluate
    await page.evaluate(() => {
        const btns = document.querySelectorAll('button');
        const plusBtns = Array.from(btns).filter(b => b.textContent === '+');
        if(plusBtns[0]) plusBtns[0].click();
        if(plusBtns[1]) plusBtns[1].click();
    });
    
    await new Promise(r => setTimeout(r, 1000));
    
    // 7. Open cart (if mobile) or it might already be open on desktop
    // Just take screenshot of the whole page showing the cart sidebar
    await page.screenshot({ path: `${outputDir}/checkout.png` });
  }

  await browser.close();
})();
