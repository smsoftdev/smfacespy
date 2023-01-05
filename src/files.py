#
# reads files.yaml 
#

import yaml

def get_files(key:str = None):
    with open('files.yaml') as f:
        files = yaml.load(f, Loader=yaml.FullLoader)['files']
        if key is None:
            return files
        return files[key]
    
if __name__== "__main__":
    print('files:', get_files())
    print('upload:', get_files('upload'))
    print('api_result:', get_files('api_result'))
