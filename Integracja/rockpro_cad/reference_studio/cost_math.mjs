// A partial estimate, not a production quote. Never infer profile/sheet units.
export const normalizeCode=value=>String(value??'').replace(/^(?:AH|PN)\s*[-–]\s*/i,'').replace(/\s+/g,'').toUpperCase();
const pieceFamilies=new Set(['handles','hinges','latches','corners','braces','wheels','stacking_sockets']);
export function estimateCosts(summary,catalog,assumePiece=true){
 const rows=[],totals=new Map();
 for(const item of summary?.rows??[]){
  const row={...item,price:null,amount:null,currency:null,reason:null,assumedUnit:false};
  const matches=catalog.items.filter(p=>item.pricing_company_id?p.id===item.pricing_company_id:normalizeCode(p.code)===normalizeCode(item.sku??item.part_id));
  if(!matches.length)row.reason='Brak powiązanej pozycji cenowej';
  else if(matches.length!==1)row.reason='Kilka rekordów tego kodu — wybierz wariant';
  else{
   const part=matches[0];row.company_id=part.id;
   const raw=part.price_raw,price=raw===null||raw===undefined||String(raw).trim()===''?null:Number(String(raw).replace(',','.'));
   if(price===null||!Number.isFinite(price)||price<0)row.reason='Brak poprawnej ceny';
   else if(!Number.isFinite(item.quantity)||item.quantity<0)row.reason='Brak ilości';
   else{
    row.price=price;row.currency=part.currency||'waluta nieoznaczona';
    const declaredPiece=['szt','szt.','piece','pcs'].includes(String(part.unit??'').toLowerCase());
    const packSize=item.pack_size??1;
    const canAssume=assumePiece&&!part.unit&&(pieceFamilies.has(item.family_id)||packSize>1);
    if(item.unit!=='szt.'||!declaredPiece&&!canAssume)row.reason='Jednostka ceny do potwierdzenia';
    else{
     row.assumedUnit=!declaredPiece;row.purchaseQuantity=Math.ceil(item.quantity/packSize);row.pack_size=packSize;
     row.amount=Math.round(price*row.purchaseQuantity*100)/100;
     totals.set(row.currency,(totals.get(row.currency)??0)+Math.round(price*row.purchaseQuantity*100));
    }
   }
  }
  rows.push(row);
 }
 return {rows,totals:[...totals].map(([currency,cents])=>({currency,amount:cents/100})),unpriced:rows.filter(r=>r.amount===null).length,assumed:rows.filter(r=>r.assumedUnit).length};
}
