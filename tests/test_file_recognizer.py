""" Test the file recognizer capabilities.
"""

from __future__ import print_function

import gzip
import os
import shutil
import socket
import sys

import nose
import nose.tools as nt

from grin import FileRecognizer, GZIP_MAGIC, ALLBYTES


def empty_file(filename, open=open):
    with open(filename, 'wb'):
        pass


def binary_file(filename, open=open):
    with open(filename, 'wb') as f:
        f.write(bytes(range(256)))


def text_file(filename, open=open):
    lines = ['foo\n', 'bar\n'] * 100
    lines.append('baz\n')
    lines.extend(['foo\n', 'bar\n'] * 100)
    with open(filename, 'wt') as f:
        f.writelines(lines)


def fake_gzip_file(filename, open=open):
    """ Write out a binary file that has the gzip magic header bytes, but is
    not a gzip file.
    """
    with open(filename, 'wb') as f:
        f.write(GZIP_MAGIC)
        f.write(ALLBYTES)


def binary_middle(filename, open=open):
    """ Write out a file that is text for the first 100 bytes, then 100 binary
    bytes, then 100 text bytes to test that the recognizer only reads some of
    the file.
    """
    text = b'a' * 100 + b'\0' * 100 + b'b' * 100
    with open(filename, 'wb') as f:
        f.write(text)


def socket_file(filename):
    s = socket.socket(socket.AF_UNIX)
    s.bind(filename)


def unreadable_file(filename):
    """ Write a file that does not have read permissions.
    """
    text_file(filename)
    os.chmod(filename, 0o200)


def unreadable_dir(filename):
    """ Make a directory that does not have read permissions.
    """
    os.mkdir(filename)
    os.chmod(filename, 0o300)


def unexecutable_dir(filename):
    """ Make a directory that does not have execute permissions.
    """
    mkdir(filename)
    os.chmod(filename, 0o600)


def totally_unusable_dir(filename):
    """ Make a directory that has neither read nor execute permissions.
    """
    mkdir(filename)
    os.chmod(filename, 0o100)


def setup():
    # Make files to test individual recognizers.
    empty_file('empty')
    binary_file('binary')
    binary_middle('binary_middle')
    text_file('text')
    text_file('text~')
    text_file('text#')
    text_file('foo.bar.baz')
    os.mkdir('dir')
    binary_file('.binary')
    text_file('.text')
    empty_file('empty.gz', open=gzip.open)
    binary_file('binary.gz', open=gzip.open)
    text_file('text.gz', open=gzip.open)
    binary_file('.binary.gz', open=gzip.open)
    text_file('.text.gz', open=gzip.open)
    fake_gzip_file('fake.gz')
    os.mkdir('.dir')
    os.symlink('binary', 'binary_link')
    os.symlink('text', 'text_link')
    os.symlink('dir', 'dir_link')
    os.symlink('.binary', '.binary_link')
    os.symlink('.text', '.text_link')
    os.symlink('.dir', '.dir_link')
    unreadable_file('unreadable_file')
    unreadable_dir('unreadable_dir')
    unexecutable_dir('unexecutable_dir')
    totally_unusable_dir('totally_unusable_dir')
    os.symlink('unreadable_file', 'unreadable_file_link')
    os.symlink('unreadable_dir', 'unreadable_dir_link')
    os.symlink('unexecutable_dir', 'unexecutable_dir_link')
    os.symlink('totally_unusable_dir', 'totally_unusable_dir_link')
    text_file('text.skip_ext')
    os.mkdir('dir.skip_ext')
    text_file('text.dont_skip_ext')
    os.mkdir('skip_dir')
    text_file('fake_skip_dir')
    socket_file('socket_test')

    # Make a directory tree to test tree-walking.
    os.mkdir('tree')
    os.mkdir('tree/.hidden_dir')
    os.mkdir('tree/dir')
    os.mkdir('tree/dir/subdir')
    text_file('tree/dir/text')
    text_file('tree/dir/subdir/text')
    text_file('tree/text')
    text_file('tree/text.skip_ext')
    os.mkdir('tree/dir.skip_ext')
    text_file('tree/dir.skip_ext/text')
    text_file('tree/text.dont_skip_ext')
    binary_file('tree/binary')
    os.mkdir('tree/skip_dir')
    text_file('tree/skip_dir/text')
    os.mkdir('tree/.skip_hidden_dir')
    text_file('tree/.skip_hidden_file')
    os.mkdir('tree/unreadable_dir')
    text_file('tree/unreadable_dir/text')
    os.chmod('tree/unreadable_dir', 0o300)
    os.mkdir('tree/unexecutable_dir')
    text_file('tree/unexecutable_dir/text')
    os.chmod('tree/unexecutable_dir', 0o600)
    os.mkdir('tree/totally_unusable_dir')
    text_file('tree/totally_unusable_dir/text')
    os.chmod('tree/totally_unusable_dir', 0o100)


