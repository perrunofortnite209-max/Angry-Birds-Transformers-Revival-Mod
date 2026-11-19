// Read-only follow-up: resolve GraphicsSync callers and indirect renderer calls.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class TraceGraphicsSyncAndPresent extends GhidraScript {
    private void dumpBody(PrintWriter w, Function fn, int limit) {
        w.println("\nFUNCTION " + fn.getName() + " @ " + fn.getEntryPoint() +
            " size=" + fn.getBody().getNumAddresses());
        w.println("DIRECT CALLERS:");
        for (Function f : fn.getCallingFunctions(monitor))
            w.println("  " + f.getName() + " @ " + f.getEntryPoint());
        w.println("INSTRUCTIONS:");
        InstructionIterator it = currentProgram.getListing().getInstructions(fn.getBody(), true);
        int n = 0;
        while (it.hasNext() && n++ < limit) {
            Instruction ins = it.next();
            w.println("  " + ins.getAddress() + ": " + ins);
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String path = args.length > 0 ? args[0] : "graphics-sync-callers.txt";
        File out = new File(path);
        if (out.getParentFile() != null) out.getParentFile().mkdirs();

        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Read-only GraphicsSync caller and DoPresent indirect-call trace");
            w.println("Program: " + currentProgram.getName());
            FunctionManager fm = currentProgram.getFunctionManager();
            Function graphicsSync = null;
            Function doPresent = null;
            FunctionIterator fit = fm.getFunctions(true);
            while (fit.hasNext()) {
                Function f = fit.next();
                String name = f.getName().toLowerCase();
                if (name.equals("graphicssync")) graphicsSync = f;
                if (name.equals("dopresent")) doPresent = f;
            }

            if (graphicsSync == null) {
                w.println("\nGraphicsSync function symbol not resolved.");
                SymbolIterator sit = currentProgram.getSymbolTable().getAllSymbols(true);
                while (sit.hasNext()) {
                    Symbol s = sit.next();
                    if (s.getName().toLowerCase().contains("graphicssync"))
                        w.println("SYMBOL " + s.getName() + " @ " + s.getAddress());
                }
            } else {
                dumpBody(w, graphicsSync, 300);
                w.println("\nALL REFERENCES TO GraphicsSync ENTRY:");
                ReferenceIterator rit = currentProgram.getReferenceManager()
                    .getReferencesTo(graphicsSync.getEntryPoint());
                while (rit.hasNext()) {
                    Reference r = rit.next();
                    Function owner = fm.getFunctionContaining(r.getFromAddress());
                    w.println("  from " + r.getFromAddress() + " type=" + r.getReferenceType() +
                        " owner=" + (owner == null ? "<none>" : owner.getName() + " @ " + owner.getEntryPoint()));
                    Instruction ins = currentProgram.getListing().getInstructionAt(r.getFromAddress());
                    if (ins != null) w.println("    " + ins);
                }
            }

            if (doPresent == null) {
                w.println("\nDoPresent function symbol not resolved.");
            } else {
                dumpBody(w, doPresent, 500);
                w.println("\nREFERENCES TO g_ptXGSRenderDevice SYMBOLS:");
                SymbolIterator sit = currentProgram.getSymbolTable().getAllSymbols(true);
                while (sit.hasNext()) {
                    Symbol s = sit.next();
                    if (s.getName().toLowerCase().contains("g_ptxgsrenderdevice")) {
                        w.println("  " + s.getName() + " @ " + s.getAddress());
                        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(s.getAddress());
                        while (refs.hasNext()) {
                            Reference r = refs.next();
                            Function owner = fm.getFunctionContaining(r.getFromAddress());
                            w.println("    ref from " + r.getFromAddress() + " owner=" +
                                (owner == null ? "<none>" : owner.getName() + " @ " + owner.getEntryPoint()));
                        }
                    }
                }
            }
            w.println("\nNo APK or PAK bytes were modified.");
        }
        println("Wrote GraphicsSync / DoPresent trace: " + out.getAbsolutePath());
    }
}
