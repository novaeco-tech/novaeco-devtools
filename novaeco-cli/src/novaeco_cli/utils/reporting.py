import json
from pathlib import Path


class RstReporter:
    def __init__(self, repo_root: str = "."):
        self.root = Path(repo_root)
        self.report_dir = self.root / "docs" / "source" / "reports" / "_generated"

    def _ensure_dir(self):
        """Creates the _generated directory if docs structure exists."""
        if (self.root / "docs").exists():
            self.report_dir.mkdir(parents=True, exist_ok=True)
            return True
        return False

    def write_security_report(self, bandit_json_path: str):
        """Converts Bandit JSON output to an RST list."""
        if not self._ensure_dir():
            return

        target_file = self.report_dir / "security_vulns.rst"

        try:
            with open(bandit_json_path, "r") as f:
                data = json.load(f)

            results = data.get("results", [])
            content = []

            if not results:
                content.append("**Status:** ✅ No security issues found.")
            else:
                content.append(f"**Status:** ⚠️ Found {len(results)} issues.")
                content.append("")
                content.append(".. list-table::")
                content.append("   :widths: 15 15 70")
                content.append("   :header-rows: 1")
                content.append("")
                content.append("   * - Severity")
                content.append("     - File")
                content.append("     - Issue")

                for item in results:
                    # Clean filename relative to repo root
                    fname = item["filename"].replace(str(self.root.absolute()), "")
                    content.append(f"   * - {item['issue_severity']}")
                    content.append(f"     - ``{fname}:{item['line_number']}``")
                    content.append(f"     - {item['issue_text']}")

            with open(target_file, "w") as f:
                f.write("\n".join(content))

            print(f"📝 Wrote security report to {target_file}")

        except FileNotFoundError:
            print("⚠️  Bandit JSON output not found. Skipping RST generation.")

    def write_coverage_report(self, cov_xml_path: str = "coverage.xml"):
        """Reads coverage.xml (or summary) and writes a summary RST."""
        if not self._ensure_dir():
            return

        target_file = self.report_dir / "coverage_summary.rst"

        # Simple parsing logic (can be replaced with xml.etree if strict accuracy needed)
        # For this example, we assume a generic message or use the console output capture

        # Ideally, use coverage.py API or parse XML
        import xml.etree.ElementTree as ET

        content = []
        try:
            tree = ET.parse(cov_xml_path)  # nosec B314 # nosemgrep
            root = tree.getroot()
            rate = float(root.attrib.get("line-rate", 0)) * 100

            content.append(f"**Line Coverage:** {rate:.2f}%")
            content.append("")

            if rate < 80:
                content.append(".. error:: Coverage is below the 80% threshold!")
            else:
                content.append(".. tip:: Coverage meets the quality gate.")

            with open(target_file, "w") as f:
                f.write("\n".join(content))

            print(f"📝 Wrote coverage report to {target_file}")

        except Exception:
            # Fallback if XML missing
            pass
