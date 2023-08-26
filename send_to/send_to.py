"""
This project aids in the creation of scripts that organize files, passed to it
as arguments. The scripts can be placed inside Window's `shell:sendto`
directory.


How it works?
-------------

The function :code:`send_to(cfg)` follows the configuration that is set in the
passed :code:`Cfg` object. This object holds configuration such as: the
destination path, wheter the files will be moved or copied, the names of the
user defined functions, etc.

The user defined functions are used to determine: if the files will be further
categorized in a subdirectory, wheter a file will be skipped, wheter a file
will be renamed and a function for doing post-processing on the destination
files.


How to use it?
--------------

This project is meant to be used as a library module, create the actual Python
script file and import the function :code:`send_to(cfg)`, the classes
:code:`Cfg` and :code:`Info` and the enum :code:`Operation` from the
:code:`send_to` module.

.. code-block:: python

    from send_to import send_to, Cfg, Info, Operation


Setting the configuration (:code:`Cfg`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Instantiate an object from the :code:`Cfg` class and set it data members.

.. code-block:: python
   :caption: Example:

    cfg = Cfg()
    cfg.version = 0
    cfg.dst_path = os.path.dirname(sys.argv[0])  # use script's location
    cfg.operation = Operation.MOVE

    # user defined functions (explained later)
    cfg.subdir = subdir
    cfg.skip = skip
    cfg.rename = rename
    cfg.post_process = post_process


:code:`Cfg` member variables:
*****************************

.. autoattribute:: Cfg.version
.. autoattribute:: Cfg.dst_path
.. autoattribute:: Cfg.operation
.. autoattribute:: Cfg.date_fmt
.. autoattribute:: Cfg.ask_for_date
.. autoattribute:: Cfg.ask_for_desc
.. autoattribute:: Cfg.overwrite_file
.. autoattribute:: Cfg.dry_run
.. autoattribute:: Cfg.debug
.. autoattribute:: Cfg.subdir
.. autoattribute:: Cfg.skip
.. autoattribute:: Cfg.rename
.. autoattribute:: Cfg.post_process


Creating the callback functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
There are 4 (optional) user defined functions that'll be called by
:code:`send_to(cfg)`. They can be created in the script file and their names
are set in the :code:`Cfg` object. These functions usually take an :code:`Info`
object as an argument.


The :code:`Info` class
**********************
Information such as: source file path, destination path, date and description
is stored in an `Info` object. This object is then passed to some of the user
defined functions so this information can be used in e.g. naming the
subdirectory, the file etc.

.. autoattribute:: Info.file_path
.. autoattribute:: Info.dst_path
.. autoattribute:: Info.date
.. autoattribute:: Info.desc


Subdirectory function
*********************
.. code-block:: python

    def subdir(info: Info) -> str:
    \"""Use this function to construct a subdirectory name based on the
    information provided by the passed `Info` object. If no subdirectory is
    required - return an empty string.

    Args:
        info (Info)

    Returns:
        str: subdirectory name or empty string
    \"""

.. code-block:: python
    :caption: Example "subdir" function:

    def my_subdir_func(info: Info) -> str:
        \"""Tell `send_to(cfg)` to create a subdirectory named \"{date}
        {description}\" e.g. \"2023-08-26 summer\".\"""
        return (f'{info.date} {info.desc}').strip()

    cfg.subdir = my_sudir_func


Skip function
*************
.. code-block:: python

    def skip(info: Info) -> bool:
    \"""Use this function to determine if the currently processed file should
    be skipped or not.

    Args:
        info (Info)

    Returns:
        bool: True to skip the current file, False otherwise
    \"""

.. code-block:: python
    :caption: Example "skip" function:

    def skip_jpgs(info: Info) -> str:
        \"""Tell `send_to(cfg)` to skip JPGs.\"""
        file = os.path.basename(info.file_path)
        file_name, file_ext = os.path.splitext(file)

        if file_ext.lower() == '.jpg':
            return True
        else:
            return False

    cfg.skip = skip_jpgs


Rename function
***************
.. code-block:: python

    def rename(info: Info) -> str:
    \"""Use this function to determine how the currently processed file should
    be renamed.

    Args:
        info (Info)

    Returns:
        str: new file name or empty string to keep the original name
    \"""

.. code-block:: python
    :caption: Example "rename" function:

    def append_desc(info: Info) -> str:
        \"""Tell `send_to(cfg)` to append description to the destination file
        name.\"""
        file = os.path.basename(info.file_path)
        file_name, file_ext = os.path.splitext(file)

        return (f"{file_name} {info.desc}{file_ext}")

    cfg.rename = append_desc


Post-processing function
************************
.. code-block:: python

    def post_process(file_path: str) -> None:
    \"""Use this function to do post-processing on the destination file.

    Args:
        file_path (str): path of the destination file
    \"""

.. code-block:: python
    :caption: Example "post_process" function:

    def resize(file_path: str) -> None:
        \"""Resize destination files to 1080p.\"""
        resize_img(file_path, file_path + "_1080p", "1920x1080")

    cfg.post_process = resize


Executing :code:`send_to(cfg)`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Call :code:`send_to(cfg)`, passing it the configuration object :code:`Cfg`.

.. code-block:: python
    :emphasize-lines: 1

    send_to(cfg)

"""

