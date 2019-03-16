#!/usr/bin/env python3

import urllib
import os
import json
from operator import itemgetter
import requests
import boto3
from flags import Flags

# Bungie API Details
API_KEY = os.environ['BUNGIE_KEY']
HEADERS = {"X-API-Key": API_KEY}
BASE_URL = "https://www.bungie.net/Platform/Destiny2/"

# S3 bucket info
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
S3_BUCKET = os.environ["S3_BUCKET"]
JSONFILE = os.environ["JSONFILE"]
MANIFEST_JSON = os.environ["MANIFEST_JSON"]

# S3 command setup
s3 = boto3.resource("s3").Bucket(S3_BUCKET)
json.load_s3 = lambda f: json.load(s3.Object(key=f).get()["Body"])
json.dump_s3 = lambda obj, f: s3.Object(key=f).put(Body=json.dumps(obj))

class RecordState(Flags):
    RecordRedeemed = 1
    RewardUnavailable = 2
    ObjectiveNotCompleted = 4
    Obscured = 8
    Invisible = 16
    EntitlementUnowned = 32
    CanEquipTitle = 64

class BungieLookup():
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

    def get_bungie_membership_id(self, player):
        member_id = {}
        # for player in players:
        try:
            request = requests.get(BASE_URL + \
            "SearchDestinyPlayer/4/" + \
            urllib.parse.quote(player), \
            headers=HEADERS)
            member_id[player] = request.json()['Response'][0]['membershipId']
        except IndexError as exception:
            print(request.url)
            # break
        return member_id

    def get_triumph_data(self, member_id):
        triumph_data = requests.get(BASE_URL  + \
        "4/Profile/" + member_id + "/?components=Records", \
        headers=HEADERS).json()['Response']['profileRecords']['data']['records']
        return triumph_data

    def get_triumph_score_v2(self, member_id, triumph_data):
        score = {}
        triumph_score = triumph_data['score']
        score[member_id] = triumph_score
        return score

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

    def load_triumph_manifest():
        try:
            triumph_manifest = json.load_s3(MANIFEST_JSON)
        except:
            data = {"triumphs":{}, "objectives":{}}
            json.dump_s3(MANIFEST_JSON)
            triumph_manifest = json.load_s3(MANIFEST_JSON)
        return triumph_manifest

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
        return top_scorer_data, score_data

    def triumph_leaderboard(self, players):
        score_dict = self.get_triumph_score(self.get_bungie_membership_id(players))
        score_data = [(player, data['score']) for player, data in score_dict.items()]
        top_scorer_data = sorted(score_data, key=lambda x: x[1], reverse=True)[0]
        score_data = sorted(score_data, key=lambda x: x[1], reverse=True)
        return top_scorer_data, score_data

    # Compare bit-wise state flag values for triumph against definitions
    def only_uncompleted_triumphs(self, triumph_data):
        triumph_state = RecordState(triumph_data['state'])
        print(triumph_data, RecordState(triumph_data['state']))
        if bool((RecordState.RecordRedeemed | RecordState.Obscured | RecordState.Invisible) & triumph_state):
            return True
        return False

    # Remove entries for unwanted Triumphs (Obscured, Completed, Invisible)
    def filter_triumph_data(self, triumph_data):
        to_delete = []
        for triumph in triumph_data:
            if self.only_uncompleted_triumphs(triumph_data=triumph_data[triumph]) is True:
                to_delete.append(triumph)
            if all(objective['complete'] for objective in triumph_data[triumph]['objectives']):
                to_delete.append(triumph)
            try:
                if self.TRIUMPH_MANIFEST['triumphs'][triumph]['completionInfo']['ScoreValue'] == 0:
                    to_delete.append(triumph)
            except KeyError:
                to_delete.append(triumph)
            try:
                if self.TRIUMPH_MANIFEST['triumphs'][triumph]['displayProperties']['name'] == '':
                    to_delete.append(triumph)
            except KeyError:
                to_delete.append(triumph)
        for completed in to_delete:
            try:
                del triumph_data[completed]
            except KeyError:
                print("Triumph: ", completed, "already deleted")
        return triumph_data

    # Lookup Triumph description and store info/progress
    def get_triumph_info(self, triumph_hash, triumph_json):
        if triumph_hash in self.TRIUMPH_MANIFEST['triumphs']:
            triumph_desc = self.TRIUMPH_MANIFEST['triumphs'][triumph_hash]
            update_cache = False
        else:
            triumph_desc = requests.get(BASE_URL + "Manifest/DestinyRecordDefinition/" + \
            triumph_hash + "/", headers=HEADERS).json()['Response']
            update_cache = True
        triumph_info = {}
        triumph_info['objectiveHashes'] = {}
        triumph_info['displayProperties'] = {}
        triumph_info['displayProperties']['name'] = triumph_desc['displayProperties']['name']
        triumph_info['displayProperties']['description'] = triumph_desc['displayProperties']['description']
        triumph_info['completionInfo'] = {}
        triumph_info['completionInfo']['ScoreValue'] = triumph_desc['completionInfo']['ScoreValue']
        for num, objective in enumerate(triumph_desc['objectiveHashes']):
            triumph_info['objectiveHashes'][objective] = self.get_objective_info(objective_hash=objective,\
            triumph_json=triumph_json, position=num)
        if update_cache is True:
            self.prepare_manifest_updates(triumph_hash=triumph_hash, \
            triumph_json=triumph_info)
        return triumph_info

    # Lookup Objective description and store info/progress
    def get_objective_info(self, objective_hash, triumph_json, position):
        if objective_hash in self.TRIUMPH_MANIFEST['objectives']:
            objective_desc = self.TRIUMPH_MANIFEST['objectives'][objective_hash]
            update_cache = False
        else:
            objective_desc = requests.get(BASE_URL + "Manifest/DestinyObjectiveDefinition/" + \
            str(objective_hash) + "/", headers=HEADERS).json()['Response']
            update_cache = True
        objective = {
        'completionValue': objective_desc['completionValue'],
        'progressDescription': objective_desc['progressDescription']
        }
        if update_cache is True:
            self.prepare_manifest_updates(objective_hash=objective_hash, objective_json=objective)
        objective['complete'] = triumph_json['objectives'][position]['complete']
        try:
            progress = triumph_json['objectives'][position]['progress']
        except NameError:
            progress = 0
        objective['progress'] = progress
        return objective

    # Super function to get info for triumphs and objectives and combine into one dictionary
    def combine_triumph_and_objective_data(self, triumph_data):
        combined_data = {}
        for triumph in triumph_data:
            triumph_info = self.get_triumph_info(triumph_hash=triumph, \
            triumph_json=triumph_data[triumph])
            combined_data[triumph] = triumph_info
            combined_data[triumph]['CompletionPercentage'] = \
            self.calc_completion_percentage(combined_data[triumph]['objectiveHashes'])
        return combined_data

    def prepare_manifest_updates(self, triumph_json=None, objective_json=None, \
    objective_hash=None, triumph_hash=None):
        if triumph_json is not None:
            self.MANIFEST_UPDATE['triumphs'][triumph_hash] = triumph_json
        if objective_json is not None:
            self.MANIFEST_UPDATE['objectives'][objective_hash] = objective_json

    def perform_manifest_updates(self):
        for triumph in self.MANIFEST_UPDATE['triumphs']:
            self.TRIUMPH_MANIFEST['triumphs'][triumph] = self.MANIFEST_UPDATE['triumphs'][triumph]
        for objective in self.MANIFEST_UPDATE['objectives']:
            self.TRIUMPH_MANIFEST['objectives'][objective] = self.MANIFEST_UPDATE['objectives'][objective]
        json.dump_s3(self.TRIUMPH_MANIFEST, MANIFEST_JSON)

    # Determine overall Triumph progress based on total number of Objectives
    # and their relative progress
    def calc_completion_percentage(self, objectives):
        individual_percentages = []
        for objective in objectives:
            percent = (objectives[objective]['progress'] / objectives[objective]['completionValue']) * 100.0
            if percent > 100.0:
                percent = 100.0
            individual_percentages.append(percent)
        total_percentage = sum(individual_percentages) / len(individual_percentages)
        # print("Objectives: ", objectives)
        # print("Individual Percentages: ", individual_percentages)
        # print("Number of objectives: ", len(individual_percentages))
        # print("Total Percentage: ", total_percentage)
        if total_percentage > 100.0:
            total_percentage = 100.0
        return total_percentage

    # Perform everything necessary to return top ten closest triumphs
    def top_five_closest_triumphs(self, player):
        # try:
        # for player in players:
        bungie_member_id = self.get_bungie_membership_id(player=player)
        filtered_triumph_data = \
        self.filter_triumph_data(triumph_data=\
        self.get_triumph_data(member_id=bungie_member_id[player]))
        score_data = self.combine_triumph_and_objective_data(\
        triumph_data=filtered_triumph_data)
        self.perform_manifest_updates()
        score_data = [[k, v] for k, v in score_data.items()]
        sorted_score_data = sorted(score_data, key=lambda k: \
        k[1]['CompletionPercentage'], reverse=True)[:5]
        return sorted_score_data


    # JSON_PATH = "stored_scores.json"
    TRIUMPH_SCORES = load_stored_scores()
    TRIUMPH_MANIFEST = load_triumph_manifest()
    MANIFEST_UPDATE = {"triumphs":{}, "objectives":{}}
