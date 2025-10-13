
import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_TOP = "top"                 
DEFAULT_TB  = "vivado_testbench.v" 
DEFAULT_TIMEOUT_SEC = 900

def test_file_update():
    """
    将 ./program_test 拷贝为 ./action_program_test_vivado
    （与原逻辑一致；如已有则覆盖）
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir  = os.path.join(current_dir, "program_test")
    target_dir  = os.path.join(current_dir, "action_program_test_vivado")

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    print("[Vivado] copied test set ->", target_dir)
    return 0


def diff_check_vivado(
    vivado_command: str,
    check_folder: str,
    fault_folder: str,
    timeout_folder: str,
    base_dir: str | None = None,
    top_module: str = DEFAULT_TOP,
    testbench: str = DEFAULT_TB,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC
):

    cwd = os.getcwd()
    if base_dir is None:
        base_dir = os.path.join(cwd, "action_program_test_vivado")

    fault_number = 0
    timeout_number = 0
    diff_number = 0

    os.makedirs(check_folder, exist_ok=True)
    os.makedirs(fault_folder, exist_ok=True)
    os.makedirs(timeout_folder, exist_ok=True)

    for folder in os.listdir(base_dir):
        case_root   = os.path.join(base_dir, folder)
        folder_path = os.path.join(case_root, "equiv_identity_vivado")
        print(f"[CASE] {folder_path}")

        if not (os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, "rtl.v"))):
            print("  - skipped (no rtl.v)")
            continue

        try:

            for fn in ["syn_vivado.v", "old_syn_vivado.v", "wave_1", "wave_2",
                       "file1.txt", "file2.txt", "output.txt", "synth_base.tcl", "synth_cand.tcl"]:
                fp = os.path.join(folder_path, fn)
                if os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except IsADirectoryError:
                        shutil.rmtree(fp, ignore_errors=True)


            tcl_base = f"""\
read_verilog rtl.v
synth_design -top {top_module}
write_verilog -force syn_vivado.v
"""
            tcl_base_path = os.path.join(folder_path, "synth_base.tcl")
            with open(tcl_base_path, "w") as f:
                f.write(tcl_base)

            vivado_base_cmd = "vivado -mode batch -source synth_base.tcl"
            print("  - Vivado baseline:", vivado_base_cmd)
            subprocess.run(
                vivado_base_cmd, shell=True, cwd=folder_path,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=timeout_sec, check=True
            )
            syn_v = os.path.join(folder_path, "syn_vivado.v")
            if not os.path.exists(syn_v):
                raise RuntimeError("Baseline syn_vivado.v not generated")


            iverilog_baseline = f"iverilog -o wave_1 syn_vivado.v {testbench}"
            vvp_baseline      = "vvp -n wave_1 -lxt2"
            print("  - iverilog baseline:", iverilog_baseline)
            subprocess.run(iverilog_baseline, shell=True, cwd=folder_path,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           timeout=timeout_sec, check=True)
            with open(os.path.join(folder_path, "file1.txt"), "w") as f1:
                r = subprocess.run(vvp_baseline, shell=True, cwd=folder_path,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   timeout=timeout_sec, check=True)
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

         
            shutil.move(syn_v, os.path.join(folder_path, "old_syn_vivado.v"))

            
            tcl_cand = f"""\
read_verilog rtl.v
{vivado_command}
write_verilog -force syn_vivado.v
"""
            tcl_cand_path = os.path.join(folder_path, "synth_cand.tcl")
            with open(tcl_cand_path, "w") as f:
                f.write(tcl_cand)

            vivado_cand_cmd = "vivado -mode batch -source synth_cand.tcl"
            print("  - Vivado candidate:", vivado_cand_cmd)
            subprocess.run(
                vivado_cand_cmd, shell=True, cwd=folder_path,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=timeout_sec, check=True
            )
            if not os.path.exists(os.path.join(folder_path, "syn_vivado.v")):
                raise RuntimeError("Candidate syn_vivado.v not generated")

            
            iverilog_cand = f"iverilog -o wave_2 syn_vivado.v {testbench}"
            vvp_cand      = "vvp -n wave_2 -lxt2"
            print("  - iverilog cand:", iverilog_cand)
            subprocess.run(iverilog_cand, shell=True, cwd=folder_path,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           timeout=timeout_sec, check=True)
            with open(os.path.join(folder_path, "file2.txt"), "w") as f2:
                r = subprocess.run(vvp_cand, shell=True, cwd=folder_path,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   timeout=timeout_sec, check=True)
                f2.write(r.stdout)

            
            output_txt = os.path.join(folder_path, "output.txt")
            with open(output_txt, "w") as outfp:
                subprocess.run(
                    ["python3", "compare.py"],
                    cwd=folder_path, stdout=outfp, stderr=subprocess.PIPE, text=True,
                    timeout=timeout_sec, check=False
                )
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

        except subprocess.CalledProcessError as e:
            fault_number += 1
            dst = os.path.join(fault_folder, folder)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(case_root, dst)
            print(f"  - FAULT: Vivado/Sim failed\n{e}")

        except Exception as e:
            fault_number += 1
            dst = os.path.join(fault_folder, folder)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(case_root, dst)
            print(f"  - FAULT: {e}")

    print(f"[SUMMARY] fault={fault_number}, timeout={timeout_number}, diff={diff_number}")
    return fault_number, timeout_number, diff_number


def Evaluate_main(new_episode: int, vivado_command: str):

    test_file_update()
    print("[Vivado] episode =", new_episode)
    print("[Vivado] command:\n", vivado_command)

    os.makedirs(f"timeout_collection_vivado/{new_episode}", exist_ok=True)
    os.makedirs(f"fault_collection_vivado/{new_episode}", exist_ok=True)
    os.makedirs(f"check_collection_vivado/{new_episode}", exist_ok=True)

    timeout_folder = f"timeout_collection_vivado/{new_episode}"
    fault_folder   = f"fault_collection_vivado/{new_episode}"
    check_folder   = f"check_collection_vivado/{new_episode}"

    fault_number, timeout_number, diff_number = diff_check_vivado(
        vivado_command=vivado_command,
        check_folder=check_folder,
        fault_folder=fault_folder,
        timeout_folder=timeout_folder,
        base_dir=os.path.join(os.getcwd(), "action_program_test_vivado"),
        top_module=DEFAULT_TOP,
        testbench=DEFAULT_TB,
        timeout_sec=DEFAULT_TIMEOUT_SEC
    )

    print(f"[Vivado] Fault number: {fault_number}")
    print(f"[Vivado] Timeout number: {timeout_number}")
    print(f"[Vivado] Diff number: {diff_number}")
    return fault_number, timeout_number
