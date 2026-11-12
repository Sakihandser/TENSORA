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
:py:mod:`Serializer` --- Serialization of code_aster objects
************************************************************

code_aster objects are saved and reloaded using the *pickle* protocol.

:func:`saveObjects` does the saving of objects which are available in the user
context (in which :func:`saveObjects` is called).
The command :func:`~code_aster.Commands.FIN` automatically calls this function.

Objects are reloaded by the function :func:`loadObjects` called just after the
Jeveux database has been reloaded by :func:`~code_aster.Commands.debut.init`
if the ``--continue`` argument is passed.
The command :func:`~code_aster.Commands.debut.POURSUITE` does also the same.
"""

import copyreg
import gc
import os.path as osp
import pickle
import re
import traceback
import types
from enum import IntFlag, auto
from functools import partial
from hashlib import sha256
from io import IOBase

import libaster
import numpy

from ..Objects import DataStructure, DSWithCppPickling, ResultNaming
from ..Utilities import (
    # DEBUG,
    MPI,
    ExecutionParameter,
    Options,
    PETSc,
    SLEPc,
    config,
    disable_fpe,
    get_caller_context,
    logger,
    no_new_attributes,
)

ARGS = "_MARK_DS_ARGS_"
STATE = "_MARK_DS_STATE_"
LIST = "_MARK_LIST_"
DICT = "_MARK_DICT_"
EMBEDDED = "_MARK_EMBEDDED_"


# same values in op9999
class FinalizeOptions(IntFlag):
    """Options for closure.

    - *SaveBase*: The database is saved.
    - *OnlyProc0*: The database is saved only on rank #0.
    - *InfoResu*: Print detailed informations about *Result* objects.
    - *Repack*: Enable repacking process.
    - *Set*: Indicates that options are set (different from the default, 0).
    """

    SaveBase = auto()
    InfoResu = auto()
    Repack = auto()
    OnlyProc0 = auto()
    InfoBase = auto()
    Set = auto()


class Serializer:
    """This class manages 'save & reload' feature.

    Arguments:
        context (dict): The context to be saved or in which the loaded objects
            have to been set.

    Attributes:
        _ctxt (dict): Working context.
        _pick_filename (str): Filename of the pickle file.
        _base (str): Filename of the Jeveux database file.
        _sha_filename (str): Filename containing the SHA of the both previous
            files.
    """

    _sha_filename = "pick.code_aster.sha"
    _pick_filename = "pick.code_aster.objects"
    _info_filename = "pick.code_aster.infos"
    _base = "glob.1"
    _ctxt = None

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, context=None):
        """Initialization
        :param context: context to save or in which loading objects
        :type context: dict
        """
        self._ctxt = context

    @classmethod
    def canRestart(cls, silent=False):
        """Tell if a restart is possible.
        This means that glob & pickled files are consistent.

        Arguments:
            silent (bool): if *True* returns silently, otherwise it raises an exception
                in case of error.

        Returns:
            bool: *True* if the previous execution can be continued.
        """
        log_error = logger.error if not silent else lambda *_: None
        for fname in (cls._base, cls._pick_filename, cls._info_filename, cls._sha_filename):
            if not osp.exists(fname):
                log_error("Can not restart, no such file: %s", fname)
                return False

        sign = read_signature(cls._sha_filename)
        if len(sign) != 3:
            log_error("Invalid sha file: %r", cls._sha_filename)
            return False
        ref_pick, ref_info, ref_base = sign
        sign_pick = file_signature(cls._pick_filename)
        if sign_pick != ref_pick:
            log_error("Current pickled file: %s", sign_pick)
            log_error("Expected signature  : %s", ref_pick)
            log_error("The %r file is not the expected one.", cls._pick_filename)
            return False

        sign_info = file_signature(cls._info_filename)
        if sign_info != ref_info:
            log_error("Current info file : %s", sign_info)
            log_error("Expected signature: %s", ref_info)
            log_error("The %r file is not the expected one.", cls._info_filename)
            return False

        sign_base = file_signature(cls._base, 0, 8000000)
        if sign_base != ref_base:
            log_error("Current base file : %s", sign_base)
            log_error("Expected signature: %s", ref_base)
            log_error("The %r file is not the expected one.", cls._base)
            return False
        return True

    def save(self):
        """Save objects of the context.

        Returns:
            list[str]: List of the names of the DataStructure objects actually
            saved.
        """
        assert self._ctxt is not None, "context is required"
        do_check = ExecutionParameter().option & Options.TestMode
        pyb_instance = DataStructure.mro()[1]
        saved = []
        with open(self._pick_filename, "wb") as pick:
            pickler = AsterPickler(pick)
            logger.info("Saving objects...")
            objList = []
            for name, obj in self._ctxt.items():
                if name == "CO" or obj is logger:
                    continue
                try:
                    logger.info("%-24s %s", name, type(obj))
                    pickler.dump({name: obj})
                    objList.append(name)
                except Exception:
                    logger.warning("object can not be pickled: %s %s", name, type(obj))
                    logger.debug(traceback.format_exc())
                    if (
                        do_check
                        and not hasattr(obj, "__pickling_disabled__")
                        and pyb_instance in type(obj).mro()
                    ):
                        raise
                    continue
                if isinstance(obj, DataStructure):
                    saved.append(name)

        logger.debug("Objects saved: %s", objList)
        with open(self._info_filename, "wb") as pick:
            # add management objects on the stack
            pickle.dump(objList, pick)
            # store state of the objects counter
            pickle.dump(ResultNaming.getCurrentName(), pick)
        return saved

    def sign(self):
        """Sign the saved files and store their SHA signatures."""
        with open(self._sha_filename, "wb") as pick:
            pickler = pickle.Pickler(pick)

            sign_pick = file_signature(self._pick_filename)
            logger.info("Signature of pickled file   : %s", sign_pick)
            sign_info = file_signature(self._info_filename)
            logger.info("Signature of info file      : %s", sign_info)
            sign_base = file_signature(self._base, 0, 8000000)
            logger.info("Signature of Jeveux database: %s", sign_base)

            pickler.dump(sign_pick)
            pickler.dump(sign_info)
            pickler.dump(sign_base)

    def load(self):
        """Load objects into the context."""
        assert self._ctxt is not None, "context is required"
        with open(self._info_filename, "rb") as pick:
            # add management objects on the stack
            objList = pickle.load(pick)
            lastId = int(pickle.load(pick), 16)
        # restore the objects counter
        ResultNaming.initCounter(lastId)

        should_fail = ExecutionParameter().option & Options.StrictUnpickling
        pool = objList[:]
        logger.debug("Objects pool: %s", pool)
        with disable_fpe():
            with open(self._pick_filename, "rb") as pick:
                unpickler = pickle.Unpickler(pick)
                # load all the objects
                names = []
                try:
                    while True:
                        name = pool.pop(0) if pool else None
                        logger.debug("loading: %s...", name)
                        try:
                            record = unpickler.load()
                            key, obj = list(record.items())[0]
                            logger.debug("object restored: %s %s...", key, type(obj))
                            assert key == name, f"expecting {name}, got {key}"
                            self._ctxt.update(record)
                        except Exception as exc:
                            if isinstance(exc, EOFError):
                                raise
                            logger.info(traceback.format_exc())
                            logger.info("can not restore object: %s", name)
                            if should_fail:
                                raise
                            continue
                        logger.info("%-24s %s", name, type(obj))
                        names.append(name)
                except EOFError:
                    pass
                # FIXME this "fix" breaks to many cases, to be reviewed
                # PicklingHelper.reset()

        not_read = set(objList).difference(names)
        if not_read:
            logger.warning("These objects have not been reloaded: %s", tuple(not_read))


def saveObjects(level=1, delete=True, options=0):
    """Save objects of the caller context.

    Arguments:
        level (int): Number of frames to go back to find the user context.
        delete (bool): If *True* the saved objects are deleted from the context.
        options (*FinalizeOptions*): Options for finalization.
    """
    saveObjectsFromContext(get_caller_context(level), delete, options)


def saveObjectsFromContext(context, delete=True, options=0):
    """Save objects of the given context.

    Arguments:
        context (dict): Context to be saved.
        delete (bool): If *True* the saved objects are deleted from the context.
        options (*FinalizeOptions*): Options for finalization.
    """
    gc.collect()
    if not options:
        options = FinalizeOptions.SaveBase
    if options & FinalizeOptions.SaveBase:
        options |= FinalizeOptions.InfoBase
    rank = MPI.ASTER_COMM_WORLD.Get_rank()
    if options & FinalizeOptions.OnlyProc0 and rank != 0:
        logger.info("Objects not saved on processor #%d", rank)
        options = FinalizeOptions.Set

    if options & FinalizeOptions.InfoResu:
        for name, obj in context.items():
            if hasattr(obj, "printInfo"):
                libaster.write("\n ======> " + name)
                obj.printInfo()

    # if ExecutionParameter().option & Options.Debug:
    #     libaster.debugJeveuxContent("Saved jeveux objects:")

    # orig = logger.getEffectiveLevel()
    # logger.setLevel(DEBUG)
    # all procs must be synced to filter context
    context = _filteringContext(context)
    if options & FinalizeOptions.SaveBase:
        pickler = Serializer(context)
        saved = pickler.save()
    else:
        saved = []
        logger.info("No database in results, objects not saved on processor #%d", rank)

    # close Jeveux files (should not be done before pickling)
    libaster.jeveux_finalize(options)
    if options & FinalizeOptions.SaveBase:
        pickler.sign()
    # logger.setLevel(orig)

    if delete:
        # Remove the objects from the context
        for name in saved:
            context[name] = None


def loadObjects(level=1):
    """Load objects from a file in the caller context.

    Arguments:
        level (int): Number of frames to go back to find the user context.
    """
    context = get_caller_context(level)

    # if ExecutionParameter().option & Options.Debug:
    #     libaster.debugJeveuxContent("Reloaded jeveux objects:")
    # orig = logger.getEffectiveLevel()
    # logger.setLevel(DEBUG)
    Serializer(context).load()
    # logger.setLevel(orig)


def contains_datastructure(sequence):
    """Tell if a sequence contains a DataStructure.

    Arguments:
        sequence (*iterable*): List-like object.

    Returns:
        bool: *True* if *sequence* contains a *DataStructure*,
        *False* otherwise.
    """
    for item in sequence:
        if isinstance(item, DataStructure):
            return True
    return False


class PicklingHelper:
    """Adapt pickling of DataStructure objects.

    The objects are identified with their names and are taken from a *cache*
    if an object with the same name already exists.

    See *Dispatch Tables* from the :py:mod:`pickle` documentation.
    """

    memods = {}

    @classmethod
    def reducer(cls, obj):
        use_cpp = isinstance(obj, DSWithCppPickling)
        logger.debug("+ reducing (c++: %s) %s '%s'...", use_cpp, type(obj).__name__, obj.getName())
        initargs = obj.__getinitargs__()
        state = obj.__getstate__()
        if use_cpp:
            initargs = (state,)
            state = None
        logger.debug("- saving %s %s", initargs, getattr(state, "_st", None))
        return partial(cls.builder, obj.__class__, obj.getName()), initargs, state

    @classmethod
    def builder(cls, class_, objName, *args):
        if not cls.memods.get(objName):
            logger.debug("+ constructing %s '%s' with initargs: %s", class_.__name__, objName, args)
            cls.memods[objName] = class_(*args)
        else:
            logger.debug("+ returning %s '%s' from cache", class_.__name__, objName)
        return cls.memods[objName]

    @classmethod
    def reset(cls):
        cls.memods = {}


def subtypes(cls):
    """Return subclasses of 'cls'."""
    types = [cls]
    if not cls:
        return types
    for subclass in cls.__subclasses__():
        types.extend(subtypes(subclass))
    return types


class AsterPickler(pickle.Pickler):
    """Adapt pickling of DataStructure objects.

    In the Python namespace, DataStructures are wrappers on *shared_ptr* through
    *pybind11* instances. So there are several *pointers* for the same instance.
    Standard pickling creates new objects for each *pointers* and during
    unpickling this creates new *pybind11* instance for each Python wrapper.
    To avoid that, the creation of DataStructure is delegated to the
    :py:class:`.PicklingHelper` object.

    See *Dispatch Tables* from the :py:mod:`pickle` documentation.
    """

    dispatch_table = copyreg.dispatch_table.copy()
    for subcl in subtypes(DataStructure):
        dispatch_table[subcl] = PicklingHelper.reducer


def _filteringContext(context):
    """Return a context by filtering the input objects by excluding:
    - modules,
    - code_aster objects,
    - ...

    Arguments:
        context (dict): Context to be filtered.

    Returns:
        dict: New cleaned context.
    """
    # functions to be ignored
    ignored = ("code_aster", "CA", "DETRUIRE", "FIN", "VARIABLE")
    re_system = re.compile("^__.*__$")
    ipython = "__IPYTHON__" in context or "get_ipython" in context
    skipped_classes = []
    if config["ASTER_HAVE_PETSC4PY"]:
        skipped_classes.append(PETSc)
    if config["ASTER_PETSC_HAVE_SLEPC"]:
        skipped_classes.append(SLEPc)
    ctxt = {}
    for name, obj in context.items():
        if not name or name in ignored or re_system.search(name):
            continue
        if getattr(numpy, name, None) is obj:  # see issue29282
            continue
        # skip objects from: PETSc, SLEPc
        if type(obj) in [getattr(klass, type(obj).__name__, None) for klass in skipped_classes]:
            continue
        # check attr needed for python<=3.6
        if hasattr(obj, "__class__") and isinstance(obj, (IOBase, MPI.Intracomm, re.Match)):
            continue
        if hasattr(obj, "__pickling_disabled__"):
            continue
        if ipython and name in ("_", "__", "___", "_ih", "_oh", "_dh", "In", "Out", "exit", "quit"):
            continue
        if type(obj) in (
            types.ModuleType,
            type,
            types.MethodType,
            types.FunctionType,
            types.BuiltinMethodType,
            types.BuiltinFunctionType,
            partial,
        ):
            continue
        ctxt[name] = obj
    return ctxt


def read_signature(sha_file):
    """Read the signatures from the file containing the SHA strings.

    Arguments:
        sha_file (str): Filename of the pickled file to read.

    Returns:
        list[str]: List of the two signatures as SHA256 strings that identify
            the pickled file and the (first) Jeveux database file.
    """
    sign = []
    try:
        with open(sha_file, "rb") as pick:
            sign.append(pickle.Unpickler(pick).load())
            sign.append(pickle.Unpickler(pick).load())
            sign.append(pickle.Unpickler(pick).load())
    except Exception:
        traceback.print_exc()
    logger.debug("pickled signatures: %s", sign)
    return sign


def file_signature(filename, offset=0, bufsize=-1):
    """Compute a signature of the file.

    Arguments:
        filename (str): File to sign.
        offset (int): Offset before reading content (default to 0).
        bufsize (int): Size of the content to read (default to -1, content is
            read up to EOF).

    Returns:
        str: Signature as SHA256 string to identify the file.
    """
    if not osp.isfile(filename):
        return "no such file"
    try:
        with open(filename, "rb") as fobj:
            fobj.seek(offset, 0)
            sign = sha256(fobj.read(bufsize)).hexdigest()
    except Exception:
        traceback.print_exc()
    return sign