def ensure_deletability(arg, dirname, fnames):
    """ os.path.walk() callback function which will make sure every directory
    is readable and executable so that it may be easily deleted.
    """
    for fn in fnames:
        fn = os.path.join(dirname, fn)
        if os.path.isdir(fn):
            os.chmod(fn, 0o700)


def teardown():
    files_to_delete = ['empty', 'binary', 'binary_middle', 'text', 'text~',
                       'empty.gz', 'binary.gz', 'text.gz', 'dir',
                       'binary_link', 'text_link', 'dir_link', '.binary',
                       '.text', '.binary.gz', '.text.gz', 'fake.gz', '.dir',
                       '.binary_link', '.text_link', '.dir_link',
                       'unreadable_file', 'unreadable_dir', 'unexecutable_dir',
                       'totally_unusable_dir', 'unreadable_file_link',
                       'unreadable_dir_link', 'unexecutable_dir_link',
                       'totally_unusable_dir_link', 'text.skip_ext',
                       'text.dont_skip_ext', 'dir.skip_ext', 'skip_dir',
                       'fake_skip_dir', 'text#', 'foo.bar.baz']
    for filename in files_to_delete:
        try:
            if os.path.islink(filename) or os.path.isfile(filename):
                os.unlink(filename)
            else:
                os.rmdir(filename)
        except OSError as e:
            print('Could not delete %s: %s' % (filename, e), file=sys.stderr)
    os.unlink('socket_test')
    os.walk('tree', ensure_deletability, None)
    shutil.rmtree('tree')


def test_binary():
    fr = FileRecognizer()
    nt.assert_true(fr.is_binary('binary'))
    nt.assert_equal(fr.recognize_file('binary'), 'binary')
    nt.assert_equal(fr.recognize('binary'), 'binary')


def test_text():
    fr = FileRecognizer()
    nt.assert_false(fr.is_binary('text'))
    nt.assert_equal(fr.recognize_file('text'), 'text')
    nt.assert_equal(fr.recognize('text'), 'text')


def test_gzipped():
    fr = FileRecognizer()
    nt.assert_true(fr.is_binary('text.gz'))
    nt.assert_equal(fr.recognize_file('text.gz'), 'gzip')
    nt.assert_equal(fr.recognize('text.gz'), 'gzip')

    nt.assert_true(fr.is_binary('binary.gz'))
    nt.assert_equal(fr.recognize_file('binary.gz'), 'binary')
    nt.assert_equal(fr.recognize('binary.gz'), 'binary')

    nt.assert_true(fr.is_binary('fake.gz'))
    nt.assert_equal(fr.recognize_file('fake.gz'), 'binary')
    nt.assert_equal(fr.recognize('fake.gz'), 'binary')


def test_binary_middle():
    fr = FileRecognizer(binary_bytes=100)
    nt.assert_false(fr.is_binary('binary_middle'))
    nt.assert_equal(fr.recognize_file('binary_middle'), 'text')
    nt.assert_equal(fr.recognize('binary_middle'), 'text')
    fr = FileRecognizer(binary_bytes=101)
    nt.assert_true(fr.is_binary('binary_middle'))
    nt.assert_equal(fr.recognize_file('binary_middle'), 'binary')
    nt.assert_equal(fr.recognize('binary_middle'), 'binary')


