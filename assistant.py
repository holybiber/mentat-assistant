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
import json
import logging
import os
import argparse
from typing import Any, Dict, Final, List, Optional
from mentat import Mentat  # type: ignore
import sys

# Possibly switch to lxml.etree in the future to support schema validation
import xml.etree.ElementTree as ET


class Assistant:
    def __init__(
        self,
        command: str,
        args: List[str],
        promptsdir: str = "prompts",
        composer_json: str = "composer.json",
    ):
        self.command: Final[str] = command
        self.args: Final[List[str]] = args
        self.promptsdir: Final[str] = promptsdir
        self.composer_json: Final[str] = composer_json
        self.xml_root: Optional[Any] = None
        # Map of search -> replace entries for the prompt
        self.replacements: Dict[str, str] = {}

    async def run(self) -> None:
        logging.info(f"Starting to run {self.command}")
        try:
            self.parse_xml()
        except RuntimeError as e:
            logging.error(e)
            return

        self.process_arguments()
        self.resolve_variables()

        prompt = self.get_prompt()
        logging.info(prompt)
        context = self.get_context()
        logging.info(f"Files to include as context: {context}")

        # Now let mentat do the work
        logging.info("Running Mentat now...")
        client = Mentat(paths=context)
        await client.startup()
        await client.call_mentat_auto_accept(prompt)
        await client.shutdown()
        logging.info("Done. Mentat finished its work.")

    # Open our command file (XML) and parse it
    def parse_xml(self) -> None:
        assert self.xml_root is None
        # Open and parse XML file
        file_path = os.path.join(self.promptsdir, f"{self.command}.xml")
        try:
            tree = ET.parse(file_path)
            self.xml_root = tree.getroot()
        except ET.ParseError as e:
            raise RuntimeError(f"Error parsing XML: {e}")
        except FileNotFoundError:
            raise RuntimeError(f"Command definition file not found: {file_path}")

    # Process all arguments. Ask the user now for values of arguments
    # missing in the command line.
    # Saves the results in self.replacements
    def process_arguments(self) -> None:
        assert self.xml_root is not None
        # Parse the remaining (previously "unknown") arguments
        parser = argparse.ArgumentParser()
        for argument in self.xml_root.findall("argument"):
            parser.add_argument(f"--{argument.get('alias')}")
        cmd_args = parser.parse_args(self.args)

        # Go through all arguments and ask the user for missing arguments
        for argument in self.xml_root.findall("argument"):
            alias = argument.get("alias")
            value = getattr(cmd_args, alias.replace("-", "_"), None)
            if value:
                logging.info(f"Replacing {argument.get('id')} with {value}")
            else:
                question = argument.get("question")
                value = input(f"Missing --{alias}. {question}\n")
            self.replacements[argument.get("id")] = value

    # Resolve all variables by running the converter
    def resolve_variables(self) -> None:
        assert self.xml_root is not None
        converter = Converter(composer_json=self.composer_json)
        for var in self.xml_root.findall("variable"):
            arg = var.get("argument")
            if arg not in self.replacements:
                logging.warning(f"Missing argument {arg} for variable {var}")
                continue
            value = converter.convert(var.get("converter"), self.replacements[arg])
            if value is not None:
                logging.info(f"Replacing {var.get('id')} with {value}")
                self.replacements[var.get("id")] = value
            else:
                logging.warning(f"Couldn't compute value of variable {var.get('id')}")

    # Get prompt from XML and replace all placeholders with their values
    # by going through self.replacements
    def get_prompt(self) -> str:
        assert self.xml_root is not None
        prompt = self.xml_root.find("prompt").text.strip()
        logging.info(f"Raw prompt: {prompt}")
        for search, replace in self.replacements.items():
            prompt = prompt.replace(search, replace)

        return prompt

    # Parse XML to get the list of files / directories that should get included
    # as context
    def get_context(self) -> List[str]:
        assert self.xml_root is not None
        ret: List[str] = []
        context_node = self.xml_root.find("context")
        if context_node is None:
            logging.info(f"No <context> node found in {self.command}.xml")
            return ret
        for include in context_node.findall("include"):
            path = include.get("path")
            if path.startswith("$"):
                if path[1:] in self.replacements:
                    ret.append(self.replacements[path[1:]])
                else:
                    logging.warning(
                        f"Couldn't determine value of {path}. " "Not adding to context."
                    )
            else:
                ret.append(path)
        return ret


# Class for converting arguments
# Currently we have one converter for determining the file path of a PHP class path
class Converter:
    def __init__(self, composer_json: str = "composer.json"):
        self.composer_json = composer_json
        self.composer_data = None
        try:
            with open(self.composer_json, "r") as file:
                self.composer_data = json.load(file)
        except FileNotFoundError:
            logging.warning(
                f"{self.composer_json} not found. Can't resolve class paths."
            )

    def convert(self, converter: str, argument: str) -> Optional[str]:
        # As we currently have only on converter, let's keep it simple:
        if converter == "resolveClassPath":
            return self.resolve_class_path(argument)
        logging.warning(f"Unknown converter {converter}. ")
        return None

    # Return the file path for the given fully-qualified class name (fqcn)
    # Returns None if we can't find matching namespace information in composer.json
    # See https://www.php-fig.org/psr/psr-4/
    # and https://getcomposer.org/doc/04-schema.md#psr-4
    def resolve_class_path(self, fqcn: str) -> Optional[str]:
        if self.composer_data is None:
            return None
        # Gather namespace information from composer.json
        namespace_map: Dict[str, str] = {}
        if (
            "autoload-dev" in self.composer_data
            and "psr-4" in self.composer_data["autoload-dev"]
        ):
            namespace_map = namespace_map | self.composer_data["autoload-dev"]["psr-4"]
        else:
            logging.info("Didn't find autoload-dev section in composer.json")
        if (
            "autoload" in self.composer_data
            and "psr-4" in self.composer_data["autoload"]
        ):
            namespace_map = namespace_map | self.composer_data["autoload"]["psr-4"]
        else:
            logging.info("Didn't find autoload section in composer.json")

        # Find the most specific (longest) matching namespace prefix
        match_length: int = -1  # match_length of 0 is possible for ""
        class_path: Optional[str] = None
        for prefix, base_dir in namespace_map.items():
            if fqcn[1:].startswith(prefix) and (len(prefix) > match_length):
                match_length = len(prefix)
                class_path = f"{base_dir}{fqcn[1 + len(prefix):]}.php".replace(
                    "\\", "/"
                )

        logging.info(f"Resolving class path for {fqcn}: {class_path}")
        return class_path


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
