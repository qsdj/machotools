import os
import re
import stat

import macholib

from macholib import mach_o

from machotools.common import _change_command_data_inplace, _find_lc_dylib_command
from machotools.utils import rstrip_null_bytes, safe_update

def _find_specific_lc_load_dylib(header, dependency_pattern):
    for index, (load_command, dylib_command, data) in \
            _find_lc_dylib_command(header, mach_o.LC_LOAD_DYLIB):
        m = dependency_pattern.search(rstrip_null_bytes(data))
        if m:
            return index, (load_command, dylib_command, data)

def _change_dependency_command(header, old_dependency_pattern, new_dependency):
    old_command = _find_specific_lc_load_dylib(header, old_dependency_pattern)
    if old_command is None:
        return
    command_index, command_tuple = old_command
    _change_command_data_inplace(header, command_index, command_tuple, new_dependency)

def dependencies(filename):
    """Returns the list of mach-o the given binary depends on.

    Parameters
    ----------
    filename: str
        Path to the mach-o to query

    Returns
    -------
    dependency_names: seq
        dependency_names[i] is the list of dependencies for the i-th header.
    """
    ret = []

    m = macholib.MachO.MachO(filename)
    for header in m.headers:
        this_ret = []
        for load_command, dylib_command, data in header.commands:
            if load_command.cmd == mach_o.LC_LOAD_DYLIB:
                this_ret.append(rstrip_null_bytes(data))
        ret.append(this_ret)
    return ret

def change_dependency(filename, old_dependency_pattern, new_dependency):
    """Change the install name of a mach-o dylib file.

    For a multi-arch binary, every header is overwritten to the same install
    name

    Parameters
    ----------
    filename: str
        Path to the mach-o file to modify
    new_install_name: str
        New install name
    """
    _r_old_dependency = re.compile(old_dependency_pattern)
    m = macholib.MachO.MachO(filename)
    for header in m.headers:
        _change_dependency_command(header, _r_old_dependency, new_dependency)

    def writer(f):
        for header in m.headers:
            f.seek(0)
            header.write(f)
    mode = stat.S_IMODE(os.stat(filename).st_mode)
    safe_update(filename, writer, "wb")
    os.chmod(filename, mode)
