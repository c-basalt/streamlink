"""
$description Japanese live broadcasting platform
$url 8181live.jp
$type live
"""

import logging
import re
import json
import time

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://8181live.jp/live/(?P<schedule_id>\d+)"
))
@pluginmatcher(re.compile(
    r"https://8181live.jp/liver/(?P<user_id>\d+)"
))
class Plugin8181Live(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.schedule_id = self.match.group("schedule_id")
        except IndexError:
            self.schedule_id = None
            self.user_id = self.match.group("user_id")

    def _fetch_stream_schedule(self):
        r = self.session.http.get(r"https://8181live.jp/liver/" + self.user_id)
        for seg in r.text.split('<p class="live_num__index"')[1:]:
            m = re.search(r'href="/live/(\d+)"', seg)
            if not m:
                continue
            schedule_id = m[1]
            live_status = re.search(r'<p class="live_info__status".*?</svg>\s*(\w+)\s*</p>', seg)
            if live_status is not None: live_status = live_status[1]
            if live_status == "LIVE":
                self.schedule_id = schedule_id
                log.info(f"found active stream: {schedule_id}")
                return
            elif live_status == "WAIT":
                log.debug(f"found scheduled stream: {schedule_id}")
            else:
                self.schedule_id = schedule_id
                log.debug(f"found scheduled stream of unexpected status: {schedule_id} {live_status}")
        if self.schedule_id is None:
            raise PluginError("Failed to find active stream")

    def _get_streams(self):
        if self.schedule_id is None:
            self._fetch_stream_schedule()
        r = self.session.http.get(r"https://8181live.jp/live/" + self.schedule_id)
        if r.status_code != 200:
            raise PluginError("Failed to load live webpage, status %s, please check your login cred" % r.status_code)
        try:
            metainfo_str = re.search(r'<script>window.__NUXT__=(.*?)</script>', r.text)[1]
        except (TypeError, IndexError):
            raise PluginError("Failed to find metainfo on stream webpage")
        try:
            url_raw = re.search(r'playlist:("[^"]+")', metainfo_str)[1]
            stream_url = json.loads(url_raw)
        except (TypeError, IndexError):
            raise PluginError("Failed to find stream url from stream metadata")
        except json.JSONDecodeError:
            raise PluginError("Failed to parse stream url from stream metadata: %s", url_raw)
        try:
            self.id = self.schedule_id
            self.author = re.search(r'liverName:"([^"]+)"', metainfo_str)[1]
            self.title = json.loads(re.search(r'detail:("[^"]+")', metainfo_str)[1]).split('\n')[0]
            log.info(f"id: {self.id}")
            log.info(f"title: {repr(self.title)}")
            log.info(f"author: {repr(self.author)}")
        except Exception:
            log.warning("error while parsing metainfo")
        log.debug('stream meta info', metainfo_str)
        streams = HLSStream.parse_variant_playlist(self.session, stream_url)
        log.debug('streams: %s' % str(streams))
        return streams

__plugin__ = Plugin8181Live
