// Fast, read-only DoPresent virtual dispatch audit; intentionally avoids decompilation.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.io.*;
public class TraceDoPresentVirtuals extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs(); File out=new File(args.length>0?args[0]:"reports/do-present-virtuals.txt");
  if(out.getParentFile()!=null) out.getParentFile().mkdirs();
  try(PrintWriter w=new PrintWriter(new FileWriter(out))){
   w.println("Focused DoPresent virtual dispatch audit (read-only; no decompilation)");
   Function dp=null; FunctionIterator fi=currentProgram.getFunctionManager().getFunctions(true);
   while(fi.hasNext()){Function f=fi.next(); if(f.getName().contains("DoPresent")){dp=f;break;}}
   if(dp==null){w.println("DoPresent function not found");return;}
   w.println("Function "+dp.getName()+" @ "+dp.getEntryPoint()+" body="+dp.getBody());
   w.println("\nINSTRUCTIONS:");
   InstructionIterator ii=currentProgram.getListing().getInstructions(dp.getBody(),true);
   while(ii.hasNext()){Instruction ins=ii.next();w.println(ins.getAddress()+": "+ins);}
   w.println("\nFUNCTION XREFS:");
   ReferenceIterator refs=currentProgram.getReferenceManager().getReferencesTo(dp.getEntryPoint());
   while(refs.hasNext()){Reference r=refs.next();w.println(r.getFromAddress()+" "+r.getReferenceType());}
   w.println("\nDEVICE SYMBOLS / XREFS / MEMORY:");
   SymbolIterator si=currentProgram.getSymbolTable().getAllSymbols(true);
   while(si.hasNext()){
    Symbol s=si.next();String n=s.getName();
    if(n.toLowerCase().contains("xgsrenderdevice")){
     w.println("SYMBOL "+n+" @ "+s.getAddress());
     ReferenceIterator xr=currentProgram.getReferenceManager().getReferencesTo(s.getAddress());
     while(xr.hasNext()){Reference r=xr.next();w.println(" XREF "+r.getFromAddress()+" "+r.getReferenceType());}
     dumpMemory(w,s.getAddress(),32);
    }
   }
   w.println("\nADDRESS CHECKS (ARM64 known globals):");
   dumpMemory(w,toAddr(0x00dee680L),64); dumpMemory(w,toAddr(0x0115a7f0L),64);
   w.println("\nCALL-SLOT REFERENCES TO 0x60 / 0x68 (potential virtual calls):");
   Listing listing=currentProgram.getListing(); InstructionIterator all=listing.getInstructions(true);
   while(all.hasNext()){Instruction ins=all.next();String text=ins.toString().toLowerCase();
    if((text.contains("[") && (text.contains("#0x60")||text.contains("#0x68"))) || text.contains("0x60]") || text.contains("0x68]")){
     w.println(ins.getAddress()+": "+ins);
    }
   }
  }
  println("Wrote focused DoPresent report: "+out);
 }
 private void dumpMemory(PrintWriter w,Address a,int count){
  w.println("MEMORY "+a+" length="+count);
  try{for(int i=0;i<count;i+=16){w.print(a.add(i)+": ");for(int j=0;j<16&&i+j<count;j++)w.printf("%02x ",currentProgram.getMemory().getByte(a.add(i+j)));w.println();}}
  catch(Exception e){w.println(" memory unavailable: "+e);}
 }
}