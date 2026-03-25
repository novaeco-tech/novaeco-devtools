from unittest.mock import MagicMock

from novaeco_cli.commands.bump import execute


def test_bump_execute_modifies_files(tmp_path, monkeypatch):
    """Integration test verifying file system modifications."""

    # 1. Setup a fake file system
    # Create a mock pyproject.toml inside the temporary test directory
    fake_toml = tmp_path / "pyproject.toml"
    fake_toml.write_text('version = "1.0.0"\nname = "test"')

    # 2. Mock the TARGETS array so it only looks at our fake file
    # (Otherwise it would try to modify the real repos!)
    monkeypatch.setattr(
        "novaeco_cli.commands.bump.TARGETS", [(str(fake_toml), r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>")]
    )

    # Run the CLI command from the context of our temporary directory
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.increment = "minor"

    # 3. Execute the actual CLI logic
    execute(args)

    # 4. Verify the file on disk was actually changed
    updated_content = fake_toml.read_text()
    assert 'version = "1.1.0"' in updated_content
