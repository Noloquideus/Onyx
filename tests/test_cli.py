import pytest
from click.testing import CliRunner
from onyx.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_help(runner):
    """Test that help works."""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Onyx - Collection of useful CLI utilities' in result.output


def test_tree_help(runner):
    """Test tree command help."""
    result = runner.invoke(cli, ['tree', '--help'])
    assert result.exit_code == 0
    assert 'Display directory structure as a tree' in result.output


def test_count_help(runner):
    """Test count command help."""
    result = runner.invoke(cli, ['count', '--help'])
    assert result.exit_code == 0
    assert 'Count lines in files within a directory' in result.output


def test_find_help(runner):
    """Test find command help."""
    result = runner.invoke(cli, ['find', '--help'])
    assert result.exit_code == 0
    assert 'Intelligent file and content search' in result.output


def test_backup_help(runner):
    """Test backup command help."""
    result = runner.invoke(cli, ['backup', '--help'])
    assert result.exit_code == 0
    assert 'Create and manage backups' in result.output


def test_git_help(runner):
    """Test git command help."""
    result = runner.invoke(cli, ['git', '--help'])
    assert result.exit_code == 0
    assert 'Git repository analytics' in result.output


def test_net_help(runner):
    """Test net command help."""
    result = runner.invoke(cli, ['net', '--help'])
    assert result.exit_code == 0
    assert 'Network connectivity and diagnostic tools' in result.output


def test_download_help(runner):
    """Test download command help."""
    result = runner.invoke(cli, ['download', '--help'])
    assert result.exit_code == 0
    assert 'Download files with progress tracking' in result.output


def test_monitor_help(runner):
    """Test monitor command help."""
    result = runner.invoke(cli, ['monitor', '--help'])
    assert result.exit_code == 0
    assert 'System resource monitoring' in result.output
