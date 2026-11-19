// Read-only focused report on DoPresent indirect virtual methods.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
public class TraceDoPresentVirtuals extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs(); File out=new File(args.length>0?args[0]:"reports/do-present-virtuals.txt");
  if(out.getParentFile()!=null) out.getParentFile().mkdirs();
  try(PrintWriter w=new PrintWriter(new FileWriter(out))){
   FunctionManager fm=currentProgram.getFunctionManager();
   Function dp=null;
   FunctionIterator it=fm.getFunctions(true);
   while(it.hasNext()){Function f=it.next(); if(f.getName().contains("DoPresent")){dp=f;break;}}
   w.println("DoPresent focused indirect-virtual call audit, read-only");
   if(dp==null){w.println("DoPresent symbol not found");return;}
   w.println("Function "+dp.getName()+" @ "+dp.getEntryPoint()+" body="+dp.getBody());
   w.println("\nDECOMPILATION:");
   w.println(getDecompiled(dp));
   w.println("\nINSTRUCTIONS:");
   InstructionIterator ins=currentProgram.getListing().getInstructions(dp.getBody(),true);
   while(ins.hasNext()){Instruction x=ins.next();w.println(x.getAddress()+": "+x);}
   w.println("\nREFERENCES TO FUNCTION:");
   ReferenceIterator fr=currentProgram.getReferenceManager().getReferencesTo(dp.getEntryPoint());
   while(fr.hasNext()){Reference r=fr.next();w.println(r.getFromAddress()+" "+r.getReferenceType());}
   w.println("\nGLOBAL DEVICE POINTER SYMBOLS / REFERENCES:");
   SymbolIterator syms=currentProgram.getSymbolTable().getAllSymbols(true);
   while(syms.hasNext()){
    Symbol s=syms.next(); String n=s.getName();
    if(n.toLowerCase().contains("xgsrenderdevice")){
     w.println("SYMBOL "+n+" @ "+s.getAddress());
     ReferenceIterator ri=currentProgram.getReferenceManager().getReferencesTo(s.getAddress());
     while(ri.hasNext()){Reference r=ri.next(); w.println("  XREF "+r.getFromAddress()+" "+r.getReferenceType());}
    }
   }
  }
  println("Wrote DoPresent virtual call audit: "+out);
 }
 private String getDecompiled(Function f){
  try{ DecompInterface d=new DecompInterface(); d.openProgram(currentProgram); DecompileResults r=d.decompileFunction(f,60,monitor); return r.getDecompiledFunction()==null?"decompilation unavailable: "+r.getErrorMessage():r.getDecompiledFunction().getC(); }catch(Exception e){return "ERROR "+e;}
 }
}