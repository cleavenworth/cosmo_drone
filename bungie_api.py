#!/usr/bin/env python3

import urllib
import os
import json
import requests
import boto3

# Bungie API Details
API_KEY = os.environ['BUNGIE_KEY']
HEADERS = {"X-API-Key": API_KEY}
BASE_URL = "https://www.bungie.net/Platform/Destiny2/"

# S3 bucket info
S3_KEY = os.environ["S3_KEY"]
S3_SECRET = os.environ["S3_SECRET"]
BUCKET = os.environ["BUCKET"]
JSONFILE = os.environ["JSONFILE"]

# S3 command setup
s3 = boto3.resource("s3").Bucket(BUCKET)
json.load_s3 = lambda f: json.load(s3.Object(key=f).get()["Body"])
json.dump_s3 = lambda obj, f: s3.Object(key=f).put(Body=json.dumps(obj))

class BungieLookup(object):
    def __init__(self, players=None, discord_lookup=None, leaderboard=None):
        if discord_lookup:
            if len(players) == 0:
                players = [""]
            else:
                players = players.split()
            players[0] = self.read_bnet_user(discord_lookup)
            self.players = players
        elif leaderboard:
            players = []
            discord_users = self.TRIUMPH_SCORES['discord_users']
            for discord_user in discord_users:
                players.append(self.read_bnet_user(discord_user))
            self.players = players
        else:
            players = players.split()
            self.players = players

    def get_bungie_membership_id(self, players):
        member_ids = {}
        for player in players:
            try:
                request = requests.get(BASE_URL + \
                "SearchDestinyPlayer/4/" + \
                urllib.parse.quote(player), \
                headers=HEADERS)
                member_ids[player] = request.json()['Response'][0]['membershipId']
            except IndexError as exception:
                print(request.url)
                break
        return member_ids

    def get_triumph_score(self, member_ids):
        scores = {}
        for player in member_ids:
            member_id = member_ids[player]
            triumph_score = requests.get(BASE_URL  + \
            "4/Profile/" + member_id + "/?components=Records", \
            headers=HEADERS).json()['Response']['profileRecords']['data']['score']
            scores[player] = {}
            scores[player]['score'] = triumph_score
            scores[player]['member_id'] = member_id
        self.save_triumph_score(scores)
        return scores

    def save_triumph_score(self, scores):
        for player in scores:
            self.TRIUMPH_SCORES["triumph_scores"][player] = scores[player]
        # with open(self.JSON_PATH, 'w') as stored_scores:
        #     json.dump(self.TRIUMPH_SCORES, stored_scores)
        json.dump_s3(self.TRIUMPH_SCORES, JSONFILE)

    def load_stored_scores():
        try:
            # with open(json_path, 'r')  as stored_scores:
                # triumph_scores = json.load(stored_scores)
            triumph_scores = json.load_s3(JSONFILE)
        except:
            # with open(json_path, 'w+') as stored_scores:
            #     data = {"discord_users":{}, "triumph_scores":{}}
            #     json.dump(data, stored_scores)
            #     triumph_scores = json.load(stored_scores)
            data = {"discord_users":{}, "triumph_scores":{}}
            json.dump_s3(data, JSONFILE)
            triumph_scores = json.load_s3(JSONFILE)
        return triumph_scores

    def read_bnet_user(self, discord_user):
        try:
            player = self.TRIUMPH_SCORES['discord_users'][discord_user]
        except KeyError:
            print("Unable to read registered BNet Username.")
        return player

    def register_bnet_user(self, player, discord_user):
        try:
            self.TRIUMPH_SCORES['discord_users'][discord_user] = player[0]
        except KeyError:
            self.TRIUMPH_SCORES["triumph_scores"][player[0]] = {}
            self.TRIUMPH_SCORES['discord_users'][discord_user] = player[0]
        self.get_triumph_score(self.get_bungie_membership_id([player[0]]))

    def compare_triumph_score(self, players):
        score_dict = self.get_triumph_score(self.get_bungie_membership_id(players))
        score_data = [(player, data['score']) for player, data in score_dict.items()]
        top_scorer_data = sorted(score_data, key=lambda x: x[1], reverse=True)[0]
        score_data = sorted(score_data, key=lambda x: x[1], reverse=True)
        return top_scorer_data,score_data

    def triumph_leaderboard(self, players):
        score_dict = self.get_triumph_score(self.get_bungie_membership_id(players))
        score_data = [(player, data['score']) for player, data in score_dict.items()]
        top_scorer_data = sorted(score_data, key=lambda x: x[1], reverse=True)[0]
        score_data = sorted(score_data, key=lambda x: x[1], reverse=True)
        return top_scorer_data, score_data

    # JSON_PATH = "stored_scores.json"
    TRIUMPH_SCORES = load_stored_scores()
