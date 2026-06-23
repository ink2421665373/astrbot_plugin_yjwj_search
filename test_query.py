import requests
import json

# 模拟完整的查询流程
def simulate_query(player_name, mode_filter=None):
    print(f"\n=== 模拟查询: {mode_filter if mode_filter else '全部模式'} {player_name} ===")
    
    # 1. 搜索玩家
    search_url = f"https://naraka.drivod.top/api/record/search?name={requests.utils.quote(player_name)}"
    response = requests.get(search_url)
    data = response.json()
    
    if data.get('code') != 200 or not data.get('data'):
        print(f"搜索失败: {data}")
        return
    
    role_id = data['data'].get('roleIdSimple')
    print(f"roleIdSimple: {role_id}")
    
    # 2. 获取战绩
    battles_url = f"https://naraka.drivod.top/api/record/mini-program/battle/recent?roleIdSimple={role_id}&pageIndex=1&pageSize=20"
    response = requests.get(battles_url)
    battles_data = response.json()
    
    if battles_data.get('code') != 200:
        print(f"战绩API错误: {battles_data.get('msg')}")
        return
    
    battles = battles_data.get('data', {}).get('list', [])
    print(f"战绩数量: {len(battles)}")
    
    # 3. 模式匹配
    mode_aliases = {
        '天选单排': ['1'],
        '天选双排': ['12'],
        '天选三排': ['2'],
        '天人单排': ['4'],
        '天人双排': ['13'],
        '天人三排': ['5'],
    }
    
    mode_codes = None
    if mode_filter and mode_filter in mode_aliases:
        mode_codes = mode_aliases[mode_filter]
        print(f"模式过滤: {mode_filter} -> {mode_codes}")
    
    # 4. 匹配逻辑
    matches = []
    all_game_modes = set()
    
    for battle in battles:
        battle_tid = battle.get('gameMode')
        battle_tid_str = str(battle_tid) if battle_tid else ''
        all_game_modes.add(str(battle_tid))
        
        if mode_codes:
            match_found = False
            for code in mode_codes:
                code_str = str(code)
                # 模拟代码中的匹配逻辑
                if battle_tid_str == code_str:
                    match_found = True
                elif battle_tid_str == str(int(code_str)):
                    match_found = True
                elif isinstance(battle_tid, int) and int(code_str) == battle_tid:
                    match_found = True
            
            if match_found:
                matches.append(battle)
                print(f"  匹配成功: gameMode={battle_tid}")
        else:
            matches.append(battle)
    
    print(f"\n结果:")
    print(f"  扫描到的模式: {sorted(all_game_modes)}")
    print(f"  匹配的战绩数: {len(matches)}")
    
    if mode_codes and not matches and all_game_modes:
        print(f"  [提示] 指定模式无数据，建议显示全部战绩")

# 测试
simulate_query("冬眠岛", None)  # 全部模式
simulate_query("冬眠岛", "天选三排")  # 天选三排
simulate_query("冬眠岛", "天选单排")  # 天选单排（玩家有的模式）