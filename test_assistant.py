import asyncio
import unittest
from unittest.mock import patch, AsyncMock
from assistant import Assistant


class TestAssistant(unittest.TestCase):
    def setUp(self):
        # Use this to see logging messages while running tests
        # logging.basicConfig(level=logging.INFO)
        self.assistant = Assistant(
            "test-arguments-and-context",
            ["--class", "TestClass", "--method", "start"],
            promptsdir="test_prompts",
        )

    def test_get_xml_root(self):
        # Test normal behavior
        root = self.assistant.get_xml_root()
        self.assertIsNotNone(root)
        self.assertIsNotNone(root.find("argument"))
        self.assertIsNotNone(root.find("context"))
        self.assertIsNone(root.find("notexisting"))

        # Test with an invalid XML structure
        assistant = Assistant("test-invalid-structure", [], promptsdir="test_prompts")
        with self.assertRaises(RuntimeError) as error:
            assistant.get_xml_root()
        self.assertIn("Error parsing XML", str(error.exception))

        # Test with not-existing XML file
        assistant = Assistant("not-existing", [], promptsdir="test_prompts")
        with self.assertRaises(RuntimeError) as error:
            assistant.get_xml_root()
        self.assertIn("Command definition file not found", str(error.exception))

    def test_get_prompt(self):
        root = self.assistant.get_xml_root()
        prompt = self.assistant.get_prompt(root)
        self.assertEqual(prompt, "Test method `start` in class `TestClass`.")

    def test_get_context(self):
        # Test normal behavior
        root = self.assistant.get_xml_root()
        self.assertListEqual(["tests", "src"], self.assistant.get_context(root))

        # Test with missing <context> node
        root.remove(root.find("context"))
        assert len(self.assistant.get_context(root)) == 0

    @patch("assistant.Mentat")
    def test_run(self, mock_mentat):
        mock_mentat.return_value = AsyncMock()
        asyncio.run(self.assistant.run())
        mock_mentat.assert_called_once()
        mock_mentat.return_value.startup.assert_called_once()
        mock_mentat.return_value.call_mentat_auto_accept.assert_called_with(
            "Test method `start` in class `TestClass`."
        )
        mock_mentat.return_value.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
