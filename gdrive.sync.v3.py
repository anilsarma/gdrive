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

import subprocess
import os
import json
import sqlite3
import googleapiclient

def get_credentials_dir():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    return  credential_dir


class ExifTool(object):

    sentinel = "{ready}\n"

    def __init__(self, executable="/usr/bin/exiftool"):
        self.executable = executable

   # def __enter__(self):
        self.process = subprocess.Popen(
            [self.executable, "-stay_open", "True",  "-@", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
       # return self

    def  __exit__(self, exc_type, exc_value, traceback):
        self.process.stdin.write("-stay_open\nFalse\n")
        self.process.stdin.flush()

    def execute(self, *args):
        args = args + ("-execute\n",)
        self.process.stdin.write(str.join("\n", args))
        self.process.stdin.flush()
        output = ""
        fd = self.process.stdout.fileno()
        while not output.endswith(self.sentinel):
            output += os.read(fd, 4096)
        return output[:-len(self.sentinel)]

    def get_metadata(self, filenames):
        return json.loads(self.execute("-G", "-j", "-n", filenames))

class UploadDB(object):

    sentinel = "{ready}\n"

    def __init__(self, db="upload.db"):
        self.db = db
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()
        try:
            self.cursor.execute('''CREATE TABLE UPLOAD_T
            (id text primary key, json text)''')
        except sqlite3.OperationalError:
            pass 

    def  __exit__(self, exc_type, exc_value, traceback):
        pass

    def save(self, id, data ):
        try:
            self.cursor.execute("insert into UPLOAD_T values ( '{0}', '{1}')".format(id, json.dumps(data)))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def get(self,id):
        result = self.conn.execute("SELECT * FROM UPLOAD_T where id='{0}'".format(id))
        data = result.fetchall()
        if len(data)==0:
            return None
        return json.loads(data[0][1])
       

exiftool = ExifTool()
db = UploadDB( os.path.join(get_credentials_dir(), "drive-sync.uploaded.json"))
filter=None
#try:
#    import argparse
#    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
#except ImportError:
#    flags = None

VERSION="1.1"
dir="."
base_drive="PhotoBackup"
remote_drive=None

def usage():
    print(sys.argv[0], " <options>")
    print("\t version ", VERSION, " gdrive sync")
    print("\t--dir     <directory> directory to process default={0}".format(dir))
    print("\t--remote  <directory> gdrive directory to upload into default=None")
    print("\t--base    <directory> gdrive base directory default={0}".format(base_drive))
    print("\t--filter  <all|jpg|jpeg|mov|mts> list of files to upload")
    os.sys.exit(1)


try:
	opts, args = getopt.getopt(sys.argv[1:], "hd:f:b:", ["help", "debug", "dir=", "remote=", "filter=", "base="])
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
    elif o=="--remote":
        remote_drive=a
    elif o == "--filter" or o =="-f":
        filter = a
    elif o == "--base" or o =="-b":
	 base_drive=a
    else:
        #assert(False!=True, "unhandled option")
        print("error: failed")
        sys.exit(0) 
    
if remote_drive==None:
	print("error: remote drive not specified ")
	usage()
	sys.exit(2)

def get_dirs(dir):
        if not exists(dir):
                return list()

        result = [ join(dir,f) for f in listdir(dir) if isdir(join(dir,f)) ]
        return sorted(result)

def get_dirs_relative(dir):
        if not exists(dir):
                return list()

        result = [ f for f in listdir(dir) if isdir(join(dir,f)) ]
        return sorted(result)

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-sync.json
#SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
#SCOPES = 'https://www.googleapis.com/auth/drive.photos.readonly'
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive Sync Program'

def get_files(dir):
    if not exists(dir):
        return list()
    result = [ join(dir,f) for f in listdir(dir) if isfile(join(dir,f)) ]
    mtime = lambda f: os.stat(f).st_mtime

    return sorted(result, key=mtime)



def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    
    credential_dir = get_credentials_dir()
    credential_path = os.path.join(credential_dir,  'drive-sync.json')
    db_path = os.path.join(credential_dir, "drive-sync.uploaded.db")
        
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_saved_rootid():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,  'drive-sync.root.dir.json')
    root=None
    try:
        with open(credential_path) as data_file:
            data = json.load(data_file)
            root = data['fileId']
    except:
        pass
    return root

def set_saved_rootid(root):
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,  'drive-sync.root.dir.json')

    data = { 'fileId' : root }
    with open(credential_path, "w") as data_file:
        data_file.write( json.dumps(data))
        data_file.close()
   
def find_rootid(service, id):
    if id is None:
        return None
    dire = service.files().get( fileId=id, fields="*" ).execute();
    if 'parents' not in dire:
        set_saved_rootid( id )
    else:
        for p in dire['parents']:
            id = find_rootid(service, p )
    return id


