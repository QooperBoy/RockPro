from pathlib import Path
p=Path(__file__).with_name('DocumentLifecycle.cs')
s=p.read_text(encoding='utf-8')
marker=' if(action=="exit_clean"){'
code=''' if(action=="save_remaining_verified"){
  var proof=J.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(folder,"backups_completed.json")));
  if(!(bool)proof["passed"])throw new Exception("Backup phase not complete");
  var savedRows=((IEnumerable)proof["documents"]).Cast<Dictionary<string,object>>().ToList();
  if(savedRows.Count!=documents.Count)throw new Exception("Inventory count changed");
  foreach(var r in savedRows){foreach(string kind in new[]{"memory_backup","disk_backup"})if(r.ContainsKey(kind)&&Hash((string)r[kind])!=(string)r[kind+"_sha256"])throw new Exception("Backup hash changed");}
  for(int i=0;i<documents.Count;i++){
   var d=documents[i];var r=savedRows[i];var b=(Dictionary<string,object>)r["before"];
   bool renamedOriginal=i==0&&Same(d.Name,Path.Combine(folder,"001_Showcase_Epson_parametry_saved_readonly.ics"));
   if(d.FileGUID!=(string)b["file_guid"]||(!renamedOriginal&&!Same(d.Name,(string)b["path"])))throw new Exception("Document identity changed");
   r["continuation_before"]=Row(d);
   if(d.Modified){
    if(!r.ContainsKey("memory_backup"))throw new Exception("Dirty document without verified backup");
    string output=(string)r["unique_saved_path"];
    if(File.Exists(output))throw new Exception("Unique save destination exists");
    ((IZSceneDoc)d).SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
    if(!Same(d.Name,output))throw new Exception("SaveAs path mismatch");
    r["save_mode"]="user_authorized_unique_saved_copy";
   }else r["save_mode"]=renamedOriginal?"user_authorized_readonly_saveas_completed":"already_clean";
   if(d.Modified||!File.Exists(d.Name))throw new Exception("Document remains dirty or missing");
   r["after"]=Row(d);r["saved_sha256"]=Hash(d.Name);
   Write(Path.Combine(folder,(i+1).ToString("D3")+"_continued_record.json"),r);Console.WriteLine("CLEAN "+d.Name);
  }
  var after=Docs(app);if(after.Count!=documents.Count||after.Any(d=>d.Modified))throw new Exception("Final inventory dirty or changed");
  Write(args[1],new{passed=true,action=action,count=after.Count,backup_directory=folder,documents=savedRows,after=after.Select(d=>(object)Row(d)).ToArray()});
  Console.WriteLine("SAVE_REMAINING PASS "+after.Count);Environment.Exit(0);return 0;
 }
'''
assert marker in s and 'if(action=="save_remaining_verified")' not in s
p.write_text(s.replace(marker,code+marker),encoding='utf-8')
