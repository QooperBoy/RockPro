using System;
using System.Collections.Generic;
using System.IO;

// Only explicitly owned documents can be registered. A failed recovery save
// leaves that document open; cleanup continues for the other owned documents.
internal sealed class OwnedDocumentScope {
 sealed class Entry {
  internal object Key; internal Func<bool> Modified;
  internal Action<string> SaveCopy; internal Action Close;
 }
 readonly List<Entry> entries=new List<Entry>();
 internal void Add(object key,Func<bool> modified,Action<string> saveCopy,Action close) {
  entries.Add(new Entry {Key=key,Modified=modified,SaveCopy=saveCopy,Close=close});
 }
 internal void Release(object key) { entries.RemoveAll(e=>Object.ReferenceEquals(e.Key,key)); }
 internal string[] Cleanup(string folder) {
  var errors=new List<string>();
  for(int i=entries.Count-1;i>=0;i--) {
   var entry=entries[i];
   try {
    if(entry.Modified()) entry.SaveCopy(Path.Combine(folder,"owned_recovery_"+Guid.NewGuid().ToString("N")+".ics"));
    entry.Close(); entries.RemoveAt(i);
   } catch(Exception ex) { errors.Add(ex.GetType().Name+": "+ex.Message); }
  }
  return errors.ToArray();
 }
}
