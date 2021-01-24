import cli
import sadface
import unittest
import sys

from unittest.mock import MagicMock, patch

from nose2.tools import params

class TestCli(unittest.TestCase):

    def test_banner(self):
        result = cli.banner()
        assert result == None

    @patch.object(sys, 'argv', ['sadface.py','deploy'])
    def test_parseargs(self):
        result = cli.parseArgs(['deploy'])
        assert result.command == 'deploy'