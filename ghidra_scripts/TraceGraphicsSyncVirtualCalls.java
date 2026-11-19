// Read-only heuristic scan for indirect calls through the GraphicsSync vtable slot.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;

public class TraceGraphicsSyncVirtualCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args.length > 0 ? args[0] : "graphics-sync-virtual-calls.txt");
        if (out.getParentFile() != null) out.getParentFile().mkdirs();
        int ptr = currentProgram.getDefaultPointerSize();
        int slotOffset = ptr == 8 ? 0x18 : 0x14;
        FunctionManager fm = currentProgram.getFunctionManager();
        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Read-only heuristic scan for GraphicsSync virtual dispatch");
            w.println("Program: " + currentProgram.getName() + " pointerSize=" + ptr +
                " candidateSlotOffset=0x" + Integer.toHexString(slotOffset));
            Function gs = null;
            FunctionIterator fit = fm.getFunctions(true);
            while (fit.hasNext()) {
                Function f = fit.next();
                if (f.getName().equalsIgnoreCase("GraphicsSync")) { gs = f; break; }
            }
            if (gs != null) {
                w.println("GraphicsSync @ " + gs.getEntryPoint());
                ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(gs.getEntryPoint());
                while (refs.hasNext()) {
                    Reference r = refs.next();
                    w.println("  TABLE/DATA REF " + r.getFromAddress() + " type=" + r.getReferenceType());
                }
            } else w.println("GraphicsSync symbol not found");

            int hits = 0;
            fit = fm.getFunctions(true);
            while (fit.hasNext()) {
                Function f = fit.next();
                InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
                while (it.hasNext()) {
                    Instruction call = it.next();
                    String m = call.getMnemonicString().toLowerCase();
                    if (!(m.equals("blr") || m.equals("blx"))) continue;
                    Instruction[] prev = new Instruction[10];
                    Instruction p = call;
                    boolean slotLoad = false;
                    for (int i = 0; i < prev.length; i++) {
                        p = currentProgram.getListing().getInstructionBefore(p.getAddress());
                        if (p == null) break;
                        prev[i] = p;
                        String s = p.toString().toLowerCase();
                        if (s.startsWith("ldr") && s.contains("#0x" + Integer.toHexString(slotOffset)))
                            slotLoad = true;
                    }
                    if (!slotLoad) continue;
                    hits++;
                    w.println("\nCANDIDATE " + hits + " owner=" + f.getName() + "@" + f.getEntryPoint());
                    for (int i = prev.length - 1; i >= 0; i--)
                        if (prev[i] != null) w.println("  " + prev[i].getAddress() + ": " + prev[i]);
                    w.println("  " + call.getAddress() + ": " + call);
                }
            }
            w.println("\nTotal heuristic candidates=" + hits);
            w.println("Candidates require manual confirmation; this scan does not prove the target is GraphicsSync.");
        }
        println("Wrote GraphicsSync virtual-call candidates: " + out.getAbsolutePath());
    }
}
