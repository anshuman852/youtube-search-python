import json
from typing import Union, List
from urllib.parse import urlencode
import re
from youtubesearchpython.core.constants import *
from youtubesearchpython.core.requests import RequestCore
from youtubesearchpython.core.componenthandler import getValue, getVideoId
from youtubesearchpython.core.playlist import InvalidStatusException

class VideoCore(RequestCore):
    def __init__(self, videoLink: str, componentMode: str, resultMode: int, timeout: int):
        super().__init__()
        self.timeout = timeout
        self.resultMode = resultMode
        self.componentMode = componentMode
        self.videoLink = videoLink
        self.url = 'https://www.youtube.com/watch' + '?' + urlencode({
            'v': getVideoId(self.videoLink)
        })

    def post_request_processing(self):
        self.__extractFromHTML()
        self.__parseSource()
        self.__getVideoComponent(self.componentMode)
        self.result = self.__videoComponent

    async def async_create(self):
        response = await self.asyncGetRequest()
        self.response = response.text
        if response.status_code == 200:
            self.post_request_processing()
        else:
            raise InvalidStatusException('ERROR: Invalid status code.')

    def sync_create(self):
        response = self.syncGetRequest()
        self.response = response.text
        self.resp2=self.response
        if response.status_code == 200:
            self.post_request_processing()
        else:
            raise InvalidStatusException(f'ERROR: Invalid status code.{response.status_code}')
    def __getLikes(self):
        resp=self.resp2
        sentiment=re.search("sentimentBar", resp)
        likes=0
        dislikes=0
        if sentiment:
            tooltip=re.search("tooltip.*?}",str(resp[sentiment.start():(sentiment.start()+200)]))
            tooltip=tooltip.group(0).replace(",","")
            l=re.findall("\d+",str(tooltip))
            likes=int(l[0])
            dislikes=int(l[1])
        return likes,dislikes

    def __extractFromHTML(self):
        f1 = "var ytInitialPlayerResponse = "
        startpoint = self.response.find(f1)
        self.response = self.response[startpoint + len(f1):]
        f2 = ';var meta = '
        endpoint = self.response.find(f2)
        if startpoint and endpoint:
            startpoint += len(f1)
            endpoint += len(f2)
            r = self.response[:endpoint]
            r = r.replace(';var meta = ', "")
            self.response = r
    def __getChannelImage(self):    
        resp=self.resp2
        images=re.findall('https:\/\/yt3.*?"',str(resp))
        if len(images)>1:
            return images[1].replace('"','')
        else:
            return None
    def __parseSource(self) -> None:
        try:
            self.responseSource = json.loads(self.response)
        except Exception as e:
            raise Exception('ERROR: Could not parse YouTube response.')

    def __result(self, mode: int) -> Union[dict, str]:
        if mode == ResultMode.dict:
            return self.__videoComponent
        elif mode == ResultMode.json:
            return json.dumps(self.__videoComponent, indent=4)

    def __getVideoComponent(self, mode: str) -> None:
        videoComponent = {}
        if mode in ['getInfo', None]:
            likes,dislikes=self.__getLikes()
            profileImage=self.__getChannelImage()
            component = {
                'id': getValue(self.responseSource, ['videoDetails', 'videoId']),
                'title': getValue(self.responseSource, ['videoDetails', 'title']),
                'duration': {
                    'secondsText': getValue(self.responseSource, ['videoDetails', 'lengthSeconds']),
                },
                'viewCount': {
                    'text': getValue(self.responseSource, ['videoDetails', 'viewCount'])
                },
                'thumbnails': getValue(self.responseSource, ['videoDetails', 'thumbnail', 'thumbnails']),
                'description': getValue(self.responseSource, ['videoDetails', 'shortDescription']),
                'channel': {
                    'name': getValue(self.responseSource, ['videoDetails', 'author']),
                    'id': getValue(self.responseSource, ['videoDetails', 'channelId']),
                    'profileImage':profileImage,
                },
                'allowRatings': getValue(self.responseSource, ['videoDetails', 'allowRatings']),
                'averageRating': getValue(self.responseSource, ['videoDetails', 'averageRating']),
                'keywords': getValue(self.responseSource, ['videoDetails', 'keywords']),
                'isLiveContent': getValue(self.responseSource, ['videoDetails', 'isLiveContent']),
                'publishDate': getValue(self.responseSource, ['microformat', 'playerMicroformatRenderer', 'publishDate']),
                'uploadDate': getValue(self.responseSource, ['microformat', 'playerMicroformatRenderer', 'uploadDate']),
                'likesCount':likes,
                'dislikesCount':dislikes,
            }
            component['isLiveNow'] = component['isLiveContent'] and component['duration']['secondsText'] == "0"
            component['link'] = 'https://www.youtube.com/watch?v=' + component['id']
            component['channel']['link'] = 'https://www.youtube.com/channel/' + component['channel']['id']
            videoComponent.update(component)
        if mode in ['getFormats', None]:
            component = {
                'streamingData': getValue(self.responseSource, ['streamingData']),
            }
            videoComponent.update(component)
        self.__videoComponent = videoComponent
