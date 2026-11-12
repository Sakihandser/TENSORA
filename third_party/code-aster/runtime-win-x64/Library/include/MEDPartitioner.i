// Copyright (C) 2007-2026  CEA, EDF
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 2.1 of the License, or (at your option) any later version.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
//
// See http://www.salome-platform.org/ or email : webmaster.salome@opencascade.com
//

%module MEDPartitioner

%header %{
/* SWIG >= 4.3 dropped Python 2 support and no longer emits the Python 2
   C-API aliases that the MEDCoupling typemaps rely on. Re-define them here
   exactly as SWIG used to, so the generated wrappers keep compiling. */
#include <Python.h>
#ifndef PyInt_Check
#define PyInt_Check(x) PyLong_Check(x)
#define PyInt_AsLong(x) PyLong_AsLong(x)
#define PyInt_FromLong(x) PyLong_FromLong(x)
#define PyInt_FromSize_t(x) PyLong_FromSize_t(x)
#define PyString_Check(name) PyBytes_Check(name)
#define PyString_FromString(x) PyUnicode_FromString(x)
#define PyString_Format(fmt, args) PyUnicode_Format(fmt, args)
#define PyString_AsString(str) PyBytes_AsString(str)
#define PyString_Size(str) PyBytes_Size(str)
#define PyString_InternFromString(key) PyUnicode_InternFromString(key)
#endif
#ifndef PyInt_AS_LONG
#define PyInt_AS_LONG PyLong_AS_LONG
#endif
%}

%{
#include "MEDFileData.hxx"

using namespace MEDCoupling;
using namespace INTERP_KERNEL;
%}

%include std_string.i

%feature("autodoc", "1");
%feature("docstring");

%feature("unref") MEDCoupling::MEDFileData "$this->decrRef();"

%nodefaultctor;

%rename (InterpKernelException) INTERP_KERNEL::Exception;

%include "MEDPartitionerCommon.i"