def test_socket():
    fr = FileRecognizer()
    nt.assert_equal(fr.recognize('socket_test'), 'skip')


def test_dir():
    fr = FileRecognizer()
    nt.assert_equal(fr.recognize_directory('dir'), 'directory')
    nt.assert_equal(fr.recognize('dir'), 'directory')


def test_skip_symlinks():
    fr = FileRecognizer(skip_symlink_files=True, skip_symlink_dirs=True)
    nt.assert_equal(fr.recognize('binary_link'), 'link')
    nt.assert_equal(fr.recognize_file('binary_link'), 'link')
    nt.assert_equal(fr.recognize('text_link'), 'link')
    nt.assert_equal(fr.recognize_file('text_link'), 'link')
    nt.assert_equal(fr.recognize('dir_link'), 'link')
    nt.assert_equal(fr.recognize_directory('dir_link'), 'link')


def test_do_not_skip_symlinks():
    fr = FileRecognizer(skip_symlink_files=False, skip_symlink_dirs=False)
    nt.assert_equal(fr.recognize('binary_link'), 'binary')
    nt.assert_equal(fr.recognize_file('binary_link'), 'binary')
    nt.assert_equal(fr.recognize('text_link'), 'text')
    nt.assert_equal(fr.recognize_file('text_link'), 'text')
    nt.assert_equal(fr.recognize('dir_link'), 'directory')
    nt.assert_equal(fr.recognize_directory('dir_link'), 'directory')


def test_skip_hidden():
    fr = FileRecognizer(skip_hidden_files=True, skip_hidden_dirs=True)
    nt.assert_equal(fr.recognize('.binary'), 'skip')
    nt.assert_equal(fr.recognize_file('.binary'), 'skip')
    nt.assert_equal(fr.recognize('.text'), 'skip')
    nt.assert_equal(fr.recognize_file('.text'), 'skip')
    nt.assert_equal(fr.recognize('.dir'), 'skip')
    nt.assert_equal(fr.recognize_directory('.dir'), 'skip')
    nt.assert_equal(fr.recognize('.binary_link'), 'skip')
    nt.assert_equal(fr.recognize_file('.binary_link'), 'skip')
    nt.assert_equal(fr.recognize('.text_link'), 'skip')
    nt.assert_equal(fr.recognize_file('.text_link'), 'skip')
    nt.assert_equal(fr.recognize('.dir_link'), 'skip')
    nt.assert_equal(fr.recognize_directory('.dir_link'), 'skip')
    nt.assert_equal(fr.recognize('.text.gz'), 'skip')
    nt.assert_equal(fr.recognize_file('.text.gz'), 'skip')
    nt.assert_equal(fr.recognize('.binary.gz'), 'skip')
    nt.assert_equal(fr.recognize_file('.binary.gz'), 'skip')


def test_skip_backup():
    fr = FileRecognizer(skip_backup_files=True)
    nt.assert_equal(fr.recognize_file('text~'), 'skip')


def test_do_not_skip_backup():
    fr = FileRecognizer(skip_backup_files=False)
    nt.assert_equal(fr.recognize_file('text~'), 'text')


def test_skip_weird_exts():
    fr = FileRecognizer(skip_exts=set())
    nt.assert_equal(fr.recognize_file('text#'), 'text')
    nt.assert_equal(fr.recognize_file('foo.bar.baz'), 'text')
    fr = FileRecognizer(skip_exts=set(['#', '.bar.baz']))
    nt.assert_equal(fr.recognize_file('text#'), 'skip')
    nt.assert_equal(fr.recognize_file('foo.bar.baz'), 'skip')


