// Imprime anexos/presentacion/presentacion.html a T2_202602_G01_presentacion.pdf (una página por lámina).
// Uso, desde la carpeta de la entrega: node anexos/presentacion/exportar_pdf.js [carpeta_capturas]
// Con una carpeta como argumento guarda además una captura PNG de cada lámina, para revisarlas.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const raiz = path.resolve(__dirname, '..', '..');
const html = fs.readFileSync(path.join(__dirname, 'presentacion.html'), 'utf8');
const pdf = path.join(raiz, 'T2_202602_G01_presentacion.pdf');
const capturas = process.argv[2];

(async () => {
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  // El HTML se escribe sin <html>/<head> (el visor de artifacts los agrega); aquí se envuelve igual.
  await pagina.setContent(`<!doctype html><html lang="es"><head><meta charset="utf-8"></head><body>${html}</body></html>`,
    { waitUntil: 'networkidle' });
  await pagina.evaluate(() => document.fonts.ready);
  const fuentes = await pagina.evaluate(() =>
    ['800 40px Archivo', '600 40px "IBM Plex Mono"', '400 40px Inter'].map(f => `${f}: ${document.fonts.check(f)}`));
  console.log('Fuentes cargadas:', fuentes.join(' · '));
  if (capturas) {
    fs.mkdirSync(capturas, { recursive: true });
    const n = await pagina.locator('.lamina').count();
    for (let k = 0; k < n; k++) {
      await pagina.evaluate(k => { location.hash = '#d' + (k + 1); mostrar(k); }, k);
      await pagina.screenshot({ path: path.join(capturas, `lamina_${String(k + 1).padStart(2, '0')}.png`) });
    }
  }
  await pagina.pdf({ path: pdf, width: '1920px', height: '1080px', printBackground: true });
  await navegador.close();
  console.log('Escrito', path.relative(raiz, pdf));
})();
