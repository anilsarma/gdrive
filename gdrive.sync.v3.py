#!/usr/bin/python

#from __future__ import print_function
import httplib2
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import apiclient.http
import hashlib
from os import listdir

import subprocess
import os
import json

"""
 Pref-requisites:
 pip install --upgrade google-api-python-client

 https://console.developers.google.com/flows/enableapi?apiid=gmail  // save the json into the .credentials directory

"""


class ExifTool(object):
    sentinel = "{ready}\n"

    def __init__(self, executable="/usr/bin/exiftool"):
        self.executable = executable

        # def __enter__(self):
        self.process = subprocess.Popen(
            [self.executable, "-stay_open", "True", "-@", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    # return self

    def __exit__(self, exc_type, exc_value, traceback):
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


def get_dirs(dir):
    if not exists(dir):
        return list()

    result = [join(dir, f) for f in listdir(dir) if isdir(join(dir, f))]
    return sorted(result)


def get_dirs_relative(dir):
    if not exists(dir):
        return list()

    result = [f for f in listdir(dir) if isdir(join(dir, f))]
    return sorted(result)


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-sync.json
# SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
# SCOPES = 'https://www.googleapis.com/auth/drive.photos.readonly'
# CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'DriveSyncProgram'


def get_files(dir):
    print("get files:", dir)
    output = []
    for r, dirs, files in os.walk(dir):
        output += [os.path.join(r, f) for f in files]
    return sorted(output)


def get_credentials():
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
    # credential_path = os.path.join(credential_dir,  'dri.json')
    CLIENT_SECRET_FILE = os.path.join(credential_dir, 'gdrive.json')
    OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
    # OAUTH_SCOPE = 'https://www.googleapis.com/auth/gmail.compose'
    store = Storage(os.path.join(credential_dir, 'gdrive.storage'))
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, scope=OAUTH_SCOPE)
        flow.user_agent = APPLICATION_NAME
        # if flags:
        http = httplib2.Http()
        credentials = tools.run_flow(flow, store, args, http=http)
        # else: # Needed only for compatibility with Python 2.6
        #   credentials = tools.run(flow, store)
        # print('Storing credentials to ' + credential_path)
    return credentials


def get_saved_rootid():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'gdrive.root.dir.json')
    root = None
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
    credential_path = os.path.join(credential_dir, 'gdrive.root.dir.json')

    data = {'fileId': root}
    with open(credential_path, "w") as data_file:
        data_file.write(json.dumps(data))
        data_file.close()


def find_rootid(service, id):
    if id is None:
        return None
    dire = service.files().get(fileId=id, fields="*").execute();
    if 'parents' not in dire:
        set_saved_rootid(id)
    else:
        for p in dire['parents']:
            id = find_rootid(service, p)
    return id


def create_gdrive_folder(service, name, parentID=None):
    # Create a folder on Drive, returns the newely created folders ID
    body = {
        'name': name,
        'mimeType': "application/vnd.google-apps.folder"
    }
    if parentID:
        body['parents'] = [parentID]

    return service.files().create(body=body, fields="*").execute()


def gdrive_check_create_folder(service, name, parent):
    query = "mimeType='application/vnd.google-apps.folder' and  '{0}' in parents and trashed=false and name='{1}'".format(
        parent, name)
    dirs = service.files().list(fields="nextPageToken,files", spaces='drive', q=query).execute();
    if not dirs['files']:
        print('no entries')
        google_file = create_gdrive_folder(service, name, parent)
    else:
        google_file = dirs['files'][0]

    return google_file


def upload_to_gdrive(service, name, type, location, parent=None):
    # upload a file
    tmp = exiftool.get_metadata(location)

    # print (tmp)
    # os.exit(0)
    body = tmp[0]
    body['name'] = name
    body['mimeType'] = type

    if parent:
        body['parents'] = [parent]

    media = apiclient.http.MediaFileUpload(location, mimetype=type, resumable=True)
    return service.files().create(body=body, media_body=media, fields='*').execute()


