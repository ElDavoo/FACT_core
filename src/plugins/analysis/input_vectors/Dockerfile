FROM docker-radare-web-gui

# Create non-root user
RUN useradd -m r2 && \
    adduser r2 sudo && \
    echo "r2:r2" | chpasswd

# Initilise base user
USER r2
WORKDIR /home/r2
ENV HOME /home/r2

COPY internal/ /home/r2/input_vectors/

ENV VIRTUAL_ENV=/home/r2/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel r2pipe

ENTRYPOINT [ "python3", "/home/r2/input_vectors/input_vectors_r2.py" ]
