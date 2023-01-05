import imp
import os

from files import get_files


def make_upload_path(token: str) -> str:
    upload = get_files('upload')
    return os.path.join(os.path.expanduser(upload), token)

def make_api_result_path(token: str) -> str:
    api_result = get_files('api_result')
    return os.path.join(os.path.expanduser(api_result), token)

def make_work_path(token: str) -> str:
    return os.path.join(os.path.expanduser('~/work'), token)

def make_upload_field_path(field: str, token: str) -> str:
    upload = get_files('upload')
    user_data = os.path.expanduser(upload)
    user_data_field = os.path.join(user_data, field)
    return os.path.join(user_data_field, token)

def make_api_result_field_path(field: str, token: str) -> str:
    api_result = get_files('api_result')
    user_data = os.path.expanduser(api_result)
    user_data_field = os.path.join(user_data, field)
    # yyyy-mmdd-hh24miss-uuuuu
    user_data_field_yyyy = os.path.join(user_data_field, token[0:4])
    user_data_field_mmdd = os.path.join(user_data_field_yyyy, token[5:9])
    return os.path.join(user_data_field_mmdd, token)
