import argparse
import http.client
import os
import random
import time

import httplib2
import spintax
from googleapiclient import sample_tools
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import pyppeteer as puppeteer
import requests
import asyncio

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)


# get list file (videos or images)
def get_list_files(source_type):
    if source_type == 'videos':
        print('indexing video files ....')
        return [x for x in os.listdir('./videos') if '.' in x]
    if source_type == 'images':
        print('indexing image files ....')
        return [x for x in os.listdir('./images') if '.' in x]
    print('indexing video temp files ....')
    return [x for x in os.listdir('./videos') if x.startswith(source_type)]


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
    parser.add_argument('--method', required=False, help='Upload with Puppeteer or API', choices=('puppeteer', 'api'))
    return parser.parse_args()


# rendering video
def render(source_type):
    print('start rendering ....')
    filename = str(time.time()).replace('.', '')
    files = get_list_files(source_type)
    if source_type == 'videos':
        files = random.sample(files, 15)
        for file in files:
            name = os.path.join('.', 'videos', "temp" + str(files.index(file) + 1) + ".ts")
            print(os.path.join('.', 'videos', file))
            filepath = os.path.join('.', 'videos', file)
            os.system("ffmpeg -i \"" + filepath + "\" -c copy -bsf:v h264_mp4toannexb -f mpegts " + name)
        files = get_list_files('temp')
        write_list_txt(files)
        print('rendering all video to one file ....')
        os.system('ffmpeg -f concat -safe 0 -i mylist.txt -c copy -bsf:a aac_adtstoasc output/' + filename + '.mp4')
    else:
        print('converting image to video file ....')
        maximum = len(files) - 1
        for i in range(random.randint(80, 240)):
            index = random.randint(0, maximum)
            os.system('ffmpeg -r 1/' + str(random.randint(5, 15))
                      + '-f image2 -s 1920x1080 -i images/' + files[index]
                      + '-vcodec libx264 -crf 25 -pix_fmt yuv420p video/temp'
                      + str(time.time()).replace('.', '') + '.mp4')
        files = get_list_files('temp')
        write_list_txt(files)
        print('rendering all video to one file ....')
        os.system('ffmpeg -f concat -safe 0 -i mylist.txt -c copy output/' + filename + '.mp4')
    print('removing temp video file ....')
    for file in os.listdir('videos'):
        if file.startswith('temp'):
            os.remove(os.path.join('videos', file))
    return 'output/' + filename + '.mp4'


# request new Authentication Code
def auth():
    scope = 'https://www.googleapis.com/auth/youtube.upload'
    argv = ['youtube.py', '--noauth_local_webserver']
    services, flags = sample_tools.init(argv, 'youtube', 'v3', __doc__, __name__, scope=scope)
    return services


# get video detail
def spin_video_detail():
    print('indexing shortcodes ....')
    shortcodes = os.listdir('./shortcodes')
    print('reading video description ....')
    f = open('input.txt', 'r')
    title = f.readline()
    title = title.replace('\n', '')
    description = f.readline()
    keywords = f.readline()
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
    return dict(
        title=title,
        desc=description,
        tags=tags
    )


# request upload video
def upload(services, videos):
    detail = spin_video_detail()
    detail['categoryId'] = 27
    privacy = 'public'
    body = dict(
        snippet=detail,
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
                    # f = open('uploaded_video.txt', 'a')
                    print(response)
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


# upload video with puppeteer
async def upload_with_puppeteer(video_path):
    detail = spin_video_detail()
    print('get browser ws endpoint ..')
    response = requests.get('http://localhost:8080/json/version')
    web_socket_debugger_url = response.json()['webSocketDebuggerUrl']
    print('connect to browser ..')
    browser = await puppeteer.connect({
        'browserWSEndpoint': web_socket_debugger_url,
        'defaultViewport': None
    })
    pages = await browser.pages()
    page = pages[len(pages) - 1]
    print('opening youtube upload page ..')
    await page.goto("https://youtube.com/upload", {"waitUntil": "networkidle0"})
    time.sleep(3)
    print('uploading video file ..')
    element_upload = await page.querySelector("input[type=\"file\"][name=\"Filedata\"]")
    await element_upload.uploadFile(video_path)
    time.sleep(10)
    print('entering title ..')
    await page.type(".title-textarea > #container > div > #child-input > #input > #textbox", detail['title'])
    print('entering description ..')
    await page.type(".description-textarea > #container > div > #child-input > #input > #textbox", detail['desc'])
    print('wait for upload complete ..')
    await page.waitForFunction('!document.querySelector(".progress-label").innerText.includes("%")', {'timeout': 0})
    print('Upload selesai!!!')
    print(detail['title'])
    print(detail['desc'])
    print(detail['tags'])


if __name__ == '__main__':
    print('starting program ....')
    # service = auth()
    args = get_args()
    output = render(args.type)
    asyncio.get_event_loop().run_until_complete(upload_with_puppeteer(output))
    # try:
    #     upload = upload(service, output)
    #     print(upload)
    #     resumable_upload(upload)
    # except HttpError as error:
    #     print('An HTTP error %d occurred:\n%s' % (error.resp.status, error.content))
