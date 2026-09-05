import { mkdir, copyFile, access } from 'node:fs/promises';

const files = [
  ['node_modules/html2pdf.js/dist/html2pdf.bundle.min.js', 'vendor/html2pdf.bundle.min.js'],
  ['node_modules/jspdf/dist/jspdf.umd.min.js', 'vendor/jspdf.umd.min.js'],
];

await mkdir('vendor', { recursive: true });
for (const [source, target] of files) {
  await access(source);
  await copyFile(source, target);
  console.log('[Machinepark] lokale browserbibliotheek: ' + target);
}
