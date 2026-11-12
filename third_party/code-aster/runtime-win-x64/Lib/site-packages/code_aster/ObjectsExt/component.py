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

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

import warnings

import numpy as np
import numpy.ma as ma

from ..Utilities import disable_fpe, force_list, logger, no_new_attributes
from ..Utilities.mpi_utils import mpi_max, mpi_min, mpi_sum, useHPCMode


class OnCellsDescription:
    """Internal description of a component.

    Args:
        parent (*SimpleFieldOnCells*): Parent field object.
        indexes (ndarray[int]): Indexes in *values* by cells and points on cells.
        discr (ndarray[int]): Local dicretization: number of points and subpoints
            by cell.
        inner (ndarray[bool], optional): Indicator for inner cells
            (only pass for restricted object).
    """

    _parent = _idx = _discr = _cells = _nbcells = _nbval = _sign = None
    _inner = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, parent, indexes, discr, inner=None):
        self._parent = parent  # parent SimpleFieldOnCells
        self._idx = indexes
        self._discr = discr
        self._cells = None
        # number of cells in this object before restriction
        self._nbcells = indexes.shape[0]
        # number of values stored for the component before any restriction
        self._nbval = None
        # mask for inner cells (applied on '_cells')
        if inner is not None:
            self._inner = inner
        elif useHPCMode():
            self._inner = np.zeros(self._nbcells, dtype=bool)
            self._inner[parent.getMesh().getInnerCells()] = True
        else:
            self._inner = np.ones(self._nbcells, dtype=bool)
        self._sign = None

    def __sizeof__(self):
        """Return the size of the data in bytes."""
        # for sys.getsizeof(obj)
        return self.sizeof()

    def sizeof(self):
        """Return the size of the data in bytes."""
        return (
            self._idx.nbytes
            + self._discr.nbytes
            + self._inner.nbytes
            + (self._cells.nbytes if self._cells is not None else 0)
        )

    def setValuesShape(self, shape):
        """Register shape of values if needed."""
        if self._nbval is None:
            self._nbval = shape[0]

    @property
    def sign(self):
        """int: Attribute that holds the signature of the description."""
        if self._sign is None:
            self._sign = (self._idx.ravel() * np.arange(self._idx.size)).sum()
        return self._sign

    def __repr__(self):
        idx = self._idx[self._idx >= 0]
        if len(idx) == 0:
            idx = np.zeros(1, dtype=int)
        lines = [
            f"- indexes shape {self._idx.shape!r}, range {idx.min()} to {idx.max()}, "
            f"{len(idx)} indexes defined"
        ]
        nbinn = self._inner.sum()
        if self._cells is None:
            lines.append(f"- on all the {self._nbcells} cells, {nbinn} inner")
        else:
            limit = 20
            ndef = len(self._cells)
            lines.append(
                f"- on {ndef}/{self._nbcells} cells ({nbinn} inner): "
                + f"{tuple(self._cells[:limit])}"
                + ("..." if ndef > limit else "")
            )
        uniq, numb = np.unique(self._discr, return_counts=True, axis=0)
        nbv = (uniq.prod(axis=1) * numb).sum()
        discr = [f"{n}x{tuple(d)}" for n, d in zip(numb, uniq)]
        lines.append(
            f"- {len(self._discr)} points/subpoints defs: " + ", ".join(discr) + f", {nbv} values"
        )
        max = self._idx.max(axis=1)
        undef = max[max < 0]
        nundef = undef.shape[0]
        nb = self._idx.shape[0]
        lines.append(f"- {nb-nundef}/{nb} cells with values")
        return "\n".join(lines)

    def copy(self):
        """Copy of the current description.

        Returns:
            *Decription*: copy of the current description.
        """
        new = self.__class__(self._parent, self._idx.copy(), self._discr.copy(), self._inner.copy())
        new._cells = None if self._cells is None else self._cells.copy()
        new._nbcells = self._nbcells
        new._nbval = self._nbval
        new._sign = self._sign
        return new

    # MPI may be empty
    def restrict(self, cells_ids):
        """Restrict the description on given cells.

        Args:
            cells_ids (list[int]): sublist of the existing cells.

        Returns:
            ndarray[int]: Indexes restricted on the cells list.
        """
        assert self._cells is None, "must be expanded first"
        if isinstance(cells_ids, int):
            cells_ids = force_list(cells_ids)
        self._idx = self._idx[cells_ids]
        idx = self._idx.ravel()
        idx = idx[idx >= 0]
        self._discr = self._discr[cells_ids]
        self._cells = np.array(cells_ids, dtype=int)
        self._inner = self._inner[cells_ids]
        self._sign = None
        return idx

    def expanded_values(self, values):
        """Expands the vector of values.

        Args:
            values (ndarray): Vector of values, consistent with idx.

        Returns:
            ndarray: Vector of values on all cells (extended with 0.)
        """
        if self._cells is not None:
            values_in = values
            values = np.zeros(self._nbval, dtype=float)
            idx = self._idx[self._idx >= 0]
            values[idx] = values_in
        return values

    def inner_values(self, values):
        """Returns the vector of inner values.

        Args:
            values (ndarray): Vector of values, consistent with idx.

        Returns:
            ndarray: Vector of values on inner cells.
        """
        values = self.expanded_values(values)
        idx = self._idx[self._inner].ravel()
        idx = idx[idx >= 0]
        return values[idx]

    def expand(self, values):
        """Expand the description to the initial shape.

        Args:
            values (ndarray[float]): values to be accordingly expanded.

        Returns:
            *Description*: expanded description.
        """
        idx = self._idx
        idx = idx[idx >= 0]
        new_values = ma.zeros(self._nbval, dtype=float)
        new_values[idx] = values
        new_idx = np.ones((self._nbcells, self._idx.shape[1]), dtype=int) * -1
        new_idx[self._cells] = self._idx
        new_discr = np.zeros((self._nbcells, 2), dtype=int)
        new_discr[self._cells] = self._discr
        return new_values, OnCellsDescription(self._parent, new_idx, new_discr)


