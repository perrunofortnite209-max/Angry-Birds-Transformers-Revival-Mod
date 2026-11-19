// Read-only trace of PresentScene callers and indirect dispatch around GraphicsSync.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;

public class TracePresentSceneCallers extends GhidraScript {
    private void dumpNearby(PrintWriter w, Address at) {
        Listing listing = currentProgram.getListing();
        Instruction ins = listing.getInstructionAt(at);
        if (ins == null) {
            w.println("    no instruction at " + at);
            return;
        }
        Instruction prev = listing.getInstructionBefore(at);
        if (prev != null) w.println("    PREV " + prev.getAddress() + ": " + prev);
        w.println("    HERE " + ins.getAddress() + ": " + ins);
        Instruction next = listing.getInstructionAfter(at);
        if (next != null) w.println("    NEXT " + next.getAddress() + ": " + next);
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String path = args.length > 0 ? args[0] : "present-scene-callers.txt";
        File out = new File(path);
        if (out.getParentFile() != null) out.getParentFile().mkdirs();
        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Read-only PresentScene call/reference trace");
            w.println("Program: " + currentProgram.getName());
            FunctionManager fm = currentProgram.getFunctionManager();
            FunctionIterator it = fm.getFunctions(true);
            while (it.hasNext()) {
                Function fn = it.next();
                if (!fn.getName().toLowerCase().contains("presentscene")) continue;
                w.println("\nFUNCTION " + fn.getName() + " @ " + fn.getEntryPoint() +
                    " bodySize=" + fn.getBody().getNumAddresses());
                w.println("DIRECT CALLERS:");
                for (Function caller : fn.getCallingFunctions(monitor))
                    w.println("  " + caller.getName() + " @ " + caller.getEntryPoint());
                w.println("ALL REFERENCES TO ENTRY:");
                ReferenceIterator refs = currentProgram.getReferenceManager()
                    .getReferencesTo(fn.getEntryPoint());
                while (refs.hasNext()) {
                    Reference r = refs.next();
                    Function owner = fm.getFunctionContaining(r.getFromAddress());
                    w.println("  from " + r.getFromAddress() + " type=" + r.getReferenceType() +
                        " owner=" + (owner == null ? "<none>" : owner.getName() + " @ " + owner.getEntryPoint()));
                    dumpNearby(w, r.getFromAddress());
                }
                w.println("BODY (first 120 instructions):");
                InstructionIterator body = currentProgram.getListing().getInstructions(fn.getBody(), true);
                int count = 0;
                while (body.hasNext() && count++ < 120) {
                    Instruction ins = body.next();
                    w.println("  " + ins.getAddress() + ": " + ins);
                }
            }
        }
        println("Wrote PresentScene trace: " + out.getAbsolutePath());
    }
}
