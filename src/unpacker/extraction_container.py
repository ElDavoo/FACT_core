from __future__ import annotations

import logging
from contextlib import suppress
from http import HTTPStatus
from os import getgid, getuid, getenv
from pathlib import Path
from typing import TYPE_CHECKING
from time import sleep

import docker
import requests
from docker.errors import APIError, DockerException
from docker.types import Mount
from requests.adapters import HTTPAdapter, Retry

import config

if TYPE_CHECKING:
    import multiprocessing
    from tempfile import TemporaryDirectory

    from docker.models.containers import Container
    from requests.adapters import Response

DOCKER_CLIENT = docker.from_env()
EXTRACTOR_DOCKER_IMAGE = 'fact_extractor'
FALLBACK_EXTRACTOR_DOCKER_IMAGE = 'fkiecad/fact_extractor'


class ExtractionContainer:
    def __init__(self, id_: int, tmp_dir: TemporaryDirectory, value: multiprocessing.managers.ValueProxy):
        self.id_ = id_
        self.tmp_dir = tmp_dir
        self.port = config.backend.unpacking.base_port + id_
        self.container_id = None
        self.exception = value
        self._adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.1))
        self.network_mode = 'container:' + getenv('HOSTNAME') if getenv('INSIDE_DOCKER') is not None else None

    def start(self):
        if self.container_id is not None:
            raise RuntimeError('Already running.')

        try:
            self._start_container()
        except APIError as exception:
            if 'port is already allocated' in str(exception):
                self._recover_from_port_in_use(exception)
            elif 'The container name' in str(exception) and 'is already in use' in str(exception):
                self._recover_from_port_in_use(exception)
            else:
                raise

    def _start_container(self):
        volume = Mount('/tmp/extractor', self.tmp_dir.name, read_only=False, type='bind')
        # check if the local image is available
        try:
            global EXTRACTOR_DOCKER_IMAGE
            DOCKER_CLIENT.images.get(EXTRACTOR_DOCKER_IMAGE)
        except docker.errors.ImageNotFound:
            logging.info(f'Local image not found, using default image {FALLBACK_EXTRACTOR_DOCKER_IMAGE}')
            EXTRACTOR_DOCKER_IMAGE = FALLBACK_EXTRACTOR_DOCKER_IMAGE
            
        container = DOCKER_CLIENT.containers.run(
            image=EXTRACTOR_DOCKER_IMAGE,
            ports={f'{self.port}/tcp': self.port} if self.network_mode is None else None,
            mem_limit=f'{config.backend.unpacking.memory_limit}m',
            mounts=[volume],
            volumes={'/dev': {'bind': '/dev', 'mode': 'rw'}},
            privileged=True,
            detach=True,
            remove=True,
            environment={'CHMOD_OWNER': f'{getuid()}:{getgid()}'},
            entrypoint=f'gunicorn --timeout 600 -w 1 -b 0.0.0.0:{self.port} server:app',
            network_mode=self.network_mode,
            ulimits=[docker.types.Ulimit(name='nofile', soft=20000, hard=50000)],
            name=f'fact_extractor_{self.id_}',
        )
        self.container_id = container.id
        logging.info(f'Started unpack worker {self.id_}')

    def stop(self):
        if self.container_id is None:
            raise RuntimeError('Container is not running.')

        logging.info(f'Stopping unpack worker {self.id_}')
        self._remove_container()

    def set_exception(self):
        return self.exception.set(1)

    def exception_occurred(self) -> bool:
        return self.exception.get() == 1

    def _remove_container(self, container: Container | None = None):
        if not container:
            container = self._get_container()
        container.stop(timeout=5)
        with suppress(DockerException):
            container.wait(timeout=5)
            container.kill()
            container.remove(force=True)
        sleep(1)

    def _get_container(self) -> Container:
        return DOCKER_CLIENT.containers.get(self.container_id)

    def restart(self):
        self.stop()
        self.exception.set(0)
        self.container_id = None
        self.start()

    def _recover_from_port_in_use(self, exception: Exception):
        logging.warning('Extractor containers already around, trying to remove them...')
        for running_container in DOCKER_CLIENT.containers.list():
            if self._is_extractor_container(running_container) and self._has_same_port(running_container):
                self._remove_container(running_container)
        self._start_container()

    @staticmethod
    def _is_extractor_container(container: Container) -> bool:
        return any(EXTRACTOR_DOCKER_IMAGE in tag or FALLBACK_EXTRACTOR_DOCKER_IMAGE in tag for tag in container.image.attrs['RepoTags'])

    def _has_same_port(self, container: Container) -> bool:
        return any(((entry['HostPort'] == str(self.port) for entry in container.ports.get(f'{self.port}/tcp', [])),
                   getenv('INSIDE_DOCKER') is not None
                    ))

    def get_logs(self) -> str:
        container = self._get_container()
        return container.logs().decode(errors='replace')

    def start_unpacking(self, tmp_dir: str, timeout: int | None = None) -> Response:
        response = self._check_connection()
        if response.status_code != HTTPStatus.OK:
            return response
        url = f'http://localhost:{self.port}/start/{Path(tmp_dir).name}'
        return requests.get(url, timeout=timeout)

    def _check_connection(self) -> Response:
        """
        Try to access the /status endpoint of the container to make sure the container is ready.
        The `self._adapter` includes a retry in order to wait if the connection cannot be established directly.
        We can't retry on the actual /start endpoint (or else we would start unpacking multiple times).
        """
        url = f'http://localhost:{self.port}/status'
        with requests.Session() as session:
            session.mount('http://', self._adapter)
            return session.get(url, timeout=5)