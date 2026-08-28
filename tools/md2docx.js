/*
 * Convert a project report from Markdown to .docx.
 *
 *     node tools/md2docx.js docs/grid-analysis-report.md docs/grid-analysis-report.docx
 *
 * Handles the subset of Markdown the reports actually use: #/##/### headings,
 * paragraphs, bullet and numbered lists (with wrapped continuation lines), pipe
 * tables, fenced code blocks, blockquotes, horizontal rules, and inline
 * bold / italic / `code`. The Markdown stays the source of truth - edit it and
 * re-run this, don't edit the .docx.
 */

const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  PageNumber, Packer, Paragraph, ShadingType, Table, TableCell, TableRow,
  TextRun, WidthType,
} = require("docx");

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("usage: node tools/md2docx.js <input.md> <output.docx>");
  process.exit(1);
}

const CODE_FONT = "Consolas";
const PAGE_WIDTH_DXA = 9360; // usable width inside default A4 margins

// ---------------------------------------------------------------- inline runs

function inlineRuns(text, base = {}) {
  // Split on **bold**, *italic* and `code`, preserving order.
  const runs = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > last) runs.push(new TextRun({ text: text.slice(last, match.index), ...base }));
    const token = match[0];
    if (token.startsWith("**")) {
      runs.push(new TextRun({ text: token.slice(2, -2), bold: true, ...base }));
    } else if (token.startsWith("`")) {
      runs.push(new TextRun({ text: token.slice(1, -1), font: CODE_FONT, size: 20, ...base }));
    } else {
      runs.push(new TextRun({ text: token.slice(1, -1), italics: true, ...base }));
    }
    last = match.index + token.length;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), ...base }));
  return runs;
}

// Collapse the hard-wrapped source lines of one block into a single string.
function joinWrapped(lines) {
  return lines.map((l) => l.trim()).join(" ").replace(/\s+/g, " ").trim();
}

// ---------------------------------------------------------------- block parser

const src = fs.readFileSync(inputPath, "utf-8").replace(/\r\n/g, "\n");
const lines = src.split("\n");
const children = [];
let numberedInstance = 0; // separate numbering restart per list

let i = 0;
while (i < lines.length) {
  const line = lines[i];

  if (!line.trim()) { i += 1; continue; }

  // Fenced code block (language tag ignored; mermaid blocks are skipped -
  // diagrams live in design-diagrams.md and render on GitHub).
  if (line.startsWith("```")) {
    const lang = line.slice(3).trim();
    const buf = [];
    i += 1;
    while (i < lines.length && !lines[i].startsWith("```")) { buf.push(lines[i]); i += 1; }
    i += 1;
    if (lang === "mermaid") continue;
    buf.forEach((codeLine, idx) => {
      children.push(new Paragraph({
        children: [new TextRun({ text: codeLine || " ", font: CODE_FONT, size: 18 })],
        shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
        spacing: { before: idx === 0 ? 120 : 0, after: idx === buf.length - 1 ? 120 : 0 },
      }));
    });
    continue;
  }

  // Horizontal rule -> thin bottom border on an empty paragraph.
  if (/^-{3,}$/.test(line.trim())) {
    children.push(new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "999999" } },
      spacing: { after: 240 },
    }));
    i += 1;
    continue;
  }

  // Headings.
  const heading = line.match(/^(#{1,3})\s+(.*)$/);
  if (heading) {
    const level = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][heading[1].length - 1];
    children.push(new Paragraph({ heading: level, children: inlineRuns(heading[2]) }));
    i += 1;
    continue;
  }

  // Blockquote.
  if (line.startsWith(">")) {
    const buf = [];
    while (i < lines.length && lines[i].startsWith(">")) {
      buf.push(lines[i].replace(/^>\s?/, ""));
      i += 1;
    }
    children.push(new Paragraph({
      children: inlineRuns(joinWrapped(buf)),
      indent: { left: 480 },
      border: { left: { style: BorderStyle.SINGLE, size: 12, color: "2B6CB0" } },
      spacing: { before: 120, after: 120 },
    }));
    continue;
  }

  // Table.
  if (line.trim().startsWith("|")) {
    const rowLines = [];
    while (i < lines.length && lines[i].trim().startsWith("|")) { rowLines.push(lines[i]); i += 1; }
    const cellsOf = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    const parsed = rowLines.filter((l) => !/^\|?[\s:|-]+\|?$/.test(l)).map(cellsOf);
    if (parsed.length === 0) continue;
    const cols = parsed[0].length;
    const colWidth = Math.floor(PAGE_WIDTH_DXA / cols);
    const widths = Array(cols).fill(colWidth);
    const rows = parsed.map((cells, rowIdx) => new TableRow({
      tableHeader: rowIdx === 0,
      children: cells.map((cell) => new TableCell({
        width: { size: colWidth, type: WidthType.DXA },
        shading: rowIdx === 0 ? { type: ShadingType.CLEAR, fill: "DCE6F1" } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: inlineRuns(cell, rowIdx === 0 ? { bold: true } : {}) })],
      })),
    }));
    children.push(new Table({ columnWidths: widths, width: { size: PAGE_WIDTH_DXA, type: WidthType.DXA }, rows }));
    children.push(new Paragraph({ spacing: { after: 120 } }));
    continue;
  }

  // Bullet / numbered list item (continuation lines are indented).
  const bullet = line.match(/^- (.*)$/);
  const numbered = line.match(/^(\d+)\. (.*)$/);
  if (bullet || numbered) {
    const isNumbered = Boolean(numbered);
    if (isNumbered && numbered[1] === "1") numberedInstance += 1;
    const items = [];
    while (i < lines.length) {
      const start = lines[i].match(isNumbered ? /^\d+\. (.*)$/ : /^- (.*)$/);
      if (!start) break;
      const buf = [start[1]];
      i += 1;
      while (i < lines.length && /^\s{2,}\S/.test(lines[i])) { buf.push(lines[i]); i += 1; }
      items.push(joinWrapped(buf));
    }
    items.forEach((item) => {
      children.push(new Paragraph({
        children: inlineRuns(item),
        numbering: isNumbered
          ? { reference: "numbers", level: 0, instance: numberedInstance }
          : { reference: "bullets", level: 0 },
        spacing: { after: 60 },
      }));
    });
    continue;
  }

  // Plain paragraph: join until a blank line or another block type.
  const buf = [line];
  i += 1;
  while (i < lines.length && lines[i].trim()
         && !/^(#{1,3}\s|```|-{3,}$|>|\|)/.test(lines[i].trim())
         && !/^- /.test(lines[i]) && !/^\d+\. /.test(lines[i])) {
    buf.push(lines[i]);
    i += 1;
  }
  children.push(new Paragraph({ children: inlineRuns(joinWrapped(buf)), spacing: { after: 120 } }));
}

// ---------------------------------------------------------------- document

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22 } }, // 11pt body
      heading1: { run: { size: 36, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 240, after: 160 } } },
      heading2: { run: { size: 28, bold: true, color: "2B6CB0" }, paragraph: { spacing: { before: 240, after: 120 } } },
      heading3: { run: { size: 24, bold: true, color: "404040" }, paragraph: { spacing: { before: 180, after: 100 } } },
    },
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
                   style: { paragraph: { indent: { left: 460, hanging: 230 } } } }],
      },
      {
        reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                   style: { paragraph: { indent: { left: 460, hanging: 230 } } } }],
      },
    ],
  },
  sections: [{
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 18, color: "808080" })],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`${path.basename(outputPath)}: ${(buffer.length / 1024).toFixed(0)} KB`);
});
