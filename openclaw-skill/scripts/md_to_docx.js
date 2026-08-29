#!/usr/bin/env node
/**
 * md_to_docx.js — Markdown to DOCX converter with professional formatting
 *
 * Features:
 *   - No bookmarks (書籤)
 *   - Clean professional layout with proper Chinese typography
 *   - Bold, italic, underline support
 *   - Hierarchical headings with proper spacing
 *   - Bullet and numbered lists
 *   - YAML front matter stripped
 *   - Page numbers in footer
 *   - Proper A4 page size with comfortable margins
 *
 * Usage: node md_to_docx.js input.md [output.docx]
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun,
  Header, Footer, AlignmentType,
  LevelFormat, HeadingLevel, BorderStyle,
  PageNumber, PageBreak
} = require("docx");

// ─── Parse CLI args ───
const args = process.argv.slice(2);
if (args.length < 1) {
  console.error("Usage: node md_to_docx.js <input.md> [output.docx]");
  process.exit(1);
}
const inputPath = args[0];
const outputPath = args[1] || inputPath.replace(/\.md$/i, ".docx");

// ─── Read and preprocess markdown ───
let md = fs.readFileSync(inputPath, "utf-8");

// Strip YAML front matter
md = md.replace(/^---\n[\s\S]*?\n---\n*/, "");

// ─── Markdown parser ───

/**
 * Parse inline formatting: **bold**, *italic*, __underline__, ~~strikethrough~~
 * Returns array of TextRun objects
 */
function parseInline(text, baseStyle = {}) {
  const runs = [];
  // Regex for inline formatting - order matters
  // Match: **bold**, *italic*, __underline__, `code`
  const pattern = /(\*\*(.+?)\*\*|__(.+?)__|_(.+?)_|\*(.+?)\*|`(.+?)`)/g;

  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index);
      if (before) {
        runs.push(new TextRun({ text: before, font: "Arial", size: 24, ...baseStyle }));
      }
    }

    if (match[2]) {
      // **bold**
      runs.push(...parseInline(match[2], { ...baseStyle, bold: true }));
    } else if (match[3]) {
      // __underline__
      runs.push(...parseInline(match[3], { ...baseStyle, underline: { type: "single" } }));
    } else if (match[4]) {
      // _italic_ (single underscore)
      runs.push(...parseInline(match[4], { ...baseStyle, italics: true }));
    } else if (match[5]) {
      // *italic* (single asterisk)
      runs.push(...parseInline(match[5], { ...baseStyle, italics: true }));
    } else if (match[6]) {
      // `code`
      runs.push(new TextRun({
        text: match[6],
        font: "Courier New",
        size: 22,
        ...baseStyle
      }));
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    const remaining = text.slice(lastIndex);
    if (remaining) {
      runs.push(new TextRun({ text: remaining, font: "Arial", size: 24, ...baseStyle }));
    }
  }

  // If no runs were created, add the whole text
  if (runs.length === 0 && text) {
    runs.push(new TextRun({ text, font: "Arial", size: 24, ...baseStyle }));
  }

  return runs;
}

/**
 * Parse markdown content into docx paragraphs
 */
function parseMarkdown(markdown) {
  const lines = markdown.split("\n");
  const paragraphs = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Skip empty lines
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Heading 1: # Title
    if (/^# (.+)/.test(line)) {
      const text = line.replace(/^# /, "").trim();
      paragraphs.push(new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 360, after: 240 },
        children: [new TextRun({
          text,
          font: "Arial",
          size: 36, // 18pt
          bold: true,
          color: "1F4E79"
        })]
      }));
      i++;
      continue;
    }

    // Heading 2: ## Title
    if (/^## (.+)/.test(line)) {
      const text = line.replace(/^## /, "").trim();
      paragraphs.push(new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 300, after: 180 },
        border: {
          bottom: { style: BorderStyle.SINGLE, size: 4, color: "4472C4", space: 4 }
        },
        children: [new TextRun({
          text,
          font: "Arial",
          size: 30, // 15pt
          bold: true,
          color: "2E75B6"
        })]
      }));
      i++;
      continue;
    }

    // Heading 3: ### Title
    if (/^### (.+)/.test(line)) {
      const text = line.replace(/^### /, "").trim();
      paragraphs.push(new Paragraph({
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 240, after: 120 },
        children: [new TextRun({
          text,
          font: "Arial",
          size: 26, // 13pt
          bold: true,
          color: "404040"
        })]
      }));
      i++;
      continue;
    }

    // Heading 4: #### Title
    if (/^#### (.+)/.test(line)) {
      const text = line.replace(/^#### /, "").trim();
      paragraphs.push(new Paragraph({
        heading: HeadingLevel.HEADING_4,
        spacing: { before: 200, after: 100 },
        children: [new TextRun({
          text,
          font: "Arial",
          size: 24, // 12pt
          bold: true,
          italics: true,
          color: "595959"
        })]
      }));
      i++;
      continue;
    }

    // Horizontal rule: --- or ***
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      paragraphs.push(new Paragraph({
        border: {
          bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 6 }
        },
        spacing: { before: 200, after: 200 },
        children: []
      }));
      i++;
      continue;
    }

    // Bullet list: - item or * item
    if (/^[\s]*[-*]\s+/.test(line)) {
      const indent = line.match(/^(\s*)/)[1].length;
      const level = Math.min(Math.floor(indent / 2), 2);
      const text = line.replace(/^[\s]*[-*]\s+/, "").trim();

      paragraphs.push(new Paragraph({
        numbering: { reference: "bullets", level },
        spacing: { before: 40, after: 40, line: 320 },
        children: parseInline(text)
      }));
      i++;
      continue;
    }

    // Numbered list: 1. item
    if (/^[\s]*\d+\.\s+/.test(line)) {
      const indent = line.match(/^(\s*)/)[1].length;
      const level = Math.min(Math.floor(indent / 2), 2);
      const text = line.replace(/^[\s]*\d+\.\s+/, "").trim();

      paragraphs.push(new Paragraph({
        numbering: { reference: "numbers", level },
        spacing: { before: 40, after: 40, line: 320 },
        children: parseInline(text)
      }));
      i++;
      continue;
    }

    // Blockquote: > text
    if (/^>\s*(.*)/.test(line)) {
      const text = line.replace(/^>\s*/, "").trim();
      if (text) {
        paragraphs.push(new Paragraph({
          indent: { left: 720 },
          spacing: { before: 120, after: 120, line: 320 },
          border: {
            left: { style: BorderStyle.SINGLE, size: 12, color: "4472C4", space: 8 }
          },
          children: parseInline(text, { italics: true, color: "555555" })
        }));
      }
      i++;
      continue;
    }

    // Regular paragraph - collect consecutive non-empty lines
    let paraText = line.trim();
    i++;

    // Don't merge with next line if next line is a heading, list, etc.
    while (i < lines.length && lines[i].trim() !== ""
      && !/^#{1,4}\s/.test(lines[i])
      && !/^[-*]\s+/.test(lines[i])
      && !/^\d+\.\s+/.test(lines[i])
      && !/^>\s/.test(lines[i])
      && !/^(-{3,}|\*{3,})$/.test(lines[i].trim())) {
      paraText += " " + lines[i].trim();
      i++;
    }

    paragraphs.push(new Paragraph({
      spacing: { before: 80, after: 80, line: 360 },
      children: parseInline(paraText)
    }));
  }

  return paragraphs;
}

