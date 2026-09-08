---
name: pdf-layout-analysis
description: Turn raw PDF forensics (spans, images, vectors) into layout-aware structure — reading order, paragraphs/sections, columns, tables, headers/footers — and reason about layout constraints before translation. Use whenever grouping text, computing reading order, detecting tables, or deciding how much room a translated block has to grow into.
---

# PDF Layout Analysis

Translation is subordinate to layout preservation, not the other way
around. This skill governs the pipeline stage between raw forensics
(`pdf-forensics`) and translation:

```text
PDF → geometry → text regions → columns → tables → images
    → reading order → layout constraints
```

## Rules

1. **A span is a rendering unit, not a semantic unit.** "Healthy " +
   "food " + "choices" may be three spans because "food" is bold, but
   it's one phrase. Group spans into lines → paragraphs before handing
   anything to a translator (master plan Section 8). Translate the
   semantic block, then map the result back onto the visual spans.
2. **Reading order is not top-to-bottom span order for multi-column
   layouts.** Detect columns by x-coordinate clustering before
   assuming vertical order. Get this wrong and translated text lands
   in the wrong place even if geometry is otherwise correct.
3. **Detect headers/footers by repetition, not by page position
   alone.** If near-identical text appears at approximately the same
   coordinates across many pages, classify it once as HEADER/FOOTER
   and translate once — reuse that translation everywhere it recurs
   (Section 26). Don't re-translate the same footer 40 times
   independently; that's how you get inconsistent output.
4. **Tables are structured objects, not independent rectangles.**
   Represent Table → Row → Cell explicitly. Preserve column widths,
   row heights, borders, and alignment as constraints the layout
   engine must respect, not as things translation is free to shift.
5. **Every translation unit carries a `layout_constraints` package**
   (`max_width`, `max_height`, `original_font_size` — see master plan
   Section 7) — layout analysis is what computes these numbers from
   the forensics bbox data, before the unit ever reaches a translator.
6. **Compute, don't guess, available space.** `max_width` /
   `max_height` come from the object's own bbox and its neighbors'
   bboxes (to avoid collisions) — never a hardcoded constant.
7. **Flag layout-infeasible cases instead of silently reflowing the
   whole page.** If a block's neighbors leave no room for expansion,
   that's a `LAYOUT_WARNING` for the text-fit engine (Milestone 3), not
   something this skill should "fix" by moving unrelated objects.

## When this applies

Building/extending anything in the document-understanding or layout
layer: grouping spans into paragraphs, computing reading order,
detecting tables/columns/headers, or computing fit constraints before
translation. Not for the translation call itself (see
`translation-quality`) and not for post-render comparison (see
`visual-pdf-qa`).