__name__ = "send_to"
__author__ = "Vasil Kalchev"
__version__ = "0.4.0"
__license__ = "MIT"


import sys
import os
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from datetime import datetime, timedelta
import shutil


@dataclass
class Info:
    file_path: str = ""
    """The path of the currently processed file."""

    dst_path: str = ""
    """Destination path"""

    date: str = ""
    """Date"""

    desc: str = ""
    """Description"""


VersionPart = Enum("VersionPart", ['MAJOR', 'MINOR', 'PATCH'])


def semver_str_to_int(version: str, part: VersionPart) -> int:
    """Convert part of a semver string to int.

    Args:
        version (str): semver string
        part (VersionPart): what part of the semver should be returned

    Returns:
        int: part of the semver in int
    """
    if part == VersionPart.MAJOR:
        ver = version.split('.')[0]
    elif part == VersionPart.MINOR:
        ver = version.split('.')[1]
    elif part == VersionPart.PATCH:
        ver = version.split('.')[2]
    else:
        ver = -1

    return int(ver)


Operation = Enum("Operation", ['MOVE', 'COPY'])


class Cfg:
    """Configuration used be :code:`send_to(cfg)` function."""

    version: int = semver_str_to_int(__version__, VersionPart.MAJOR)
    """Set it to the major version of the :code:`send_to` module that the
    script is currently developed for."""

    dst_path: str
    """Destination path for the processed files."""

    operation: Operation = Operation.MOVE
    """Operation the will be performed on the files - copy or move."""

    date_fmt: str = "%Y-%m-%d"
    """String format of the date."""

    ask_for_date: bool = True
    """Prompt the user to input a date/date shift."""

    ask_for_desc: bool = True
    """Prompt the user to input a description."""

    overwrite_file: bool = False
    """Overwrite files with the same name in the destination."""

    dry_run: bool = False
    """Just print the console messages without actually doing anything."""

    debug: bool = True
    """Print more console messages."""

    subdir: Callable[[Info], str]
    """User defined function for determining the name of the subdirectory under
    :code:`dst_path` where the files will be placed."""

    skip: Callable[[Info], bool]
    """User defined function for determining if a file will be skipped."""

    rename: Callable[[Info], str]
    """ User defined function for determining how the destination file will be
    named."""

    post_process: Callable[[str], None]
    """User defined function for doing post-processing on a destination
    file."""


class IncompatibleCfgVersion(Exception):
    """Script's major version and configuration's version don't match.
    """
    pass


class InvalidDateInput(Exception):
    """User's date input is invalid.
    """
    pass


def operation_to_str(operation: Operation) -> tuple[str, str]:
    """Determine the words that will be used when printing to the console
    based on the configured operation.

    Args:
        operation (Cfg.Operation): the operation that will be performed

    Returns:
        tuple[str, str]: strings of the operation in continuous and past tense
    """
    if operation is Operation.MOVE:
        return ("moving", "moved")
    elif operation is Operation.COPY:
        return ("copying", "copied")
    else:
        return ("<invalid operation>", "<invalid operation>")


def determine_date(ask_for_date: bool, date_fmt: str) -> str:
    """Prompt the user for a date/use today's date and format it.

    Args:
        ask_for_date (bool): True - prompt the user to manually input the
            desired date, False - use today's date
        date_fmt (str): string format of the date

    Returns:
        str: the determined date
    """

    if ask_for_date:
        date = input(
            f"Input date (\'{date_fmt}\') or day shift (e.g. \'-1\' for "
            "yesterday) or leave blank for today: "
            )
        try:
            # this will succeed when the user inputs a date complying with the
            # passed date format
            datetime.strptime(date, date_fmt)
        except ValueError:
            # user wants to either use today's date or a date shift
            if not date:  # nothing entered - use today's date
                date = datetime.today().strftime(date_fmt)
                print(f'using today\'s date: {date}')
            elif int(date) < 0 and int(date) > -8:  # compute date shift
                td = abs(int(date))
                date = (datetime.now() - timedelta(td)).strftime(date_fmt)
                print(f'shifting time by -{td} days: {date}')
            else:
                raise InvalidDateInput
    else:
        date = datetime.today().strftime(date_fmt)
        print(f'using today\'s date: {date}')

    return date