def test_do_not_skip_hidden_or_symlinks():
    fr = FileRecognizer(skip_hidden_files=False, skip_hidden_dirs=False,
                        skip_symlink_dirs=False, skip_symlink_files=False)
    nt.assert_equal(fr.recognize('.binary'), 'binary')
    nt.assert_equal(fr.recognize_file('.binary'), 'binary')
    nt.assert_equal(fr.recognize('.text'), 'text')
    nt.assert_equal(fr.recognize_file('.text'), 'text')
    nt.assert_equal(fr.recognize('.dir'), 'directory')
    nt.assert_equal(fr.recognize_directory('.dir'), 'directory')
    nt.assert_equal(fr.recognize('.binary_link'), 'binary')
    nt.assert_equal(fr.recognize_file('.binary_link'), 'binary')
    nt.assert_equal(fr.recognize('.text_link'), 'text')
    nt.assert_equal(fr.recognize_file('.text_link'), 'text')
    nt.assert_equal(fr.recognize('.dir_link'), 'directory')
    nt.assert_equal(fr.recognize_directory('.dir_link'), 'directory')
    nt.assert_equal(fr.recognize('.text.gz'), 'gzip')
    nt.assert_equal(fr.recognize_file('.text.gz'), 'gzip')
    nt.assert_equal(fr.recognize('.binary.gz'), 'binary')
    nt.assert_equal(fr.recognize_file('.binary.gz'), 'binary')


def test_do_not_skip_hidden_but_skip_symlinks():
    fr = FileRecognizer(skip_hidden_files=False, skip_hidden_dirs=False,
                        skip_symlink_dirs=True, skip_symlink_files=True)
    nt.assert_equal(fr.recognize('.binary'), 'binary')
    nt.assert_equal(fr.recognize_file('.binary'), 'binary')
    nt.assert_equal(fr.recognize('.text'), 'text')
    nt.assert_equal(fr.recognize_file('.text'), 'text')
    nt.assert_equal(fr.recognize('.dir'), 'directory')
    nt.assert_equal(fr.recognize_directory('.dir'), 'directory')
    nt.assert_equal(fr.recognize('.binary_link'), 'link')
    nt.assert_equal(fr.recognize_file('.binary_link'), 'link')
    nt.assert_equal(fr.recognize('.text_link'), 'link')
    nt.assert_equal(fr.recognize_file('.text_link'), 'link')
    nt.assert_equal(fr.recognize('.dir_link'), 'link')
    nt.assert_equal(fr.recognize_directory('.dir_link'), 'link')
    nt.assert_equal(fr.recognize('.text.gz'), 'gzip')
    nt.assert_equal(fr.recognize_file('.text.gz'), 'gzip')
    nt.assert_equal(fr.recognize('.binary.gz'), 'binary')
    nt.assert_equal(fr.recognize_file('.binary.gz'), 'binary')


def test_lack_of_permissions():
    fr = FileRecognizer()
    nt.assert_equal(fr.recognize('unreadable_file'), 'unreadable')
    nt.assert_equal(fr.recognize_file('unreadable_file'), 'unreadable')
    nt.assert_equal(fr.recognize('unreadable_dir'), 'directory')
    nt.assert_equal(fr.recognize_directory('unreadable_dir'), 'directory')
    nt.assert_equal(fr.recognize('unexecutable_dir'), 'directory')
    nt.assert_equal(fr.recognize_directory('unexecutable_dir'), 'directory')
    nt.assert_equal(fr.recognize('totally_unusable_dir'), 'directory')
    nt.assert_equal(fr.recognize_directory('totally_unusable_dir'),
                    'directory')


def test_symlink_src_unreadable():
    fr = FileRecognizer(skip_symlink_files=False, skip_symlink_dirs=False)
    nt.assert_equal(fr.recognize('unreadable_file_link'), 'unreadable')
    nt.assert_equal(fr.recognize_file('unreadable_file_link'), 'unreadable')
    nt.assert_equal(fr.recognize('unreadable_dir_link'), 'directory')
    nt.assert_equal(fr.recognize_directory('unreadable_dir_link'), 'directory')
    nt.assert_equal(fr.recognize('unexecutable_dir_link'), 'directory')
    nt.assert_equal(fr.recognize_directory('unexecutable_dir_link'),
                    'directory')
    nt.assert_equal(fr.recognize('totally_unusable_dir_link'), 'directory')
    nt.assert_equal(fr.recognize_directory('totally_unusable_dir_link'),
                    'directory')


