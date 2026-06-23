import aiohttp
import json

SEARCH_API = 'https://naraka.drivod.top/api/record/search'
RECENT_BATTLES_API = 'https://naraka.drivod.top/api/record/mini-program/battle/recent'

async def get_role_id(player_name, cookies=None):
    url = f'{SEARCH_API}?name={player_name}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            text = await r.text()
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                return 0
            
            if result.get('code') == 200 and result.get('data'):
                data = result.get('data')
                if isinstance(data, dict):
                    role_id = data.get('roleIdMiniProgram') or data.get('roleId')
                    if role_id:
                        return role_id
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            role_id = item.get('roleIdMiniProgram') or item.get('roleId')
                            if role_id:
                                return role_id
            return 0

async def update(player_id_in, cookies=None):
    return '更新成功'

async def get_result(player_id_in, mode_in, season_in, cookies=None):
    battles_url = f'{RECENT_BATTLES_API}?roleId={player_id_in}&pageIndex=1&pageSize=10'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(battles_url) as r:
            battles_text = await r.text()
            
            try:
                battles_result = json.loads(battles_text)
            except json.JSONDecodeError:
                return {
                    'status': 'error',
                    'result': {
                        'code': 500,
                        'errmsg': 'JSON解析失败'
                    }
                }
            
            if battles_result.get('code') != 200 or not battles_result.get('data'):
                return {
                    'status': 'error',
                    'result': {
                        'code': battles_result.get('code', 500),
                        'errmsg': battles_result.get('msg', '获取失败')
                    }
                }
            
            battles_data = battles_result.get('data', {}).get('list', [])
            matches = []
            
            for battle in battles_data:
                battle_info = {
                    "battle_tid": str(battle.get('gameMode', '')),
                    "hero_id": str(battle.get('hero', {}).get('heroId', '')),
                    "time": str(int(battle.get('battleEndTime', 0)/1000)),
                    "map_name": battle.get('mapName', '未知'),
                    "damage": battle.get('damage', 0),
                    "rank": battle.get('rank', 0),
                    "total_users_count": battle.get('totalPlayers', 0),
                    "kill_times": battle.get('kill', 0),
                    "grade": battle.get('rating', ''),
                    "rating_delta": battle.get('roundRankScore', 0) - battle.get('beginRankScore', 0),
                    "match_id": battle.get('battleId', '')
                }
                matches.append(battle_info)
            
            return {
                'status': 'ok',
                'result': {
                    'player_info': {
                        'name': '未知',
                        'rating': '未知',
                        'level': '未知'
                    },
                    'matches': matches
                }
            }

async def get_match_detail(match_id, cookies=None):
    return {
        'status': 'ok',
        'result': {
            'data': []
        }
    }
