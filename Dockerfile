FROM debian

# Configure environment variables and time zone
# to avoid questions during docker build
ENV TZ="Europe/Berlin"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update -y && \
    apt-get install -y -o Acquire::Retries=10 \
                    --no-install-recommends \
    python3 \
	python3-pip \
    git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /home/
# Adding --default-timeout=100 to avoid networking issues during the fairly long docker build
# Using --break-system-packages to avoid the externally-managed-environment error
# As we're anyway in a docker container we don't go the "normal" way of installing python3-venv and using a virtual environment
RUN pip install --default-timeout=100 --break-system-packages -r /home/requirements.txt

COPY assistant.py /home/
ADD prompts /home/prompts

ENTRYPOINT ["/usr/bin/python3",  "/home/assistant.py", "--promptsdir", "/home/prompts"]