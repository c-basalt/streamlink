from streamlink.plugins.fc2_live import FC2Live
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFC2Live(PluginCanHandleUrl):
    __plugin__ = FC2Live

    should_match = [
        'https://live.fc2.com/78847652/',
    ]
