#!/usr/bin/python

from __future__ import print_function
#import httplib2
#import os

#from apiclient import discovery
#from oauth2client import client
#from oauth2client import tools
#from oauth2client.file import Storage
#import inspect
#from apiclient.http import MediaFileUpload
import hashlib
import getopt
import sys
import os
import re
import argparse

def md5(fname):
    hasher = hashlib.md5()
    blocksize = 65536
    afile = open(fname, 'rb')
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()


def get_dirs(dir):
    if not os.path.exists(dir):
        return list()
    result = [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]
    return sorted(result)


def get_files(dir):
    if not os.path.exists(dir):
        return list()
    result = [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
    return sorted(result)


VERSION = "1.0"


def usage():
    print(sys.argv[0], " <options>  <from> <to>")
    print("\t version ", VERSION, " backup directory")
    print("\t--dir  <directory> directory to process\n")
    os.sys.exit(1)


''' copy file to destination but if the destination file exists, don't override make a new file
    this is useful for images created by cameras that re-use the same name.
    
    This prevents overwriting different files with the same name.
    
    Not for general purpose use.
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="copy from from a source to destination, but will check the md5 checksum will copy only if different.")
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument("srcdir", help="input directory to read for files")
    parser.add_argument("destdir", help="input directory to read for files")
    #parser.add_argument("--remote", help="input directory to read for files", required=True)

    args = parser.parse_args()

    from_dir = args.srcdir
    to_dir = args.destdir
    from_files = get_files(from_dir)
    for a in from_files:
        # print("{0} {1}".format(a, md5(a)))

        result = re.search("(.+)(\..+?)$", os.path.basename(a))
        name = result.group(1)
        ext = result.group(2)
        index = -1

        skip = False
        done = False
        dest = None
        while not done:
            if index == -1:
                unique = ""
            else:
                unique = ".{0}".format(index)

            dest = "{0}/{1}{2}{3}".format(to_dir, name, unique, ext)
            index = index + 1
            if os.path.exists(dest):
                # print("file exists .. " + dest)
                if md5(a) == md5(dest):
                    if int(os.path.getmtime(a)) == int(os.path.getmtime(dest)):
                        print("\tskipping {0} {1}, md5/mtime matches".format(a, dest))
                        skip = True
                        done = True
                        continue
                    else:
                        print("\tmodification time mismatch {} {} {}<=>{}".format(a, dest, os.path.getmtime(a), os.path.getmtime(dest)))
                        break
                # print ("need to make a new file name {0}".format(os.path.basename(dest)))
                continue
            done = True

        if skip:
            continue

        print("\t{} file from {} to {}".format("copying" if not args.dry else "will copy", a, dest))
        if not args.dry:
            os.system("/bin/cp -fp {0} {1}".format(a, dest))
            os.utime(dest, ( os.path.getctime(a), os.path.getmtime(a)))
