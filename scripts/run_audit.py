#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Static Audit Orchestrator for NTN
- Runs code_review.py across 14 modules
- Performs PowerShell (.ps1) syntax checks via PowerShell AST parser
- Performs Shell (.sh) syntax checks via WSL bash -n when available
Outputs a consolidated JSON report: audit_results.json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')

MODULES = [
    "01APIForge", "02DataSpider", "03ScanPulse", "04OptiCore",
    "05-07TradeGuard", "08NeuroHub", "09MMS", "10ReviewGuard",
    "11ASTSConsole", "12TACoreService", "13AIStrategyAssistant", "14ObservabilityCenter"
]


def _decode_output(data: bytes) -> str:
    if data is None:
        return ""
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def run_subprocess(cmd: List[str], cwd: str = PROJECT_ROOT, timeout: int = 300, env: Dict[str, str] | None = None) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, shell=False, env=env)
    stdout = _decode_output(proc.stdout)
    stderr = _decode_output(proc.stderr)
    return proc.returncode, stdout, stderr

# Prefer pwsh (PowerShell 7) when available

def _pwsh_available() -> bool:
    try:
        rc, out, err = run_subprocess(["pwsh", "-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], timeout=10)
        return rc == 0
    except Exception:
        return False


def run_code_review() -> Dict:
    py = sys.executable or 'python'
    code_review_path = os.path.join(PROJECT_ROOT, 'code_review.py')
    if not os.path.exists(code_review_path):
        return {"status": "error", "message": f"code_review.py not found at {code_review_path}"}

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    rc, out, err = run_subprocess([py, code_review_path], env=env)
    result_path = os.path.join(PROJECT_ROOT, 'code_review_results.json')

    status = "ok" if os.path.exists(result_path) else ("ok" if rc == 0 else "error")
    result_obj = {
        "status": status,
        "return_code": rc,
        "stdout": out.strip(),
        "stderr": err.strip(),
        "result_file": result_path,
        "summary": {}
    }

    if os.path.exists(result_path):
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result_obj["summary"] = {
                "total_files": data.get('total_files'),
                "total_syntax_errors": data.get('total_syntax_errors'),
                "total_bugs": data.get('total_bugs')
            }
        except Exception as e:
            result_obj["status"] = "error"
            result_obj["stderr"] = (result_obj.get("stderr") or "") + f"\nFailed to parse code_review_results.json: {e}"
    return result_obj


def list_files_by_prefix_ext(directory: str, prefix: str, ext: str) -> List[str]:
    files = []
    if not os.path.isdir(directory):
        return files
    for name in os.listdir(directory):
        if name.lower().startswith(prefix.lower()) and name.lower().endswith(ext.lower()):
            files.append(os.path.join(directory, name))
    return sorted(files)


def check_powershell_syntax(files: List[str]) -> Dict:
    results = {}
    if not files:
        return results
    ps_exe = "pwsh" if _pwsh_available() else "powershell"
    for path in files:
        ps_quoted = "'" + path.replace("'", "''") + "'"
        ps_cmd = (
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); $OutputEncoding = [System.Text.UTF8Encoding]::new(); "
            f"$tokens=$null; $errors=$null; "
            f"[void][System.Management.Automation.Language.Parser]::ParseFile({ps_quoted}, [ref]$tokens, [ref]$errors); "
            f"if ($errors -and $errors.Count -gt 0) {{ $errors | ForEach-Object {{ $_.Extent.Text + ' :: ' + $_.Message }}; exit 1 }} "
            f"else {{ Write-Output 'OK' }}"
        )
        try:
            rc, out, err = run_subprocess([ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd])
            ok = (rc == 0) and ("OK" in (out or ""))
            results[path] = {
                "status": "ok" if ok else "error",
                "return_code": rc,
                "stdout": out.strip(),
                "stderr": err.strip(),
                "engine": ps_exe,
            }
        except Exception as e:
            results[path] = {"status": "error", "exception": str(e), "engine": ps_exe}
    return results


def windows_to_wsl_path(win_path: str) -> str:
    drive, rest = os.path.splitdrive(win_path)
    drive_letter = drive.replace(':', '').lower()
    wsl = f"/mnt/{drive_letter}" + rest.replace('\\', '/')
    return wsl


def wsl_available() -> bool:
    try:
        rc, out, err = run_subprocess(["wsl", "--status"], timeout=15)
        return rc == 0
    except Exception:
        return False


def check_shell_syntax(files: List[str]) -> Dict:
    results = {}
    if not files:
        return results
    has_wsl = wsl_available()
    for path in files:
        if not has_wsl:
            results[path] = {"status": "skipped", "reason": "WSL not available; cannot run bash -n"}
            continue
        # Create a temporary LF-normalized copy for syntax checking only
        tmp_copy = None
        try:
            with open(path, "rb") as f:
                data = f.read()
            normalized = data.replace(b"\r\n", b"\n")
            tmp_copy = os.path.join(tempfile.gettempdir(), f"ntn_audit_lf_{os.path.basename(path)}")
            with open(tmp_copy, "wb") as f:
                f.write(normalized)

            wsl_path = windows_to_wsl_path(tmp_copy)
            rc, out, err = run_subprocess(["wsl", "bash", "-n", wsl_path])
            results[path] = {
                "status": "ok" if rc == 0 else "error",
                "return_code": rc,
                "stdout": out.strip(),
                "stderr": err.strip(),
                "note": "Checked with LF-normalized temp copy",
            }
        except Exception as e:
            results[path] = {"status": "error", "exception": str(e)}
        finally:
            if tmp_copy and os.path.exists(tmp_copy):
                try:
                    os.remove(tmp_copy)
                except Exception:
                    pass
    return results


def main():
    parser = argparse.ArgumentParser(description="NTN Unified Static Audit Orchestrator")
    parser.add_argument("--scope", choices=["all", "python", "powershell", "shell"], default="all")
    parser.add_argument("--output", default=os.path.join(PROJECT_ROOT, "audit_results.json"))
    args = parser.parse_args()

    report: Dict = {
        "timestamp": datetime.now().isoformat(),
        "project_root": PROJECT_ROOT,
        "scope": args.scope,
        "python_review": None,
        "powershell_syntax": None,
        "shell_syntax": None
    }

    if args.scope in ("all", "python"):
        report["python_review"] = run_code_review()

    if args.scope in ("all", "powershell"):
        ps1_files = list_files_by_prefix_ext(SCRIPTS_DIR, "audit_", ".ps1")
        report["powershell_syntax"] = check_powershell_syntax(ps1_files)

    if args.scope in ("all", "shell"):
        sh_files = list_files_by_prefix_ext(SCRIPTS_DIR, "audit_", ".sh")
        report["shell_syntax"] = check_shell_syntax(sh_files)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Console summary
    print("=== NTN Unified Static Audit Summary ===")
    if report.get("python_review"):
        pr = report["python_review"]
        status = pr.get("status")
        summ = pr.get("summary", {}) or {}
        print(f"Python Review: {status} | files={summ.get('total_files')} syntax_errors={summ.get('total_syntax_errors')} bugs={summ.get('total_bugs')}")
        if status != "ok":
            se = (pr.get("stderr") or "").splitlines()
            if se:
                print("- code_review stderr (first 5 lines):")
                for line in se[:5]:
                    print(f"  {line}")
    if report.get("powershell_syntax") is not None:
        ps_results = report["powershell_syntax"] or {}
        ok = sum(1 for v in ps_results.values() if v.get("status") == "ok")
        total = len(ps_results)
        print(f"PowerShell Scripts Syntax: ok={ok}/{total}")
        failures = [k for k, v in ps_results.items() if v.get("status") != "ok"]
        if failures:
            print("- Failing PowerShell scripts:")
            for k in failures:
                err = (ps_results[k].get("stderr") or ps_results[k].get("stdout") or "").splitlines()
                engine = ps_results[k].get("engine")
                print(f"  {k} (engine={engine})")
                for line in err[:3]:
                    print(f"    {line}")
    if report.get("shell_syntax") is not None:
        sh_results = report["shell_syntax"] or {}
        ok = sum(1 for v in sh_results.values() if v.get("status") == "ok")
        skipped = sum(1 for v in sh_results.values() if v.get("status") == "skipped")
        total = len(sh_results)
        print(f"Shell Scripts Syntax (via WSL bash -n): ok={ok}/{total}, skipped={skipped}")
        failures = [k for k, v in sh_results.items() if v.get("status") == "error"]
        if failures:
            print("- Failing Shell scripts:")
            for k in failures:
                err = (sh_results[k].get("stderr") or sh_results[k].get("stdout") or "").splitlines()
                note = sh_results[k].get("note")
                print(f"  {k}{' [' + note + ']' if note else ''}")
                for line in err[:3]:
                    print(f"    {line}")
    print(f"Report saved: {args.output}")


if __name__ == "__main__":
    main()