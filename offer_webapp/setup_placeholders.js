const fs = require('fs');
const data = require('./src/data/offer_catalog.json');
const disciplines = [...new Set(data.map(d => d.name))];
fs.mkdirSync('./public/disciplines', { recursive: true });
disciplines.forEach(d => {
  try {
    fs.copyFileSync('./public/bg_generic.png', `./public/disciplines/${d}.png`);
  } catch (e) {
    console.error(e);
  }
});
console.log('Placeholders created for:', disciplines);
