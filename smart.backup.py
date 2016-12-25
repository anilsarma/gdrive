#!/usr/bin/python

from __future__ import print_function
import httplib2
import os
import pprint
import json 

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import inspect 
from apiclient.http import MediaFileUpload
import hashlib
import getopt
import sys
from os.path import isfile, join, isdir, exists
from os import listdir
import re

def md5(fname):
        hasher = hashlib.md5()
        blocksize=65536
        afile = open(fname, 'rb')
        buf = afile.read(blocksize)
        while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
        return hasher.hexdigest()



def get_dirs(dir):
    if not exists(dir):
        return list()
        
    result = [ join(dir,f) for f in listdir(dir) if isdir(join(dir,f)) ]
    return sorted(result)


def get_files(dir):
    if not exists(dir):
        return list()
    result = [ join(dir,f) for f in listdir(dir) if isfile(join(dir,f)) ]
    return sorted(result)



VERSION="1.0"
def usage():
    print(sys.argv[0], " <options>  <from> <to>")
    print("\t version ", VERSION, " backup directory")
    print("\t--dir  <directory> directory to process\n")
    os.sys.exit(1)


try:	opts, args = getopt.getopt(sys.argv[1:], "hd:", ["help", "debug", "dir=", "remote="])
except getopt.GetoptError as err:
	# print help information and exit:
	print(str(err)) # will print something like "option -a not recognized"
	usage()
	sys.exit(2)

# argument parsing.
for o, a in opts:
    if o == "--help":
        usage()
        sys.exit(0)
    elif o == "--debug":
        verbose = True
    elif o == "--param":
        pass #params=a
    elif o == "--dir" or o =="-d":
        dir = a
    else:
        #assert(False!=True, "unhandled option")
        print("error: failed")
        sys.exit(0) 
if (len(args)<2):
    usage()
    sys.exit(1)
print(args)
print ("{0}  -- {1}".format( args[0], args[1]))
from_dir = args[0]
to_dir   = args[1]
from_files = get_files( from_dir)
for a in from_files:
    #print("{0} {1}".format(a, md5(a)))

    result = re.search("(.+)(\..+?)$", os.path.basename(a) )
    name = result.group(1)        
    ext = result.group(2)
    index = -1
    
    skip = False
    done = False
    dest = None
    while not done:
        if index==-1:
            unique = ""
        else:
            unique = ".{0}".format(index)

        dest = "{0}/{1}{2}{3}".format(to_dir, name, unique, ext)
        index = index + 1
        if os.path.exists(dest):
            #print("file exists .. " + dest)
            if (md5(a) == md5(dest)):
                print ("skipping {0} md5 matches {1}".format(a, dest))
                skip = True
                done = True
                continue
            #print ("need to make a new file name {0}".format(os.path.basename(dest)))
            continue
        done = True

    if skip:
        continue
    
    print("copying file from {0} to {1}".format(a, dest))
    os.system("/bin/cp -fp {0} {1}".format(a, dest))
    
