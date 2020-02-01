import argparse
import http.client
import os
import random
import sys
import time

import httplib2
import spintax
from googleapiclient import sample_tools
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)


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
        f.write("file 'videos/" + i + "'\n")
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


# request new Authentication Code
def auth():
    scope = 'https://www.googleapis.com/auth/youtube.upload'
    argv = ['youtube.py', '--noauth_local_webserver']
    services, flags = sample_tools.init(argv, 'youtube', 'v3', __doc__, __name__, scope=scope)
    return services


# request upload video
def upload(services, videos):
    print('indexing shortcodes ....')
    shortcodes = os.listdir('./shortcodes')
    print('reading video description ....')
    f = open('input.txt', 'r')
    title = f.readline()
    title = title.replace('\n', '')
    description = f.readline()
    keywords = f.readline()
    category = 27
    privacy = 'public'
    print('replacing shortcode ....')
    for shortcode in shortcodes:
        f = open('shortcodes/' + shortcode, 'r')
        text = f.readline()
        shortcode = '[' + shortcode.replace('.txt', '', ) + ']'
        if shortcode in title:
            title = title.replace(shortcode, text)
        if shortcode in description:
            description = description.replace(shortcode, text)
        if shortcode in keywords:
            keywords = keywords.replace(shortcode, text)
    print('spinning video detail ....')
    title = spintax.spin(title)
    if '[title]' in description:
        description = description.replace('[title]', title)
    if '[title]' in keywords:
        keywords = keywords.replace('[title]', title)
    keywords = spintax.spin(keywords)
    tags = keywords.split(',')
    description = description.replace('\\n', '\n')
    description = spintax.spin(description)
    body = dict(
        snippet=dict(
            title=title,
            description=description,
            tags=tags,
            categoryId=category
        ),
        status=dict(
            privacyStatus=privacy
        )
    )
    print('make request upload ....')
    return services.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(videos, chunksize=-1, resumable=True)
    )


# uploading video
def resumable_upload(request):
    response = None
    err = None
    retry = 0
    while response is None:
        try:
            print('Uploading video file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print('Video was successfully uploaded, url: https://youtube.com/watch?v=%s' % response['id'])
                    os.system('rm output/*')
                else:
                    exit('The upload failed with an unexpected response: %s' % response)
        except HttpError as err:
            if err.resp.status in [500, 502, 503, 504]:
                err = 'A retriable HTTP error %d occurred:\n%s' % (err.resp.status, err.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as err:
            err = 'A retriable error occurred: %s' % err

        if err is not None:
            print(err)
            retry += 1
            if retry > 10:
                exit('No longer attempting to retry.')

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print('Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)


if __name__ == '__main__':
    print('starting program ....')
    service = auth()
    args = get_args()
    output = render(args.type)
    try:
        upload = upload(service, output)
        print(upload)
        resumable_upload(upload)
    except HttpError as error:
        print('An HTTP error %d occurred:\n%s' % (error.resp.status, error.content))