// ─── Extract title from content ───
function extractTitle(markdown) {
  const match = markdown.match(/^# (.+)/m);
  return match ? match[1].trim() : path.basename(inputPath, ".md");
}

// ─── Build document ───
async function buildDocx() {
  const title = extractTitle(md);
  const content = parseMarkdown(md);

  const doc = new Document({
    creator: "Audio Transcription Pipeline",
    title: title,
    description: "Auto-generated speaker notes",
    styles: {
      default: {
        document: {
          run: { font: "Arial", size: 24 } // 12pt default
        }
      },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
          quickFormat: true,
          run: { size: 36, bold: true, font: "Arial", color: "1F4E79" },
          paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 }
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
          quickFormat: true,
          run: { size: 30, bold: true, font: "Arial", color: "2E75B6" },
          paragraph: { spacing: { before: 300, after: 180 }, outlineLevel: 1 }
        },
        {
          id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal",
          quickFormat: true,
          run: { size: 26, bold: true, font: "Arial", color: "404040" },
          paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 }
        },
        {
          id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal",
          quickFormat: true,
          run: { size: 24, bold: true, italics: true, font: "Arial", color: "595959" },
          paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 3 }
        }
      ]
    },
    numbering: {
      config: [
        {
          reference: "bullets",
          levels: [
            {
              level: 0, format: LevelFormat.BULLET, text: "\u2022",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } }
            },
            {
              level: 1, format: LevelFormat.BULLET, text: "\u25E6",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 1440, hanging: 360 } } }
            },
            {
              level: 2, format: LevelFormat.BULLET, text: "\u25AA",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 2160, hanging: 360 } } }
            }
          ]
        },
        {
          reference: "numbers",
          levels: [
            {
              level: 0, format: LevelFormat.DECIMAL, text: "%1.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } }
            },
            {
              level: 1, format: LevelFormat.LOWER_LETTER, text: "%2)",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 1440, hanging: 360 } } }
            },
            {
              level: 2, format: LevelFormat.LOWER_ROMAN, text: "%3.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 2160, hanging: 360 } } }
            }
          ]
        }
      ]
    },
    sections: [{
      properties: {
        page: {
          size: {
            width: 11906,  // A4 width in DXA
            height: 16838  // A4 height in DXA
          },
          margin: {
            top: 1440,    // 1 inch = 2.54 cm
            right: 1260,  // ~2.2 cm
            bottom: 1440,
            left: 1260
          }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            spacing: { after: 120 },
            border: {
              bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 4 }
            },
            children: [new TextRun({
              text: title,
              font: "Arial",
              size: 18, // 9pt
              color: "999999",
              italics: true
            })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            border: {
              top: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 4 }
            },
            children: [
              new TextRun({ text: "Page ", font: "Arial", size: 18, color: "999999" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "999999" }),
              new TextRun({ text: " / ", font: "Arial", size: 18, color: "999999" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: "999999" })
            ]
          })]
        })
      },
      children: content
    }]
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(JSON.stringify({
    status: "success",
    output: outputPath,
    size: buffer.length,
    paragraphs: content.length
  }));
}

buildDocx().catch(err => {
  console.error(JSON.stringify({ status: "error", message: err.message }));
  process.exit(1);
});
