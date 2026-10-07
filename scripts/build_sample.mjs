import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const tables = JSON.parse(await fs.readFile('outputs/sample_tables.json', 'utf8'));
const wb = Workbook.create();
for (const [name, rows] of Object.entries(tables)) {
  const sheet = wb.worksheets.add(name);
  const range = sheet.getRangeByIndexes(0, 0, rows.length, rows[0].length);
  range.values = rows;
  range.format.font = {name: 'Arial', size: 11};
  range.format.verticalAlignment = 'center';
  range.format.columnWidth = 24;
  range.format.rowHeight = 26;
  const header = sheet.getRangeByIndexes(0, 0, 1, rows[0].length);
  header.format.fill = '#234E70';
  header.format.font = {name: 'Arial', size: 11, bold: true, color: '#FFFFFF'};
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  if (name === 'Be') sheet.getRange('D1:D10').format.columnWidth = 42;
  if (name === 'Insight_be') sheet.getRange('B1:B10').format.columnWidth = 90;
  if (name === 'Interview_TNV') range.format.columnWidth = 48;
  if (name === 'Interview_TNV') {range.format.wrapText = true; range.format.rowHeight = 45;}
  if (name === 'Be') sheet.getRange('B2:C10').setNumberFormat('0');
  if (name === 'TNV') sheet.getRange('C2:D20').setNumberFormat('0');
  if (name === 'Danh_gia_ghep') sheet.getRange('C2:C100').dataValidation = {rule:{type:'list',values:['Ưu tiên','Bình thường','Không ghép']}};
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Be!A1:D10',include:'values',tableMaxRows:10,tableMaxCols:4,maxChars:2500})).ndjson);
for (const name of Object.keys(tables)) {
  const preview = await wb.render({sheetName:name,autoCrop:'all',scale:1,format:'png'});
  await fs.writeFile(`outputs/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save('data/du_lieu_mau.xlsx');
