wfrom astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import sys
import os
import aiohttp
import asyncio
import json
import urllib.parse
from datetime import datetime

class NarakaSearchPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        logger.info("永劫无间战绩查询插件初始化成功")

    SEARCH_API = 'https://naraka.drivod.top/api/record/search'
    RECENT_BATTLES_API = 'https://naraka.drivod.top/api/record/mini-program/battle/recent'
    STATS_API = 'https://naraka.drivod.top/api/record/mini-program/stats'
    BATTLE_DETAIL_API = 'https://naraka.drivod.top/api/record/mini-program/battle/detail/person'

    mode_names = {
        '1': '天选单排', '2': '天选三排', 
        '4': '天人单人', '5': '天人三排',
        '12': '天选双排', '13': '天人双排'
    }
    
    mode_aliases = {
        '天选单排': ['1'],
        '天选双排': ['12'],
        '天选三排': ['2'],
        '天人单排': ['4'],
        '天人双排': ['13'],
        '天人三排': ['5'],
    }
    hero_names = {
        '1000001': '胡桃', '1000003': '宁红夜', '1000004': '迦南',
        '1000005': '特木尔', '1000006': '季沧海', '1000007': '天海',
        '1000008': '天海','1000009': '妖刀姬', '1000010': '崔三娘', 
        '1000011': '岳山','1000012': '岳山','1000013': '无尘', 
        '1000015': '顾清寒', '1000016': '武田信忠','1000017': '殷紫萍', 
        '1000018': '沈妙', '1000019': '沈妙','1000020': '胡为',
        '1000021': '季莹莹', '1000022': '玉玲珑','1000023': '哈迪',
        '1000024': '魏青','1000025': '刘炼', '1000026': '张起灵', 
        '1000027': '席拉','1000028': '蓝梦','1000029': '万钧', 
        '1000030': '万钧','1000031': '李寻欢', '1000032': '巫真',
        '1000033': '甘璇'
      
    }

    async def fetch_url(self, url, timeout=10):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        logger.error(f"HTTP错误: {r.status}")
                        return None
                    text = await r.text()
                    return text
        except aiohttp.ClientError as e:
            logger.error(f"网络错误: {str(e)}")
            return None
        except asyncio.TimeoutError:
            logger.error("请求超时")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return None

    async def get_role_id(self, player_name):
        encoded_name = urllib.parse.quote(player_name)
        url = f'{self.SEARCH_API}?name={encoded_name}'
        text = await self.fetch_url(url)
        if not text:
            return {'role_id': 0, 'role_name': '', 'error': '网络请求失败'}
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.error("JSON解析失败")
            return {'role_id': 0, 'role_name': '', 'error': '数据解析失败'}
        if result.get('code') == 200 and result.get('data'):
            data = result.get('data')
            if isinstance(data, dict):
                role_id = data.get('roleIdMiniProgram') or data.get('roleId')
                role_name = data.get('roleName', '')
                if role_id:
                    return {'role_id': role_id, 'role_name': role_name}
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        role_id = item.get('roleIdMiniProgram') or item.get('roleId')
                        role_name = item.get('roleName', '')
                        if role_id:
                            return {'role_id': role_id, 'role_name': role_name}
        return {'role_id': 0, 'role_name': '', 'error': '未找到角色'}

    async def get_stats(self, player_id_in, game_mode):
        stats_url = f'{self.STATS_API}?roleId={player_id_in}&gameMode={game_mode}&seasonId=9620020'
        text = await self.fetch_url(stats_url)
        if not text:
            return None
        try:
            stats_result = json.loads(text)
        except json.JSONDecodeError:
            return None
        if stats_result.get('code') == 200 and stats_result.get('data'):
            return stats_result.get('data')
        return None

    async def get_battle_detail(self, player_id_in, battle_id):
        detail_url = f'{self.BATTLE_DETAIL_API}?roleId={player_id_in}&battleId={battle_id}'
        text = await self.fetch_url(detail_url, timeout=8)
        if not text:
            return None
        try:
            detail_result = json.loads(text)
        except json.JSONDecodeError:
            return None
        if detail_result.get('code') == 200 and detail_result.get('data'):
            return detail_result.get('data')
        return None

    async def get_battle_detail_team(self, player_id_in, battle_id):
        team_detail_url = f'{self.BATTLE_DETAIL_API.replace("/person", "/team")}?roleId={player_id_in}&battleId={battle_id}'
        text = await self.fetch_url(team_detail_url, timeout=8)
        if not text:
            return None
        try:
            team_result = json.loads(text)
        except json.JSONDecodeError:
            return None
        if team_result.get('code') == 200 and team_result.get('data'):
            return team_result.get('data')
        return None

    async def get_result(self, player_id_in, mode_in, season_in):
        battles_url = f'{self.RECENT_BATTLES_API}?roleId={player_id_in}&pageIndex=1&pageSize=10'
        async with aiohttp.ClientSession() as session:
            async with session.get(battles_url) as r:
                battles_text = await r.text()
                try:
                    battles_result = json.loads(battles_text)
                except json.JSONDecodeError:
                    return {'status': 'error', 'result': {'code': 500, 'errmsg': 'JSON解析失败'}}
                if battles_result.get('code') != 200 or not battles_result.get('data'):
                    return {'status': 'error', 'result': {'code': battles_result.get('code', 500), 'errmsg': battles_result.get('msg', '获取失败')}}
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
                        "rating_delta": (battle.get('roundRankScore') or 0) - (battle.get('beginRankScore') or 0),
                        "match_id": battle.get('battleId', '')
                    }
                    matches.append(battle_info)
                return {'status': 'ok', 'result': {'player_info': {'name': '未知', 'rating': '未知', 'level': '未知'}, 'matches': matches}}

    @filter.command("yj")
    async def naraka_search(self, event: AstrMessageEvent):
        message = event.message_str.strip()
        if not message:
            yield event.plain_result("📖 使用说明\n━━━━━━━━━━━━\n命令：/yj [模式] <角色名>\n示例：/yj 冬眠岛\n示例：/yj 三排 冬眠岛\n可用模式：单排、双排、三排、天选、匹配、天人\n━━━━━━━━━━━━")
            return

        clean_message = message
        if clean_message.startswith('/yj '):
            clean_message = clean_message[3:].strip()
        elif clean_message.lower().startswith('yj '):
            clean_message = clean_message[2:].strip()

        if not clean_message:
            yield event.plain_result("📖 使用说明\n━━━━━━━━━━━━\n命令：/yj [模式] <角色名>\n示例：/yj 冬眠岛\n示例：/yj 三排 冬眠岛\n可用模式：单排、双排、三排、天选、匹配、天人\n━━━━━━━━━━━━")
            return

        player_name = clean_message
        mode_filter = None
        mode_display = '全部模式'
        selected_mode_codes = []

        parts = clean_message.split(' ', 1)
        if len(parts) == 2:
            first_part = parts[0]
            second_part = parts[1]
            
            if first_part in self.mode_aliases:
                mode_filter = first_part
                player_name = second_part
                selected_mode_codes = self.mode_aliases[first_part]
                mode_display = first_part
            elif first_part in self.mode_names.values():
                for code, name in self.mode_names.items():
                    if name == first_part:
                        mode_filter = first_part
                        selected_mode_codes = [code]
                        break
                player_name = second_part
                mode_display = first_part

        logger.info(f"查询角色: {player_name}, 模式: {mode_display}")

        try:
            role_data = await self.get_role_id(player_name)
            player_id = role_data.get('role_id', 0)
            player_name_display = role_data.get('role_name', player_name)
            
            if player_id == 0:
                yield event.plain_result(f"🔍 未找到角色\n━━━━━━━━━━━━\n角色名：{player_name}\n请确认角色名是否正确\n━━━━━━━━━━━━")
                return

            stats_data = None
            if selected_mode_codes:
                stats_data = await self.get_stats(player_id, selected_mode_codes[0])

            res = await self.get_result(player_id, '5000001', 'chuanyun')
            result_data = res['result']

            matches = result_data.get('matches', [])

            if mode_filter and selected_mode_codes:
                matches = [m for m in matches if m.get('battle_tid') in selected_mode_codes]

            msg_parts = []
            msg_parts.append("⚔️ 永劫无间战绩 ⚔️")
            msg_parts.append("━━━━━━━━━━━━━━━━━━━━")
            msg_parts.append(f"👤 {player_name_display}")
            msg_parts.append(f"🎮 {mode_display}")
            msg_parts.append("━━━━━━━━━━━━━━━━━━━━")

            if stats_data:
                grade_info = stats_data.get('grade', {})
                grade_name = grade_info.get('gradeName', '未知')
                grade_score = grade_info.get('gradeScore', 0)
                dragon_kill = stats_data.get('dragonKill', 0)
                
                msg_parts.append(f"🏆 {grade_name} │ {grade_score}分")
                msg_parts.append(f"🐉 屠龙: {dragon_kill}次")
                
                stats = stats_data.get('stats', [])
                stats_dict = {s['name']: s['value'] for s in stats}
                
                msg_parts.append("📈 赛季统计")
                msg_parts.append(f"   对局数: {stats_dict.get('对局数', 0)}")
                msg_parts.append(f"   第一数: {stats_dict.get('第一数', 0)}")
                msg_parts.append(f"   前五数: {stats_dict.get('前五数', 0)}")
                msg_parts.append(f"   第一率: {stats_dict.get('第一率', '0%')}")
                msg_parts.append(f"   前五率: {stats_dict.get('前五率', '0%')}")
                msg_parts.append("━━━━━━━━━━━━━━━━━━━━")
                msg_parts.append("⚔️ 战斗数据")
                msg_parts.append(f"   场均击败: {stats_dict.get('场均击败', 0)}")
                msg_parts.append(f"   场均助攻: {stats_dict.get('场均助攻', 0)}")
                msg_parts.append(f"   场均治疗: {stats_dict.get('场均治疗', 0)}")
                msg_parts.append(f"   场伤: {stats_dict.get('场伤', 0)}")
                msg_parts.append(f"   K/D: {stats_dict.get('K/D', 0)}")
                msg_parts.append(f"   最多振刀: {stats_dict.get('最多振刀', 0)}")
                msg_parts.append("━━━━━━━━━━━━━━━━━━━━")
                msg_parts.append("🔥 最高记录")
                msg_parts.append(f"   最高击败: {stats_dict.get('最高击败', 0)}")
                msg_parts.append(f"   最高助攻: {stats_dict.get('最高助攻', 0)}")
                msg_parts.append(f"   最高治疗: {stats_dict.get('最高治疗', 0)}")
                msg_parts.append(f"   最高伤害: {stats_dict.get('最高伤害', 0)}")
                msg_parts.append(f"   场均生存: {stats_dict.get('场均生存', '0')}")
                msg_parts.append("━━━━━━━━━━━━━━━━━━━━")

            if matches:
                msg_parts.append("📊 最近对战记录")
                msg_parts.append("")
                for i, match in enumerate(matches[:10], 1):
                    hero_name = self.hero_names.get(match['hero_id'], match['hero_id'])
                    battle_tid = match.get('battle_tid', '')
                    match_mode = self.mode_names.get(battle_tid, battle_tid if battle_tid else '未知')
                    match_time = datetime.fromtimestamp(int(match['time'])).strftime('%m-%d %H:%M')
                    map_name = match.get('map_name', '未知')
                    damage = match.get('damage', 0)
                    rank = match.get('rank', 0)
                    kill_times = match.get('kill_times', 0)
                    grade = match.get('grade', '无')
                    rating_delta = match.get('rating_delta', 0)
                    match_id = match.get('match_id', '')

                    delta_str = f"+{rating_delta}" if rating_delta > 0 else str(rating_delta)
                    msg_parts.append(f"第{i}场 │ {match_time} │ {map_name}")
                    msg_parts.append(f"     │ {hero_name} │ {match_mode}")
                    msg_parts.append(f"     │ 排名{rank} │ 击杀{kill_times} │ 伤害{damage}")
                    msg_parts.append(f"     │ {grade}级 │ {delta_str}分")

                    if match_id:
                        detail_data = await self.get_battle_detail(player_id, match_id)
                        if detail_data:
                            data_list = detail_data.get('dataList', [])
                            data_dict = {item['name']: item['value'] for item in data_list}
                            
                            msg_parts.append(f"     ├─ 生存: {data_dict.get('生存', '0')} │ 治疗: {data_dict.get('治疗', '0')}")
                            msg_parts.append(f"     ├─ 击杀: {data_dict.get('击败', '0')} │ 伤害: {data_dict.get('伤害', '0')}")
                            msg_parts.append(f"     ├─ 振刀: {data_dict.get('振刀', '0')} │ 招式命中: {data_dict.get('招式命中', '0')}")
                            msg_parts.append(f"     ├─ 释放技能: {data_dict.get('释放技能', '0')} │ 爆头: {data_dict.get('爆头数', '0')}")
                            msg_parts.append(f"     ├─ 救援/复活: {data_dict.get('救援/复活', '0')} │ 开堆: {data_dict.get('开堆', '0')}")
                            msg_parts.append(f"     ├─ 移动距离: {data_dict.get('移动距离', '0')} │ 暗潮币: {data_dict.get('消耗暗潮币', '0')}")
                            
                            weapons = detail_data.get('weapons', [])
                            if weapons:
                                weapon_info = []
                                for w in weapons:
                                    w_name = w.get('weaponName', '')
                                    w_damage = w.get('damage', 0)
                                    w_kill = w.get('kill', 0)
                                    w_percent = w.get('percent', 0)
                                    weapon_info.append(f"{w_name}(击杀{w_kill}, 伤害{w_damage}, {w_percent:.1%})")
                                msg_parts.append(f"     ├─ 武器: {' | '.join(weapon_info)}")
                            
                            soul_items = detail_data.get('soulItems', [])
                            if soul_items:
                                soul_info = []
                                for s in soul_items:
                                    s_name = s.get('soulItemName', '')
                                    s_level = s.get('soulItemLevel', 0)
                                    soul_info.append(f"{s_name}(Lv.{s_level})")
                                msg_parts.append(f"     ├─ 魂玉: {' | '.join(soul_info)}")
                            
                            armor = detail_data.get('armor', {})
                            if armor:
                                armor_level = armor.get('armorLevel', 0)
                                msg_parts.append(f"     ├─ 护甲: {armor_level}级")
                            
                            honors = detail_data.get('honorTitles', [])
                            if honors:
                                honor_names = [h.get('honorName', '') for h in honors[:5]]
                                if honor_names:
                                    msg_parts.append(f"     ├─ 称号: {'、'.join(honor_names)}")
                            
                            # 获取队友数据
                            team_data = await self.get_battle_detail_team(player_id, match_id)
                            if team_data:
                                teammates = team_data.get('teammates', [])
                                if teammates:
                                    msg_parts.append(f"     └─ 队友数据:")
                                    for idx, teammate in enumerate(teammates):
                                        hero = teammate.get('hero', {})
                                        hero_name = hero.get('heroName', '未知')
                                        role = teammate.get('role', {})
                                        role_name = role.get('roleName', '未知')
                                        is_me = teammate.get('isMe', False)
                                        
                                        tm_data_list = teammate.get('dataList', [])
                                        tm_data_dict = {item['name']: item['value'] for item in tm_data_list}
                                        
                                        prefix = "     " if idx == len(teammates) - 1 else "     "
                                        msg_parts.append(f"{prefix}   ├─ {hero_name}({role_name}): 击杀{tm_data_dict.get('击败', '0')}, 伤害{tm_data_dict.get('伤害', '0')}, 治疗{tm_data_dict.get('治疗', '0')}")

                    msg_parts.append("━━━━━━━━━━━━━━━━━━━━")
            else:
                msg_parts.append("📭 暂无对局数据")

            msg_parts.append("✅ 查询完成")
            msg_parts.append("")
            msg_parts.append("💡 使用 /yj [模式] <角色名> 查询战绩")

            yield event.plain_result("\n".join(msg_parts))

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            yield event.plain_result(f"❌ 查询失败\n━━━━━━━━━━━━\n错误信息：{str(e)}\n━━━━━━━━━━━━")

    async def terminate(self):
        logger.info("永劫无间战绩查询插件已卸载")

plugin = NarakaSearchPlugin