class OnNodesDescription:
    """Internal description of a component.

    Args:
        parent (*SimpleFieldOnNodes*): Parent field object.
        inner (ndarray[bool], optional): Indicator for inner nodes
            (only pass for restricted object).
    """

    _parent = _nodes = _nbnodes = _nbval = _sign = None
    _inner_c = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, parent, inner=None):
        self._parent = parent  # parent SimpleFieldOnCells
        self._nodes = None
        # number of nodes in this object before restriction
        self._nbnodes = None
        # number of values stored for the component before any restriction
        self._nbval = None
        # mask for inner nodes (applied on '_nodes')
        self._inner_c = inner
        self._sign = None

    @property
    def _inner(self):
        """ndarray: delayed initialization, waiting for the size of values"""
        if self._inner_c is None:
            if useHPCMode():
                self._inner_c = np.zeros(self._nbnodes, dtype=bool)
                self._inner[self._parent.getMesh().getInnerNodes()] = True
            else:
                self._inner_c = np.ones(self._nbnodes, dtype=bool)
        return self._inner_c

    def __sizeof__(self):
        """Return the size of the data in bytes."""
        # for sys.getsizeof(obj)
        return self.sizeof()

    def sizeof(self):
        """Return the size of the data in bytes."""
        return self._inner.nbytes + (self._nodes.nbytes if self._nodes is not None else 0)

    def setValuesShape(self, shape):
        """Register shape of values if needed."""
        if self._nbval is None:
            self._nbval = self._nbnodes = shape[0]

    @property
    def sign(self):
        """int: Attribute that holds the signature of the description."""
        if self._sign is None:
            self._sign = self._nbval
        return self._sign

    def __repr__(self):
        lines = []
        nbinn = self._inner.sum()
        if self._nodes is None:
            lines.append(f"- on all the {self._nbnodes} nodes, {nbinn} inner")
        else:
            limit = 20
            ndef = len(self._nodes)
            lines.append(
                f"- on {ndef}/{self._nbnodes} nodes ({nbinn} inner): "
                + f"{tuple(self._nodes[:limit])}"
                + ("..." if ndef > limit else "")
            )
        # lines.append(f"- {nb-nundef}/{nb} nodes with values")
        return "\n".join(lines)

    def copy(self):
        """Copy of the current description.

        Returns:
            *Decription*: copy of the current description.
        """
        new = self.__class__(self._parent, self._inner.copy())
        new._nodes = None if self._nodes is None else self._nodes.copy()
        new._nbnodes = self._nbnodes
        new._nbval = self._nbval
        new._sign = self._sign
        return new

    # MPI may be empty
    def restrict(self, nodes_ids):
        """Restrict the description on given nodes.

        Args:
            nodes_ids (list[int]): sublist of the existing nodes.

        Returns:
            ndarray[int]: Indexes restricted on the nodes list.
        """
        assert self._nodes is None, "must be expanded first"
        if isinstance(nodes_ids, int):
            nodes_ids = force_list(nodes_ids)
        self._nodes = np.array(nodes_ids, dtype=int)
        self._inner_c = self._inner[nodes_ids]
        self._sign = None
        return nodes_ids

    def expanded_values(self, values):
        """Expands the vector of values.

        Args:
            values (ndarray): Vector of values, consistent with the current nodes ids.

        Returns:
            ndarray: Vector of values on all nodes (extended with 0.)
        """
        if self._nodes is not None:
            values_in = values
            values = np.zeros(self._nbval, dtype=float)
            values[self._nodes] = values_in
        return values

    def inner_values(self, values):
        """Returns the vector of inner values.

        Args:
            values (ndarray): Vector of values, consistent with the current nodes ids.

        Returns:
            ndarray: Vector of values on inner nodes.
        """
        values = self.expanded_values(values)
        idx = self._nodes
        if self._nodes is None:
            return values[self._inner]
        idx = self._nodes[self._inner]
        return values[idx]

    def expand(self, values):
        """Expand the description to the initial shape.

        Args:
            values (ndarray[float]): values to be accordingly expanded.

        Returns:
            *Description*: expanded description.
        """
        idx = self._nodes
        new_values = ma.zeros(self._nbval, dtype=float)
        new_values[idx] = values
        return new_values, OnNodesDescription(self._parent)


