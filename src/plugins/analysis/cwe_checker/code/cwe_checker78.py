"""
This plugin implements a wrapper around the cwe_checker, which checks ELF executables for
CWE 78 (Common Weakness Enumeration). Please refer to cwe_checkers implementation for further information.
Please note that these checks are heuristics and the checks are static.
This means that there are definitely false positives and false negatives. The objective of this
plugin is to find potentially interesting binaries that deserve a deep manual analysis or intensive fuzzing.

Currently, the cwe_checker supports the following architectures:
- Intel x86 (32 and 64 bits)
- ARM
- PowerPC
- Mips
"""

from docker.types import Mount

from helperFunctions.docker import run_docker_container
from .cwe_checker import DOCKER_IMAGE, AnalysisPlugin as Base


class AnalysisPlugin(Base):
    """
    This class implements the FACT Python wrapper for the BAP plugin cwe_checker.
    """

    NAME = 'cwe_checker78'
    DESCRIPTION = (
        'This plugin checks ELF binaries for CWE 78 (Common Weakness Enumeration). '
        'Due to the danger of CWE78 static analysis, this plugin may run for a long time.'
    )
    FILE = __file__
    TIMEOUT = 900

    def _run_cwe_checker_in_docker(self, file_object, verbose: bool = False):
        result = run_docker_container(
            DOCKER_IMAGE,
            combine_stderr_stdout=True,
            timeout=self.TIMEOUT - 30,
            network_disabled=True,
            command='/input -p CWE78 --json --verbose' if verbose else '/input -p CWE78 --json --quiet',
            mounts=[
                Mount('/input', file_object.file_path, type='bind'),
            ],
            mem_limit=self.memory_limit,
            memswap_limit=self.swap_limit,
        )
        return result.stdout
