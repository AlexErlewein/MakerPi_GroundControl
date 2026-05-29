const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const htmlFile = process.argv[2] || 'ANGEBOT.html';
const pdfFile = process.argv[3] || 'ANGEBOT.pdf';

async function htmlToPdf() {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    const htmlPath = path.resolve(htmlFile);
    const fileUrl = `file://${htmlPath}`;

    console.log(`Loading ${fileUrl}...`);
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });

    console.log(`Generating PDF...`);
    await page.pdf({
        path: pdfFile,
        format: 'A4',
        printBackground: true,
        margin: {
            top: '20mm',
            right: '15mm',
            bottom: '15mm',
            left: '15mm'
        }
    });

    await browser.close();
    console.log(`PDF created: ${pdfFile}`);
}

htmlToPdf().catch(console.error);