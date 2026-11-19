// Read-only dump of data slots and pointer targets referenced by PresentScene.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.io.*;

public class TracePresentSceneTables extends GhidraScript {
    private void dumpBytes(PrintWriter w, Address at, int before, int after) throws Exception {
        Memory mem = currentProgram.getMemory();
        Address start = at.subtract(before);
        byte[] b = new byte[before + after];
        int n = mem.getBytes(start, b);
        w.print("    BYTES " + start + " (" + n + "): ");
        for (int i = 0; i < n; i++) w.printf("%02x ", b[i] & 0xff);
        w.println();
    }

    private void dumpRefs(PrintWriter w, Address at) {
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(at);
        int count = 0;
        while (refs.hasNext() && count++ < 40) {
            Reference r = refs.next();
            Function owner = currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            w.println("      XREF from " + r.getFromAddress() + " type=" + r.getReferenceType() +
                " owner=" + (owner == null ? "<none>" : owner.getName() + "@" + owner.getEntryPoint()));
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args.length > 0 ? args[0] : "present-scene-tables.txt");
        if (out.getParentFile() != null) out.getParentFile().mkdirs();
        int ptrSize = currentProgram.getDefaultPointerSize();
        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("Read-only PresentScene data-slot / pointer-target trace");
            w.println("Program: " + currentProgram.getName() + " pointerSize=" + ptrSize);
            FunctionManager fm = currentProgram.getFunctionManager();
            FunctionIterator it = fm.getFunctions(true);
            while (it.hasNext()) {
                Function fn = it.next();
                if (!fn.getName().toLowerCase().contains("presentscene")) continue;
                w.println("\nFUNCTION " + fn.getName() + " @ " + fn.getEntryPoint());
                ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(fn.getEntryPoint());
                while (refs.hasNext()) {
                    Reference r = refs.next();
                    Address from = r.getFromAddress();
                    w.println("  ENTRY REF from=" + from + " type=" + r.getReferenceType());
                    dumpBytes(w, from, 16, 32);
                    Data d = currentProgram.getListing().getDataAt(from);
                    if (d != null) w.println("    DATA " + d);
                    try {
                        Address target = null;
                        if (ptrSize == 8) {
                            long value = currentProgram.getMemory().getLong(from);
                            target = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
                            w.println("    PTR64 value=0x" + Long.toHexString(value) + " target=" + target);
                        } else {
                            long value = Integer.toUnsignedLong(currentProgram.getMemory().getInt(from));
                            target = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
                            w.println("    PTR32 value=0x" + Long.toHexString(value) + " target=" + target);
                        }
                        if (target != null) {
                            Function tf = fm.getFunctionAt(target);
                            w.println("    TARGET FUNCTION=" + (tf == null ? "<none>" : tf.getName() + "@" + tf.getEntryPoint()));
                            dumpRefs(w, target);
                            dumpBytes(w, target, 8, 24);
                        }
                    } catch (Exception ex) {
                        w.println("    POINTER READ ERROR: " + ex.getMessage());
                    }
                }
            }
        }
        println("Wrote PresentScene table trace: " + out.getAbsolutePath());
    }
}
