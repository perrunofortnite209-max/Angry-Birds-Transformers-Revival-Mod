// Read-only export of exact Ghidra instruction bytes for FPS functions.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.io.*;

public class DumpFunctionBytes extends GhidraScript {
    private boolean relevant(String n) {
        String s=n.toLowerCase();
        return s.contains("getdesiredframerate") || s.contains("limitfpswithsleep")
            || s.contains("dopresent") || s.contains("setframeratelimiter")
            || s.contains("getframeratelimiter") || s.contains("addfpssample")
            || s.contains("xgsclamptotargetfps");
    }
    private String hex(byte[] b) {
        StringBuilder s=new StringBuilder();
        for(byte v:b) s.append(String.format("%02x",v & 0xff));
        return s.toString();
    }
    @Override public void run() throws Exception {
        String[] args=getScriptArgs();
        String outPath=args.length>0?args[0]:"fps-function-bytes.txt";
        File out=new File(outPath);
        if(out.getParentFile()!=null) out.getParentFile().mkdirs();
        try(PrintWriter w=new PrintWriter(new FileWriter(out))) {
            w.println("Program: "+currentProgram.getName());
            w.println("Language: "+currentProgram.getLanguageID());
            w.println("Image base: "+currentProgram.getImageBase());
            w.println("Executable format: "+currentProgram.getExecutableFormat());
            Memory mem=currentProgram.getMemory();
            for(MemoryBlock b:mem.getBlocks()) {
                w.println("BLOCK "+b.getName()+" start="+b.getStart()+" end="+b.getEnd()
                    +" initialized="+b.isInitialized()+" size="+b.getSize());
            }
            FunctionIterator it=currentProgram.getFunctionManager().getFunctions(true);
            while(it.hasNext()) {
                Function fn=it.next();
                if(!relevant(fn.getName())) continue;
                w.println("\n===== FUNCTION "+fn.getName()+" @ "+fn.getEntryPoint()
                    +" size="+fn.getBody().getNumAddresses()+" =====");
                InstructionIterator ii=currentProgram.getListing().getInstructions(fn.getBody(),true);
                while(ii.hasNext()) {
                    Instruction ins=ii.next();
                    byte[] bytes=new byte[ins.getLength()];
                    mem.getBytes(ins.getAddress(),bytes);
                    w.println(ins.getAddress()+" | "+hex(bytes)+" | "+ins.toString());
                }
            }
        }
        println("Wrote exact FPS function bytes: "+out.getAbsolutePath());
    }
}
