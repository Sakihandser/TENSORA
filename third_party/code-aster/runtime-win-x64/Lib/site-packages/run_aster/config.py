# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
:py:mod:`config` --- Configuration of the version
-------------------------------------------------

The :py:class:`Config` object gives access to the configuration parameters
of the installed version.
These parameters are usually set during the ``waf configure`` step and are
stored in a YAML file (or JSON for compatibility).

The configuration file is installed in
``<installation-prefix>/share/aster/config.yaml``.
It contains *version parameters*.

The list of the supported *version parameters* are (with their type):

.. code-block:: none

    version_tag: str        - version number
    version_sha1: str       - sha1 of the revision
    tmpdir: str             - temporary directory used for execution
    addmem: int             - memory added to the memory limit found from export
    parallel: bool          - true for a parallel version
    python: str             - Python interpreter
    python_interactive: str - Python interpreter for interactive executions
    python_interactive_is_wrapped: bool - Tell of Python for interactive sessions is a wrapper
    mpiexec: str            - mpiexec/srun command line with arguments
    mpi_get_rank: str       - command line to get the mpi rank
    only-proc0: bool        - true to limit output to proc #0, false to show all
    require_mpiexec: bool   - tell if mpiexec/srun is required even with one process
    use_srun: bool          - true if processes are started with srun
    FC: str                 - fortran compiler
    FCFLAGS: list[str]      - flags for fortran compiler
    exectool: dict[str]     - command lines for execution wrappers
    outputdir: str          - output directory for ``waf test`` and derivated
    copymode: str           - utility to copy data/results files: 'rsync' or 'shutil'

All these parameters are set during the *configure* step of the installation.

They can be set during the *configure* step using environment variables named
``CONFIG_PARAMETERS_<parameter-name>``.

.. note::

    ``mpiexec`` command line needs these variables ``mpi_nbcpu`` and ``program``
    following the `Python Format String Syntax`_. For example:

    .. code-block:: sh

        mpiexec -n {mpi_nbcpu} --tag-output {program}

.. _Python Format String Syntax: https://docs.python.org/3/library/string.html#formatstrings

These *version parameters* can be overridden by a user file:
``$HOME/.config/aster/config.yaml``.

The user can override these parameters depending on the *server name* and/or the
*version* using filters. A *server* is defined by its *name*, a *version* by
its *path*.

Parameters are read from the installation directory
(``share/aster/config.yaml``), then, from the user file (from ``.config/aster``
directory), per-server configurations are read in the order they are listed
and finally, the per-version configurations are evaluated.

Example of ``$HOME/.config/aster/config.yaml`` (for this example only ``tmpdir``
is set in different cases):

.. code-block:: yaml

    server:
      - name: eocn*
        config:
          tmpdir: /tmp_for_eocn_nodes

    version:
      - path: '*/install/14*'
        config:
          tmpdir: /tmp_for_v14

      - path: '*/dev/codeaster/install/*'
        config:
          tmpdir: /tmp_for_development_version


What is the value for ``tmpdir`` on a cluster node named ``eocn123`` running
the version installed in the ``/projets/aster/install/14.4/mpi``?

- First, ``tmpdir`` is read from
  ``/projets/aster/install/14.4/mpi/share/aster/config.yaml``.

- Does ``eocn123`` match ``"*"``? Yes, so use ``/tmp_for_all_servers``.

- Does ``eocn123`` match ``"eocn*"``? Yes, so use ``/tmp_for_eocn_nodes``.

- Does ``/projets/aster/install/14.4/mpi`` match ``"*/install/14*"``?
  Yes, so use ``/tmp_for_v14``.

- Does ``/projets/aster/install/14.4/mpi`` match ``"*/dev/codeaster/install/*"``?
  No.

- Finally, the working directory will be created in ``/tmp_for_v14``.

Each block ``config`` can override one or more parameter already defined in
``config.yaml``.

An *execution wrapper* is a tool, for example a debugger or *valgrind*, that
can preceed the executed command line.
Example of ``$HOME/.config/aster/config.yaml``:

.. code-block:: yaml

    server:
      - name: '*'
        config:
          exectool:
            valgrind: valgrind --tool=memcheck --leak-check=full --error-limit=no --track-origins=yes


