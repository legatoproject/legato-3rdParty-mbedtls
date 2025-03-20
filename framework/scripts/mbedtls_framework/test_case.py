"""Library for constructing an Mbed TLS test case.
"""

# Copyright The Mbed TLS Contributors
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-or-later
#

import binascii
import os
import sys
from typing import Iterable, List, Optional
from enum import Enum

from . import build_tree
from . import psa_information
from . import typing_util

HASHES_3_6 = {
    "PSA_ALG_MD5" : "MBEDTLS_MD_CAN_MD5",
    "PSA_ALG_RIPEMD160" : "MBEDTLS_MD_CAN_RIPEMD160",
    "PSA_ALG_SHA_1" : "MBEDTLS_MD_CAN_SHA1",
    "PSA_ALG_SHA_224" : "MBEDTLS_MD_CAN_SHA224",
    "PSA_ALG_SHA_256" : "MBEDTLS_MD_CAN_SHA256",
    "PSA_ALG_SHA_384" : "MBEDTLS_MD_CAN_SHA384",
    "PSA_ALG_SHA_512" : "MBEDTLS_MD_CAN_SHA512",
    "PSA_ALG_SHA3_224" : "MBEDTLS_MD_CAN_SHA3_224",
    "PSA_ALG_SHA3_256" : "MBEDTLS_MD_CAN_SHA3_256",
    "PSA_ALG_SHA3_384" : "MBEDTLS_MD_CAN_SHA3_384",
    "PSA_ALG_SHA3_512" : "MBEDTLS_MD_CAN_SHA3_512"
}

PK_MACROS_3_6 = {
    "PSA_KEY_TYPE_ECC_PUBLIC_KEY" : "MBEDTLS_PK_HAVE_ECC_KEYS"
}

class Domain36(Enum):
    PSA = 1
    TLS_1_3_ONLY = 2
    USE_PSA = 3
    LEGACY = 4

def hex_string(data: bytes) -> str:
    return '"' + binascii.hexlify(data).decode('ascii') + '"'

class MissingDescription(Exception):
    pass

class MissingFunction(Exception):
    pass

class TestCase:
    """An Mbed TLS test case."""

    def __init__(self, description: Optional[str] = None):
        self.comments = [] #type: List[str]
        self.description = description #type: Optional[str]
        self.dependencies = [] #type: List[str]
        self.function = None #type: Optional[str]
        self.arguments = [] #type: List[str]
        self.skip_reasons = [] #type: List[str]

    def add_comment(self, *lines: str) -> None:
        self.comments += lines

    def set_description(self, description: str) -> None:
        self.description = description

    def get_dependencies(self) -> List[str]:
        return self.dependencies

    def set_dependencies(self, dependencies: List[str]) -> None:
        self.dependencies = dependencies

    def set_function(self, function: str) -> None:
        self.function = function

    def set_arguments(self, arguments: List[str]) -> None:
        self.arguments = arguments

    def skip_because(self, reason: str) -> None:
        """Skip this test case.

        It will be included in the output, but commented out.

        This is intended for test cases that are obtained from a
        systematic enumeration, but that have dependencies that cannot
        be fulfilled. Since we don't want to have test cases that are
        never executed, we arrange not to have actual test cases. But
        we do include comments to make it easier to understand the output
        of test case generation.

        reason must be a non-empty string explaining to humans why this
        test case is skipped.
        """
        self.skip_reasons.append(reason)

    def check_completeness(self) -> None:
        if self.description is None:
            raise MissingDescription
        if self.function is None:
            raise MissingFunction

    def write(self, out: typing_util.Writable) -> None:
        """Write the .data file paragraph for this test case.

        The output starts and ends with a single newline character. If the
        surrounding code writes lines (consisting of non-newline characters
        and a final newline), you will end up with a blank line before, but
        not after the test case.
        """
        self.check_completeness()
        assert self.description is not None # guide mypy
        assert self.function is not None # guide mypy
        out.write('\n')
        for line in self.comments:
            out.write('# ' + line + '\n')
        prefix = ''
        if self.skip_reasons:
            prefix = '## '
            for reason in self.skip_reasons:
                out.write('## # skipped because: ' + reason + '\n')
        out.write(prefix + self.description + '\n')
        dependencies = self.get_dependencies()
        if dependencies:
            out.write(prefix + 'depends_on:' +
                      ':'.join(dependencies) + '\n')
        out.write(prefix + self.function + ':' +
                  ':'.join(self.arguments) + '\n')

def write_data_file(filename: str,
                    test_cases: Iterable[TestCase],
                    caller: Optional[str] = None) -> None:
    """Write the test cases to the specified file.

    If the file already exists, it is overwritten.
    """
    if caller is None:
        caller = os.path.basename(sys.argv[0])
    tempfile = filename + '.new'
    with open(tempfile, 'w') as out:
        out.write('# Automatically generated by {}. Do not edit!\n'
                  .format(caller))
        for tc in test_cases:
            tc.write(out)
        out.write('\n# End of automatically generated file.\n')
    os.replace(tempfile, filename)

def psa_or_3_6_feature_macro(psa_name: str,
                             domain_3_6: Domain36) -> str:
    """Determine the dependency symbol for a given psa_name based on
       the domain and Mbed TLS version. For more information about the domains,
       and MBEDTLS_MD_CAN_ prefixed symbols, see transition-guards.md.
       This function currently works with hashes and some PK symbols only.
       It accepts PSA_ALG_xxx or PSA_KEY_TYPE_xxx as inputs for psa_name.
    """

    if domain_3_6 == Domain36.PSA or domain_3_6 == Domain36.TLS_1_3_ONLY or \
        not build_tree.is_mbedtls_3_6():
        if psa_name in PK_MACROS_3_6 or psa_name in HASHES_3_6:
            return psa_information.psa_want_symbol(psa_name)

    if domain_3_6 == Domain36.USE_PSA:
        if psa_name in PK_MACROS_3_6:
            return PK_MACROS_3_6[psa_name]

    if psa_name in HASHES_3_6:
        return HASHES_3_6[psa_name]

    raise ValueError(f'Unable to determine dependency symbol for {psa_name} in {domain_3_6}')
