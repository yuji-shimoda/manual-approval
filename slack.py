import os
import boto3
import json
import requests
from urllib import parse
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TOKYO = 'ap-northeast-1'
SLACK = os.environ['SLACK']


def worker(event, context):
    payload = {
        "text": event['Message'],
        "attachments": [
            {
                "fallback": "Notify Manual Approval",
                "callback_id": "approval_task",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "approve",
                        "text": "承認",
                        "style": "primary",
                        "type": "button",
                        "value": event['TaskToken'],
                        "confirm": {
                            "title": "最終確認",
                            "text": "本当に承認しますか？",
                            "ok_text": "はい",
                            "dismiss_text": "いいえ"
                        }
                    },
                    {
                        "name": "reject",
                        "text": "差戻",
                        "style": "danger",
                        "type": "button",
                        "value": event['TaskToken'],
                        "confirm": {
                            "title": "最終確認",
                            "text": "本当に差し戻しますか？",
                            "ok_text": "はい",
                            "dismiss_text": "いいえ"
                        }
                    }
                ]
            }
        ]
    }
    message = json.dumps(payload)
    try:
        requests.post(SLACK, data=message)
    except Exception as e:
        logger.exception("{}".format(e))


def receiver(event, context):
    param = parse.parse_qs(event['body'])
    data = json.loads(param['payload'][0])
    response_url = data['response_url']
    user = data['user']['name']
    action = data['actions'][0]['name']
    taskToken = data['actions'][0]['value']
    if action == 'approve':
        output = {
            "result": 'approve'
        }
        success(taskToken, output)
        message = create_message(user, 'approved')
        post_slack(response_url, message)
    elif action == 'reject':
        fail(taskToken)
        message = create_message(user, 'rejected')
        post_slack(response_url, message)


def success(taskToken, payload):
    sfn = boto3.client('stepfunctions', region_name=TOKYO)
    try:
        sfn.send_task_success(
            taskToken=taskToken,
            output=json.dumps(payload)
        )
    except Exception as e:
        logger.exception("sfn.send_task_success {}".format(e))


def fail(taskToken):
    sfn = boto3.client('stepfunctions', region_name=TOKYO)
    try:
        sfn.send_task_failure(
            taskToken=taskToken
        )
    except Exception as e:
        logger.exception("sfn.send_task_failure {}".format(e))


def post_slack(url, message):
    try:
        requests.post(url, data=message)
    except Exception as e:
        logger.exception("{}".format(e))


def create_message(user, action):
    payload = {
        "response_type": "in_channel",
        "mrkdwn": "true",
        "attachments": [
            {
                "fallback": "Manual Approve Information",
                "color": "good",
                "response_type": "in_channel",
                "pretext": "{} {}.".format(user, action),
            }
        ]
    }
    return json.dumps(payload)
