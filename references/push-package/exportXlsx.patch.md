# Patch: drop the Source column from the GAAP Analysis export

The reference tab (`Mgmt Reporting (4).xlsx` → "GAAP Analysis") has no trailing Source
column, so `buildIncomeStatementXlsx` should not write one. Three deletions in
`src/lib/exportXlsx.ts`:

1. Remove the Source column width:

```diff
-  ws.getColumn(3 + dataColCount).width = 30; // Source
```

2. Remove the Source header cell:

```diff
-  const srcHeader = headerRow.getCell(3 + dataColCount);
-  srcHeader.value = "Source";
-  srcHeader.font = { name: DEFAULT_FONT, size: 8, bold: true };
-  srcHeader.border = { bottom: { style: "medium", color: { argb: "FF000000" } } };
```

3. Remove the per-row note cell, and stop spanning band styling over the extra column:

```diff
-      for (let i = 0; i < dataColCount + 1; i++) {
+      for (let i = 0; i < dataColCount; i++) {
         const c = excelRow.getCell(3 + i);
         applyRowStyle(c, s, false);
       }
...
-    const noteCell = excelRow.getCell(3 + dataColCount);
-    noteCell.value = opts.note ? opts.note(row) : "";
-    noteCell.font = { name: DEFAULT_FONT, size: 8, color: { argb: "FF6B7A8A" } };
-    noteCell.alignment = { horizontal: "left" };
```

`XlsxOptions.note` becomes unused — drop it from the interface and from callers.

Everything else in that file already matches the reference: freeze C5, gridlines off,
column A 6.86 / B 27.29 / data 14.71, Calibri 8 body and bold 10 section bands, the
reference fills and number formats, and the label indents.
