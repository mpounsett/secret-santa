# -*- coding: utf-8 -*-

import contextlib
import stat
import tempfile
import os


@contextlib.contextmanager
def safe_write(path, fsync=False):
    f = tempfile.NamedTemporaryFile(mode='w',
                                    prefix='.',
                                    dir=os.path.dirname(path),
                                    delete=False
                                    )
    yield f

    if fsync:
        f.flush()
        os.fsync(f.fileno())
    os.fchmod(f.fileno(),
              stat.S_IRUSR | stat.S_IWUSR |
              stat.S_IRGRP |
              stat.S_IROTH
              )
    f.close()
    os.rename(f.name, path)
    try:
        os.remove(f.name)
    except (IOError, OSError):
        pass
