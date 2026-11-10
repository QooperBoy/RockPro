using System;using System.Linq;using RockPro.CAD;
class WallMountMathChecks {
 static int count;
 static void Check(bool ok,string label){if(!ok)throw new Exception(label);Console.WriteLine("PASS "+label);count++;}
 static void Main(){
  double[][] rotations={new[]{1.0,0,0,0,0,0,1,0,0,-1,0,0,4,5,6,1},new[]{-1.0,0,0,0,0,0,1,0,0,1,0,0,4,5,6,1},new[]{0.0,-1,0,0,0,0,1,0,-1,0,0,0,4,5,6,1},new[]{0.0,1,0,0,0,0,1,0,1,0,0,0,4,5,6,1},new[]{1.0,0,0,0,0,1,0,0,0,0,1,0,4,5,6,1},new[]{1.0,0,0,0,0,-1,0,0,0,0,-1,0,4,5,6,1}};
  double[] world={0,1,0,0,1,0,0,0,0,0,1,0,.12,.34,.56,1};
  for(int i=0;i<6;i++){
   var f=rotations[i];var round=WallMountMapper.Compose(WallMountMapper.Relative(world,f),f);Check(round.Zip(world,(a,b)=>Math.Abs(a-b)).Max()<1e-12,"rigid mirrored catalog frame roundtrip wall "+(i+1));
   var anchor=WallMountMapper.Anchor(f,300,400);var distance=Enumerable.Range(0,3).Sum(k=>Math.Pow(anchor[12+k]-f[12+k],2));Check(Math.Abs(distance-.25)<1e-12,"millimetre U/V translation wall "+(i+1));
  }
  Check(!WallMountMapper.Overlap(new[]{0.0,0,100,100},new[]{112.0,0,212,100},12),"exact clearance accepted");
  Check(WallMountMapper.Overlap(new[]{0.0,0,100,100},new[]{111.9,0,212,100},12),"clearance intrusion rejected");
  Check(!WallMountMapper.Overlap(new[]{0.0,0,100,100},new[]{0.0,112,100,212},12),"different height rows clear");
  Check(WallMountMapper.Overlap(new[]{0.0,0,100,100},new[]{50.0,50,150,150},12),"crossing footprints detected");
  Console.WriteLine(count+" wall-mapping checks PASS");
 }
}
