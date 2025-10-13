# MapTest
## [MapTest: Guided Mapping Parameters Test for Fault Detection in Logic Synthesis Tools]
**The logic synthesis tools we tested include:**
1. **Commercial Logic Synthesis Tool Vivado (latest version 2024,2025)**
2. **Open Source Logic Synthesis Tool Yosys (latest version 0.30 + 48)**
***

**Env dependencies:**
1. **Vivado 2024,Vivado 2025**
2. **Yosys 0.30 + 48**
3. **Icarus Verilog 13.0**
4. **Verismith 1.0.0.2**
5. **python 3.8**
6. **GHC 8.6.5**
7. **Cabal 3.6.0**
8. **Stack 2.9.3**
9. **HLS 2.0.0.1**
***

### Our Works
Logic synthesis tools act as domain-specific compilers that translate hardware description languages (HDLs) into gate-level circuits—crucial for digital design automation. However, the highly parameterized mapping stage, which determines how logic is implemented using device primitives (e.g., lookup tables, flip-flops), remains insufficiently tested. Small configuration changes can introduce latent faults, challenging conventional testing such as random fuzzing due to the combinatorial configuration space and the high cost of functional equivalence checking.
To overcome these issues, we propose MapTest, a guided testing framework for detecting faults in the mapping stage. MapTest combines (1) a Monte Carlo Tree Search (MCTS)-based parameter search to efficiently explore and prioritize fault-prone configurations, and (2) a differential testing approach integrated with selective formal equivalence checking for fault detection and validation. Experiments on commercial and open-source tools (Vivado and Yosys) show that MapTest discovers significantly more distinct faults than existing methods, including 21 previously unknown ones later confirmed by developers. 

***
Main File

Our methodology is located in the project root directory:

1.MapTestforVivado folder:

This folder includes compare.py, MapTest_Vivado_main.py, and valuate_Vivado.py files.
compare.py performs differential testing between synthesis results under different mapping configurations, while valuate_Vivado.py carries out selective formal equivalence checking for validation.
The main function is embedded in MapTest_Vivado_main.py. We can conduct testing on mapping-stage faults in Vivado.

2.MapTestforYosys folder:

This folder contains the implementation of MapTest for Yosys, following the same structure as the Vivado version.
By executing the MapTest_Yosys_main.py file after assigning the test case path to the variable files_path, we can conduct testing on mapping-stage faults in Yosys.
***

bug1：vivado pPesDKAS Crash fault Error in Optimization process preventing netlist generation.

bug2：vivado nSn02KAC Crash fault Crash encountered in HARParse::parseArchitecture() during synthesis.

bug3：vivado nceWcKAI Crash fault Unexpected crash in HARTSWorker::runInternal() halts netlist generation.

bug4：vivado ncqj1KAA Crash fault Crash in Optimization process causing synthesis to fail.

bug5：vivado nd7iBKAQ Crash fault Crash inside HARTNDb::reSynthReInfer(bool) during synthesis.

bug6：vivado ncXqPKAU Crash fault Crash in HARParse::parseArchitecture(bool) causing synthesis to fail.

bug7：vivado ndBk9KAE Crash fault ComMsgMgrImpl::getVerbosity() triggered a fatal crash in synthesis.

bug8：vivado ncoGKKAY Crash fault Fatal crash in HXMSAXParser::Parse() during netlist creation.

bug9：vivado o45MQKAY Crash fault Internal crash in HARTNDb::map() stops synthesis.

bug10：vivado o4QNRKA2 Crash fault Instantiation crash in TclNRRunCallbacks().

bug11：vivado o4SSQKA2 Crash fault Crash in HARTHOptPost::optimize() while generating netlist.

bug12：vivado o42unKAA Crash fault System crash in HDNTLibraryMgr::loadLibrary() triggering synthesis error.

bug13：vivado o4KA0KAM Crash fault Failure during NDes::optimize() phase of synthesis.

bug14：vivado o4TBZKA2 Crash fault Synthesis failed during the optimization stage of the synthesis process.

bug15：vivado 8cH6TMSA0 Performance fault Vivado Synthesis Hang Issue with Specific Design File During Optimization.

bug16：vivado pPiwgKAC Performance fault Netlist output aborted due to HDNTLibraryMgr::getCommonLibrary() failure.

bug17：vivado obTWDKA2 Performance fault Synthesis stopped at TclNRRunCallbacks().

bug18：vivado obbS1KAI Performance fault Failure in Optimization process causes synthesis exit.

bug19：yosys 4480 Performance fault Yosys Optimization Issue: Process Stuck at OPT_CLEAN Pass.

bug20：vivado 7PhRiCSAV Function fault Signal or expression concatenation error during synthesis.

bug21：yosys 5350 Function fault Issue with abc -dress causing incorrect simulation results.***
**We've had so much help from Vivado and Yosys staff in finding and confirming bugs. I would like to express my gratitude here.**


