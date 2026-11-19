// Read-only follow-up: trace calls and data references in the FPS control path.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class TraceFpsControlData extends GhidraScript {
    private boolean relevant(String n) {
        String s = n.toLowerCase();
        return s.contains("getdesiredframerate") || s.contains("limitfpswithsleep")
            || s.contains("dopresent") || s.contains("setframeratelimiter")
            || s.contains("getframeratelimiter") || s.contains("xgsclamptotargetfps")
            || s.contains("updaterecommendedperformance") || s.contains("addfpssample");
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "fps-control-trace.txt";
        File out = new File(outPath);
        if (out.getParentFile() != null) out.getParentFile().mkdirs();
        Listing listing = currentProgram.getListing();
        ReferenceManager refs = currentProgram.getReferenceManager();
        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Read-only FPS control trace");
            w.println("Program: " + currentProgram.getName());
            w.println("Image base: " + currentProgram.getImageBase());
            w.println();

            FunctionIterator it = fm.getFunctions(true);
            Set<Address> dataTargets = new TreeSet<>();
            List<Function> selected = new ArrayList<>();
            while (it.hasNext()) {
                Function fn = it.next();
                if (relevant(fn.getName())) selected.add(fn);
            }

            for (Function fn : selected) {
                w.println("===== " + fn.getName() + " @ " + fn.getEntryPoint()
                    + " size=" + fn.getBody().getNumAddresses() + " =====");
                Set<Function> callers = fn.getCallingFunctions(monitor);
                w.println("CALLERS:");
                for (Function caller : callers) w.println("  " + caller.getName() + " @ " + caller.getEntryPoint());

                Set<Function> callees = fn.getCalledFunctions(monitor);
                w.println("CALLEES:");
                for (Function callee : callees) w.println("  " + callee.getName() + " @ " + callee.getEntryPoint());

                w.println("INSTRUCTIONS AND REFERENCES:");
                InstructionIterator ii = listing.getInstructions(fn.getBody(), true);
                int count = 0;
                while (ii.hasNext() && count++ < 260) {
                    Instruction ins = ii.next();
                    w.print("  " + ins.getAddress() + ": " + ins);
                    Reference[] from = refs.getReferencesFrom(ins.getAddress());
                    for (Reference ref : from) {
                        Address to = ref.getToAddress();
                        w.print(" -> " + to + " [" + ref.getReferenceType() + "]");
                        if (ref.getReferenceType().isData()) dataTargets.add(to);
                        Symbol sym = currentProgram.getSymbolTable().getPrimarySymbol(to);
                        if (sym != null) w.print(" {" + sym.getName() + "}");
                    }
                    w.println();
                }

                DecompileResults result = decomp.decompileFunction(fn, 45, monitor);
                if (result != null && result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    w.println("DECOMPILED:");
                    String[] lines = result.getDecompiledFunction().getC().split("\\R");
                    for (int i = 0; i < lines.length && i < 220; i++) w.println(lines[i]);
                    if (lines.length > 220) w.println("... [truncated]");
                } else {
                    w.println("Decompile unavailable: " + (result == null ? "no result" : result.getErrorMessage()));
                }
                w.println();
            }

            w.println("===== REFERENCES TO DATA TARGETS USED BY CONTROL FUNCTIONS =====");
            for (Address target : dataTargets) {
                w.println("DATA TARGET " + target);
                Symbol sym = currentProgram.getSymbolTable().getPrimarySymbol(target);
                if (sym != null) w.println("  SYMBOL " + sym.getName());
                if (!target.isMemoryAddress()) { w.println("  [skip non-memory target]"); continue; }
                ReferenceIterator ri = refs.getReferencesTo(target);
                int n = 0;
                while (ri.hasNext() && n++ < 100) {
                    Reference ref = ri.next();
                    Function owner = fm.getFunctionContaining(ref.getFromAddress());
                    w.println("  FROM " + ref.getFromAddress() + " "
                        + (owner == null ? "<no function>" : owner.getName() + " @ " + owner.getEntryPoint())
                        + " [" + ref.getReferenceType() + "]");
                }
            }
        } finally {
            decomp.dispose();
        }
        println("Wrote FPS control data trace: " + out.getAbsolutePath());
    }
}
