const fs = require('fs');

// 1x1 transparent PNG base64
const transparentPngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
const buffer = Buffer.from(transparentPngBase64, 'base64');

const data = require('./src/data/offer_catalog.json');
const disciplines = [...new Set(data.map(d => d.name))];
fs.mkdirSync('./public/disciplines', { recursive: true });

disciplines.forEach(d => {
  try {
    fs.writeFileSync(`./public/disciplines/${d}.png`, buffer);
  } catch (e) {
    console.error(e);
  }
});
console.log('Transparent placeholders created for:', disciplines);
