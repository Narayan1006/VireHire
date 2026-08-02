import { chromium } from 'playwright'
import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const htmlPath = path.join(__dirname, 'VeriHire-Project-Overview.html')
const pdfPath = path.join(__dirname, 'VeriHire-Project-Overview.pdf')

if (!fs.existsSync(htmlPath)) {
  console.error('HTML source not found:', htmlPath)
  process.exit(1)
}

const browser = await chromium.launch()
const page = await browser.newPage()
await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`, { waitUntil: 'networkidle' })
await page.pdf({
  path: pdfPath,
  format: 'A4',
  printBackground: true,
  margin: { top: '0', right: '0', bottom: '0', left: '0' },
})
await browser.close()
console.log('PDF written to', pdfPath)