class Component:
    r"""Abstract component of a field on cells or on nodes.

    Args:
        values (ndarray[float]): Values of the component,
            dimension \Sum_i(nbpts_i * nbcmp_i).
        descr (*Description*): Description of the component.
    """

    Description = None
    _values = _descr = _sign = restr = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, values, description):
        self.init_from(values, description)

    def init_from(self, values, description):
        """Initialize content."""
        assert isinstance(values, ma.MaskedArray)
        self._values = values
        self._descr = description
        self._descr.setValuesShape(values.shape)
        self._sign = None

    def copy(self):
        """Return a copy of the component."""
        return self.__class__(self._values.copy(), self._descr.copy())

    def __sizeof__(self):
        """Return the size of the data in bytes."""
        # for sys.getsizeof(obj)
        return self.sizeof()

    @mpi_sum(hpc=True)
    def sizeof(self):
        """Return the size of the data in bytes."""
        return self._values.nbytes + self._descr.sizeof()

    @property
    def innerValues(self):
        """ndarray[float]: Vector of local values (its shape is inconsistent
        with the internal description)."""
        return self._descr.inner_values(self._values)

    @property
    def values(self):
        """ndarray[float]: Vector of values."""
        return self._values

    @values.setter
    def values(self, values):
        """Set the vector values (components values that are not expected
        are forced to 0.).

        Args:
            values (ndarray[float]): New values.
        """
        if isinstance(values, float):
            values = np.full(self._values.shape, values, dtype=float)
        assert values.shape == self._values.shape
        if not isinstance(values, ma.MaskedArray):
            values = ma.array(values, mask=self._values.mask)
        self._values = values

    @property
    @mpi_sum(hpc=True)
    def size(self):
        """Return the number of values of the component."""
        return len(self.innerValues)

    def __repr__(self):
        lines = repr(self._values.data).splitlines()
        if len(lines) > 6:
            lines = lines[:3] + ["..."] + lines[-3:]
        lines.insert(
            0, f"- {len(self._values.data)} values in vector ({self._values.count()} non-masked):"
        )
        lines.append(repr(self._descr))
        return "\n".join(lines)

    def _check_consistency(self, other):
        """Check consistency between the both signatures. A float is returned as is."""
        if isinstance(other, self.__class__):
            if self.sign != other.sign:
                logger.warning("lhs: %s", repr(self))
                logger.warning("rhs: %s", repr(other))
                raise IndexError("inconsistent shapes")
            other = other._values
        return other

    def apply(self, func):
        """Apply a function of the values."""
        if not isinstance(func, np.ufunc):
            func = np.vectorize(func)
        return self.__class__(func(self._values), self._descr.copy())

    def applyOnArray(self, func):
        """Apply a function of the array of values."""
        return self.__class__(func(self._values), self._descr.copy())

    def __iadd__(self, other):
        other = self._check_consistency(other)
        self._values += other
        return self

    def __add__(self, other):
        other = self._check_consistency(other)
        return self.__class__(self._values + other, self._descr.copy())

    def __radd__(self, other):
        return self + other

    def __isub__(self, other):
        other = self._check_consistency(other)
        self._values -= other
        return self

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return -self + other

    def __neg__(self):
        return self.__class__(-self._values, self._descr.copy())

    def __imul__(self, other):
        other = self._check_consistency(other)
        self._values *= other
        return self

    def __mul__(self, other):
        other = self._check_consistency(other)
        return self.__class__(self._values * other, self._descr.copy())

    def __rmul__(self, other):
        return self * other

    def __itruediv__(self, other):
        other = self._check_consistency(other)
        if np.any(other == 0.0):
            raise ZeroDivisionError()
        with disable_fpe():
            self._values /= other
        return self

    def __truediv__(self, other):
        other = self._check_consistency(other)
        if np.any(other == 0.0):
            raise ZeroDivisionError()
        with disable_fpe():
            values = self._values / other
        return self.__class__(values, self._descr.copy())

    def __rtruediv__(self, other):
        if np.any(self._values == 0.0):
            raise ZeroDivisionError()
        with disable_fpe():
            values = 1.0 / self._values
        return self.__class__(values * other, self._descr.copy())

    def __abs__(self):
        return self.__class__(np.abs(self._values), self._descr.copy())

    def __ipow__(self, other):
        other = self._check_consistency(other)
        self._values **= other
        return self

    def __pow__(self, other):
        other = self._check_consistency(other)
        return self.__class__(np.power(self._values, other), self._descr.copy())

    @mpi_min(hpc=True)
    def min(self):
        """Return the minimum value.

        Returns:
            float: minimum of the values.
        """
        return self.innerValues.min()

    @mpi_max(hpc=True)
    def max(self):
        """Return the maximum value.

        Returns:
            float: maximum of the values.
        """
        return self.innerValues.max()

    @mpi_sum(hpc=True)
    def sum(self):
        """Return the sum of the values.

        Returns:
            float: sum of the values.
        """
        return self.innerValues.sum()

    def mean(self):
        """Return the mean value.

        Returns:
            float: mean of the values.
        """
        if len(self.innerValues) == 0:
            return 0.0
        return self.innerValues.mean()

    def minimum(self, other):
        """Compare the component with another one and keep the element-wise minima.

        Args:
            other (*Component*): Another component.
        """
        other = self._check_consistency(other)
        self._values = np.minimum(self._values, other)

    def maximum(self, other):
        """Compare the component with another one and keep the element-wise maxima.

        Args:
            other (*Component*): Another component.
        """
        other = self._check_consistency(other)
        self._values = np.maximum(self._values, other)

    @property
    def sign(self):
        """int: Attribute that holds the signature of the component."""
        if self._sign is None:
            self._sign = self._descr.sign + len(self._values)
        return self._sign

    # @DebugArgs.pickle_on_error
    def restrict(self, ids):
        """Restrict the component on given cells/nodes.

        Args:
            cells_ids (list[int]): Cells ids to be used.
        """
        if self.restr is not None:
            exp = self.expand()
            self.init_from(exp._values, exp._descr)
        idx = self._descr.restrict(ids)
        self._values = self._values[idx]
        self._sign = None

    # @DebugArgs.pickle_on_error
    def expand(self):
        """Expand the component by adding 0. where it not defined.

        Returns:
            *Component*: expanded component.
        """
        if self.restr is None:
            return self.copy()
        return self.__class__(*self._descr.expand(self._values))

    # @DebugArgs.pickle_on_error
    def onSupportOf(self, other, strict=False):
        """Move the component onto the same support of another.

        NB: The both components must be defined on the same cells/nodes.

        Args:
            other (*Component*): Use the support of this component.
            strict (bool): If *True* it raises an *IndexError* exception if
                the component is not defined on the support of `other`.
                By default, it is *True* and the values are expanded with 0.0.

        Returns:
            *Component*: A new component.
        """
        if self.restr is None and other.restr is not None:
            changed = self.onSupportOf(other.expand())
            changed.restrict(other.restr)
            return changed
        if self.restr is not None and other.restr is None:
            return self.expand().onSupportOf(other)
        if self.restr is not None:
            if np.any(self.restr != other.restr):
                raise IndexError("components must be defined on the same cells")
            return self.expand().onSupportOf(other)
        return self._on_support_of(other, strict)


