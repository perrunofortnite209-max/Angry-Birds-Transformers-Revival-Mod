// Ghidra headless script: trace FPS-related string references into containing functions,
// locate FPS-named functions, and decompile the most relevant code paths.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class FindFpsStringXrefs extends GhidraScript {
    private final Set<Function> candidates = new LinkedHashSet<>();

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "fps-xrefs.txt";
        File out = new File(outPath);
        if (out.getParentFile() != null) out.getParentFile().mkdirs();

        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Program: " + currentProgram.getName());
            w.println("Language: " + currentProgram.getLanguageID());
            w.println("Image base: " + currentProgram.getImageBase());
            w.println();

            Listing listing = currentProgram.getListing();
            ReferenceManager refs = currentProgram.getReferenceManager();
            int hits = 0;
            for (Data data : listing.getDefinedData(true)) {
                Object value = data.getValue();
                if (value == null) continue;
                String s = value.toString();
                if (!s.matches("(?is).*(fps|framerate|frame.?rate|lowbattery|target.?30|target.?60|144.?hz|vsync).*")) continue;
                Address target = data.getAddress();
                ReferenceIterator it = refs.getReferencesTo(target);
                while (it.hasNext()) {
                    Reference ref = it.next();
                    hits++;
                    Address from = ref.getFromAddress();
                    Function fn = currentProgram.getFunctionManager().getFunctionContaining(from);
                    if (fn != null) candidates.add(fn);
                    w.println("STRING @ " + target + " [" + data.getDataType() + "]: " + s);
                    w.println("  XREF " + from + " type=" + ref.getReferenceType()
                        + (fn == null ? "" : " function=" + fn.getName() + " entry=" + fn.getEntryPoint()));
                    Instruction ins = listing.getInstructionAt(from);
                    if (ins == null) ins = listing.getInstructionContaining(from);
                    if (ins != null) {
                        Instruction cur = ins;
                        for (int i = 0; i < 5 && cur != null; i++) cur = cur.getPrevious();
                        int count = 0;
                        while (cur != null && count < 18) {
                            w.println("    " + cur.getAddress() + ": " + cur);
                            if (cur.getAddress().compareTo(ins.getAddress()) > 0) {
                                // continue through a small window after the reference
                            }
                            cur = cur.getNext();
                            count++;
                        }
                    }
                    w.println();
                }
            }
            w.println("Total string xrefs: " + hits);
            w.println();

            // Ghidra may recover local/static ELF symbols even when llvm-nm -D cannot see them.
            FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(true);
            while (fit.hasNext()) {
                Function fn = fit.next();
                String n = fn.getName();
                if (n.matches("(?i).*(fps|framerate|frame.?rate|clamp.*target|target.*fps|desiredframerate|dopresent|updaterecommendedperformance|processframe|loadmiscxml).*")) {
                    candidates.add(fn);
                }
            }

            w.println("===== CANDIDATE FUNCTIONS (" + candidates.size() + ") =====");
            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            int emitted = 0;
            for (Function fn : candidates) {
                if (monitor.isCancelled() || emitted >= 100) break;
                w.println();
                w.println("===== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint()
                    + " size=" + fn.getBody().getNumAddresses() + " =====");
                w.println("Signature: " + fn.getSignature());
                Set<Function> callers = fn.getCallingFunctions(monitor);
                w.println("Callers (" + callers.size() + "):");
                int callerCount = 0;
                for (Function caller : callers) {
                    if (callerCount++ >= 30) { w.println("  ..."); break; }
                    w.println("  " + caller.getName() + " @ " + caller.getEntryPoint());
                }
                DecompileResults result = decomp.decompileFunction(fn, 45, monitor);
                if (result != null && result.decompileCompleted()
                        && result.getDecompiledFunction() != null) {
                    w.println("--- DECOMPILED ---");
                    String code = result.getDecompiledFunction().getC();
                    String[] lines = code.split("\\R");
                    for (int i = 0; i < lines.length && i < 180; i++) w.println(lines[i]);
                    if (lines.length > 180) w.println("... [truncated]");
                } else {
                    w.println("Decompile unavailable: " +
                        (result == null ? "no result" : result.getErrorMessage()));
                }
                emitted++;
            }
            decomp.dispose();
            w.println();
            w.println("Functions emitted: " + emitted);
        }
        println("Wrote FPS xref and function decompilation report: " + out.getAbsolutePath());
    }
}
