import asyncio
from typing import Dict
import unittest
from unittest.mock import patch, AsyncMock
from assistant import Assistant, Converter, parse_args


class TestAssistant(unittest.TestCase):
    def setUp(self):
        # Use this to see logging messages while running tests
        # logging.basicConfig(level=logging.INFO)
        self.assistant = Assistant(
            "test-arguments-and-context",
            ["--class", "TestClass", "--method", "start"],
            promptsdir="test",
        )
        self.assistant2 = Assistant(
            "test-variable-substitution",
            [
                "--class",
                "\\Assistant\\Random",
                "--test-class",
                "\\Assistant\\Test\\RandomTest",
            ],
            promptsdir="test",
            composer_json="test/composer.json",
        )

    def test_parse_xml(self):
        # Test normal behavior
        self.assistant.parse_xml()
        self.assertIsNotNone(self.assistant.xml_root)
        self.assertIsNotNone(self.assistant.xml_root.find("argument"))
        self.assertIsNotNone(self.assistant.xml_root.find("context"))
        self.assertIsNone(self.assistant.xml_root.find("notexisting"))

        # Test with an invalid XML structure
        assistant = Assistant("test-invalid-structure", [], promptsdir="test")
        with self.assertRaises(RuntimeError) as error:
            assistant.parse_xml()
        self.assertIn("Error parsing XML", str(error.exception))

        # Test with not-existing XML file
        assistant = Assistant("not-existing", [], promptsdir="test_prompts")
        with self.assertRaises(RuntimeError) as error:
            assistant.parse_xml()
        self.assertIn("Command definition file not found", str(error.exception))

    def test_get_prompt(self):
        expected_prompt = "Test method `start` in class `TestClass`."
        self.assistant.parse_xml()
        self.assistant.process_arguments()
        self.assertEqual(self.assistant.get_prompt(), expected_prompt)

        # giving arguments in the form --class=TestClass
        # should give the same result as giving it as --class TestClass
        self.assistant.args = ["--class=TestClass", "--method=start"]
        self.assertEqual(self.assistant.get_prompt(), expected_prompt)

    def test_get_context(self):
        # Test normal behavior
        self.assistant.parse_xml()
        self.assertListEqual(["tests", "src"], self.assistant.get_context())

        # Test with missing <context> node
        self.assistant.xml_root.remove(self.assistant.xml_root.find("context"))
        assert len(self.assistant.get_context()) == 0

        # Test variable substitution
        self.assistant2.parse_xml()
        self.assistant2.process_arguments()
        with self.assertLogs(level="WARNING"):
            self.assertListEqual(["tests"], self.assistant2.get_context())
        self.assistant2.resolve_variables()
        self.assertListEqual(
            ["tests", "src/Assistant/Random.php"], self.assistant2.get_context()
        )

    @patch("assistant.Mentat")
    def test_run(self, mock_mentat):
        mock_mentat.return_value = AsyncMock()
        with self.assertLogs(level="WARNING"):
            asyncio.run(self.assistant.run())
        mock_mentat.assert_called_once()
        mock_mentat.return_value.startup.assert_called_once()
        mock_mentat.return_value.call_mentat_auto_accept.assert_called_with(
            "Test method `start` in class `TestClass`."
        )
        mock_mentat.return_value.shutdown.assert_called_once()


class TestMain(unittest.TestCase):
    def test_parse_args(self):
        assistant = parse_args(["generate-unit-tests"])
        self.assertEqual(assistant.command, "generate-unit-tests")
        self.assertEqual(assistant.promptsdir, "prompts")
        self.assertListEqual(assistant.args, [])

        assistant = parse_args(["test", "--class=TestClass", "-v"])
        self.assertEqual(assistant.command, "test")
        self.assertListEqual(assistant.args, ["--class=TestClass"])

        assistant = parse_args(
            [
                "test",
                "--class=TestClass",
                "--method",
                "testMethod",
                "--promptsdir",
                "test_prompts",
            ]
        )
        self.assertEqual(assistant.command, "test")
        self.assertListEqual(
            assistant.args, ["--class=TestClass", "--method", "testMethod"]
        )
        self.assertEqual(assistant.promptsdir, "test_prompts")


class TestConverter(unittest.TestCase):
    def test_convert(self):
        with self.assertLogs(level="WARNING"):
            converter = Converter(composer_json="not_existing.json")
        self.assertIsNone(converter.convert("resolveClassPath", "test"))
        with self.assertLogs(level="WARNING"):
            self.assertIsNone(converter.convert("unknown", "test"))

    def test_resolve_class_path(self):
        converter = Converter(composer_json="test/composer.json")
        test_cases: Dict[str, str] = {
            "\\Acme\\Log\\Writer\\File_Writer": "./acme-log-writer/lib/File_Writer.php",
            "\\Aura\\Web\\Response\\Status": "/path/aura-web/src/Response/Status.php",
            "\\Aura\\Web\\Tests\\BaseTest": "/path/aura-web/tests/BaseTest.php",
            "\\Symfony\\Core\\Request": "./vendor/Symfony/Core/Request.php",
            "\\Zend\\Acl": "/usr/includes/Zend/Acl.php",
            "\\Test\\Random": "src/Test/Random.php",
        }
        for fqcn, file_path in test_cases.items():
            self.assertEqual(converter.resolve_class_path(fqcn), file_path)

        with self.assertLogs(level="WARNING"):
            converter = Converter(composer_json="not_existing.json")
        self.assertIsNone(converter.resolve_class_path("\\Test\\Random"))


if __name__ == "__main__":
    unittest.main()
