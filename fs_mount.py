import os
import logging
from collections import defaultdict
import errno
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

import tensorflow as tf
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, ENOTSUP

if not hasattr(__builtins__, 'bytes'):
    bytes = str


class FSMount(LoggingMixIn, Operations):

    def __init__(self, root):
        self.root = root
        self.open_handle = []

    def full_path(self, path):
        return os.path.join(self.root, path)

    def access(self, path, amode):
        return 0

    bmap = None

    def chmod(self, path, mode):
        raise FuseOSError(errno.EROFS)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.EROFS)

    def create(self, path, mode, fi=None):
        try:
            tf.io.gfile.GFile(self.full_path(path), 'w')
        except tf.errors.OpError:
            raise FuseOSError(errno.EROFS)

    def destroy(self, path):
        'Called on filesystem destruction. Path is always /'
        pass

    def flush(self, path, fh):
        return 0

    def fsync(self, path, datasync, fh):
        return 0

    def fsyncdir(self, path, datasync, fh):
        return 0

    def getattr(self, path, fh=None):
        try:
            stat = tf.io.gfile.stat(self.full_path(path))
        except tf.errors.OpError:
            raise FuseOSError(errno.ENOENT)

        return dict(
            st_mode=S_IFDIR if stat.is_directory else S_IFREG,
            st_mtime=stat.mtime_nsec)

    def getxattr(self, path, name, position=0):
        raise FuseOSError(errno.ENOTSUP)

    def init(self, path):
        '''
        Called on filesystem initialization. (Path is always /)

        Use it instead of __init__ if you start threads on initialization.
        '''

        pass

    def ioctl(self, path, cmd, arg, fip, flags, data):
        raise FuseOSError(errno.ENOTTY)

    def link(self, target, source):
        'creates a hard link `target -> source` (e.g. ln source target)'

        raise FuseOSError(errno.EROFS)

    def listxattr(self, path):
        return []

    lock = None

    def mkdir(self, path, mode):
        try:
            stat = tf.io.gfile.stat(self.full_path(path))
        except tf.errors.OpError:
            raise FuseOSError(errno.EROFS)
        return 0

    def mknod(self, path, mode, dev):
        raise FuseOSError(errno.EROFS)

    def open(self, path, flags):
        '''
        When raw_fi is False (default case), open should return a numerical
        file handle.

        When raw_fi is True the signature of open becomes:
            open(self, path, fi)

        and the file handle should be set directly.
        '''

        return 0

    def opendir(self, path):
        'Returns a numerical file handle.'

        return 0

    def read(self, path, size, offset, fh):
        file = tf.io.gfile.GFile(self.full_path(path), 'r')
        if offset == 0:
            return file.read(size)
        elif file.seekable():
            file.seek(offset)
            return file.read(size)
        else:
            raise FuseOSError(errno.EIO)

    def readdir(self, path, fh):
        return ['.', '..'] + tf.io.gfile.listdir(self.full_path(path))

    def readlink(self, path):
        raise FuseOSError(errno.ENOENT)

    def release(self, path, fh):
        return 0

    def releasedir(self, path, fh):
        return 0

    def removexattr(self, path, name):
        raise FuseOSError(ENOTSUP)

    def rename(self, old, new):
        try:
            tf.io.gfile.rename(
                self.full_path(old),
                self.full_path(new), 
                overwrite=False)
        except tf.errors.OpError:
            raise FuseOSError(errno.EROFS)

    def rmdir(self, path):
        try:
            tf.io.gfile.rmtree(self.full_path(path))
        except tf.errors.OpError:
            raise FuseOSError(errno.EROFS)

    def setxattr(self, path, name, value, options, position=0):
        raise FuseOSError(ENOTSUP)

    def statfs(self, path):
        '''
        Returns a dictionary with keys identical to the statvfs C structure of
        statvfs(3).

        On Mac OS X f_bsize and f_frsize must be a power of 2
        (minimum 512).
        '''

        return {}

    def symlink(self, target, source):
        'creates a symlink `target -> source` (e.g. ln -s source target)'

        raise FuseOSError(errno.EROFS)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(errno.EROFS)

    def unlink(self, path):
        try:
            tf.io.gfile.remove(self.full_path(path))
        except tf.errors.OpError:
            raise FuseOSError(errno.EROFS)

    def utimens(self, path, times=None):
        'Times is a (atime, mtime) tuple. If None use current time.'
        return 0

    def write(self, path, data, offset, fh):
        file = tf.io.gfile.GFile(self.full_path(path), 'w')
        if offset == 0:
            file.write(data)
            return len(data)
        elif file.seekable():
            file.seek(offset)
            file.write(data)
            return len(data)
        else:
            raise FuseOSError(errno.EROFS)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--src')
    parser.add_argument('--dst')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(FSMount(args.src), args.dst, foreground=True)
