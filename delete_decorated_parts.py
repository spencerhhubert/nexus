import os
import re

def delete_files(directory, regex):
    dir_name = directory
    all_file_names = os.listdir(dir_name)
    total_deleted = 0
    for i in range(len(all_file_names)):
        full_path = os.path.abspath(os.path.join(dir_name, all_file_names[i]))
        removed_extension = all_file_names[i][:-4]
        if re.search(regex, removed_extension) and not os.path.isdir(full_path):
            os.remove(full_path)
            total_deleted = total_deleted + 1
    return total_deleted

print(delete_files("parts/", "p"))