def md5(fname):
    hasher = hashlib.md5()
    blocksize = 65536
    afile = open(fname, 'rb')
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()


def check_remote_base(service, name, type, location, parent=None):
    # upload a file
    body = {
        'name': name,
        'mimeType': type,
    }
    query = "mimeType='{0}'".format(type)
    if parent:
        query = "{0} and  '{1}' in parents".format(query, parent)
    query = "{0} and trashed=false and name='{1}'".format(query, name)

    results = service.files().list(fields="nextPageToken,files", spaces='drive', q=query).execute();
    items = results.get('files', [])
    if not items:
        return 0  # no items found.

    m = md5(location)
    for item in items:
        if item["md5Checksum"] == m:
            print("Check Sum: {0} <=> {1} ({2},{3}] === matches ===".format(m, item["md5Checksum"], name, location))
            return 1  # found and matches
        print("Check Sum:" + m + " <=> " + item["md5Checksum"])

    return 2  # found files but md5 does not match.


def check_remote(service, name, type, location, parent=None):
    ret = check_remote_base(service, name, type, location, parent)
    if ret == 1:
        return True  # found a exact match
    return False  # no matching file found.


def check_and_upload_to_gdrive(service, name, type, location, parent=None, folder=None):
    ret = check_remote_base(service, name, type, location, parent)
    if ret != 1:
        print("uploading {0} from {1} to {2}".format(name, location, parent))
        return upload_to_gdrive(service, name, type, location, parent)


def extension_filter(f):
    ext = os.path.splitext(f)[1][1:].strip()
    if ext.upper() in ["JPG", "PY"]:
        return True
    return False


def get_mime_type(f):
    ext = os.path.splitext(f)[1][1:].strip().upper()
    type = "image/jpeg"
    if ext in ['MOV', "MP4", 'MPEG']:
        return "video/mpeg"

    if ext in ['JPG', 'JPEG']:
        return "image/jpeg"
    return "text/plain"


MIME_TYPE_FOLDER = "application/vnd.google-apps.folder"


def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    file_metadata = {
        'name': 'photos',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    rootFileId = get_saved_rootid()
    if rootFileId != None:
        dire = service.files().get(fileId=rootFileId, fields="*").execute();
    else:
        page_token = None
        # parents = {}
        # look up the root folder.
        while rootFileId is None:
            results = service.files().list(pageSize=100, fields="nextPageToken, files", pageToken=page_token,
                                           q="mimeType='application/vnd.google-apps.folder'").execute()
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
                            rootFileId = find_rootid(service, p)
                            if rootFileId is not None:
                                break
                        print('{0} ({1})'.format(item['name'], item['id']))
                        # print ("JSON\n" + json.dumps(item, indent = 4))

            if not page_token:
                break;

    base_drive_file = gdrive_check_create_folder(service, args.google_folder, rootFileId)
    uploaddir_id = base_drive_file['id']

    files = get_files(args.dir)
    result = [f for f in files if extension_filter(f)]
    root_dir = os.path.abspath(args.dir)
    for f in result:
        # name = os.path.basename(f)
        long_name = os.path.abspath(f)
        relpath = os.path.relpath(long_name, root_dir)
        directory_id = uploaddir_id
        dirname = os.path.dirname(relpath)
        name = os.path.relpath(relpath, dirname)
        # print("relpath has a subdir", relpath, dirname, name)
        dirnames = [] if dirname == "" else dirname.split(os.path.sep)
        for d in dirnames:
            # print ("checking for direcotyr", d)
            gdrive_dir = gdrive_check_create_folder(service, d, directory_id)
            directory_id = gdrive_dir['id']

        mime_type = get_mime_type(name)
        check_and_upload_to_gdrive(service, name, mime_type, f, directory_id)


import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument("--dir", help="directory to process", required=True)
    parser.add_argument("--google-folder", help='folder in google directory', default='PhotoBackup')
    args = parser.parse_args()

    exiftool = ExifTool()
    main()
