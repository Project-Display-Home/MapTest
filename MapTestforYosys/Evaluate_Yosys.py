import os
import shutil
import subprocess

def test_file_update():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(current_dir)
    

    source_dir = os.path.join(current_dir, "program_test")
    print(source_dir)
    

    target_dir = os.path.join(current_dir, "action_program_test_yosys")
    print(target_dir)
    

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    

    shutil.copytree(source_dir, target_dir)
    print("copied")

    return 0

import os
import shutil
import subprocess
import time

def diff_check(command_sequence,check_folder,fault_folder,timeout_folder,base_dir,yosys_tb,timeout_sec):
ber: compare.py 判断有差异的样例数量

    cwd = os.getcwd()
    if base_dir is None:
        base_dir = os.path.join(cwd, "action_program_test_yosys")

    fault_number = 0
    timeout_number = 0
    diff_number = 0

    os.makedirs(check_folder, exist_ok=True)
    os.makedirs(fault_folder, exist_ok=True)
    os.makedirs(timeout_folder, exist_ok=True)


    for folder in os.listdir(base_dir):
        case_root = os.path.join(base_dir, folder)
        folder_path = os.path.join(case_root, "equiv_identity_yosys")
        print(f"[CASE] {folder_path}")

        if not (os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, "rtl.v"))):
            print("  - skipped (no rtl.v)")
            continue

        try:
     
            for fn in ["syn_yosys.v", "old_syn_yosys.v", "wave_1", "wave_2",
                       "file1.txt", "file2.txt", "output.txt"]:
                fpath = os.path.join(folder_path, fn)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except IsADirectoryError:
                        shutil.rmtree(fpath, ignore_errors=True)

           
            yosys_cmd_baseline = [
                "yosys", "-p",
                'read_verilog rtl.v; synth; write_verilog syn_yosys.v'
            ]
            print("  - Yosys baseline:", " ".join(yosys_cmd_baseline))
            subprocess.run(
                yosys_cmd_baseline, cwd=folder_path, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec
            )
            syn_v = os.path.join(folder_path, "syn_yosys.v")
            if not os.path.exists(syn_v):
                raise RuntimeError("Baseline syn_yosys.v not generated")

            
            iverilog_baseline = "iverilog -o wave_1 syn_yosys.v {}".format(yosys_tb)
            vvp_baseline = "vvp -n wave_1 -lxt2"
            print("  - iverilog baseline:", iverilog_baseline)
            print("  - vvp baseline:", vvp_baseline)
            subprocess.run(iverilog_baseline, cwd=folder_path, shell=True, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec)
            with open(os.path.join(folder_path, "file1.txt"), "w") as f1:
                r = subprocess.run(vvp_baseline, cwd=folder_path, shell=True, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec)
                f1.write(r.stdout)

            
            f1_path = os.path.join(folder_path, "file1.txt")
            try:
                with open(f1_path, "r") as fr:
                    txt = fr.read()
                txt = txt.replace("wave_1", "wave_2")
                with open(f1_path, "w") as fw:
                    fw.write(txt)
            except Exception:
                pass

        
            old_syn_v = os.path.join(folder_path, "old_syn_yosys.v")
            shutil.move(syn_v, old_syn_v)

            
            yosys_cmd_cand = [
                "yosys", "-p",
                f'read_verilog rtl.v; hierarchy; {command_sequence} write_verilog syn_yosys.v'
            ]
            print("  - Yosys candidate:", " ".join(yosys_cmd_cand))
            subprocess.run(
                yosys_cmd_cand, cwd=folder_path, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec
            )
            if not os.path.exists(os.path.join(folder_path, "syn_yosys.v")):
                raise RuntimeError("Candidate syn_yosys.v not generated")

         
            iverilog_cand = "iverilog -o wave_2 syn_yosys.v {}".format(yosys_tb)
            vvp_cand = "vvp -n wave_2 -lxt2"
            print("  - iverilog cand:", iverilog_cand)
            print("  - vvp cand:", vvp_cand)
            subprocess.run(iverilog_cand, cwd=folder_path, shell=True, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec)
            with open(os.path.join(folder_path, "file2.txt"), "w") as f2:
                r = subprocess.run(vvp_cand, cwd=folder_path, shell=True, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec)
                f2.write(r.stdout)

        
            output_txt = os.path.join(folder_path, "output.txt")
            with open(output_txt, "w") as outfp:
                subprocess.run(["python3", "compare.py"], cwd=folder_path,
                               stdout=outfp, stderr=subprocess.PIPE, text=True, check=False, timeout=timeout_sec)

            with open(output_txt, "r") as of:
                out_str = of.read()
            has_diff = ("error" in out_str.lower()) or ("fail" in out_str.lower()) or ("number different" in out_str.lower())

            if has_diff:
                diff_number += 1
                dst = os.path.join(check_folder, folder)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(case_root, dst)
                print("  - DIFF: outputs mismatch, copied to check_folder.")
            else:
                print("  - PASS: outputs equivalent.")

        except subprocess.TimeoutExpired as te:
            timeout_number += 1
            dst = os.path.join(timeout_folder, folder)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(case_root, dst)
            print(f"  - TIMEOUT: {te}")

        except Exception as e:
            fault_number += 1
            dst = os.path.join(fault_folder, folder)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(case_root, dst)
            print(f"  - FAULT: {e}")

    print(f"[SUMMARY] fault={fault_number}, timeout={timeout_number}, diff={diff_number}")
    return fault_number, timeout_number, diff_number



def Evaluate_main(new_episode,command_sequence):
    test_file_update()
    print(new_episode)
    print(command_sequence)

    os.makedirs("timeout_collection_yosys", exist_ok=True)
    os.makedirs("fault_collection_yosys", exist_ok=True)

    os.makedirs(f"timeout_collection_yosys/{new_episode}", exist_ok=True)
    os.makedirs(f"fault_collection_yosys/{new_episode}", exist_ok=True)

    timeout_folder = f"timeout_collection_yosys/{new_episode}"
    fault_folder = f"fault_collection_yosys/{new_episode}"
    print(timeout_folder)
    print(fault_folder)

    base_dir="/absolute/or/relative/path/to/action_program_test_yosys",
    yosys_tb="yosys_testbench.v",
    timeout_sec=600
    
    faults, timeouts, diffs = diff_check(command_sequence,check_folder,fault_folder,timeout_folder,base_dir,yosys_tb,timeout_sec)
    print(f"Fault number: {fault_number}")
    print(f"Timeout number: {timeout_number}")

    return fault_number, timeout_number

