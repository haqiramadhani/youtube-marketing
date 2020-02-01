import argparse
import os
import random
import sys
import time

from googleapiclient import sample_tools


# get list file (videos or images)
def get_list_files(source_type):
    if source_type == 'videos':
        print('indexing video files ....')
        return os.listdir('./videos')
    if source_type == 'images':
        print('indexing image files ....')
        return os.listdir('./images')
    print('indexing video temp files ....')
    return [x for x in os.listdir('./videos') if x.startswith('t')]


# write file for concat
def write_list_txt(list_files):
    print('writing list file to mylist.txt ....')
    f = open('mylist.txt', 'w')
    for i in list_files:
        f.writelines("file '" + i + "'")
    f.close()


# parsing argument from commandline
def get_args():
    print('reading argument ....')
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', required=True, help='From Video or Images', choices=('videos', 'images'))
    return parser.parse_args()


# rendering video
def render(source_type):
    print('start rendering ....')
    filename = str(time.time()).replace('.', '')
    files = get_list_files(source_type)
    if source_type == 'videos':
        write_list_txt(files)
    else:
        print('converting image to video file ....')
        maximum = len(files) - 1
        for i in range(random.randint(80, 240)):
            index = random.randint(0, maximum)
            os.system('ffmpeg -r 1/' + random.randint(5, 15)
                      + '-f image2 -s 1920x1080 -i images/' + files[index]
                      + '-vcodec libx264 -crf 25 -pix_fmt yuv420p video/t'
                      + str(time.time()).replace('.', '') + '.mp4')
        files = get_list_files('t')
        write_list_txt(files)
    print('rendering all video to one file ....')
    os.system('ffmpeg -f concat -safe 0 -i mylist.txt -c copy output/' + filename + '.mp4')
    print('removing temp video file ....')
    os.system('rm videos/t*')
    return 'output/' + filename + '.mp4'


def auth():
    scope = 'https://www.googleapis.com/auth/youtube.upload'
    services, flags = sample_tools.init(['youtube.py', '--noauth_local_webserver'], 'youtube', 'v3', __doc__, __name__, scope=scope)
    return services


if __name__ == '__main__':
    print('starting program ....')
    service = auth()
    args = get_args()
    output = render(args.type)
