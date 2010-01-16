import os

def remove_file(file_path, full_path):
    """Remove the file path from the beginning of the given path, returning the
    relative path suffix."""
    if not full_path.startswith(file_path + os.sep):
        raise ValueError('{} does not start with {}'.format(full_path,
                                                            file_path))
    return full_path[len(file_path)+len(os.sep):]