def create_gdrive_folder(service, name, parentID = None):
    # Create a folder on Drive, returns the newely created folders ID
    body = {
        'name': name,
        'mimeType': "application/vnd.google-apps.folder"
    }
    if parentID:
        body['parents'] = [ parentID ]
    
    return service.files().create(body = body, fields="*").execute()


def gdrive_check_create_folder( service, name, parent):

    query="mimeType='application/vnd.google-apps.folder' and  '{0}' in parents and trashed=false and name='{1}'".format(parent, name)
    dirs =  service.files().list( fields="nextPageToken,files" , spaces='drive', q=query).execute();
    file = None
    if not dirs['files']:
        print('no entries')
        file = create_gdrive_folder( service, name, parent)
    else:
        file = dirs['files'][0]

    if file is None:
        print("Failed to create {0}".format(name))
        #os.sys.exit(0)
            
    return file

def upload_to_gdrive(service, name, type, location, parent=None):
    # upload a file
    tmp = exiftool.get_metadata( location )

    #os.exit(0)
    body = tmp[0]
    body['name']=  name
    body['mimeType']= type

    if parent:
        body['parents'] = [ parent ]

    #print(json.dumps(tmp[0], indent=4))    
    #os.sys.exit(0)
    media = MediaFileUpload( location, mimetype=type, resumable=True )
    tries = 0
    while tries < 5:
        tries = tries + 1
        try:
            item =   service.files().create(body=body, media_body=media, fields='*').execute()
        except googleapiclient.errors.HttpError:
            print("retrying .. after failure")
            continue
        db.save(os.path.abspath(location), item)
        break
    return item

def md5(fname):
        hasher = hashlib.md5()
        blocksize=65536
        afile = open(fname, 'rb')
        buf = afile.read(blocksize)
        while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
        return hasher.hexdigest()

def check_remote_base(service, name, type, location, parent=None):
    # upload a file
    saved = db.get(os.path.abspath(location))
    m = None

    if saved:
        m = md5( location )
        if saved["md5Checksum"] == m:
            print( "Check Sum: {0} <=> {1} ({2},{3}] === matches saved ===".format(m, saved["md5Checksum"], name, location) )
            return 1 # same as previousloaded.
    body = {
        'name' : name,
        'mimeType' : type,
    }
    query = "mimeType='{0}'".format(type)
    if parent:
        query = "{0} and  '{1}' in parents".format(query, parent)

    query = "{0} and trashed=false and name='{1}'".format(query, name)
    
    results =  service.files().list( fields="nextPageToken,files" , spaces='drive', q=query).execute();
    items = results.get('files', [])
    if not items:
        return 0 #no items found.

    if not m:
        m = md5( location )

    for item in items:
        if item["md5Checksum"] == m:
            print( "Check Sum: {0} <=> {1} ({2},{3}] === matches ===".format(m, item["md5Checksum"], name, location) )
            db.save(os.path.abspath(location), item)
            return 1 # found and matches
        print( "Check Sum:" + m + " <=> " + item["md5Checksum"] )
        
    return 2 # found files but md5 does not match.

def check_remote(service, name, type, location, parent=None):
    ret = check_remote_base(service,name, type, location, parent)
    if ret == 1:
        return True # found a exact match
    return False # no matching file found.
 
def check_and_upload_to_gdrive(service, name, type, location, parent=None):
    ret = check_remote_base(service, name, type, location, parent)
    if ret != 1:
        print("uploading {0} from {1} to {2}".format(name, location, parent))
        return upload_to_gdrive(service,name, type, location, parent)

def extension_filter(f):
    ext = os.path.splitext(f)[1][1:].strip()
    ext = ext.upper()
    if filter==None or filter.upper() == "JPEG":
        if (ext == "JPEG" or ext == "JPG" ):
            return True
    elif filter.upper() == "MOV" or filter.upper() == "MTS":
        if (ext == "MOV" or ext == "MTS" ):
            return True
    elif filter.upper() == "ALL":
         if (ext == "JPEG" or ext == "JPG" or ext =="MOV" or ext == "MP3" or ext == "MTS"):
             return True
    return False

