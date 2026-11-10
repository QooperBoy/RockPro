// Hash the stored asset before decoding. Gzip keeps supplier geometry portable
// in Git and avoids shipping tens of megabytes of repeated JSON coordinates.
export async function decodeMesh(raw,compression){
 if(compression==='gzip'){
  if(typeof DecompressionStream==='undefined')throw Error('Ta przeglądarka nie obsługuje kompresji modeli 3D.');
  raw=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  if(raw.byteLength>64*1024*1024)throw Error('Model 3D przekracza limit podglądu.');
 }else if(compression)throw Error('Nieobsługiwana kompresja modelu 3D.');
 return JSON.parse(new TextDecoder().decode(raw));
}
