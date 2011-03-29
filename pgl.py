# Copyright (c) 2011 Nick Hurley <hurley at todesschaf dot org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""Helpers for git extensions written in python
"""
import inspect
import os
import subprocess
import sys
import traceback

config = {}

def __extract_name_email(info, type_):
    """Extract a name and email from a string in the form:
           User Name <user@example.com> tstamp offset
       Stick that into our config dict for either git committer or git author.
    """
    val = ' '.join(info.split(' ')[:-2])
    angle = val.find('<')
    if angle > -1:
        config['GIT_%s_NAME' % type_] = val[:angle - 1]
        config['GIT_%s_EMAIL' % type_] = val[angle + 1:-1]
    else:
        config['GIT_%s_NAME' % type_] = val

def __create_config():
    """Create our configuration dict from git and the env variables we're given.
    """
    devnull = file('/dev/null', 'w')

    # Stick all our git variables in our dict, just in case anyone needs them
    gitvar = subprocess.Popen(['git', 'var', '-l'], stdout=subprocess.PIPE,
        stderr=devnull)
    for line in gitvar.stdout:
        k, v = line.split('=', 1)
        if k == 'GIT_COMMITTER_IDENT':
            __extract_name_email(v, 'COMMITTER')
        elif k == 'GIT_AUTHOR_IDENT':
            __extract_name_email(v, 'AUTHOR')
        elif v == 'true':
            v = True
        elif v == 'false':
            v = False
        else:
            try:
                v = int(v)
            except:
                pass
        config[k] = v
    gitvar.wait()

    # Find out where git's sub-exes live
    gitexec = subprocess.Popen(['git', '--exec-path'], stdout=subprocess.PIPE,
        stderr=devnull)
    config['GIT_LIBEXEC'] = gitexec.stdout.readlines()[0].strip()
    gitexec.wait()

    # Figure out the git dir in our repo, if applicable
    gitdir = subprocess.Popen(['git', 'rev-parse', '--git-dir'],
        stdout=subprocess.PIPE, stderr=devnull)
    lines = gitdir.stdout.readlines()
    if gitdir.wait() == 0:
        config['GIT_DIR'] = lines[0].strip()

    # Figure out the top level of our repo, if applicable
    gittoplevel = subprocess.Popen(['git', 'rev-parse', '--show-toplevel'],
        stdout=subprocess.PIPE, stderr=devnull)
    lines = gittoplevel.stdout.readlines()
    if gittoplevel.wait() == 0:
        config['GIT_TOPLEVEL'] = lines[0].strip()

    # We may have been called by a wrapper that passes us some info through the
    # environment. Use it if it's there
    for k, v in os.environ.iteritems():
        if k.startswith('PY_GIT_'):
            config[k[3:]] = v
        elif k == 'PGL_OK':
            config['PGL_OK'] = True

    # Make sure our git dir and toplevel are fully-qualified
    if 'GIT_DIR' in config and not os.path.isabs(config['GIT_DIR']):
        git_dir = os.path.join(config['GIT_TOPLEVEL'], config['GIT_DIR'])
        config['GIT_DIR'] = os.path.abspath(git_dir)

def warn(msg):
    """Print a warning
    """
    sys.stderr.write('%s\n' % (msg,))

def die(msg):
    """Print an error message and exit the program
    """
    sys.stderr.write('%s\n' % (msg,))
    sys.exit(1)

def do_checks():
    """Check to ensure we've got everything we expect
    """
    try:
        import argparse
    except:
        die('Your python must support the argparse module')

def main(_main):
    """Mark a function as the main function for our git subprogram. Based
    very heavily on automain by Gerald Kaszuba, but with modifications to make
    it work better for our purposes.
    """
    parent = inspect.stack()[1][0]
    name = parent.f_locals.get('__name__', None)
    if name == '__main__':
        __create_config()
        if 'PGL_OK' not in config:
            do_checks()
        rval = 1
        try:
            rval = _main()
        except Exception, e:
            sys.stdout.write('%s\n' % str(e))
            f = file('pygit.tb', 'w')
            traceback.print_tb(sys.exc_info()[2], None, f)
            f.close()
        sys.exit(rval)
    return _main

if __name__ == '__main__':
    """If we get run as a script, check to make sure it's all ok and exit with
    an appropriate error code
    """
    do_checks()
    sys.exit(0)