This ``valgrind`` command line is actually defined by default in the configuration
file of the installed version and it is callable with ``run_aster --valgrind ...``.
Another one is also defined by default to wrap *gdb* execution:
``run_aster --gdb ...``.
"""

import json
import os
import os.path as osp
import platform
from fnmatch import fnmatchcase
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from .logger import logger
from .settings import AbstractParameter, Store
from .base_params import RUNASTER_ROOT

# all parameters must be set by `data/wscript - check_config()`
VERSION_PARAMS = {
    "version_tag": "str",
    "version_sha1": "str",
    "tmpdir": "str",
    "shared_tmpdir": "str",
    "addmem": "int",
    "parallel": "bool",
    "python": "str",
    "python_interactive": "str",
    "python_interactive_is_wrapped": "bool",
    "mpiexec": "str",
    "mpi_get_rank": "str",
    "require_mpiexec": "bool",
    "use_srun": "bool",
    "only-proc0": "bool",
    "FC": "varstr",
    "FCFLAGS": "varlist[str]",
    "exectool": "dict[str]",
    "outputdir": "str",
    "use_s3sp": "bool",
    "copymode": "str",
}


class ConfigurationStore(Store):
    """Object that stores settings for a version."""

    @staticmethod
    def _new_param(name):
        """Create a Parameter of the right type."""
        return AbstractParameter.factory(VERSION_PARAMS, name)


class Config:
    """Configuration parameters.

    Arguments:
        mainfcfg (str): File name of the configuration file.
    """

    usercfg = str(Path.home() / ".config" / "aster" / "config.yaml")

    def __init__(self, mainfcfg):
        if not osp.exists(mainfcfg) or not yaml:
            jcfg = osp.splitext(mainfcfg)[0] + ".json"
            if osp.exists(jcfg):
                mainfcfg = jcfg
        self._mainfcfg = mainfcfg
        self._storage = ConfigurationStore()

    @property
    def storage(self):
        """dict: Attribute that holds the 'storage' property."""
        # while it is empty, try to load the config files
        if not self._storage:
            self.load()
        return self._storage

    def load(self):
        """Load the configuration file."""
        self.load_one(self._mainfcfg, main=True)
        usercfg = Config.usercfg
        try:
            os.makedirs(osp.dirname(usercfg), exist_ok=True)
        except OSError as exc:
            logger.warning("can not create user preferences file: %s", str(exc))
            return
        if not osp.exists(usercfg) or not yaml:
            jcfg = osp.splitext(usercfg)[0] + ".json"
            if osp.exists(jcfg):
                Config.usercfg = usercfg = jcfg
        self.load_one(usercfg)

    def load_one(self, cfgfile, main=False):
        """Load `cfgfile`.

        Arguments:
            cfgfile (str): File name of the configuration file.
            main (bool): *True* for the configuration file installed for this
                version, *False* for user configuration file.
        """
        ext = osp.splitext(cfgfile)[-1]
        assert ext in (".yaml", ".json"), "'.yaml'/'.json' expected for the configuration file."
        logger.debug("reading configuration file %s", cfgfile)
        try:
            with open(cfgfile, "rb") as fcfg:
                if ext == ".yaml":
                    assert (
                        yaml
                    ), f"yaml not available, can not use {cfgfile}, please convert it into '.json' instead"
                    content = yaml.load(fcfg.read(), Loader=yaml.Loader)
                elif ext == ".json":
                    content = json.load(fcfg)
        except FileNotFoundError:
            if main:
                logger.warning("file not found: %s", cfgfile)
            logger.debug("file not found: %s", cfgfile)
            return
        self.import_dict(content, with_sections=not main)

    def import_dict(self, content, with_sections):
        """Set the configuration parameters from a dict.

        Arguments:
            content (dict): file content
            with_sections (bool): *True* if it contains 'server' and/or
                'version' subsections, *False* if it directly contains the
                version parameters.
        """
        if with_sections:
            params = self.filter(content, "server", "name", platform.node())
            params.update(self.filter(content, "version", "path", RUNASTER_ROOT))
        else:
            params = content
        for key, value in params.items():
            self._storage.set(key, value)
            logger.debug("+ %s: %s", key, self._storage.get(key))

    @staticmethod
    def filter(content, section, filter_key, filter_value):
        """Filter content by keeping sections that match the filter.

        Arguments:
            content (dict): file content with optional "server" and
                "version" list.

        Returns:
            dict: Version parameters for the current server and version.
        """
        params = {}
        candidates = content.get(section, [])
        if not isinstance(candidates, list):
            candidates = [candidates]
        for cfg in candidates:
            if not isinstance(cfg, dict):
                logger.warning("dict expected for %r, not: %s", section, cfg)
                continue
            if not fnmatchcase(filter_value, cfg.get(filter_key, "")):
                continue
            config = cfg.get("config", {})
            if not isinstance(config, dict):
                logger.warning("dict expected for 'config', not: %s", config)
                continue
            params.update(config)
        return params

    def get(self, key, default=None):
        """Return the value of `key` parameter or `default` if it is not
        defined.

        Arguments:
            key (str): Parameter name.
            default (misc): Default value, (default is *None*).

        Returns:
            misc: Value or default value.
        """
        return self.storage.get(key, default)


CFG = Config(osp.join(RUNASTER_ROOT, "share", "aster", "config.yaml"))
