from pathlib import Path
p=Path('artifacts/core-native/sdk/DocumentLifecycle.cs')
s=p.read_text(encoding='utf-8')
key=' if(action=="save_all"){'
insert=''' if(action=="close_owned_empty"){
  var owned=new Dictionary<string,string>{{"Scene1","{7684DB7D-B0C5-4265-AC43-C560789E1AC3}"},{"Scene2","{151E8EC7-AA5D-44A1-952D-D757A7DEE681}"}};
  var closed=new List<object>();
  foreach(var d in documents){
   if(!owned.ContainsKey(d.Name))continue;
   var scene=d as IZSceneDoc;
   if(scene==null||d.FileGUID!=owned[d.Name]||scene.GetTopElement().GetChildrenCount()!=0)throw new Exception("Refusing to close nonempty or unidentified scene");
   var proof=Row(d);proof["ownership"]="Exact GUID of this agent's failed primitive creation probe; zero physical children";
   d.SetModifiedFlag(false);d.Close();closed.Add(proof);
  }
  Write(args[1],new{passed=true,action=action,closed=closed,remaining=Docs(app).Select(d=>(object)Row(d)).ToArray()});Console.WriteLine("Closed only owned empty probes: "+closed.Count);Environment.Exit(0);return 0;
 }
'''
assert key in s
p.write_text(s.replace(key,insert+key),encoding='utf-8')
