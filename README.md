# mentat-assistant
Command line tool to programmatically call [Mentat](https://www.mentat.ai/), the AI coding assistant
and let it run a custom series of prompts and commands by using
the [Mentat Python SDK](https://docs.mentat.ai/en/latest/sdk/index.html)

Usage (without docker):

    `python3 assistant.py [-v] [--promptsdir /path/to/prompts] command [ARGS]`

The assistant will look up prompts/command.xml and run it. It'll use any other
args for substituting place holders in the defined prompt and ask for any missing arguments.
Additionally you can fill variables with a converter from other arguments.
Currently there is one converter to resolve fully qualified PHP class names to file names
so you can use the result either in your prompt or to automatically add files into the context.
You can define your own custom prompts you want Mentat to run by adding them to the `prompts/` folder.
Look at [prompts/generate-unit-tests.xml](prompts/generate-unit-tests.xml) for an example of the XML structure.

## Setup without docker
1. Clone this repository
2. Add a file `.env` with your OpenAI API key (`OPENAI_API_KEY=sk-...` - see [.env.example](.env.example))
3. Install the necessary python packages via
`pip install -r requirements.txt`

## Setup using docker
Alternatively you can run the assistant with the docker-based wrapper provided in [bin/assistant](bin/assistant):
1. Clone this repository
2. Add a file `.env` with your OpenAI API key (`OPENAI_API_KEY=sk-...` - see [.env.example](.env.example))
3. Make `./bin/assistant` executable (on Linux: `chmod +x ./bin/assistant`)

Usage (same command line options as described previously):

    `./bin/assistant [-v] [--promptsdir /path/to/prompts] command [ARGS]`

To simplify usage so that you don't have to call it with the full path `/path/to/mentat/bin/assistant` every time:
- Create a symlink from [bin/assistant](bin/assistant) into your `$PATH` so that you can easily run the wrapper script from anywhere on your computer, e.g. `ln -s /path/to/mentat-assistant/bin/assistant ~/.local/bin/assistant`

Now you can run `assistant` from anywhere and it always operates on your current directory.

## Configuration
Both setup variants will use your [Mentat configuration](https://docs.mentat.ai/en/latest/user/configuration.html). E.g. you can create a `~/.mentat/.mentat_config.json` with
```
{
    "model": "gpt-4-1106-preview"
}
```
and Mentat will always use this model. Alternatively add a per-project `.mentat-config.json` into the directory you want to work on.


# Contributing
This code is licensed unter the [MIT License](LICENSE) - you're warmly invited to contribute!

## Code quality
To make sure to have some good level of code quality please run
- `black .` to auto-format the code with the [black auto-formatter](https://github.com/psf/black)
- `python3 -m unittest discover -s test/` to run all tests
- `flake8 .` to check for any linting issues
- `mypy .` for static type checking

However currently there are not that many type annotations and `mypy --strict .` would report a number
of issues. Currently I don't intend to fix that as that would make the code harder to read
and overly complicated for a non-mission-critical script.
Instead I have plans to implement XML schema validation to ensure the
XML command definition files are well-formatted with all required attributes.

With GitHub Actions these four commands are run on any push or pull request in the repository,
see the [Github workflow](.github/workflows/main.yml)

## Explanations on the Docker wrapper
[Dockerfile](Dockerfile): The container is based on Debian and is also available on Docker Hub: [holybiber/mentat-assistant](https://hub.docker.com/r/holybiber/mentat-assistant).

[docker-compose.yml](docker-compose.yml): Docker compose setup, makes mentat configuration available to the container

[bin/assistant](bin/assistant): Wrapper for docker compose so that we can run the assistant easily

## See also
https://github.com/holybiber/mentat