# Fork of [Streamlink](https://github.com/streamlink/streamlink) with fc2 plugin

Download the [plugin file](https://github.com/c-basalt/streamlink/blob/master/src/streamlink/plugins/fc2_live.py) and put it into your streamlink installation path to enable fc2 live record. Example paths:
 - Windows: `C:\Program Files\Python38\Lib\site-packages\streamlink\plugins`
 - Linux: `/usr/local/lib/python3.8/dist-packages/streamlink/plugins`

# Auto record scripts

Use channel_id in url to deploy automatic recording. Optionally pass a sleep param to avoid burst when number of channels is large.

- Requires more RAM, start recording faster
`bash record_fc2_general.sh <channel_id> [sleep_before_start]`

- Requires `curl`, wait for higher qualities
`bash record_fc2_general_new.sh <channel_id> [sleep_before_start]`
