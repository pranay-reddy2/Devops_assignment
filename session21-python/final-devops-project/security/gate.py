"""Security gate: turn scanner reports into one pass/fail decision.

The scan jobs only *produce* JSON reports; this script owns the policy, so it
is written once and enforced the same way locally and in GitHub Actions.

Policy (block = pipeline stops before the image is pushed):
  SAST    bandit       HIGH severity or a scanner error   -> block, MEDIUM -> warn
  SCA     pip-audit    any known vulnerability with a fix -> block, no fix yet -> warn
  Secrets gitleaks     any finding                        -> block
  Image   trivy        CRITICAL/HIGH with a fixed version -> block, unfixed -> warn
  npm     npm audit    HIGH/CRITICAL advisory              -> block, moderate/low -> warn

Usage: python security/gate.py <reports-dir>
"""
import json
import os
import sys
from pathlib import Path


def load(path):
    if not path.exists():
        return None
    text = path.read_text().strip()
    return json.loads(text) if text else []


def check_bandit(report):
    # A crashed scan writes a report with no results; that must not count as clean.
    block = [f"scanner error: {e['filename']}: {e['reason']}" for e in report.get("errors", [])]
    warn = []
    for r in report.get("results", []):
        line = f"{r['test_id']} {r['issue_severity']} {r['filename']}:{r['line_number']} {r['issue_text']}"
        if r["issue_severity"] == "HIGH":
            block.append(line)
        elif r["issue_severity"] == "MEDIUM":
            warn.append(line)
    return block, warn


def check_pip_audit(report):
    block, warn = [], []
    for dep in report.get("dependencies", []):
        for v in dep.get("vulns", []):
            line = f"{dep['name']}=={dep['version']} {v['id']} fix: {', '.join(v.get('fix_versions', [])) or 'none'}"
            (block if v.get("fix_versions") else warn).append(line)
    return block, warn


def check_gitleaks(report):
    return [f"{f['RuleID']} {f['File']}:{f['StartLine']}" for f in report], []


def check_trivy(report):
    block, warn = [], []
    for result in report.get("Results", []):
        for v in result.get("Vulnerabilities") or []:
            if v["Severity"] not in ("CRITICAL", "HIGH"):
                continue
            line = f"{v['Severity']} {v['VulnerabilityID']} {v['PkgName']} {v['InstalledVersion']} -> {v.get('FixedVersion') or 'no fix'}"
            (block if v.get("FixedVersion") else warn).append(line)
    return block, warn


def check_npm(report):
    block, warn = [], []
    for name, v in (report.get("vulnerabilities") or {}).items():
        line = f"{name} {v['severity']} {v.get('range', '')}"
        (block if v["severity"] in ("high", "critical") else warn).append(line)
    return block, warn


CHECKS = [
    ("SAST", "bandit.json", check_bandit),
    ("SCA-py", "pip-audit.json", check_pip_audit),
    ("SCA-npm", "npm-audit.json", check_npm),
    ("Secrets", "gitleaks.json", check_gitleaks),
    ("Image-backend", "trivy-backend.json", check_trivy),
    ("Image-frontend", "trivy-frontend.json", check_trivy),
]


def main():
    reports = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
    rows, details, failed = [], [], False
    for name, filename, check in CHECKS:
        data = load(reports / filename)
        if data is None:
            rows.append((name, filename, "-", "-", "MISSING"))
            failed = True
            continue
        block, warn = check(data)
        verdict = "FAIL" if block else "PASS"
        failed |= bool(block)
        rows.append((name, filename, str(len(block)), str(len(warn)), verdict))
        details += [f"  BLOCK {name}: {b}" for b in block[:8]]
        if len(block) > 8:
            details.append(f"  BLOCK {name}: ... and {len(block) - 8} more (see {filename})")
        details += [f"  warn  {name}: {w}" for w in warn[:5]]
        if len(warn) > 5:
            details.append(f"  warn  {name}: ... and {len(warn) - 5} more (see {filename})")

    header = ("Stage", "Report", "Blocking", "Warnings", "Result")
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(5)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    out = ["SECURITY GATE", fmt.format(*header)] + [fmt.format(*r) for r in rows]
    out += details
    out.append(f"DECISION: {'BLOCKED - image will not be pushed or deployed' if failed else 'PASSED - safe to push and deploy'}")
    print("\n".join(out))

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write("### Security gate\n\n| " + " | ".join(header) + " |\n|" + "---|" * 5 + "\n")
            fh.writelines("| " + " | ".join(r) + " |\n" for r in rows)
            fh.write(f"\n**{'BLOCKED' if failed else 'PASSED'}**\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
