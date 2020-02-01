import argparse
import os


# get list file (videos or images)
def get_list_files(source_type):
    if source_type == 'videos':
        return os.listdir('./videos')
    else:
        return os.listdir('./images')


def write_list_txt(list_files):
    file = open('mylist.txt', 'w')
    for i in list_files:
        file.writelines("file '" + i + "'")
    file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', required=True, help='From Video or Images', choices=('videos', 'images'))
    args = parser.parse_args()
    files = get_list_files(args.type)
    write_list_txt(files)
