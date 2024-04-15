import logging
from contextlib import suppress
from subprocess import CompletedProcess

import docker
from docker.errors import APIError, DockerException, ImageNotFound
from requests.exceptions import ReadTimeout, RequestException


def run_docker_container(
    image: str, logging_label: str = 'Docker', timeout: int = 300, combine_stderr_stdout: bool = False, **kwargs
) -> CompletedProcess:
    """
    This is a convenience function that runs a docker container and returns a
    subprocess.CompletedProcess instance for the command ran in the container.
    All remaining keyword args are passed to `docker.containers.run`.

    :param image: The name of the docker image
    :param logging_label: Label used for logging
    :param timeout: Timeout after which the execution is canceled
    :param combine_stderr_stdout: Whether to combine stderr and stdout or not

    :return: A subprocess.CompletedProcess instance for the command ran in the
        container.

    :raises docker.errors.ImageNotFound: If the docker image was not found
    :raises requests.exceptions.ReadTimeout: If the timeout was reached
    :raises docker.errors.APIError: If the communication with docker fails
    """

    mounts = kwargs.get('mounts', [])
    temp_files = []
    for mount in mounts:

        source: str = mount['Source']

        if source.startswith(config.backend.docker_mount_base_dir):
            continue
        if source.startswith('/dev'):
            continue

        # New file names have a random suffix to avoid conflicts
        new_target: str = os.path.join(config.backend.docker_mount_base_dir,
                                       f"{os.path.basename(mount['Source'])}_{''
                                       .join(random.choices(string.ascii_letters, k=4))}")

        try:

            if os.path.isdir(source):
                shutil.copytree(source, new_target)
            else:
                shutil.copy(source, new_target)
            temp_files.append(new_target)

        except Exception as e:
            logging.error(f"[{logging_label}]: Error while copying {mount['Source']} to {new_target}: {e}")

        mount['Source'] = new_target

    client = docker.client.from_env()
    kwargs.setdefault('detach', True)

    try:
        container = client.containers.run(image, **kwargs)
    except (ImageNotFound, APIError) as e:
        logging.warning(f'[{logging_label}]: encountered docker error while processing: {e}')
        raise

    try:
        response = container.wait(timeout=timeout)
        exit_code = response['StatusCode']
        stdout = (
            container.logs(stdout=True, stderr=False).decode()
            if not combine_stderr_stdout
            else container.logs(stdout=True, stderr=True).decode()
        )
        stderr = container.logs(stdout=False, stderr=True).decode() if not combine_stderr_stdout else None
    except ReadTimeout:
        logging.warning(f'[{logging_label}]: timeout while processing')
        raise
    except RequestException as e:
        logging.warning(f'[{logging_label}]: connection error while processing: {e}')
        raise
    except APIError as e:
        logging.warning(f'[{logging_label}]: encountered docker error while processing: {e}')
        raise
    finally:

        for temp_file in temp_files:
            try:
                if os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                else:
                    os.remove(temp_file)
            except Exception as e:
                logging.error(f"[{logging_label}]: Error while removing {temp_file}: {e}")

        with suppress(DockerException):
            container.stop()
            container.remove()

    # We do not know the docker entrypoint so we just insert a generic "entrypoint"
    command = kwargs.get('command', None)
    if isinstance(command, str):
        args = 'entrypoint' + command
    elif isinstance(command, list):
        args = ['entrypoint', *command]
    else:
        args = ['entrypoint']

    return CompletedProcess(args=args, returncode=exit_code, stdout=stdout, stderr=stderr)
