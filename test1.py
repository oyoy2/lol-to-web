import tkinter as tk
import threading
import datetime
import re
import time
import subprocess
import datetime

import psutil
import requests
import json
import os

requests_session = requests.Session()
LCU_API = {
    "current_summoner": "/lol-summoner/v1/current-summoner",
    "game_session": "/lol-gameflow/v1/session",
    "match_history": "/lol-match-history/v1/products/lol",
    "summoner_names": "/lol-summoner/v2/summoners/names",
    "grid_champions": "/lol-champ-select/v1/grid-champions",
    "rank": "/lol-ranked/v1/ranked-stats/",
    "games": "/lol-match-history/v1/games/",
}
CMD_CHECK_LOL_PROCESS = 'wmic process where name="LeagueClientUx.exe" get processid,executablepath,name'
requests.packages.urllib3.disable_warnings()
requests.DEFAULT_RETRIES = 1000


def find_lcu_prot_and_token():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == "LeagueClientUx.exe" and proc.info['cmdline']:
                cmdline = " ".join(proc.info['cmdline'])
                # 使用正则表达式提取参数值
                token_match = re.search(r"--remoting-auth-token=([^\s]+)", cmdline)
                port_match = re.search(r"--app-port=(\d+)", cmdline)

                # 获取提取的参数值
                if token_match and port_match:
                    token = token_match.group(1)
                    port = port_match.group(1)
                    return port, token
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return None, None


def get_All_Game_Id(lol_PT, name):
    """
    从英雄联盟玩家近期比赛数据中提取所有比赛ID。

    Args:
        lol_PT (str): 英雄联盟平台 ID（例如：HN1）
        name (str): 玩家游戏名称

    Returns:
        list: 包含所有比赛 ID 的列表
    """

    gamedata = get_data(lol_PT, name)  # 假设 get_data 函数已定义并返回比赛数据
    game_ids = []

    for game in gamedata:
        game_id = game.get("gameId")
        if game_id:
            game_ids.append(game_id)

    return game_ids


def get_all_game_data(lol_PT, name):
    allgameid = get_All_Game_Id(lol_PT, name)
    data = {}
    for index, i in enumerate(allgameid):
        data[index] = get_game_detail(lol_PT, str(i))
    return data


