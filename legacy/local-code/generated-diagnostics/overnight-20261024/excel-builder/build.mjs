import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const out=path.resolve(process.argv[2]);
await fs.mkdir(out,{recursive:true});
const rows=[
 ['schema_version',1,'','Wersja formatu arkusza'],
 ['project_id','PRZYKLAD','','Zastąp identyfikatorem projektu z RockPro'],
 ['expected_layout_revision',0,'','Odczytana wersja układu; 0 oznacza brak zapisu'],
 ['name','Epson EB-L630U','','Nazwa urządzenia'],
 ['x',440,'mm','Długość obrysu urządzenia'],['y',339,'mm','Głębokość obrysu urządzenia'],
 ['z',136,'mm','Wysokość obrysu urządzenia'],['count',1,'szt','Liczba urządzeń'],
 ['orientation','XYZ','','Dozwolone: XYZ, XZY, YXZ, YZX, ZXY, ZYX'],
 ['arrangement','X','','Kierunek ustawienia kolejnych urządzeń: X, Y, Z'],
 ['gap',20,'mm','Odstęp między urządzeniami'],['clearance',20,'mm','Luz obwodowy'],
 ['separator',0,'mm','Grubość przegrody między urządzeniami'],
 ['side','none','','Komora dodatkowa: none, X albo Y'],
 ['side_width',80,'mm','Szerokość komory dodatkowej'],['side_depth',300,'mm','Głębokość wyposażenia komory'],
 ['side_height',50,'mm','Wysokość wyposażenia komory'],['side_name','Kable','','Nazwa wyposażenia komory'],
 ['thickness',9.8,'mm','Grubość sklejki'],['lid_height',25,'mm','Wysokość pokrywy'],
 ['lid_hinge_height',0,'mm','Wymagane miejsce zawiasu; 0 = jeszcze niewybrany'],
 ['lid_constructor_override',false,'','Jawne odstępstwo konstruktora od proporcji pokrywy'],
];
for(const variant of ['poprawny','bledny','graniczny']){
 const wb=Workbook.create(),s=wb.worksheets.add('Konfiguracja');
 s.showGridLines=false;s.tabColor='#408080';
 s.getRange('A1:D1').merge();s.getRange('A1').values=[['RockPro — konfiguracja skrzyni']];
 s.getRange('A1:D1').format={fill:'#203c42',font:{bold:true,color:'#ffffff',size:18},rowHeight:38};
 s.getRange('A2:D2').merge();s.getRange('A2').values=[['Edytuj wartości w kolumnie B. Jednostki mm, cm i m podawaj jawnie w kolumnie C.']];
 s.getRange('A2:D2').format={wrapText:true,rowHeight:38,font:{size:11,color:'#52666d'}};
 s.getRange('A4:D4').values=[['Pole','Wartość','Jednostka','Opis']];
 s.getRange('A4:D4').format={fill:'#408080',font:{bold:true,color:'#ffffff'},rowHeight:26};
 const data=rows.map(r=>[...r]);
 if(variant==='bledny')data.find(r=>r[0]==='count')[1]=0;
 if(variant==='graniczny')data.find(r=>r[0]==='x')[1]=5000;
 s.getRange(`A5:D${data.length+4}`).values=data;
 s.getRange(`A5:D${data.length+4}`).format.rowHeight=27;
 s.getRange(`B5:C${data.length+4}`).format.fill='#fff0dc';
 s.getRange(`B5:B${data.length+4}`).format.font.color='#175b83';
 s.getRange('A:A').format.columnWidth=29;s.getRange('B:B').format.columnWidth=25;
 s.getRange('C:C').format.columnWidth=14;s.getRange('D:D').format.columnWidth=62;
 s.getRange(`D5:D${data.length+4}`).format.wrapText=true;
 s.freezePanes.freezeRows(4);wb.recalculate();
 console.log(variant,(await wb.inspect({kind:'table',range:'Konfiguracja!A4:D10',include:'values',tableMaxRows:7,tableMaxCols:4,maxChars:2000})).ndjson);
 const book=await SpreadsheetFile.exportXlsx(wb);await book.save(path.join(out,`RockPro_${variant}.xlsx`));
 if(variant==='poprawny'){
  const preview=await wb.render({sheetName:'Konfiguracja',range:'A1:D26',scale:1.5,format:'png'});
  await fs.writeFile(path.join(out,'preview.png'),new Uint8Array(await preview.arrayBuffer()));
 }
}
