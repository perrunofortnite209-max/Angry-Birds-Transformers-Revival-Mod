// Read-only graphics synchronization and render-call audit for libABBS.so.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class FindGraphicsSyncCalls extends GhidraScript {
    private boolean syncName(String n) {
        String s=n.toLowerCase();
        return s.matches(".*(glfinish|glflush|glclientwaitsync|glwaitsync|eglwaitsync|eglclientwaitsync|waitforfences|waitforsync|fence|pthread_mutex_lock|sem_wait|futex|nanosleep|usleep|sleepthread).*");
    }
    private boolean renderName(String n) {
        String s=n.toLowerCase();
        return s.contains("dopresent") || s.contains("dorender") ||
            s.contains("renderalleffects") || s.contains("cexplosionmanager") ||
            s.contains("cparticleeffectmanager") || s.contains("prepareframe") ||
            s.contains("renderall") || s.contains("drawframe") ||
            s.contains("graphicssync") || s.contains("presentscene") ||
            s.contains("insertgpufence") || s.contains("blockoncpu") ||
            s.contains("iscpufence");
    }
    private void dumpFunction(PrintWriter w, Function fn) throws Exception {
        w.println("\\nFUNCTION "+fn.getName()+" @ "+fn.getEntryPoint()+
            " size="+fn.getBody().getNumAddresses());
        w.println("CALLERS:");
        for(Function f:fn.getCallingFunctions(monitor)) w.println("  "+f.getName()+" @ "+f.getEntryPoint());
        w.println("CALLEES:");
        for(Function f:fn.getCalledFunctions(monitor)) w.println("  "+f.getName()+" @ "+f.getEntryPoint());
        InstructionIterator it=currentProgram.getListing().getInstructions(fn.getBody(),true);
        int count=0;
        while(it.hasNext() && count++<220) {
            Instruction ins=it.next();
            Reference[] refs=currentProgram.getReferenceManager().getReferencesFrom(ins.getAddress());
            if(refs.length==0) continue;
            w.print("  "+ins.getAddress()+": "+ins);
            for(Reference r:refs) {
                Symbol sym=currentProgram.getSymbolTable().getPrimarySymbol(r.getToAddress());
                w.print(" -> "+r.getToAddress()+" ["+r.getReferenceType()+"]");
                if(sym!=null) w.print(" {"+sym.getName()+"}");
            }
            w.println();
        }
    }
    @Override public void run() throws Exception {
        String[] args=getScriptArgs();
        String path=args.length>0?args[0]:"graphics-sync-audit.txt";
        File out=new File(path);
        if(out.getParentFile()!=null) out.getParentFile().mkdirs();
        FunctionManager fm=currentProgram.getFunctionManager();
        List<Function> sync=new ArrayList<>(), render=new ArrayList<>(), callers=new ArrayList<>();
        FunctionIterator it=fm.getFunctions(true);
        while(it.hasNext()) {
            Function fn=it.next();
            if(syncName(fn.getName())) sync.add(fn);
            if(renderName(fn.getName())) render.add(fn);
        }
        try(PrintWriter w=new PrintWriter(new FileWriter(out))) {
            w.println("Read-only graphics synchronization audit");
            w.println("Program: "+currentProgram.getName());
            w.println("Image base: "+currentProgram.getImageBase());
            w.println("\\n===== SYNC / WAIT IMPORTS AND FUNCTIONS ("+sync.size()+") =====");
            for(Function fn:sync) dumpFunction(w,fn);
            w.println("\\n===== RENDER / EFFECT / SYNC WRAPPERS ("+render.size()+") =====");
            for(Function fn:render) dumpFunction(w,fn);
            w.println("\\n===== FUNCTIONS THAT CALL SYNC / WAIT PRIMITIVES OR GRAPHICSSYNC =====");
            it=fm.getFunctions(true);
            while(it.hasNext()) {
                Function fn=it.next();
                for(Function callee:fn.getCalledFunctions(monitor)) {
                    String cn=callee.getName().toLowerCase();
                    if(syncName(callee.getName()) || cn.contains("graphicssync") || cn.contains("presentscene")) {
                        callers.add(fn);
                        w.println("\\nCALLER "+fn.getName()+" @ "+fn.getEntryPoint()+
                            " -> "+callee.getName()+" @ "+callee.getEntryPoint());
                        InstructionIterator ii=currentProgram.getListing().getInstructions(fn.getBody(),true);
                        int c=0;
                        while(ii.hasNext() && c++<300) {
                            Instruction ins=ii.next();
                            for(Reference ref:currentProgram.getReferenceManager().getReferencesFrom(ins.getAddress()))
                                if(ref.getToAddress().equals(callee.getEntryPoint())) w.println("  "+ins.getAddress()+": "+ins);
                        }
                    }
                }
            }
            w.println("\\nSummary: sync functions="+sync.size()+", render/effect/sync functions="+render.size()+
                ", functions calling sync primitives/wrappers="+callers.size());
            w.println("No binary modifications were made.");
        }
        println("Wrote graphics sync audit: "+out.getAbsolutePath());
    }
}
