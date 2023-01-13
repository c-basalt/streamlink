"""
$description Global live broadcasting social platform.
$url live.fc2.com
$type live
"""

import logging
import re
import json
import time

from websocket import ABNF

from streamlink.plugin import Plugin, PluginArgument, PluginArguments, PluginError, pluginmatcher
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://live\.fc2\.com/(?P<channel_id>\d+)"
))
class FC2Live(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "token",
            sensitive=True,
            help="`fcu` or `fcus` token in cookie string."
        )
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_id = self.match.group("channel_id")

    def _get_stream_info(self):
        payload = {
            'channel': 1,
            'profile': 1,
            'streamid': self.channel_id,
        }
        data = self.session.http.post('https://live.fc2.com/api/memberApi.php', payload).json()['data']
        self.id = data['channel_data']['channelid']
        self.title = data['channel_data']['title']
        self.author = data['profile_data']['name']
        self.category = data['channel_data']['category_name']
        if not data['channel_data'].get('version', None) or not data['channel_data']['is_publish']:
            raise PluginError("The live stream is offline")
        if data['channel_data']['login_only']:
            token = self.options.get("token")
            if token is None:
                raise PluginError("The live stream is login only")
            elif data['channel_data']['login_only'] > 1:
                raise PluginError("The live stream is point only")
            else:
                self.session.set_option('http-cookies', { 'fcu': token, 'fcus': token })
                r = self.session.http.post('https://live.fc2.com/api/userInfo.php')
                if (r.json().get("user_info", {}).get("fc2id", 0)):
                    log.debug("Use fcu token to login for the stream")
                else:
                    raise PluginError("Invalid token for login-only stream")
        if data['channel_data']['ticket_only']:
            raise PluginError("The live stream is ticket only")
        if data['channel_data']['fee']:
            raise PluginError("The live stream is paid only")
        log.info(f"id: {self.id}")
        log.info(f"title: {repr(self.title)}")
        log.info(f"author: {repr(self.author)}")
        log.info(f"category: {repr(self.category)}")
        log.info(f"cover: {repr(data['channel_data']['image'])}")
        log.info(f"desc: {repr(data['channel_data']['info'])}")
        log.info(f"start: {data['channel_data']['start']}")

        payload = {
            'channel_id': self.channel_id,
            'channel_version': data['channel_data']['version'],
            'client_type': 'pc',
            'client_app': 'browser_hls',
        }
        data = self.session.http.post('https://live.fc2.com/api/getControlServer.php', payload).json()
        return '%s?control_token=%s' % (data['url'], data['control_token'])

    def _get_streams(self):
        ws_url = self._get_stream_info()
        self.wsclient = FC2WSClient(
            self.session,
            ws_url,
            origin="https://live.fc2.com",
        )
        self.wsclient.start()
        _check_interval = 0.1
        for _ in range(round(self.session.get_option('http-timeout')/_check_interval)):
            if not self.wsclient.is_alive():
                raise PluginError("Failed to get HLS from control server, websocket disconnected")
            if not self.wsclient.m3u8_url:
                time.sleep(_check_interval)
            else:
                break
        else:
            raise PluginError("Failed to get HLS from control server, timed out")
        streams = HLSStream.parse_variant_playlist(self.session, self.wsclient.m3u8_url)
        log.debug('streams: %s' % str(streams))
        return streams

class FC2WSClient(WebsocketClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._count = 0
        self.last_heartbeat = 0
        self.m3u8_url = None
        log.debug(self.ws.url)
    @property
    def count(self):
        self._count += 1
        return self._count
    def send_heartbeat(self):
        self.last_heartbeat = time.time()
        log.debug(f"sending heartbeat")
        self.send_json({"name":"heartbeat","arguments":{},"id":self.count})
    def request_hls(self):
        log.debug(f"requesting hls from server")
        self.send_json({"name":"get_hls_information","arguments":{},"id":self.count})
    def on_open(self, wsapp):
        self.request_hls()
    def on_data(self, wsapp, data, data_type, cont):
        if time.time() - self.last_heartbeat > 30:
            self.send_heartbeat()
        if data_type == ABNF.OPCODE_TEXT:
            data = json.loads(data)
            if "playlists" in data.get("arguments", {}):
                playlists = data["arguments"]["playlists"]
                for playlist in playlists:
                    if playlist['mode'] == 0:
                        self.m3u8_url = playlist['url']
            elif data['name'] in [
                'initial_connect',
                'connect_complete',
                'connect_data',
                'user_count',
                'video_information',
                'point_information',
                'ng_comment',
                '_response_', # url or heartbeat
            ]:
                log.debug(("%s: %s" % (data['name'], data['arguments']))[:500])
            elif data['name'] in ['comment']:
                log.debug("%s: %s" % (data['name'], json.dumps(data['arguments'], ensure_ascii=False)))
            else:
                log.debug(json.dumps(data, ensure_ascii=False))

__plugin__ = FC2Live
