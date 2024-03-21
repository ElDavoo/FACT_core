# We can't use alpine since alpine (unintentionally) does not include yaml support in dtc
FROM ubuntu:noble
RUN apt update && apt install -y device-tree-compiler && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/bin/dtc"]
