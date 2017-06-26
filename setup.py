# 
# Copyright 2017, Technische Universitaet Dresden, Germany, all rights reserved.
# Author: Andreas Gocht
#  
# Permission to use, copy, modify, and distribute this Python software and
# its associated documentation for any purpose without fee is hereby
# granted, provided that the above copyright notice appears in all copies,
# and that both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of TU Dresden is not used in
# advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.


from distutils.core import setup, Extension
from distutils.command.install import install
import distutils.ccompiler

import os
import subprocess
import re
import sys
import stat
import platform
import functools

"""
return a tuple with (returncode,stdout) from the call to subprocess
"""
def call(arguments):
    result = ()
    if sys.version_info > (3,5):
        out = subprocess.run(arguments,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        result = (out.returncode, out.stdout.decode("utf-8"))
    else:
        p = subprocess.Popen(arguments,stdout=subprocess.PIPE,stderr=None)
        stdout, _ = p.communicate()
        p.wait()
        result = (p.returncode,stdout)
    return result
         

scorep_config = ["scorep-config","--nocompiler", "--user", "--thread=pthread", "--mpp=none"]
scorep_config_mpi = ["scorep-config","--nocompiler", "--user", "--thread=pthread", "--mpp=mpi"]

def get_config(scorep_config):
    (retrun_code, _) = call(scorep_config + ["--cuda"])
    if retrun_code == 0:
        scorep_config.append("--cuda")
        print("Cuda is supported, building with cuda")
    else:
        print("Cuda is not supported, building without cuda")
        scorep_config.append("--nocuda")
        
    (retrun_code, _) = call(scorep_config + ["--opencl"])
    if retrun_code == 0:
        scorep_config.append("--opencl")
        print("OpenCL is supported, building with OpenCL")
    else:
        print("OpenCl is not supported, building without OpenCL")
        scorep_config.append("--noopencl")
                  
    
    (_, ldflags) = call(scorep_config + ["--ldflags"])
    (_, libs)    = call(scorep_config + ["--libs"])
    (_, mgmt_libs)    = call(scorep_config + ["--mgmt-libs"])
    (_, cflags)  = call(scorep_config + ["--cflags"])
     
    (_, scorep_adapter_init) = call(scorep_config + ["--adapter-init"])
     
    libs = libs + " " + mgmt_libs

    lib_dir = re.findall(" -L[/+-@.\w]*",ldflags)
    lib     = re.findall(" -l[/+-@.\w]*",libs)
    include = re.findall(" -I[/+-@.\w]*",cflags)
    macro   = re.findall(" -D[/+-@.\w]*",cflags)
    linker_flags = re.findall(" -Wl[/+-@.\w]*",ldflags)
    
    remove_flag3 = lambda x: x[3:]
    remove_space1 = lambda x: x[1:]
    
    lib_dir      = list(map(remove_flag3, lib_dir))
    lib          = list(map(remove_flag3, lib))
    include      = list(map(remove_flag3, include))
    macro        = list(map(remove_flag3, macro))
    linker_flags = list(map(remove_space1, linker_flags)) 
    
    macro   = list(map(lambda x: tuple([x,1]), macro))
    
    return (include, lib, lib_dir, macro, linker_flags, scorep_adapter_init)

(include, lib, lib_dir, macro, linker_flags, scorep_adapter_init) = get_config(scorep_config)
(include_mpi, lib_mpi, lib_dir_mpi, macro_mpi, linker_flags_mpi, scorep_adapter_init_mpi) = get_config(scorep_config_mpi)

with open("./scorep_init.c","w") as f:
    f.write(scorep_adapter_init)
    
with open("./scorep_init_mpi.c","w") as f:
    f.write(scorep_adapter_init_mpi)

## black magic to find prefix
# Setup the default install prefix
prefix = sys.prefix

# Get the install prefix if one is specified from the command line
for arg in sys.argv:
    if arg.startswith('--prefix='):
        prefix = arg[9:]
        prefix = os.path.expandvars(prefix)


# build scorep with mpi for ld_prealod
cc = distutils.ccompiler.new_compiler()
cc.compile(["./scorep_init_mpi.c"])
cc.link("scorep_init_mpi",objects = ["./scorep_init_mpi.o"],output_filename = "./libscorep_init_mpi.so",\
        library_dirs = lib_dir_mpi, libraries = lib_mpi)

module1 = Extension('_scorep',
                    include_dirs = include,
                    libraries = lib,
                    library_dirs = lib_dir,
                    define_macros = macro,
                    extra_link_args = linker_flags,
                    sources = ['scorep.c','scorep_init.c'])

module2 = Extension('_scorep_mpi',
                    include_dirs = include_mpi,
                    libraries = lib_mpi + ["scorep_init_mpi"],
                    library_dirs = lib_dir_mpi + ["./"],
                    runtime_library_dirs = ["{}/lib/".format(prefix)],
                    define_macros = macro_mpi + [("USE_MPI",None)],
                    extra_link_args = linker_flags_mpi, 
                    sources = ['scorep.c'])


## modify scorep.py for a shebang with the right python version
# fix python interpreter 
# from https://stackoverflow.com/a/17099342
def fix_shebang(file_path, python_version):
    print("fix python version")
    # accept array of python version from platform.python_version_tuple()
    sed = "sed -i 's/#!.*\/usr\/bin\/.*python.*$/#!\/usr\/bin\/env python{}\.{}/'"\
            .format(python_version[0], python_version[1])
    # bring command together with file path
    cmd = ' '.join([sed, file_path])
    # execute the sed command and replace in place
    os.system(cmd)

# Get current Python version
fix_shebang_curr = functools.partial(fix_shebang, python_version=platform.python_version_tuple())

# add execution rights to file
def add_exec(file_path):
    print("change permissions")
    # change Permission with bitwies or and the constants from stat modul
    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR|  stat.S_IXUSR | \
            stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

# custom class for additional install instructions
class my_install(install):
    # Dict with a filename and the function that should be executed 
    # upon the matching files
    # function must have only one parameter, the file path
    files_and_commands = {'scorep.py' : (fix_shebang_curr, add_exec)}

    def run(self):
        # standard install routine
        install.run(self)
        # get all installed files
        install_files = self.get_outputs()

        ## Parse dictionary
        # first loop over all key of the dict
        for key in self.files_and_commands.keys():
            # find matching pathes in the list with the installed files
            matching_files = list(filter(lambda x: key in x, install_files))
            # loop over all matching files
            for files in matching_files:
                # and over the file operations
                for function in self.files_and_commands[key]:
                    # apply file operations
                    function(files)


setup (
    name = 'scorep',
    version = '0.5',
    description = 'This is a scorep tracing package',
    author = 'Andreas Gocht',
    author_email = 'andreas.gocht@tu-dresden.de',
    url = '',
    long_description = '''
This package allows taring of python code using Score-P]

The Package just uses Score-P user regions.

Differnend python theads are not differentiated, but using MPI should work (not tested).

This module is more or less similar to the python trace module. 
''',
    py_modules = ['scorep'],
    # Eggsecutable?
    data_files = [("lib",["libscorep_init_mpi.so"])],
    ext_modules = [module1,module2],
    cmdclass={'install': my_install}
)

