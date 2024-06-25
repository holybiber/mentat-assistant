# mentat-assistant
Command line tool to programmatically call [Mentat](https://www.mentat.ai/), the AI coding assistant
und let it run a custom series of prompts and commands by using
the [Mentat Python SDK](https://docs.mentat.ai/en/latest/sdk/index.html)

Usage:
    `python3 assistant.py [command] [ARGS]`

You can define your own custom prompts you want Mentat to run.
The assistant will look up prompts/command.xml and run it, using any other
args for substituting place holders in the defined prompt.

## Code quality
To make sure to have some good level of code quality please run
- `black .` to auto-format the code with the [black auto-formatter](https://github.com/psf/black)
- `python3 -m unittest discover` to run all tests
- `flake8 .` to check for any linting issues
- `mypy .` for static type checking

However currently there are not that many type annotations and `mypy --strict .` would report a number
of issues. Currently I don't intend to fix that as that would make the code harder to read
and overly complicated for a non-mission-critical script.
Instead I have plans to implement XML schema validation to ensure the
XML command definition files are well-formatted with all required attributes.

With GitHub Actions these four commands are run on any push or pull request in the repository,
see the [Github workflow](.github/workflows/main.yml)
