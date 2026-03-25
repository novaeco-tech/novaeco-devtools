import json

import pytest
from novaeco_cli.utils.reporting import RstReporter


@pytest.fixture
def reporter(tmp_path):
    """
    Fixture that initializes the RstReporter with a temporary directory
    as the repository root, ensuring tests don't pollute the real workspace.
    """
    return RstReporter(repo_root=str(tmp_path))


# --- Tests for _ensure_dir ---


def test_ensure_dir_creates_target_if_docs_exist(reporter, tmp_path):
    """Verify it creates the _generated folder if the docs/ folder exists."""
    # Setup: Create the mock 'docs' folder
    (tmp_path / "docs").mkdir()

    # Execute
    result = reporter._ensure_dir()

    # Assert
    assert result is True
    assert reporter.report_dir.exists()
    assert reporter.report_dir.name == "_generated"


def test_ensure_dir_aborts_if_no_docs(reporter, tmp_path):
    """Verify it safely aborts if the repo doesn't have a docs/ folder."""
    # Execute without creating 'docs'
    result = reporter._ensure_dir()

    # Assert
    assert result is False
    assert not reporter.report_dir.exists()


# --- Tests for write_security_report ---


def test_security_report_no_issues(reporter, tmp_path):
    """Verify RST generation when Bandit finds 0 issues."""
    (tmp_path / "docs").mkdir()

    # Mock the Bandit output JSON
    json_path = tmp_path / "bandit.json"
    json_path.write_text(json.dumps({"results": []}))

    reporter.write_security_report(str(json_path))

    output_file = reporter.report_dir / "security_vulns.rst"
    assert output_file.exists()

    content = output_file.read_text()
    assert "✅ No security issues found" in content


def test_security_report_with_issues(reporter, tmp_path):
    """Verify RST table generation when Bandit finds vulnerabilities."""
    (tmp_path / "docs").mkdir()

    # Mock the Bandit output JSON with a fake issue
    fake_file_path = str(tmp_path / "src" / "bad.py")
    json_path = tmp_path / "bandit.json"
    json_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "filename": fake_file_path,
                        "line_number": 42,
                        "issue_severity": "HIGH",
                        "issue_text": "Hardcoded password found",
                    }
                ]
            }
        )
    )

    reporter.write_security_report(str(json_path))

    output_file = reporter.report_dir / "security_vulns.rst"
    content = output_file.read_text()

    # Assert table headers and values
    assert "⚠️ Found 1 issues" in content
    assert ".. list-table::" in content
    assert "HIGH" in content
    assert "Hardcoded password found" in content
    # Verify the relative path cleanup worked
    assert "src/bad.py:42" in content


def test_security_report_missing_json(reporter, tmp_path, capsys):
    """Verify it handles a missing JSON file gracefully."""
    (tmp_path / "docs").mkdir()

    # Execute pointing to a file that doesn't exist
    reporter.write_security_report(str(tmp_path / "missing.json"))

    # Assert it caught the FileNotFoundError and printed a warning
    captured = capsys.readouterr()
    assert "⚠️  Bandit JSON output not found" in captured.out
    assert not (reporter.report_dir / "security_vulns.rst").exists()


# --- Tests for write_coverage_report ---


def test_coverage_report_passing(reporter, tmp_path):
    """Verify RST generation for coverage >= 80%."""
    (tmp_path / "docs").mkdir()

    # Mock the coverage.xml output
    xml_path = tmp_path / "coverage.xml"
    xml_path.write_text('<coverage line-rate="0.85"></coverage>')

    reporter.write_coverage_report(str(xml_path))

    output_file = reporter.report_dir / "coverage_summary.rst"
    assert output_file.exists()

    content = output_file.read_text()
    assert "85.00%" in content
    assert ".. tip::" in content  # Success admonition


def test_coverage_report_failing(reporter, tmp_path):
    """Verify RST generation for coverage < 80%."""
    (tmp_path / "docs").mkdir()

    # Mock the coverage.xml output
    xml_path = tmp_path / "coverage.xml"
    xml_path.write_text('<coverage line-rate="0.543"></coverage>')

    reporter.write_coverage_report(str(xml_path))

    output_file = reporter.report_dir / "coverage_summary.rst"
    content = output_file.read_text()

    assert "54.30%" in content
    assert ".. error::" in content  # Failure admonition


def test_coverage_report_bad_xml(reporter, tmp_path):
    """Verify it gracefully handles malformed or missing XML."""
    (tmp_path / "docs").mkdir()

    xml_path = tmp_path / "coverage.xml"
    xml_path.write_text("This is not valid XML data")

    # It should catch the ParseError and pass silently
    reporter.write_coverage_report(str(xml_path))

    assert not (reporter.report_dir / "coverage_summary.rst").exists()
