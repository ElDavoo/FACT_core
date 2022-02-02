import gc
import os

import pytest
from common_helper_process import execute_shell_command_get_return_code

import update_statistic
from helperFunctions.fileSystem import get_src_dir
from install import init_postgres


@pytest.mark.parametrize('script, expected_str', [
    ('start_fact.py', 'FACT Starter'),
    ('start_fact_backend.py', 'FACT Backend'),
    ('start_fact_frontend.py', 'FACT Frontend'),
    ('start_fact_db.py', 'FACT DB-Service'),
])
def test_start_script_help_and_version(script, expected_str):
    output, return_code = execute_shell_command_get_return_code('{} -h'.format(os.path.join(get_src_dir(), script)), timeout=5)
    assert return_code == 0
    assert 'usage: {}'.format(script) in output

    output, return_code = execute_shell_command_get_return_code('{} -V'.format(os.path.join(get_src_dir(), script)), timeout=5)
    assert expected_str in output, 'Wrong output {}'.format(output)
    assert return_code == 0

    gc.collect()


@pytest.mark.parametrize('script', [update_statistic, init_postgres])
def test_start_scripts_with_main(script):
    assert script.main([script.__name__, '-t']) == 0, 'script did not run successfully'
    gc.collect()


@pytest.mark.skip(reason='Not working in CI')
def test_fact_complete_start():
    output, return_code = execute_shell_command_get_return_code('{} -d -t'.format(os.path.join(get_src_dir(), 'start_fact.py')))
    assert '[DEBUG]' in output
    assert 'Analysis System online...' in output
    assert 'Analysis System offline' in output
    assert return_code == 0

    gc.collect()
