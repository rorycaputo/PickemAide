import os
import requests

def write_string_to_file(string, file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(file_path, 'w') as file:
        if isinstance(string, requests.Response):
            file.write(string.text)
        else:
            file.write(string)
