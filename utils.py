

from datetime import datetime
import dateutil.relativedelta
import json
from slacker import Slacker
from colour import Color


class SlackMessage:

    def __init__(self, msg_dict, channel_name, channel_id):
        self.msg = msg_dict
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.timestamp = float(self.msg['ts'])
        self.datetime = datetime.fromtimestamp(self.timestamp)
        self.score = self.calculate_score(self.msg)

    @classmethod
    def calculate_score(cls, msg):
        result = 0
        for reaction_type in msg.get('reactions', []):
            result += reaction_type['count']
        return result

    @property
    def permalink(self):
        url = 'https://opendatascience.slack.com/archives/{}/p{}'
        url = url.format(self.channel_id, str(self.timestamp).replace('.', ''))
        return url
    
    def ordered_emoji(self, threshold=0, max_emoji=7):
        sorted_emoji = sorted(self.msg['reactions'], key=lambda x: x['count'], reverse=True)
        text_emoji = [":{}:".format(x['name']) for x in sorted_emoji if x['count'] > threshold]
        return ' '.join(text_emoji[:max_emoji])
    
    def __str__(self):
        result = "[ {} | {} | {} ]\n  {}"
        return result.format(self.channel_name, self.datetime, self.score, self.msg['text']) 


def msg_as_attachment(msg_obj, hex_color="#36a64f"):
        result = {
            "color": hex_color,
            "title": "<@{}> in {}. Collect {} emoji, including {}".format(
                                                msg_obj.msg['user'], 
                                                msg_obj.channel_name, 
                                                msg_obj.score,
                                                msg_obj.ordered_emoji()),
            "title_link": "https://api.slack.com/",
            "text": msg_obj.msg['text'],
            "footer": "<{}|link to post>".format(msg_obj.permalink),
            "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            "ts": msg_obj.timestamp
        }
        return result

def harvest_channel(slack, channel_name, days=7):
    messages = []
    channel_id = slack.channels.get_channel_id(channel_name)
    time_border_dt = datetime.today() - dateutil.relativedelta.relativedelta(days=days)
    time_border_ts = datetime.timestamp(time_border_dt)
    cnt_retry = 0
    chunk = slack.channels.history(channel=channel_id, oldest=time_border_ts, count=1000)
    messages.extend([SlackMessage(m, channel_name, channel_id) for m in reversed(chunk.body['messages'])])
    while chunk.body['has_more'] and cnt_retry < 20:
        chunk = slack.channels.history(channel=channel_id, 
                                       count=1000, 
                                       oldest=messages[-1].timestamp,
                                      )
        messages.extend([SlackMessage(m, channel_name, channel_id) for m in reversed(chunk.body['messages'])])
        cnt_retry += 1 
    return messages