def print_help():
    """Print help. Used when calling this module directly."""

    help = """This module is meant to be imported in a script. Refer to the
    documentation."""
    print(help)


def send_to(cfg: Cfg) -> None:
    """Executes the "send_to" procedure based on the passed config.

    Args:
        cfg (Cfg): A completed config object.

    Raises:
        IncompatibleCfgVersion: Raised when the major version of the script
            doesn't match the version of the configuration object.
    """

    print(f'send_to v{__version__}, cfg v{cfg.version}\n')

    # compare the major version of the script with the version configuration
    # object
    script_maj_ver = semver_str_to_int(__version__, VersionPart.MAJOR)
    if script_maj_ver != cfg.version:
        raise IncompatibleCfgVersion

    # determine the words that will be printed in the console based on the
    # configured operation
    op_str_cont, op_str_past = operation_to_str(cfg.operation)

    # when using Window's shell:sendto the selected files are passed as
    # arguments after the script's name
    files = sys.argv[1:]  # set files that will be copied/moved
    if len(files) == 0:
        sys.exit("Error: No files passed as arguments.")

    # print a list of the files that will be processed
    print(f'Files to be {op_str_past}: ', end='')
    for file in files:
        print(f'{os.path.basename(file)} ', end='')
    print()

    # This object stores the information collected by the user and the current
    # file that is being processed. It'll be passed to the user defined
    # functions.
    info = Info()
    info.dst_path = cfg.dst_path

    # Determine the date that will be used based on the passed configuration.
    # The date is collected and later passed to the `subdir()` and `rename()`
    # functions so it can be used in the sub-directory and/or the files names.
    info.date = determine_date(cfg.ask_for_date, cfg.date_fmt)

    # Optionally ask the user for a description of the files that will be
    # processed.
    # The description is also collected for the same purpose as the date.
    if cfg.ask_for_desc:
        info.desc = input('Input description (can be left blank): ')
    else:
        info.desc = ""

    subdir_name = ""
    try:
        # Call the user's function `subdir(info)` to determine the name of the
        # subdirectory where the file be placed. When an empty string is
        # returned - no subdirectory is created.
        subdir_name = cfg.subdir(info)
    except AttributeError:  # no subdir function assigned
        pass

    if subdir_name != "":
        # If a sub-directory name was returned - try to create it.
        info.dst_path = f"{cfg.dst_path}\\{subdir_name}"

        if cfg.dry_run is False:
            try:
                os.mkdir(info.dst_path)
                if cfg.debug:
                    print(f'DEBUG: created directory {info.dst_path}')
            except FileExistsError:
                if cfg.debug:
                    print('DEBUG: directory already exists')
    else:
        info.dst_path = cfg.dst_path

    for file in files:
        skip = False
        try:
            # Call the user's function `skip(info)` to determine if the current
            # file should be skipped.
            info.file_path = file
            skip = cfg.skip(info)
        except TypeError:  # no skip function assigned
            pass

        if skip:
            print(f'{file} is ignored')
            continue  # go to next file

        new_file_name = ""  # the name of the file + its extension
        try:
            # Call the user's function `rename(info)` to determine the new name
            # of the currenly processed file. When an empty string is returned
            # - the original file's name will be used.
            new_file_name = cfg.rename(info)
        except TypeError:  # no renaming function assigned
            pass

        if new_file_name == "":
            # if no name was returned - use the original name
            new_file_name = os.path.basename(file)

        # prepend the directory's path to the full file name
        new_file = info.dst_path + '\\' + new_file_name

        print(f'{op_str_cont} {file} to {new_file}', end='')

        file_exists = os.path.exists(new_file)
        if file_exists and cfg.overwrite_file is False:
            print(' - already exists, skipping')
        else:
            if file_exists:
                print(' - already exists, overwritting', end='')

            if cfg.dry_run is False:
                if cfg.operation == Operation.MOVE:
                    shutil.move(file, new_file)
                elif cfg.operation == Operation.COPY:
                    shutil.copy(file, new_file)
            print()

        try:
            # Pass the destination file's path to the user's function
            # `post_process()` to allow the user to do post-processing on the
            # file.
            cfg.post_process(new_file)
            print(f'post-processing {new_file}')
        except TypeError:  # no post-processing function assigned
            pass

    print('\nDone! ', end='')

    if cfg.debug:
        input("Press \"Enter\" to exit...")


if __name__ == "__main__":
    print(f'send_to v{__version__}\n')
    print_help()
