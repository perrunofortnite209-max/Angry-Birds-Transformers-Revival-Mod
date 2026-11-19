// Read-only focused decompilation of frame-boundary methods. No APK/PAK writes.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
public class TraceFrameBoundary extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs(); File out=new File(args.length>0?args[0]:"reports/frame-boundary.txt");
  if(out.getParentFile()!=null) out.getParentFile().mkdirs();
  DecompInterface d=new DecompInterface(); d.openProgram(currentProgram);
  try(PrintWriter w=new PrintWriter(new FileWriter(out))){
   w.println("Read-only frame-boundary audit: EndScene / PresentScene / GraphicsSync");
   FunctionIterator it=currentProgram.getFunctionManager().getFunctions(true);
   while(it.hasNext()){
    Function f=it.next(); String n=f.getName();
    if(!(n.contains("EndScene")||n.contains("PresentScene")||n.contains("GraphicsSync"))) continue;
    w.println("\n===== "+n+" @ "+f.getEntryPoint()+" size="+f.getBody().getNumAddresses()+" =====");
    w.println("CALLERS:");
    ReferenceIterator ri=currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
    while(ri.hasNext()){Reference r=ri.next(); Function caller=currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress()); w.println("  "+r.getFromAddress()+" "+r.getReferenceType()+" caller="+(caller==null?"<none>":caller.getName()+"@"+caller.getEntryPoint()));}
    w.println("INSTRUCTIONS:");
    InstructionIterator ii=currentProgram.getListing().getInstructions(f.getBody(),true);
    while(ii.hasNext()) w.println("  "+ii.next());
    DecompileResults res=d.decompileFunction(f,45,monitor);
    if(res!=null && res.decompileCompleted() && res.getDecompiledFunction()!=null){
     w.println("DECOMPILED C:");
     w.println(res.getDecompiledFunction().getC());
    } else w.println("DECOMPILER: "+(res==null?"no result":res.getErrorMessage()));
   }
  } finally { d.dispose(); }
  println("Wrote frame-boundary audit: "+out);
 }
}