class ComponentOnNodes(Component):
    r"""Represents the values of a component of a field on nodes.

    The input arrays will not be modified. The caller should not change them
    during the existence of the *Component* object.

    Use *in place* operators (`+=`, `*=`...) when possible for performance reasons.

    Args:
        values (ndarray[float]): Values of the component,
            dimension \Sum_i(nbpts_i * nbcmp_i).
        descr (*Description*): Description of the component.
    """

    Description = OnNodesDescription

    @property
    def restr(self):
        return self._descr._nodes

    def getNodes(self):
        """Return the nodes id."""
        if self.restr is None:
            return np.arange(self._descr._nbnodes)
        return self.restr

    def getNumberOfNodes(self):
        """Return the total number of nodes (even if the current component is
        currently restricted).

        Returns:
            int: Number of nodes the field is defined on.
        """
        return self._descr._nbnodes

    # TODO
    def plot_descr(self, filename=None):
        """Plot the description of values by nodes.

        A matplotlib GUI backend should be enabled, for example with:
        ``matplotlib.use("TkAgg")``.

        Args:
            filename (str|Path, optional): Save the image to this file if provided.
                Otherwise plot interactively the figure.

        Returns:
            bool: *True* if the plot was done, *False* otherwise.
        """
        return False

    def filterByValues(self, mini, maxi, strict_mini=True, strict_maxi=True):
        """Returns the nodes ids where at least one value of the node is in
        the interval.

        Args:
            mini (float): minimum value.
            maxi (float): maximum value.
            strict_mini (bool): Use strict comparison (the default) for the minimum.
            strict_maxi (bool): Use strict comparison (the default) for the maximum.

        Returns:
            list[int]: Nodes ids.
        """
        if self.restr is not None:
            nodes = self.expand().filterByValues(mini, maxi, strict_mini, strict_maxi)
            return list(set(self.restr).intersection(nodes))
        if strict_mini:
            filter = mini < self._values
        else:
            filter = mini <= self._values
        if strict_maxi:
            filter &= self._values < maxi
        else:
            filter &= self._values <= maxi

        filter &= self._descr._inner
        nodes = list(np.arange(self.getNumberOfNodes(), dtype=int)[filter])
        return nodes

    def _on_support_of(self, other, strict):
        """internally called on expanded components"""
        assert self._descr._nbnodes == other._descr._nbnodes, (
            self._descr._nbnodes == other._descr._nbnodes
        )
        assert self.restr is None and other.restr is None, (self.restr, other.restr)
        assert self._values.shape == other._values.shape
        undef = np.logical_not(self._values.mask | other._values.mask)
        if strict and np.any(undef):
            raise IndexError("no value on all the support")
        new = other.copy()
        new._values = ma.array(self._values, mask=other._values.mask, dtype=float)
        self._sign = None
        return new