MIME_TYPE_FOLDER="application/vnd.google-apps.folder"
def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

   # results = service.files().list(
    #    pageSize=100,fields="nextPageToken, files").execute()

    file_metadata = {
        'name' : 'photos',
        'mimeType' : 'application/vnd.google-apps.folder'
    }
    #print(dir(service))
    #about = service.about().get(fields="*").execute();
    #print(json.dumps(about, indent=4))
    #print(json.dumps(service.comments().list(fields="*").execute(), indent=4))
    #print("dump")
    #dire = service.files().get( fileId="0AMyFZD6ay2zeUk9PVA", fields="*" ).execute();
    #print(json.dumps(dire, indent=4))
   # set_saved_rootid("0AMyFZD6ay2zeUk9PVA")
    rootFileId = get_saved_rootid()
    if rootFileId != None:
        #pprint.pprint(inspect.getmembers(service))
        dire = service.files().get( fileId=rootFileId, fields="*" ).execute();
        #print(json.dumps(dire, indent=4))
        #os.sys.exit(0)
    else:
        page_token=None
        parents = {}
        while rootFileId is None:
            results = service.files().list(
                pageSize=100,fields="nextPageToken, files", pageToken=page_token,  q="mimeType='application/vnd.google-apps.folder'").execute()
            items = results.get('files', [])
            page_token = results.get('nextPageToken')
            if not items:
                print('No files found.')
                break
            else:
                print('Files:')
                for item in items:
                    if 'parents' in item:
                        for p in item['parents']:
                            rootFileId=find_rootid(service, p )
                            if rootFileId != None:
                                break
                            if rootFileId != None:
                                break
                       #     if p not in parents:
                       #         parents[p] = p
                        print('{0} ({1})'.format(item['name'], item['id']))
                        #print ("JSON\n" + json.dumps(item, indent = 4))
                      
            if not page_token:
                break;
 
    
    #query="mimeType='application/vnd.google-apps.folder' and  '{0}' in parents and trashed=false and name='{1}'".format(rootFileId, base_drive)
    #testdirs =  service.files().list( fields="nextPageToken,files" , spaces='drive', q=query).execute();
    #print(json.dumps(test_dir, indent=4))

    #if not testdirs['files']:
    #    print('no entries')
    #    test_dir = create_gdrive_folder( service, base_drive, rootFileId )
    #else:
    #    test_dir = testdirs['files'][0]

    #if test_dir is None:
    #    print("Failed to create " + base_drive)
    #    os.sys.exit(0)
            
    base_drive_file = gdrive_check_create_folder(service, base_drive, rootFileId )

    #base_drive_file = base_drive_file['id']
    #print(json.dumps(base_drive_file, indent=4))
    remote_file=None
    if remote_drive:
        print("checking remote drive {0}".format(remote_drive))
        remote_file = gdrive_check_create_folder( service, remote_drive, base_drive_file['id'])
    # upload a file
    # check if files exists in remote disk

    uploaddirID=base_drive_file['id']
    if remote_file:
        uploaddirID=remote_file['id']
  
    #print("{0} {1}".format( "directory ", dir ))
    ext = "JPG"
    files = get_files(dir)
    result = [  join("", f) for f in files if  extension_filter(f) ]
    for f in result:
        name = os.path.basename(f)
        r = re.search(".+\.(.+)$", name)
        ext = r.group(1)
        type = "image/jpeg"
        if ext.upper() == "MOV" or ext.upper() == "MTS":
            type = "video/mpeg"
        check_and_upload_to_gdrive(service, name, type, f, uploaddirID)

    os.sys.exit(0)

    #dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="name='My Drive'").execute();
    #print(json.dumps(dire, indent=4))
    #q="mimeType='application/vnd.google-apps.folder' and name='photos'", 
    #dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="mimeType='application/vnd.google-apps.folder' and  '0B8yFZD6ay2zefm0xRkFpdGh2UC1RZEc4bU9DNjdfaGk4MHplc2hZYV9RdTNxT0VNVm5xV3M' in parents ").execute();
    #dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="'0B8yFZD6ay2zefm0xRkFpdGh2UC1RZEc4bU9DNjdfaGk4MHplc2hZYV9RdTNxT0VNVm5xV3M' in parents ").execute();
    #dire = service.files().list( fields="nextPageToken,files" , spaces='photos').execute();
    #print(json.dumps(dire, indent=4))

    os.sys.exit(0);
    results = service.files().list(
        pageSize=100,fields="nextPageToken, files", body=file_metadata).execute()
    
    while True:
        #results = service.files().list(
            #pageSize=100,fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        page_token = results.get('nextPageToken')
        print ("next token"+ str(page_token))

        #print results
        
        if not items:
            print('No files found.')
            break
        else:
            print('Files:')
            for item in items:
                if item['mimeType'] == MIME_TYPE_FOLDER:
                    print('{0} ({1})'.format(item['name'], item['id']))
                    #print ("JSON\n" + json.dumps(item, indent = 4))
        if not page_token:
            break;
        results = service.files().list( pageSize=10,fields="nextPageToken,files", pageToken=page_token).execute()
            
    

if __name__ == '__main__':
    main()

