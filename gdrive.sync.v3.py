
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


try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-sync.json
#SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
#SCOPES = 'https://www.googleapis.com/auth/drive.photos.readonly'
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive Sync Program'


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
    credential_path = os.path.join(credential_dir,  'drive-sync.json')

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

def upload_to_gdrive(service, name, type, location, parent=None):
    # upload a file
    body = {
        'name' : name,
        'mimeType' : type,
    }
    if parent:
        body['parents'] = [ parent ]
    media = MediaFileUpload( location, mimetype=type, resumable=True )
    return  service.files().create(body=body, media_body=media, fields='*').execute()

def md5(fname):
        hasher = hashlib.md5()
        blocksize=65536
        afile = open(fname, 'rb')
        buf = afile.read(blocksize)
        while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
        return hasher.hexdigest()

def check_remote(service, name, type, location, parent=None):
    # upload a file
    body = {
        'name' : name,
        'mimeType' : type,
    }
    query = "mimeType='" + type + "'"
    if parent:
        query = query + " and  '" + parent + "' in parents"

    query = query + " and trashed=false and name='" + name + "'"
    
    results =  service.files().list( fields="nextPageToken,files" , spaces='drive', q=query).execute();
    items = results.get('files', [])
    if not items:
        return False

    m = md5( location )
    for item in items:
        if item["md5Checksum"] == m:
            print( "Check Sum:" + m + " <=> " + item["md5Checksum"] + " === matches ===" )
            return True
        print( "Check Sum:" + m + " <=> " + item["md5Checksum"] )
        
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
    print(dir(service))
    about = service.about().get(fields="*").execute();
    print(json.dumps(about, indent=4))
    #print(json.dumps(service.comments().list(fields="*").execute(), indent=4))
    print("dump")
    dire = service.files().get( fileId="0AMyFZD6ay2zeUk9PVA", fields="*" ).execute();
    print(json.dumps(dire, indent=4))
   # set_saved_rootid("0AMyFZD6ay2zeUk9PVA")
    rootFileId = get_saved_rootid()
    if rootFileId != None:
        #pprint.pprint(inspect.getmembers(service))
        dire = service.files().get( fileId=rootFileId, fields="*" ).execute();
        print(json.dumps(dire, indent=4))
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
                        print ("JSON\n" + json.dumps(item, indent = 4))
                      
            if not page_token:
                break;
 
    
    testdirs =  service.files().list( fields="nextPageToken,files" , spaces='drive', q="mimeType='application/vnd.google-apps.folder' and  '" + rootFileId + "' in parents and trashed=false and name='TestDrive'").execute();
    #print(json.dumps(test_dir, indent=4))
    testdriveid=None
    if not testdirs['files']:
        print('no entries')
        test_dir = create_gdrive_folder( service, "TestDrive", rootFileId )
    else:
        test_dir = testdirs['files'][0]

    if test_dir is None:
        print("Failed to create TestDrive")
        os.sys.exit(0)
            
    #test_dir = test_dir['id']
    print(json.dumps(test_dir, indent=4))

    # upload a file
    # check if files exists in remote disk
    if not check_remote(service, "test_image.jpeg", "image/jpeg", "./test.jpeg", test_dir['id']):
        print("uploading .... ")
        file = upload_to_gdrive(service, "test_image.jpeg", "image/jpeg", "./test.jpeg", test_dir['id'])

        print(json.dumps(file, indent=4))
    print(test_dir['id'])
    os.sys.exit(0)
    #dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="name='My Drive'").execute();
    print(json.dumps(dire, indent=4))
    #q="mimeType='application/vnd.google-apps.folder' and name='photos'", 
    #dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="mimeType='application/vnd.google-apps.folder' and  '0B8yFZD6ay2zefm0xRkFpdGh2UC1RZEc4bU9DNjdfaGk4MHplc2hZYV9RdTNxT0VNVm5xV3M' in parents ").execute();
    dire = service.files().list( fields="nextPageToken,files" , spaces='drive', q="'0B8yFZD6ay2zefm0xRkFpdGh2UC1RZEc4bU9DNjdfaGk4MHplc2hZYV9RdTNxT0VNVm5xV3M' in parents ").execute();
    #dire = service.files().list( fields="nextPageToken,files" , spaces='photos').execute();
    print(json.dumps(dire, indent=4))

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
                    print ("JSON\n" + json.dumps(item, indent = 4))
        if not page_token:
            break;
        results = service.files().list( pageSize=10,fields="nextPageToken,files", pageToken=page_token).execute()
            
    

if __name__ == '__main__':
    main()

