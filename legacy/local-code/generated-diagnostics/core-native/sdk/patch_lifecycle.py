from pathlib import Path
p=Path('artifacts/core-native/sdk/DocumentLifecycle.cs')
s=p.read_text(encoding='utf-8-sig')
a=s.index('  for(int i=0;i<documents.Count;i++)')
b=s.index('  var after=Docs(app);',a)
s=s[:a]+'''  // Capture every dirty/unnamed document before saving any original.
  for(int i=0;i<documents.Count;i++){
   IZDoc d=documents[i];var record=new Dictionary<string,object>{{"before",Row(d)}};records.Add(record);
   string old=d.Name;bool named=Path.IsPathRooted(old)&&File.Exists(old);bool needs=d.Modified||!named;
   record["needed_save_before"]=needs;
   if(needs){
    IZSceneDoc scene=d as IZSceneDoc;if(scene==null)throw new Exception("Cannot back up unsaved non-scene document safely; no original save performed");
    string label=(i+1).ToString("D3")+"_"+Safe(Path.GetFileNameWithoutExtension(old));if(label.EndsWith("_"))label+="unnamed";
    string memory=Path.Combine(folder,label+"_memory_before.ics");scene.SaveAsCopy(memory,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
    record["memory_backup"]=memory;record["memory_backup_sha256"]=Hash(memory);
    if(named){string disk=Path.Combine(folder,label+"_disk_before.ics");File.Copy(old,disk,false);record["disk_backup"]=disk;record["disk_backup_sha256"]=Hash(disk);}
    record["unique_saved_path"]=Path.Combine(folder,label+"_saved.ics");
   }
  }
  Write(Path.Combine(folder,"backups_completed.json"),new{passed=true,original_saves_started=false,documents=records});
  for(int i=0;i<documents.Count;i++){
   IZDoc d=documents[i];var record=(Dictionary<string,object>)records[i];string old=d.Name;bool named=Path.IsPathRooted(old)&&File.Exists(old);bool needs=d.Modified||!named;
   if(needs){
    if(!record.ContainsKey("memory_backup"))throw new Exception("Previously clean document changed during backup; stop before unprotected save");
    if(named&&!d.IsReadOnly()){d.Save();record["save_mode"]="save_existing_user_authorized";if(!Same(d.Name,old))throw new Exception("Save changed existing document path");}
    else{string output=(string)record["unique_saved_path"];((IZSceneDoc)d).SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);record["save_mode"]=named?"read_only_preserved_as_unique_copy":"unnamed_preserved_as_unique_copy";record["saved_path"]=output;if(!Same(d.Name,output))throw new Exception("SaveAs path mismatch");}
   }else record["save_mode"]="already_clean_unchanged";
   if(d.Modified||!Path.IsPathRooted(d.Name)||!File.Exists(d.Name))throw new Exception("Document remains unsaved after save-all");
   record["after"]=Row(d);record["saved_sha256"]=Hash(d.Name);Write(Path.Combine(folder,(i+1).ToString("D3")+"_record.json"),record);Console.WriteLine("SAVED "+d.Name);
  }
''' +s[b:]
p.write_text(s,encoding='utf-8')
