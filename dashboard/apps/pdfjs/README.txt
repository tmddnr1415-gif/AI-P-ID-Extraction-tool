pdf.js (pdfjs-dist 3.11.174) - Mozilla, Apache License 2.0 (LICENSE)
Source: https://github.com/mozilla/pdf.js  /  npm package pdfjs-dist@3.11.174

Used by the dashboard "My memo" (내 메모장) PDF viewer: draws PDF pages inside the browser
so the user can write on them with the pen tools. Nothing is sent to the internet.

Files (unchanged from the npm package):
  pdf.min.js          build/pdf.min.js
  pdf.worker.min.js   build/pdf.worker.min.js
  cmaps/              character maps for CJK fonts that are not embedded in a PDF
  standard_fonts/     the 14 standard PDF fonts
Served by the dashboard server at /apps/pdfjs/ . If this folder is missing, the memo falls
back to the browser's built-in PDF viewer (no pen on the PDF).