class ComponentOnCells(Component):
    r"""Represents the values of a component of a field on cells.

    The input arrays will not be modified. The caller should not change them
    during the existence of the *ComponentOnCells* object.

    Use *in place* operators (`+=`, `*=`...) when possible for performance reasons.

    Args:
        values (ndarray[float]): Values of the component,
            dimension \Sum_i(nbpts_i * nbcmp_i).
        descr (*Description*): Description of the component.
    """

    Description = OnCellsDescription
    # WARNING: _idx must be used to access values only on a not restricted component.
    # '_discr' is not used but interesting in `Description.__repr__`.

    @property
    def _idx(self):
        return self._descr._idx

    @property
    def restr(self):
        return self._descr._cells

    def getValuesByCells(self):
        """Returns the values by cells, expanded by 0.0 where undefined."""
        if self.restr is not None:
            return self.expand().getValuesByCells()[self.restr]
        values = np.append(self.values, [0.0])
        return np.take(values, self._idx)

    def getCells(self):
        """Return the cells id."""
        if self.restr is None:
            return np.arange(self._descr._nbcells)
        return self.restr

    def getNumberOfCells(self):
        """Return the total number of cells (even if the current component is
        currently restricted).

        Returns:
            int: Number of cells the field is defined on.
        """
        return self._descr._nbcells

    def plot_descr(self, filename=None):
        """Plot the description of values by cells.

        A matplotlib GUI backend should be enabled, for example with:
        ``matplotlib.use("TkAgg")``.

        Args:
            filename (str|Path, optional): Save the image to this file if provided.
                Otherwise plot interactively the figure.

        Returns:
            bool: *True* if the plot was done, *False* otherwise.
        """
        if not HAS_MATPLOTLIB:
            warnings.warn("matplotlib is not available")
            return False
        if self.restr is not None:
            return self.expand().plot_descr(filename)

        idx = np.where(self._idx >= 0, 1, 0)
        # undef = np.where(self._descr._mask[self._idx] == False, -2, 0)
        undef = np.where(self._values.mask[self._idx], -2, 0)
        idx = np.where(undef == 0, idx, undef * idx)
        fig, ax = plt.subplots()
        ax.grid(True, linestyle="--")
        ax.set_xlabel("numbers of points")
        ax.set_ylabel("cells id")
        cmap = ListedColormap([(0.6, 0.6, 0.6), "white", (0.0, 0.4, 0.8)], "indexed")
        plt.imshow(idx, interpolation="nearest", cmap=cmap, aspect="auto", vmin=-1, vmax=1)
        if filename:
            plt.savefig(filename)
        else:
            plt.show()
        return True

    def filterByValues(self, mini, maxi, strict_mini=True, strict_maxi=True):
        """Returns the cells ids where at least one value of the cell is in
        the interval.

        Args:
            mini (float): minimum value.
            maxi (float): maximum value.
            strict_mini (bool): Use strict comparison (the default) for the minimum.
            strict_maxi (bool): Use strict comparison (the default) for the maximum.

        Returns:
            list[int]: Cells ids.
        """
        if self.restr is not None:
            cells = self.expand().filterByValues(mini, maxi, strict_mini, strict_maxi)
            return list(set(self.restr).intersection(cells))
        if strict_mini:
            filter = mini < self._values
        else:
            filter = mini <= self._values
        if strict_maxi:
            filter &= self._values < maxi
        else:
            filter &= self._values <= maxi

        filter = np.append(filter, [False])  # not defined (-1): not in interval...
        # idx = np.where(self._descr._mask[self._idx] == False, -1, self._idx)  # or masked
        idx = np.where(self._values.mask, -1, self._idx)  # or masked
        idx_filt = filter[idx]
        cells_filt = idx_filt.max(axis=1)
        cells_filt &= self._descr._inner
        cells = list(np.arange(self.getNumberOfCells(), dtype=int)[cells_filt])
        return cells

    def _on_support_of(self, other, strict):
        """internally called on expanded components"""
        assert self._descr._nbcells == other._descr._nbcells, (
            self._descr._nbcells == other._descr._nbcells
        )
        assert self.restr is None and other.restr is None, (self.restr, other.restr)
        nbc0, nbp0 = self._idx.shape
        nbco, nbpo = other._idx.shape
        assert nbc0 == nbco == self._descr._nbcells
        bools = other._idx >= 0
        idx = other._idx[bools]
        bself = np.zeros((nbc0, nbp0), dtype=bool)
        if nbp0 > nbpo:
            bself[:nbco, :nbpo] = bools
        else:
            bself = bools[:nbc0, :nbp0]
        keep = self._idx[bself]
        if strict and np.any(keep < 0):
            raise IndexError("no value on all the support")
        if nbp0 < nbpo:
            keep = np.append(keep, np.ones(nbpo - nbp0, dtype=int) * -1)
        prol = np.append(self._values, [0.0])
        new = other.copy()
        new._values[idx] = np.take(prol, keep)
        new._descr._idx = other._idx.copy()
        self._sign = None
        return new
