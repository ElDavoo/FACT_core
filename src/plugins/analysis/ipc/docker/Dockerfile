FROM fkiecad/ghidra_headless_base:11.0.1 as runtime

WORKDIR /ipc

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ipc_analyzer/ /opt/ghidra/Ghidra/Features/Python/ghidra_scripts/
COPY ghidra_headless.py .

ENTRYPOINT ["/ipc/ghidra_headless.py"]
