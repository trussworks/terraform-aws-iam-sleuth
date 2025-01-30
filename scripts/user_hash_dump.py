#! /usr/bin/env python

import os
import sys

import requests

SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]

users_list = requests.get(
    "https://slack.com/api/users.list?token=%s" % SLACK_API_TOKEN
).json()

if users_list["ok"] is not True:
    print("Slack API call failed")
    sys.exit(1)

for user in users_list["members"]:
    name = "NA"
    if "name" in user:
        name = user["name"]
    print("User: {} ID: {}".format(name, user["id"]))
