from supersonic.core.diff import DiffParser, FileDiff


def test_parse_simple_diff():
    """Test parsing a simple diff"""
    diff_content = """
diff --git a/test.txt b/test.txt
index abc..def
--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
-old content
+new content
 unchanged
"""
    parser = DiffParser()
    diffs = parser.parse(diff_content)

    assert len(diffs) == 1
    assert diffs[0].path == "test.txt"
    assert diffs[0].new_content == "new content\nunchanged"
    assert diffs[0].original_content == "old content\nunchanged"
    assert not diffs[0].is_new_file
    assert not diffs[0].is_deletion


def test_parse_new_file():
    """Test parsing a new file diff"""
    diff_content = """
diff --git a/new.txt b/new.txt
new file mode 100644
index 000000..def
--- /dev/null
+++ b/new.txt
@@ -0,0 +1 @@
+new content
"""
    parser = DiffParser()
    diffs = parser.parse(diff_content)

    assert len(diffs) == 1
    assert diffs[0].path == "new.txt"
    assert diffs[0].new_content == "new content"
    assert diffs[0].is_new_file
    assert not diffs[0].is_deletion


def test_generate_commit_message():
    """Test commit message generation"""
    parser = DiffParser()
    diffs = [
        FileDiff(
            path="test.py",
            original_content="def old():\n    pass",
            new_content="def new():\n    return True",
            is_new_file=False,
            is_deletion=False,
        )
    ]

    message = parser.generate_commit_message(diffs)
    assert "Update" in message
    assert "py" in message
