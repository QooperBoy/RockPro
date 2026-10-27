// Pure placement rules for a conceptual mesh preview. Inputs/outputs are metres.
export function placement(bounds, baseline, target, resizeAxes=[]) {
 const center=bounds.slice(0,3).map((v,k)=>(v+bounds[k+3])/2);
 const scale=[0,1,2].map(k=>resizeAxes.includes(k)?target[k]/(baseline[k+3]-baseline[k]):1);
 const destination=center.map((c,k)=>{
  const start=baseline[k],size=baseline[k+3]-start,width=bounds[k+3]-bounds[k];
  if(resizeAxes.includes(k))return start+(c-start)*target[k]/size;
  // Objects outside the shell keep their edge offset (e.g. wheels below the floor).
  if(c<start)return c;
  if(c>start+size)return start+target[k]+c-start-size;
  const available=size-width;
  if(Math.abs(available)<1e-6)return start+target[k]/2;
  const fraction=(c-start-width/2)/available;
  return start+width/2+fraction*(target[k]-width);
 });
 return {center,destination,scale};
}