def check_lol_process():
    res = subprocess.Popen(CMD_CHECK_LOL_PROCESS,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    res.wait()
    temp = res.communicate()
    temp = re.findall('LeagueClientUx.exe', str(temp))
    time.sleep(1)
    return bool(temp)


def get_current_summoner_info(lol_PT):
    return _send_api_request(LCU_API["current_summoner"], lol_PT)


def get_game_session_info(lol_PT):
    return _send_api_request(LCU_API["game_session"], lol_PT)


def get_chat_me_info(lol_PT):
    return _send_api_request(LCU_API["chat_me"], lol_PT)


def set_chat_me_status(lol_PT, status):
    data = {"availability": status}
    return _send_api_request(LCU_API["chat_me"], lol_PT, method="PUT", data=data)


def get_grid_champions(lol_PT, data):
    return _send_api_request(LCU_API["grid_champions"] + f"/{data}", lol_PT)


def get_grid_champions1(lol_PT, data):
    return _send_api_request(LCU_API["grid_champions"] + f"/{data['participants'][0]['championId']}", lol_PT)


def get_match_history(lol_PT, name):
    try:
        summoner = get_summoner(lol_PT, name)
        return _send_api_request(LCU_API["match_history"] + f"/{summoner}/matches", lol_PT)
    except Exception as e:
        print(f"获取 {name} 的匹配历史时发生错误：{e}")
        return None


def _send_api_request(api, lol_PT, method="GET", params=None, data=None, retries=10):
    port, token = lol_PT
    url = f"https://riot:{token}@127.0.0.1:{port}{api}"
    for _ in range(retries):
        try:
            if method == "GET":
                response = requests_session.get(url, params=params, verify=False)
            elif method == "PUT":
                response = requests_session.put(url, json=data, verify=False)
            elif method == "POST":
                response = requests_session.post(url, json=data, verify=False)
            if response:
                response.raise_for_status()
                return response.json()
            else:
                print(f"Failed to send {method} request to {url}")
        except Exception as e:
            print(f"发送 {method} 请求到 {url} 时发生错误：{e}")
            print(f"正在重试... (剩余尝试次数: {retries - _ - 1})")
    return None  # retries 次尝试后仍失败，返回 None


def get_summoner(lol_PT, name):
    data = [name]
    summoner = _send_api_request(LCU_API["summoner_names"], lol_PT, method="POST", data=data)
    summoner = summoner[0]['puuid']
    return summoner


def get_game_detail(lol_PT, gameid):
    return _send_api_request(LCU_API["games"] + gameid, lol_PT)


def get_extract_data(lol_PT, name):
    data = get_all_game_data(lol_PT, name)  # 获取所有比赛数据
    extractdata = []
    for match_key, match_data in data.items():  # Use .items() to get both key and value
        game_info = {
            'gameCreationDate': match_data['gameCreationDate'],
            'gameDuration': match_data['gameDuration'],
            'gameId': match_data['gameId'],
            'gameMode': match_data['gameMode'],
            'gameType': match_data['gameType'],
            'queueId': match_data['queueId'],

        }
        participant_identities = match_data.get("participantIdentities", [])
        participant_info_list = extract_participant_info(participant_identities)
        participants_data = extract_participant_data(match_data)
        combined_data = {
            "game_info": game_info,
            "participant_info": participant_info_list,
            "participants_data": participants_data
        }
        extractdata.append(combined_data)

    return extractdata


def extract_participant_info(participant_identities):
    participant_info_list = []
    for participant in participant_identities:
        player = participant.get("player", {})
        participant_info = {
            "profile_icon": player.get("profileIcon"),
            "puuid": player.get("puuid"),
            "summoner_id": player.get("summonerId"),
            "summoner_name": player.get("summonerName"),
        }
        participant_info_list.append(participant_info)

    return participant_info_list



def extract_participant_data(match_data):
    participants_data = []
    for participant in match_data.get("participants", []):
        participants_data.append(participant)
    return participants_data


rank_mapping = {
    'IRON': '黑铁',
    'BRONZE': '青铜',
    'SILVER': '白银',
    'GOLD': '黄金',
    'PLATINUM': '铂金',
    'EMERALD': '翡翠',
    'DIAMOND': '钻石',
    'MASTER': '大师',
    'GRANDMASTER': '宗师',
    'CHALLENGER': '王者'
}


def get_rank_info(queue_data):
    if not queue_data:
        return {"段位": "未排位", "胜场": "0胜", "负场": "0负", "点数": "0点"}

    highest_tier = queue_data['tier']
    chinese_tier = rank_mapping.get(highest_tier, highest_tier)  # 使用 rank_mapping 进行映射
    rank = chinese_tier + queue_data['division']
    wins = queue_data['wins']
    losses = queue_data['losses']
    lp = queue_data['leaguePoints']
    return {"段位": rank, "胜场": f"{wins}胜", "负场": f"{losses}负", "点数": f"{lp}点"}


def get_ranks(lol_PT, name):
    summoner = get_summoner(lol_PT, name)
    rank_data = _send_api_request(LCU_API["rank"] + summoner + "/", lol_PT)

    data = {}
    for queue in rank_data['queues']:
        queue_type = queue['queueType']
        if queue_type == 'RANKED_SOLO_5x5':
            data["单双"] = get_rank_info(queue)
        elif queue_type == 'RANKED_FLEX_SR':
            data["组排"] = get_rank_info(queue)
        elif queue_type.startswith('RANKED_TFT'):
            data["云顶"] = get_rank_info(queue)

    return data


def get_rank1(lol_PT, name):
    summoner = get_summoner(lol_PT, name)
    rank1 = _send_api_request(LCU_API["rank"] + summoner + "/", lol_PT)

    return rank1


def get_data(lol_PT, name):
    if check_lol_process():
        match_history = get_match_history(lol_PT, name)
        data = []
        if match_history:
            for i in match_history['games']['games']:
                champion_name = get_grid_champions1(lol_PT, data=i)
                champion_name = champion_name['name']
                champion_name = {'champion_name': champion_name}
                i = {**i, **champion_name}
                data.append(i)
        return data
    else:
        return None
