"""
Command line tool to programmatically call Mentat, the AI coding assistant
und let it run a custom series of prompts and commands by using
the Mentat Python SDK

Usage:
    python3 assistant.py [command] [ARGS]

You can define your own custom prompts you want Mentat to run.
The assistant will look up prompts/command.xml and run it, using any other
args for substituting place holders in the defined prompt.
"""

import asyncio
import logging
import os
import argparse
from typing import Final, List
from mentat import Mentat  # type: ignore
import sys

# Possibly switch to lxml.etree in the future to support schema validation
import xml.etree.ElementTree as ET


class Assistant:
    def __init__(self, command: str, args: List[str], promptsdir: str = "prompts"):
        self.command: Final[str] = command
        self.promptsdir: Final[str] = promptsdir
        self.args: Final[List[str]] = args

    async def run(self) -> None:
        logging.info(f"Starting to run {self.command}")
        try:
            root = self.get_xml_root()
        except RuntimeError as e:
            logging.error(e)
            return

        # Prepare prompt and context
        prompt = self.get_prompt(root)
        logging.info(prompt)
        context = self.get_context(root)
        logging.info(f"Files to include as context: {context}")

        # Now let mentat do the work
        logging.info("Running Mentat now...")
        client = Mentat(paths=context)
        await client.startup()
        await client.call_mentat_auto_accept(prompt)
        await client.shutdown()
        logging.info("Done. Mentat finished its work.")

    def get_xml_root(self):
        # Open and parse XML file
        file_path = os.path.join(self.promptsdir, f"{self.command}.xml")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise RuntimeError(f"Error parsing XML: {e}")
        except FileNotFoundError:
            raise RuntimeError(f"Command definition file not found: {file_path}")
        return root

    # Get prompt from XML and replace all placeholders with their values.
    # Ask the user now for values of arguments missing in the command line
    def get_prompt(self, xml_root) -> str:
        raw_prompt = xml_root.find("prompt").text.strip()
        logging.info(f"Raw prompt: {raw_prompt}")

        # Parse the remaining (previously "unknown") arguments
        parser = argparse.ArgumentParser()
        for argument in xml_root.findall("argument"):
            parser.add_argument(f"--{argument.get('alias')}")

        args = parser.parse_args(self.args)
        prompt = raw_prompt
        # Go through all arguments and ask the user for missing arguments
        for argument in xml_root.findall("argument"):
            alias = argument.get("alias")
            value = getattr(args, alias.replace("-", "_"), None)
            if value:
                logging.info(f"Replacing {argument.get('id')} with {value}")
            else:
                question = argument.get("question")
                value = input(f"Missing --{alias}. {question}\n")
            prompt = prompt.replace(argument.get("id"), value)
        return prompt

    # Parse XML to get the list of files / directories that should get included
    # as context
    def get_context(self, xml_root) -> List[str]:
        ret: List[str] = []
        context_node = xml_root.find("context")
        if context_node is None:
            logging.info(f"No <context> node found in {self.command}.xml")
            return ret
        for include in context_node.findall("include"):
            ret.append(include.get("path"))
        return ret


# Parse the given arguments and return accordingly initialized Assistant
def parse_args(sys_args) -> Assistant:
    description = "Run pre-defined functions/prompts with mentat"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("command", help="Name of the function / prompt")
    parser.add_argument(
        "--promptsdir",
        default="prompts",
        help="Directory holding the command definition XML file(s)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    # The command may have more arguments we don't know yet.
    # An alternative would be to parse the available XML files now and add
    # their argument structure via parser.add_subparsers().
    # However that would be incompatible with providing a --promptsdir option
    args, more_args = parser.parse_known_args(sys_args)

    # Set up logging
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    if args.verbose:
        root.setLevel(logging.INFO)
    sh = logging.StreamHandler(sys.stdout)
    fformatter = logging.Formatter("%(levelname)s: %(message)s")
    sh.setFormatter(fformatter)
    root.addHandler(sh)

    return Assistant(args.command, more_args, promptsdir=args.promptsdir)


if __name__ == "__main__":
    assistant = parse_args(sys.argv[1:])
    asyncio.run(assistant.run())
