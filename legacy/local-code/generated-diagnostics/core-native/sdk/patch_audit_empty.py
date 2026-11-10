from pathlib import Path
p=Path('artifacts/core-native/sdk/DocumentLifecycle.cs')
s=p.read_text(encoding='utf-8')
old='static Dictionary<string,object> Row(IZDoc d){return new Dictionary<string,object>{{"path",d.Name},{"file_guid",d.FileGUID},{"modified",d.Modified},{"read_only",d.IsReadOnly()},{"type",(int)d.Type}};}'
new='static Dictionary<string,object> Row(IZDoc d){var r=new Dictionary<string,object>{{"path",d.Name},{"file_guid",d.FileGUID},{"modified",d.Modified},{"read_only",d.IsReadOnly()},{"type",(int)d.Type}};if(d.Name=="Scene1"||d.Name=="Scene2"){var scene=d as IZSceneDoc;if(scene!=null){r["physical_children"]=scene.GetTopElement().GetChildrenCount();}}return r;}'
assert old in s
p.write_text(s.replace(old,new),encoding='utf-8')
