// Ghidra headless script: report references to FPS-related strings and nearby code.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.lang.*;
import java.io.*;

public class FindFpsStringXrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "fps-xrefs.txt";
        File out = new File(outPath);
        out.getParentFile().mkdirs();
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
                boolean found = false;
                while (it.hasNext()) {
                    Reference ref = it.next();
                    found = true;
                    hits++;
                    Address from = ref.getFromAddress();
                    w.println("STRING @ " + target + " [" + data.getDataType() + "]: " + s);
                    w.println("  XREF " + from + " type=" + ref.getReferenceType());
                    Instruction ins = listing.getInstructionAt(from);
                    if (ins == null) ins = listing.getInstructionContaining(from);
                    if (ins != null) {
                        Instruction cur = ins;
                        for (int i = 0; i < 12 && cur != null; i++) cur = cur.getPrevious();
                        int count = 0;
                        while (cur != null && count < 32) {
                            w.println("    " + cur.getAddress() + ": " + cur);
                            if (cur.getAddress().compareTo(ins.getAddress()) > 0x100) break;
                            cur = cur.getNext();
                            count++;
                        }
                    }
                    w.println();
                }
                if (!found && s.matches("(?is).*(fps|framerate|frame.?rate|lowbattery|target.?30|target.?60).*")) {
                    w.println("STRING NO XREF @ " + target + ": " + s);
                }
            }
            w.println("Total xrefs: " + hits);
        }
        println("Wrote FPS string cross-reference report: " + out.getAbsolutePath());
    }
}
