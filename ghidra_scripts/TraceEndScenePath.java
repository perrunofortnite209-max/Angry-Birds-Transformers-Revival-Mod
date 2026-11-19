// Read-only disassembly and call-reference audit for the frame presentation path.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;
public class TraceEndScenePath extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs(); File out=new File(args.length>0?args[0]:"reports/end-scene-path.txt");
  if(out.getParentFile()!=null) out.getParentFile().mkdirs();
  List<Function> targets=new ArrayList<>();
  FunctionIterator it=currentProgram.getFunctionManager().getFunctions(true);
  while(it.hasNext()){
   Function f=it.next(); String n=f.getName().toLowerCase();
   if(n.contains("endscene")||n.contains("presentscene")||n.contains("graphicssync")) targets.add(f);
  }
  try(PrintWriter w=new PrintWriter(new FileWriter(out))){
   w.println("READ-ONLY END/PRESENT/SYNC CALL-PATH AUDIT");
   for(Function f:targets){
    w.println("\n===== "+f.getName()+" @ "+f.getEntryPoint()+" body="+f.getBody()+" =====");
    InstructionIterator ii=currentProgram.getListing().getInstructions(f.getBody(),true);
    while(ii.hasNext()){
     Instruction ins=ii.next(); w.println(ins.getAddress()+": "+ins);
     Reference[] rs=currentProgram.getReferenceManager().getReferencesFrom(ins.getAddress());
     for(Reference r:rs) w.println("  REF -> "+r.getToAddress()+" type="+r.getReferenceType());
    }
    w.println("-- references TO function --");
    ReferenceIterator ri=currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
    while(ri.hasNext()){Reference r=ri.next();w.println(r.getFromAddress()+" type="+r.getReferenceType());}
   }
   w.println("\n===== ALL CALL REFERENCES TO TARGET FUNCTIONS =====");
   Set<Address> entries=new HashSet<>(); for(Function f:targets) entries.add(f.getEntryPoint());
   InstructionIterator all=currentProgram.getListing().getInstructions(true);
   while(all.hasNext()){
    Instruction ins=all.next();
    for(Reference r:currentProgram.getReferenceManager().getReferencesFrom(ins.getAddress())){
     if(entries.contains(r.getToAddress())) w.println(ins.getAddress()+": "+ins+" -> "+r.getToAddress()+" ("+r.getReferenceType()+")");
    }
   }
  }
  println("Wrote read-only EndScene path report: "+out);
 }
}
