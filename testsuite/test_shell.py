# -*- coding: utf-8 -*-
import os.path
import sys
import unittest

import pep8
from testsuite.support import ROOT_DIR, PseudoFile


class ShellTestCase(unittest.TestCase):
    """Test the usual CLI options and output."""

    def setUp(self):
        self._saved_argv = sys.argv
        self._saved_stdout = sys.stdout
        self._saved_stderr = sys.stderr
        self._saved_pconfig = pep8.PROJECT_CONFIG
        self._saved_cpread = pep8.RawConfigParser._read
        self._saved_stdin_get_value = pep8.stdin_get_value
        self._config_filenames = []
        self.stdin = ''
        sys.argv = ['pep8']
        sys.stdout = PseudoFile()
        sys.stderr = PseudoFile()

        def fake_config_parser_read(cp, fp, filename):
            self._config_filenames.append(filename)
        pep8.RawConfigParser._read = fake_config_parser_read
        pep8.stdin_get_value = self.stdin_get_value

    def tearDown(self):
        sys.argv = self._saved_argv
        sys.stdout = self._saved_stdout
        sys.stderr = self._saved_stderr
        pep8.PROJECT_CONFIG = self._saved_pconfig
        pep8.RawConfigParser._read = self._saved_cpread
        pep8.stdin_get_value = self._saved_stdin_get_value

    def stdin_get_value(self):
        return self.stdin

    def pep8(self, *args):
        del sys.stdout[:], sys.stderr[:]
        sys.argv[1:] = args
        try:
            pep8._main()
            errorcode = None
        except SystemExit:
            errorcode = sys.exc_info()[1].code
        return sys.stdout.getvalue(), sys.stderr.getvalue(), errorcode

    def test_print_usage(self):
        stdout, stderr, errcode = self.pep8('--help')
        self.assertFalse(errcode)
        self.assertFalse(stderr)
        self.assertTrue(stdout.startswith("Usage: pep8 [options] input"))

        stdout, stderr, errcode = self.pep8('--version')
        self.assertFalse(errcode)
        self.assertFalse(stderr)
        self.assertEqual(stdout.count('\n'), 1)

        stdout, stderr, errcode = self.pep8('--obfuscated')
        self.assertEqual(errcode, 2)
        self.assertEqual(stderr.splitlines(),
                         ["Usage: pep8 [options] input ...", "",
                          "pep8: error: no such option: --obfuscated"])
        self.assertFalse(stdout)

        self.assertFalse(self._config_filenames)

    def test_check_simple(self):
        E11 = os.path.join(ROOT_DIR, 'testsuite', 'E11.py')
        stdout, stderr, errcode = self.pep8(E11)
        stdout = stdout.splitlines()
        self.assertEqual(errcode, 1)
        self.assertFalse(stderr)
        self.assertEqual(len(stdout), 6)
        for line, num, col in zip(stdout, (3, 6, 9, 12), (3, 6, 1, 5)):
            path, x, y, msg = line.split(':')
            self.assertTrue(path.endswith(E11))
            self.assertEqual(x, str(num))
            self.assertEqual(y, str(col))
            self.assertTrue(msg.startswith(' E11'))
        # Config file read from the pep8's tox.ini
        (config_filename,) = self._config_filenames
        self.assertTrue(config_filename.endswith('tox.ini'))

    def test_check_stdin(self):
        pep8.PROJECT_CONFIG = ()
        stdout, stderr, errcode = self.pep8('-')
        self.assertFalse(errcode)
        self.assertFalse(stderr)
        self.assertFalse(stdout)

        self.stdin = 'import os, sys\n'
        stdout, stderr, errcode = self.pep8('-')
        stdout = stdout.splitlines()
        self.assertEqual(errcode, 1)
        self.assertFalse(stderr)
        self.assertEqual(stdout,
                         ['stdin:1:10: E401 multiple imports on one line'])

    def test_check_non_existent(self):
        self.stdin = 'import os, sys\n'
        stdout, stderr, errcode = self.pep8('fictitious.py')
        self.assertEqual(errcode, 1)
        self.assertFalse(stderr)
        self.assertTrue(stdout.startswith('fictitious.py:1:1: E902 '))

    def test_check_noarg(self):
        # issue #170: do not read stdin by default
        pep8.PROJECT_CONFIG = ()
        stdout, stderr, errcode = self.pep8()
        self.assertEqual(errcode, 2)
        self.assertEqual(stderr.splitlines(),
                         ["Usage: pep8 [options] input ...", "",
                          "pep8: error: input not specified"])
        self.assertFalse(self._config_filenames)
