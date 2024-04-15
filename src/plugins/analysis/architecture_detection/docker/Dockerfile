# We can't use alpine since alpine (unintentionally) does not include yaml support in dtc
FROM ubuntu:noble
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y dist-upgrade && \
    apt-get install -y device-tree-compiler && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/bin/dtc"]
