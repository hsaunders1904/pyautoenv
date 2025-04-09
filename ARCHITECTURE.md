# Architecture

Most work done in `pyautoenv` is a performed by
the Python script [`pyautoenv.py`](./pyautoenv.py).
This script will generate a shell command
to activate/deactivate virtual environments based on
the environment variables and the current working directory.

Activation scripts are provided for each supported shell.
These scripts check that Python is available on the system
and will run the `pyautoenv.py` script
and execute its returned shell command.
