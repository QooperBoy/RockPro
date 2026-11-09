from pathlib import Path
from html import escape
from docx import Document
from docx.text.paragraph import Paragraph as DP
from docx.table import Table as DT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import pypdfium2 as pdfium
P=Path(__file__).parent
pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB','C:/Windows/Fonts/arialbd.ttf'))
styles={
 'Normal':ParagraphStyle('body',fontName='Arial',fontSize=10,leading=13.2,spaceAfter=6),
 'Title':ParagraphStyle('title',fontName='ArialB',fontSize=23,leading=28,spaceAfter=15),
 'Heading 1':ParagraphStyle('h1',fontName='ArialB',fontSize=17,leading=21,spaceAfter=13),
 'Heading 2':ParagraphStyle('h2',fontName='ArialB',fontSize=11.5,leading=15,spaceBefore=9,spaceAfter=6,keepWithNext=True),
 'cell':ParagraphStyle('cell',fontName='Arial',fontSize=9,leading=11.5),
}
def para(t, style): return Paragraph(escape(t).replace('\n','<br/>'), styles[style])
doc=Document(P/'RockPro_IronCAD_Dokumentacja_techniczna_MVP.docx')
story=[]
for el in doc.element.body:
 if el.tag.endswith('}p'):
  pp=DP(el,doc)
  if 'w:type="page"' in el.xml: story.append(PageBreak());continue
  if pp.text: story.append(para(pp.text, pp.style.name if pp.style.name in styles else 'Normal'))
 elif el.tag.endswith('}tbl'):
  tt=DT(el,doc)
  data=[[para(c.text,'cell') for c in r.cells] for r in tt.rows]
  widths=[float(c.width)/914400*72 for c in tt.rows[0].cells]
  scale=504/sum(widths); widths=[w*scale for w in widths]
  tb=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
  tb.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DFEAF0')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),4.5),('BOTTOMPADDING',(0,0),(-1,-1),4.5)]))
  story.extend([tb,Spacer(1,9)])
def frame(c,d):
 c.setFont('Arial',8)
 c.drawString(54,759,'RockPro  |  Integracja IronCAD  |  Dokumentacja techniczna MVP')
 c.drawString(54,31,'20 października 2026  •  Wersja 1.0')
 c.drawRightString(558,31,str(d.page))
out=P/'RockPro_IronCAD_Dokumentacja_techniczna_MVP.pdf'
SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=54,rightMargin=54,topMargin=55,bottomMargin=50).build(story,onFirstPage=frame,onLaterPages=frame)
qa=P/'qa_pdf';qa.mkdir(exist_ok=True)
pdf=pdfium.PdfDocument(str(out))
from PIL import Image,ImageOps,ImageDraw
thumbs=[]
for i,pg in enumerate(pdf):
 im=pg.render(scale=1.5).to_pil()
 im.save(qa/f'page-{i+1}.png')
 im.thumbnail((408,528))
 thumbs.append(im.copy())
contact=Image.new('RGB',(408*3,550*((len(thumbs)+2)//3)),'#bbb')
for i,im in enumerate(thumbs):contact.paste(im,((i%3)*408,(i//3)*550))
contact.save(qa/'contact.png')
print('Pages:',len(pdf))
