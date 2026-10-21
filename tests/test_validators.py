"""Tests of how assertion failures are reported and of the command line exit status."""

import os
import tempfile
import unittest

from click.testing import CliRunner

from sa4_bitstream_validator.__main__ import cli
from sa4_bitstream_validator.validators import XMLValidator

SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" vc:minVersion="1.1"
           xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning">
  <xs:element name="Root">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="a" type="xs:integer"/>
        <xs:element name="b" type="xs:integer"/>
      </xs:sequence>
      <xs:assert test="a &lt;= 16"/>
      <xs:assert provision="recommendation" test="
          b = 1
          or
          b = 2"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def write(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w") as f:
        f.write(text)
    return path


class AssertionReporting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.schema = write(self.tmp.name, "rules.xsd", SCHEMA)

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, a, b):
        xml = write(self.tmp.name, "d.xml", f"<Root><a>{a}</a><b>{b}</b></Root>")
        return XMLValidator().validate(xml, self.schema)

    def test_passing_description(self):
        ok, errors, results = self.validate(1, 1)
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_failing_requirement_is_reported(self):
        ok, errors, results = self.validate(20, 1)
        self.assertFalse(ok)
        self.assertEqual(len(results["failing_assertions"]), 1)

    def test_multi_line_recommendation_is_a_warning_not_lost(self):
        ok, errors, results = self.validate(1, 7)
        self.assertTrue(ok, "a recommendation does not fail the description")
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(results["warning_assertions"]), 1)

    def test_error_no_assertion_explains_is_a_failure(self):
        xml = write(self.tmp.name, "d.xml", "<Root><b>1</b><a>1</a></Root>")
        ok, errors, results = XMLValidator().validate(xml, self.schema)
        self.assertFalse(ok)
        self.assertTrue(results["failing_assertions"])


class ExitStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.schema = write(self.tmp.name, "rules.xsd", SCHEMA)
        self.runner = CliRunner()

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, a, b):
        xml = write(self.tmp.name, "d.xml", f"<Root><a>{a}</a><b>{b}</b></Root>")
        return self.runner.invoke(cli, ["check", xml, self.schema]).exit_code

    def test_conformant_is_0(self):
        self.assertEqual(self.check(1, 1), 0)

    def test_not_conformant_is_1(self):
        self.assertEqual(self.check(20, 1), 1)

    def test_warning_only_is_0(self):
        self.assertEqual(self.check(1, 7), 0)

    def test_validate_with_missing_config_is_2(self):
        bitstream = write(self.tmp.name, "s.264", "x")
        result = self.runner.invoke(
            cli, ["validate", bitstream, "3GPP-AVC-HD", "--config", os.path.join(self.tmp.name, "none.yaml")]
        )
        self.assertEqual(result.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