def test_skip_ext():
    fr = FileRecognizer(skip_exts=set(['.skip_ext']))
    nt.assert_equal(fr.recognize('text.skip_ext'), 'skip')
    nt.assert_equal(fr.recognize_file('text.skip_ext'), 'skip')
    nt.assert_equal(fr.recognize('text'), 'text')
    nt.assert_equal(fr.recognize_file('text'), 'text')
    nt.assert_equal(fr.recognize('text.dont_skip_ext'), 'text')
    nt.assert_equal(fr.recognize_file('text.dont_skip_ext'), 'text')
    nt.assert_equal(fr.recognize('dir.skip_ext'), 'directory')
    nt.assert_equal(fr.recognize_directory('dir.skip_ext'), 'directory')


def test_skip_dir():
    fr = FileRecognizer(skip_dirs=set(['skip_dir', 'fake_skip_dir']))
    nt.assert_equal(fr.recognize('skip_dir'), 'skip')
    nt.assert_equal(fr.recognize_directory('skip_dir'), 'skip')
    nt.assert_equal(fr.recognize('fake_skip_dir'), 'text')
    nt.assert_equal(fr.recognize_file('fake_skip_dir'), 'text')


def test_walking():
    fr = FileRecognizer(skip_hidden_files=True, skip_hidden_dirs=True,
                        skip_exts=set(['.skip_ext']),
                        skip_dirs=set(['skip_dir']))
    truth = [
        ('tree/binary', 'binary'),
        ('tree/dir.skip_ext/text', 'text'),
        ('tree/dir/subdir/text', 'text'),
        ('tree/dir/text', 'text'),
        ('tree/text', 'text'),
        ('tree/text.dont_skip_ext', 'text'),
    ]
    result = sorted(fr.walk('tree'))
    nt.assert_equal(result, truth)


def predot():
    os.chdir('tree')


def postdot():
    os.chdir(os.pardir)


@nose.with_setup(predot, postdot)
def test_dot():
    fr = FileRecognizer(skip_hidden_files=True, skip_hidden_dirs=True,
                        skip_exts=set(['.skip_ext']),
                        skip_dirs=set(['skip_dir']))
    truth = [
        (os.path.join(os.curdir, 'binary'), 'binary'),
        (os.path.join(os.curdir, 'dir.skip_ext', 'text'), 'text'),
        (os.path.join(os.curdir, 'dir', 'subdir', 'text'), 'text'),
        (os.path.join(os.curdir, 'dir', 'text'), 'text'),
        (os.path.join(os.curdir, 'text'), 'text'),
        (os.path.join(os.curdir, 'text.dont_skip_ext'), 'text'),
    ]
    result = sorted(fr.walk(os.curdir))
    nt.assert_equal(result, truth)


def predotdot():
    os.chdir('tree')
    os.chdir('dir')


def postdotdot():
    os.chdir(os.pardir)
    os.chdir(os.pardir)


@nose.with_setup(predotdot, postdotdot)
def test_dot_dot():
    fr = FileRecognizer(skip_hidden_files=True, skip_hidden_dirs=True,
                        skip_exts=set(['.skip_ext']),
                        skip_dirs=set(['skip_dir']))
    truth = [
        (os.path.join(os.curdir, 'binary'), 'binary'),
        (os.path.join(os.curdir, 'dir.skip_ext', 'text'), 'text'),
        (os.path.join(os.curdir, 'dir', 'subdir', 'text'), 'text'),
        (os.path.join(os.curdir, 'dir', 'text'), 'text'),
        (os.path.join(os.curdir, 'text'), 'text'),
        (os.path.join(os.curdir, 'text.dont_skip_ext'), 'text'),
    ]
    result = sorted(fr.walk(os.pardir))
    nt.assert_equal(result, truth)
