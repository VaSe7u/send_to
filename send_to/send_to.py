"""send_to

A module that allows to easily create scripts for organizing files to different
folders. Can be used in combination with Window's shell:sendto.

# How it works?
The `send_to(cfg)` procedure uses a `Cfg` object to determine the:
 - destination directory
 - operation (move/copy)
 - date format, wheter to prompt the user for a date or use today
 - wheter to ask for description
 - wheter to overwrite the destination files
 - ...
It then goes through all the files (passed as arguments) and calls the
functions defined by the user:
 - `subdir(date, desc)`: name of the sub-directory
 - `skip(file_path)`: wheter to skip the passed file
 - `rename(file_path, date, desc)`: new name for the passed file
 - `post_process(file_path)`: do custom post-processing on the passed file

# How to use it?
Create your script file (it's easiest to place it inside the target folder).
Use the `Cfg` class to set your configuration and attach your callback
functions (optional). Call the `send_to(cfg)` procedure.
"""

__name__ = "send_to"
__author__ = "Vasil Kalchev"
__version__ = "0.3.0"
__license__ = "MIT"


import sys
import os
from datetime import datetime, timedelta
import shutil
from enum import Enum


def subdir_func(dst_path: str, date: str, desc: str) -> str:
    """Empty function for determining the name for the optional sub-directory
    where the files will be placed.

    Usage instructions:
     - Create a function with the same signature in the your script.
     - The function must return the desired name of the sub-directory where the
    files will be placed. Parameters `dst_path`, `date` and `desc` can be used
    to construct the name.
     - Set Cfg.subdir to the name of your `subdir()` function.

    Args:
        dst_path (str): destination path
        date (str): a date string
        desc (str): a description string

    Returns:
        str: sub-directory name
    """
    return ""


def skip_func(file_path: str) -> bool:
    """Empty function for determining wheter the passed source file will be
    skipped.

    Usage instructions:
     - Create a function with the same signature in the your script.
     - The function must return a boolean indicating wheter the passed file
    will be skipped or not.
     - Set Cfg.skip to the name of your `skip()` function.

    Args:
        file_path (str): path to the currently processed file

    Returns:
        bool: skip/no skip
    """
    return False


def rename_func(file_path: str, dst_path: str, date: str, desc: str) -> str:
    """Empty function for determining a new name for the passed file.

    Usage instructions:
     - Create a function with the same signature in the your script.
     - The function must return the new name of the passed file. Parameters
    `date` and `desc` can be used to construct the name.
     - Set Cfg.rename to the name of your `rename()` function.

    Args:
        file_path (str): path to the currently processed file
        dst_path (str): destination path
        date (str): a date string
        desc (str): a description string

    Returns:
        str: new file name
    """
    return ""


def post_process_func(file_path: str) -> None:
    """Empty function for executing post-processing on the passed file.

    Usage instructions:
     - Create a function with the same signature in the your script.
     - The function can do any sort of post-processing on the passed file.
     - Set Cfg.post_process to the name of your `post_process()` function.

    Args:
        file_path (str): path to the currently processed file
    """
    pass


Operation = Enum("Operation", ['MOVE', 'COPY'])


class Cfg:
    """User's configuration.
    """

    def __init__(self,
                 version: int = int(__version__.split('.')[0]),
                 dst_path: str = "",
                 operation: Operation = Operation.MOVE):
        """Construct an object with default configuration values.

        Args:
            dst_path (str, optional): destination path. Defaults to "".
            operation (Operation, optional): copy or move. Defaults to
            Operation.MOVE.
        """

        self.version: int = version
        """Set it to the major version of the script that the configuration is
        developed for."""

        self.dst_path: str = dst_path
        """Destination path."""

        self.operation: Operation = operation
        """Operation the will be performed on the files - copy or move."""

        self.date_fmt: str = "%Y-%m-%d"
        """String format of the date."""

        self.ask_for_date: bool = True
        """Prompt the user to input a date/date shift."""

        self.ask_for_desc: bool = True
        """Prompt the user to input a description."""

        self.overwrite_file: bool = False
        """Overwrite files with the same name in the destination."""

        self.dry_run: bool = False
        """Just print the console messages without actually doing anything."""

        self.debug: bool = True
        """Print more console messages."""

        self.subdir = subdir_func
        """User defined function for determining the name of the optional
        sub-directory where the files will be placed."""

        self.skip = skip_func
        """User defined function for determining if a file will be skipped."""

        self.rename = rename_func
        """ User defined function for determining a new name for a file."""

        self.post_process = post_process_func
        """User defined function for doing post-processing on a resultant
        file."""


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


