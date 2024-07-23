"""
$description Global live broadcasting social platform.
$url rplay.live
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments, PluginError, pluginmatcher
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://rplay\.live/(?P<channel_id>c/[\d\w]+/live|live/[\d\w]+)"
))
class RPlayLive(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "token",
            sensitive=True,
            help="JWT token found in `Authorization` header"
        ),
        PluginArgument(
            "oid",
            sensitive=True,
            help="user id corresponding to token"
        ),

    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        channel_id = self.match.group("channel_id")

        if channel_id.startswith('c'):
            self._username = re.search(r'c/([\d\w]+)/live', channel_id)[1]
            self._user_id = None
        else:
            self._user_id = re.search(r'live/([\d\w]+)', channel_id)[1]
            self._username = None
        self._userinfo = None

        self.session.http.headers.update({"Referer": "https://rplay.live"})

    @property
    def user_id(self):
        if self._user_id:
            return self._user_id
        else:
            assert self._username
            r = self.session.http.get(f'https://api.rplay.live/account/getuser?customUrl={self._username}')
            self._userinfo = r.json()
            self._user_id = self._userinfo['_id']
            return self._user_id

    @property
    def nickname(self):
        if not self._userinfo:
            r = self.session.http.get(f'https://api.rplay.live/account/getuser?userOid={self.user_id}')
            self._userinfo = r.json()
        return self._userinfo.get('nickname')

    def _get_streams(self):
        live_info = self.session.http.get(f'https://api.rplay.live/live/play?creatorOid={self.user_id}').json()
        stream_state = live_info['streamState']
        if stream_state == 'offline':
            raise PluginError("The live stream is offline")
        elif stream_state != 'live':
            raise PluginError(f"The live stream is on alternative site: {stream_state}")

        r = self.session.http.get('https://api.rplay.live/live/key2',
                                  headers={'Authorization': self.options.get("token")},
                                  params={'requestorOid': self.options.get("oid"), 'loginType': 'plex'})
        if r.status_code != 200:
            raise PluginError("Failed to get live key")
        key2 = r.text

        streams = HLSStream.parse_variant_playlist(
            self.session, f'https://api.rplay.live/live/stream/playlist.m3u8?creatorOid={self.user_id}&key2={key2}')

        self.id = self.user_id
        self.title = live_info.get('title')
        self.author = self.nickname

        log.info(f"id: {self.id}")
        log.info(f"title: {repr(self.title)}")
        log.info(f"author: {repr(self.author)}")
        log.info(f"desc: {repr(live_info.get('description'))}")
        log.info(f"start: {live_info.get('streamStartTime')}")
        log.debug(f'streams: {streams}')

        return streams


__plugin__ = RPlayLive
