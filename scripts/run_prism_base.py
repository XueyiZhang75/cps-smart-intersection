"""
PRISM Base Model Verification Runner
Runs the minimum PRISM model against base safety properties.

Usage:
  python scripts/run_prism_base.py
"""

import os
import subprocess
import sys

PROJECT_ROOT = r"E:\cps-smart-intersection"
PRISM_DIR = os.path.join(PROJECT_ROOT, "prism")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "prism")
MODEL_FILE = os.path.join(PRISM_DIR, "intersection_base.pm")
PROPS_FILE = os.path.join(PRISM_DIR, "properties_base.pctl")

# PRISM installation path
PRISM_JAR_DIR = r"E:\prism-4.10\lib"
PRISM_MAIN = "prism.PrismCL"


def find_prism():
    """Try to locate a working PRISM invocation."""
    # Method 1: prism on PATH
    try:
        result = subprocess.run(["prism", "--version"], capture_output=True, text=True, timeout=10)
        if "PRISM version" in result.stdout or "PRISM version" in result.stderr:
            return ["prism"], None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Method 2: java -cp with local installation
    # PRISM native DLLs depend on each other (dd.dll, dv.dll, odd.dll, etc.)
    # They must be on the system PATH for Windows DLL resolution to work.
    if os.path.exists(PRISM_JAR_DIR):
        env = os.environ.copy()
        env["PATH"] = PRISM_JAR_DIR + os.pathsep + env.get("PATH", "")
        jars = os.path.join(PRISM_JAR_DIR, "*")
        cmd = [
            "java", "--enable-native-access=ALL-UNNAMED",
            "-cp", f"{os.path.join(PRISM_JAR_DIR, 'prism.jar')};{jars}",
            f"-Djava.library.path={PRISM_JAR_DIR}",
            PRISM_MAIN,
        ]
        try:
            result = subprocess.run(cmd + ["--version"], capture_output=True,
                                    text=True, timeout=10, env=env)
            combined = result.stdout + result.stderr
            if "PRISM version" in combined and "UnsatisfiedLinkError" not in combined:
                return cmd, env
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return None


def run_prism(prism_cmd, model, props, output_log, env=None):
    """Run PRISM and capture output."""
    cmd = prism_cmd + [model, props]
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    output = result.stdout + "\n" + result.stderr

    with open(output_log, "w") as f:
        f.write(output)

    return output, result.returncode


def parse_results(output):
    """Extract property results from PRISM output."""
    results = []
    lines = output.split("\n")
    current_prop = None
    for line in lines:
        if line.strip().startswith("Model checking:"):
            current_prop = line.strip().replace("Model checking: ", "")
        if "Result:" in line and current_prop:
            result_val = line.strip()
            results.append({"property": current_prop, "result": result_val})
            current_prop = None
    return results


def write_results_md(results, filepath, prism_available, raw_output_path=None):
    """Write human-readable verification results."""
    lines = []
    lines.append("# PRISM Base Safety Verification Results\n")

    if not prism_available:
        lines.append("## Status: PRISM Not Available\n")
        lines.append("PRISM model checker could not be invoked in the current environment.")
        lines.append("The native DLLs in `E:\\prism-4.10\\lib\\` have missing dependencies")
        lines.append("(likely Visual C++ runtime mismatch with the installed Java version).\n")
        lines.append("### Files Prepared")
        lines.append(f"- Model: `{MODEL_FILE}`")
        lines.append(f"- Properties: `{PROPS_FILE}`")
        lines.append(f"- Mapping: `docs/sumo_prism_mapping.md`\n")
        lines.append("### To Run Manually")
        lines.append("Once PRISM DLL dependencies are resolved:")
        lines.append("```")
        lines.append(f"prism {MODEL_FILE} {PROPS_FILE}")
        lines.append("```\n")
        lines.append("### Expected Results (by structural analysis)")
        lines.append("| Property | Expected |")
        lines.append("|----------|----------|")
        lines.append("| P>=1 [ G !\"conflict\" ] | **true** — model structurally guarantees cl_count=0 at service phase entry |")
        lines.append("| P>=1 [ G !\"veh_conflict_during_ped\" ] | **true** — single phase variable makes simultaneous phases impossible |")
        lines.append("| P>=1 [ \"clearance\" => (F cl_count=3) ] | **true** — clearance always counts to CLEARANCE_DUR=3 then advances |")
    else:
        lines.append("## Status: Verification Complete\n")
        if raw_output_path:
            lines.append(f"Raw PRISM output: `{raw_output_path}`\n")
        lines.append("### Results\n")
        lines.append("| Property | Result |")
        lines.append("|----------|--------|")
        for r in results:
            lines.append(f"| {r['property']} | {r['result']} |")
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 60)
    print("  PRISM Base Safety Verification")
    print("=" * 60)
    print(f"Model:      {MODEL_FILE}")
    print(f"Properties: {PROPS_FILE}")
    print()

    # Check files exist
    if not os.path.exists(MODEL_FILE):
        print(f"[ERROR] Model file not found: {MODEL_FILE}")
        return
    if not os.path.exists(PROPS_FILE):
        print(f"[ERROR] Properties file not found: {PROPS_FILE}")
        return

    # Find PRISM
    print("[CHECK] Searching for PRISM...")
    found = find_prism()

    if found is None:
        prism_cmd, prism_env = None, None
    else:
        prism_cmd, prism_env = found

    if prism_cmd is None:
        print("[WARN] PRISM model checker not available in current environment.")
        print("       Native DLLs at E:\\prism-4.10\\lib have missing dependencies.")
        print("       Generating results with expected-value analysis only.\n")

        md_path = os.path.join(RESULTS_DIR, "base_verification_results.md")
        write_results_md([], md_path, prism_available=False)
        print(f"[OK] Results written to {md_path}")
        return

    print(f"[OK] PRISM found: {prism_cmd[0]}\n")

    # Run verification
    raw_log = os.path.join(RESULTS_DIR, "prism_raw_output.txt")
    output, retcode = run_prism(prism_cmd, MODEL_FILE, PROPS_FILE, raw_log, env=prism_env)
    print(f"[DONE] Return code: {retcode}")
    print(f"[LOG]  Raw output: {raw_log}\n")

    # Check for DLL errors
    if "UnsatisfiedLinkError" in output or "Can't find dependent libraries" in output:
        print("[WARN] PRISM started but native DLLs failed to load.")
        print("       Model checking could not complete.")
        print("       Generating results with expected-value analysis only.\n")
        md_path = os.path.join(RESULTS_DIR, "base_verification_results.md")
        write_results_md([], md_path, prism_available=False)
        print(f"[OK] Results: {md_path}")
        return

    # Parse and save results
    results = parse_results(output)
    md_path = os.path.join(RESULTS_DIR, "base_verification_results.md")
    write_results_md(results, md_path, prism_available=True, raw_output_path=raw_log)
    print(f"[OK] Results: {md_path}")

    # Print summary
    print("\nVerification Results:")
    for r in results:
        print(f"  {r['property']}")
        print(f"    => {r['result']}")


if __name__ == "__main__":
    main()