class IncompatibleCfgVersion(Exception):
    """Script's and configuration's major versions don't match.
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
    help = """This module is meant to be imported in a configuration file."""
    print(help)


def send_to(cfg: Cfg) -> None:
    """Executes the "send_to" procedure based on the passed config.

    Args:
        cfg (Cfg): A completed config object.

    Raises:
        IncompatibleCfgVersion: Raised when the major version of the script
        doesn't match the major version of the configuration object.
    """

    print(f'send_to v{__version__}, cfg v{cfg.version}\n')

    # compare the major versions of the script and the configuration object
    script_maj_ver = semver_str_to_int(__version__, VersionPart.MAJOR)
    if script_maj_ver != cfg.version:
        raise IncompatibleCfgVersion

    # determine the words that will be printed in the console based on the
    # configured operation
    op_str_cont, op_str_past = operation_to_str(cfg.operation)

    # when using Window's shell:sendto the selected files are passed as
    # arguments after the script's name
    files = sys.argv[1:]  # set files that will be copied/moved

    # Prints a list of the files that will be processed.
    print(f'Files to be {op_str_past}: ', end='')
    for file in files:
        print(f'{os.path.basename(file)} ', end='')
    print()

    # Determine the date that will be used based on the passed configuration.
    # The date is collected and later passed to the `subdir()` and `rename()`
    # functions so it can be used in the sub-directory and/or the files names.
    date = determine_date(cfg.ask_for_date, cfg.date_fmt)

    # Optionally ask the user for a description of the files that will be
    # processed.
    # The description is also collected for the same purpose as the date.
    if cfg.ask_for_desc:
        desc = input('Input description (can be left blank): ')
    else:
        desc = ''

    subdir_name = ""
    try:
        # Try calling the user defined function `subdir()` in order to
        # determine the name of the folder where the files will be placed. If
        # the function returns an empty string - no sub-directory will be
        # created.
        subdir_name = cfg.subdir(cfg.dst_path, date, desc)
    except AttributeError:  # no subdir function assigned
        pass

    if subdir_name != "":
        # If a sub-directory name was returned - try to create it.
        dst_path = f"{cfg.dst_path}\\{subdir_name}"

        if cfg.dry_run is False:
            try:
                os.mkdir(dst_path)
                if cfg.debug:
                    print(f'DEBUG: created directory {dst_path}')
            except FileExistsError:
                if cfg.debug:
                    print('DEBUG: directory already exists')
    else:
        dst_path = cfg.dst_path

    for file in files:
        skip = False
        try:
            # Pass the source file's path to the user defined function
            # `skip()` to determine if this file will be skipped or not.
            skip = cfg.skip(file)
        except TypeError:  # no skip function assigned
            pass

        if skip:
            print(f'{file} is ignored')
            continue

        new_file_name = ""  # the name of the file + its extension
        try:
            # Pass the source file's path, the destination path, the collected
            # date and description to the user defined function `rename()` to
            # get the new name of this file.
            new_file_name = cfg.rename(file, dst_path, date, desc)
        except TypeError:  # no renaming function assigned
            pass

        if new_file_name == "":
            # if no name was returned - use the original name
            new_file_name = os.path.basename(file)

        # prepend the directory's path to the full file name
        new_file = dst_path + '\\' + new_file_name

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
            # Pass the destination file's path to the user defined function
            # `post_process()` to allow the user to do post-processing on the
            # file.
            cfg.post_process(new_file)
            print(f'post-processing {new_file}')
        except TypeError:  # no post-processing function assigned
            pass

    print('\nDone! ', end='')

    if cfg.debug:
        input("Press any key to exit...")


if __name__ == '__main__':
    print_help()
