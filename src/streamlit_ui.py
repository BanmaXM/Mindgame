#!/usr/bin/env python
"""
Streamlit 版 Mind Games 界面
支持配置不同的LLM实例
"""

import streamlit as st
import os
import sys
import time
from typing import Dict, List, Optional, Any

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.game_manager import GameManager
from src.agent import HumanAgent, LLMAgent, OpenAIAgent

# 设置页面配置
st.set_page_config(
    page_title="Mind Games",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 会话状态初始化
if 'manager' not in st.session_state:
    st.session_state.manager = None
if 'game_state' not in st.session_state:
    st.session_state.game_state = None
if 'game_log' not in st.session_state:
    st.session_state.game_log = []
if 'rounds_data' not in st.session_state:
    st.session_state.rounds_data = []
if 'current_round' not in st.session_state:
    st.session_state.current_round = 0
if 'current_observation' not in st.session_state:
    st.session_state.current_observation = ""
if 'waiting_for_action' not in st.session_state:
    st.session_state.waiting_for_action = False
if 'game_over' not in st.session_state:
    st.session_state.game_over = False

def setup_game(game_name: str, human_players: int, agent_configs: List[Dict]):
    """
    设置游戏环境和玩家
    
    Args:
        game_name: 游戏名称
        human_players: 人类玩家数量
        agent_configs: LLM代理配置列表
    """
    st.session_state.manager = GameManager()
    st.session_state.manager.setup_game(game_name)
    st.session_state.game_log = []
    st.session_state.rounds_data = []
    st.session_state.current_round = 0
    st.session_state.current_observation = ""
    st.session_state.waiting_for_action = False
    st.session_state.game_over = False
    
    # 添加人类玩家
    for i in range(human_players):
        st.session_state.manager.add_human_player()
        
    # 添加AI玩家
    total_players = st.session_state.manager.get_required_players()
    ai_players_needed = total_players - human_players
    
    for i in range(min(ai_players_needed, len(agent_configs))):
        config = agent_configs[i]
        agent_type = config['agent_type']
        
        if agent_type == 'openai':
            # 检查是否有API密钥
            if not config['api_key']:
                st.error(f"AI #{i+1} 缺少API密钥，将使用环境变量中的默认密钥")
                
            try:
                # 创建 OpenAI 代理
                print(f"Creating OpenAI agent with: model={config['model_name']}, api_type={config['api_type']}")
                agent = OpenAIAgent(
                    model_name=config['model_name'],
                    api_key=config['api_key'] if config['api_key'] else None,
                    base_url=config['base_url'],
                    api_type=config['api_type']
                )
                st.session_state.manager.add_agent(agent)
            except Exception as e:
                st.error(f"AI #{i+1} 创建失败: {str(e)}")
                # 如果OpenAI创建失败，默认使用本地模型
                st.warning(f"Fallback to local model for AI #{i+1}")
                try:
                    agent = LLMAgent(model_name="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", device="auto")
                    st.session_state.manager.add_agent(agent)
                except Exception as e2:
                    st.error(f"Fallback also failed: {str(e2)}")
                    raise
        
        elif agent_type == 'local':
            # 创建本地 LLM 代理
            agent = LLMAgent(
                model_name=config['model_name'],
                device=config.get('device', 'auto'),
                quantize=config.get('quantize', False)
            )
            st.session_state.manager.add_agent(agent)
    
    # 如果还需要更多玩家，添加默认OpenAI玩家
    for i in range(ai_players_needed - len(agent_configs)):
        # 使用默认配置
        agent = OpenAIAgent(model_name="gpt-3.5-turbo")
        st.session_state.manager.add_agent(agent)

def initialize_game():
    """初始化游戏但不开始完整流程"""
    try:
        if not st.session_state.get('manager'):
            st.error("游戏管理器未初始化，请先配置游戏")
            return False
            
        # 设置回调函数
        callbacks = {
            "on_observation": on_observation,
            "on_action": on_action,
            "on_step_complete": on_step_complete
        }
        
        # 保存回调以供后续使用
        st.session_state.callbacks = callbacks
        
        # 初始化游戏日志
        if 'game_log' not in st.session_state:
            st.session_state.game_log = []
        else:
            st.session_state.game_log = []  # 清除旧日志
            
        # 添加开始游戏日志
        st.session_state.game_log.append("🎮 === 游戏开始 === 🎮")
            
        # 开始游戏，只是初始化环境
        st.session_state.manager.start_game()
        
        # 初始化游戏状态变量
        st.session_state.game_step = 0
        st.session_state.game_over = False
        st.session_state.waiting_for_action = False
        st.session_state.current_observation = None
        st.session_state.current_player_id = None
        st.session_state.current_round = 0
        st.session_state.game_initialized = True
        
        st.success("游戏初始化成功！")
        return True
        
    except Exception as e:
        st.error(f"游戏初始化错误: {str(e)}")
        st.exception(e)
        return False

def advance_game_step():
    """执行游戏的一步"""
    # 检查游戏是否初始化
    if not st.session_state.get('game_initialized', False):
        st.warning("游戏尚未初始化，请先点击'开始游戏'按钮")
        return
    
    # 检查必要的session state变量
    if not st.session_state.get('manager'):
        st.error("游戏管理器未初始化")
        return
        
    # 确保游戏状态变量已初始化
    if 'game_over' not in st.session_state:
        st.session_state.game_over = False
        
    if 'game_step' not in st.session_state:
        st.session_state.game_step = 0
    
    # 检查游戏是否已结束
    if st.session_state.game_over:
        st.info("游戏已结束！")
        return
        
    try:
        # 检查游戏环境是否初始化
        if not hasattr(st.session_state.manager, 'env') or st.session_state.manager.env is None:
            st.error("游戏环境未初始化，请重新开始游戏")
            return
            
        # 获取当前观察和玩家
        player_id, observation = st.session_state.manager.env.get_observation()
        
        # 确保回调存在
        if 'callbacks' not in st.session_state:
            st.session_state.callbacks = {}
        
        # 触发观察回调
        if 'on_observation' in st.session_state.callbacks:
            st.session_state.callbacks['on_observation'](player_id, observation)
        
        # 检查是否为人类玩家 - 如果是则等待输入
        if hasattr(st.session_state.manager, 'human_player_ids') and player_id in st.session_state.manager.human_player_ids:
            # 人类玩家的动作会通过UI输入处理
            st.session_state.waiting_for_action = True
            st.session_state.current_player_id = player_id
            st.session_state.current_observation = observation  # 保存当前观察供人类玩家查看
            st.info(f"等待人类玩家(ID: {player_id})输入动作...")
            return
        
        # 获取当前玩家的代理
        if not hasattr(st.session_state.manager, 'agents') or player_id not in st.session_state.manager.agents:
            st.error(f"找不到玩家ID {player_id} 对应的代理")
            return
            
        agent = st.session_state.manager.agents[player_id]
        
        # 代理生成动作
        with st.spinner(f"等待AI玩家(ID: {player_id})生成动作..."):
            action = agent(observation)
        
        # 触发动作回调
        if 'on_action' in st.session_state.callbacks:
            st.session_state.callbacks['on_action'](player_id, action)
        
        # 执行动作
        game_over, step_info = st.session_state.manager.env.step(action=action)
        
        # 触发步骤完成回调
        if 'on_step_complete' in st.session_state.callbacks:
            st.session_state.callbacks['on_step_complete'](game_over, step_info)
        
        # 更新游戏状态
        st.session_state.game_step += 1
        st.session_state.game_over = game_over
        
        if game_over:
            st.success("游戏已结束!")
            
    except Exception as e:
        st.error(f"游戏步骤执行错误: {str(e)}")
        st.exception(e)

def submit_human_action(action: str):
    """提交人类玩家的动作"""
    # 检查必要的session state变量
    if not st.session_state.get('manager'):
        st.error("游戏管理器未初始化")
        return
    
    if not st.session_state.get('waiting_for_action', False):
        return
    
    # 从人类玩家列表中获取玩家ID
    if 'current_player_id' in st.session_state:
        player_id = st.session_state.current_player_id
    elif hasattr(st.session_state.manager, 'human_player_ids') and st.session_state.manager.human_player_ids:
        # 使用第一个人类玩家ID
        player_id = st.session_state.manager.human_player_ids[0]
    else:
        st.error("找不到人类玩家ID")
        return
    
    try:
        # 触发动作回调
        if st.session_state.get('callbacks') and 'on_action' in st.session_state.callbacks:
            st.session_state.callbacks['on_action'](player_id, action)
        
        # 执行动作
        if not hasattr(st.session_state.manager, 'env') or st.session_state.manager.env is None:
            st.error("游戏环境未初始化")
            return
            
        game_over, step_info = st.session_state.manager.env.step(action=action)
        
        # 触发步骤完成回调
        if st.session_state.get('callbacks') and 'on_step_complete' in st.session_state.callbacks:
            st.session_state.callbacks['on_step_complete'](game_over, step_info)
        
        # 初始化游戏步骤计数器（如果不存在）
        if 'game_step' not in st.session_state:
            st.session_state.game_step = 0
            
        # 更新游戏状态
        st.session_state.game_step += 1
        st.session_state.game_over = game_over
        st.session_state.waiting_for_action = False
        
        # 清除当前观察
        if 'current_observation' in st.session_state:
            st.session_state.current_observation = None
            
        st.success("动作已提交成功!")
        
        # 如果游戏没有结束，自动继续执行AI玩家的回合
        if not game_over:
            # 使用延迟来确保成功消息能显示出来
            time.sleep(0.5)
            # 继续执行游戏步骤，处理AI玩家的回合
            advance_game_step()
        
    except Exception as e:
        st.error(f"提交动作时出错: {str(e)}")
        st.exception(e)

def on_observation(player_id: int, observation: str):
    """观察回调"""
    # 确保当前轮次数据存在
    if len(st.session_state.rounds_data) <= st.session_state.current_round:
        st.session_state.rounds_data.append({
            'round': st.session_state.current_round + 1,
            'observations': {},
            'actions': {}
        })
    
    # 保存观察内容
    current_round_data = st.session_state.rounds_data[st.session_state.current_round]
    current_round_data['observations'][player_id] = observation
    
    # 如果是人类玩家，设置当前观察和状态
    if player_id in st.session_state.manager.human_player_ids:
        st.session_state.current_observation = observation
        st.session_state.waiting_for_action = True
    
    # 添加到游戏日志
    message = f"📋 [轮次 {st.session_state.current_round + 1}][玩家 {player_id}] 收到观察"
    st.session_state.game_log.append(message)

def on_action(player_id: int, action: str):
    """动作回调"""
    # 保存行动内容
    if len(st.session_state.rounds_data) > st.session_state.current_round:
        current_round_data = st.session_state.rounds_data[st.session_state.current_round]
        current_round_data['actions'][player_id] = action
    
    # 添加到游戏日志
    player_type = "人类" if player_id in st.session_state.manager.human_player_ids else "AI"
    message = f"🎮 [轮次 {st.session_state.current_round + 1}][{player_type} {player_id}] 执行动作: {action}"
    st.session_state.game_log.append(message)
    
    # 如果是人类玩家提交了动作，更新状态
    if player_id in st.session_state.manager.human_player_ids:
        st.session_state.waiting_for_action = False

def on_step_complete(done: bool, info: Dict[str, Any]):
    """步骤完成回调"""
    if done:
        st.session_state.game_over = True
        st.session_state.game_log.append("===== 🏁 游戏结束 =====")
        
        # 添加游戏结果到日志
        if 'scores' in info:
            st.session_state.game_log.append("📊 最终得分:")
            for player_id, score in info['scores'].items():
                player_type = "人类" if player_id in st.session_state.manager.human_player_ids else "AI"
                st.session_state.game_log.append(f"  {player_type} {player_id}: {score}")
        
        if 'winners' in info:
            winners = ", ".join([f"{w}" for w in info['winners']])
            st.session_state.game_log.append(f"🏆 获胜者: {winners}")
    else:
        # 如果游戏没有结束，增加轮次计数
        st.session_state.current_round += 1
        st.session_state.game_log.append(f"===== 🔄 进入第 {st.session_state.current_round + 1} 轮 =====")

def submit_action(action: str):
    """提交人类玩家动作"""
    # 使用submit_human_action函数处理
    if st.session_state.manager and st.session_state.waiting_for_action:
        if action.strip():
            submit_human_action(action)
            return True
    return False

def render_sidebar():
    """渲染侧边栏设置"""
    st.sidebar.title("Mind Games")
    st.sidebar.markdown("---")
    st.sidebar.subheader("游戏设置")
    
    # 游戏选择
    game_options = {
        "secret_mafia": "Secret Mafia",
        "three_player_ipd": "三人囚徒困境",
        "colonel_blotto": "Colonel Blotto",
        "codenames": "Codenames"
    }
    selected_game = st.sidebar.selectbox(
        "选择游戏", 
        options=list(game_options.keys()),
        format_func=lambda x: game_options[x],
        index=1  # 默认选择三人囚徒困境
    )
    
    # 人类玩家数量
    if selected_game == "three_player_ipd":
        max_humans = 3
    elif selected_game == "secret_mafia":
        max_humans = 7
    elif selected_game == "colonel_blotto":
        max_humans = 2
    else:  # codenames
        max_humans = 4
        
    human_count = st.sidebar.slider("人类玩家数量", 1, max_humans, 1)
    
    # AI代理配置
    st.sidebar.markdown("---")
    st.sidebar.subheader("AI代理配置")
    
    agent_configs = []
    ai_count = st.sidebar.number_input("AI代理数量", 1, 10, 1)
    
    for i in range(ai_count):
        with st.sidebar.expander(f"AI #{i+1} 配置"):
            agent_type = st.selectbox(
                "代理类型", 
                options=["openai", "local"],
                index=0,
                key=f"agent_type_{i}"
            )
            
            if agent_type == "openai":
                model_name = st.text_input("模型名称", "gpt-3.5-turbo", key=f"model_{i}")
                api_type = st.selectbox(
                    "API类型", 
                    options=["standard", "azure_key"],
                    format_func=lambda x: "Azure OpenAI" if x == "azure_key" else "标准 OpenAI",
                    key=f"api_type_{i}"
                )
                api_key = st.text_input("API密钥", "", type="password", key=f"api_key_{i}")
                
                if api_type == "azure_key":
                    base_url = st.text_input("Azure端点", "https://your-resource.openai.azure.com", key=f"base_url_{i}")
                else:
                    base_url = st.text_input("API基础URL", "https://api.openai.com/v1", key=f"base_url_{i}")
                
                agent_configs.append({
                    'agent_type': 'openai',
                    'model_name': model_name,
                    'api_key': api_key,
                    'base_url': base_url,
                    'api_type': api_type
                })
                
            else:  # local
                model_name = st.text_input("模型名称", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", key=f"model_{i}")
                device = st.selectbox(
                    "设备", 
                    options=["auto", "cpu", "cuda:0"],
                    key=f"device_{i}"
                )
                quantize = st.checkbox("量化模型", False, key=f"quantize_{i}")
                
                agent_configs.append({
                    'agent_type': 'local',
                    'model_name': model_name,
                    'device': device,
                    'quantize': quantize
                })
    
    # 游戏控制按钮
    st.sidebar.markdown("---")
    start_button = st.sidebar.button("开始游戏", key="start_game_button")
    reset_button = st.sidebar.button("重置游戏", key="reset_game_button")
    
    # 重置游戏
    if reset_button:
        for key in ['manager', 'game_initialized', 'game_step', 'game_over', 'waiting_for_action',
                  'current_observation', 'current_player_id', 'game_log', 'current_round']:
            if key in st.session_state:
                del st.session_state[key]
        st.sidebar.success("游戏已重置!")
        st.rerun()
    
    # 检查是否点击了开始按钮
    if start_button:
        with st.spinner("正在设置游戏环境..."):
            # 设置游戏及玩家
            setup_game(selected_game, human_count, agent_configs)
            
            # 初始化游戏，检查返回值
            if initialize_game():
                st.sidebar.success("游戏已开始! 点击'进行下一步'按钮继续")
                st.rerun()  # 重新运行以刷新UI
            else:
                st.sidebar.error("游戏初始化失败，请检查设置和错误信息")

def render_main():
    """渲染主界面"""
    st.title("🧠 Mind Games")
    
    # 如果游戏已初始化，显示控制面板
    if hasattr(st.session_state, 'game_initialized') and st.session_state.game_initialized:
        # 游戏控制面板
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.session_state.get('game_over', False):
                    st.success("游戏已结束!")
                else:
                    step_button = st.button("进行下一步", key="next_step_button", 
                                       disabled=st.session_state.get('waiting_for_action', False))
                    if step_button:
                        advance_game_step()
                        st.rerun()
                    
                    # 显示当前游戏步骤
                    st.info(f"当前步骤: {st.session_state.get('game_step', 0) + 1}")
            
            with col2:
                if st.session_state.get('waiting_for_action', False) and st.session_state.get('current_observation'):
                    st.info("等待人类玩家行动")
                    action_input = st.text_area("输入你的行动", key="human_action")
                    if st.button("提交行动", key="submit_action_control_panel"):
                        submit_human_action(action_input)
                        st.rerun()
    
    # 分为两列
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.subheader("游戏日志")
        # 创建一个容器来显示日志，使用固定高度
        log_container = st.container(height=400)
        with log_container:
            for log in st.session_state.game_log:
                st.markdown(log)
        
        # 轮次详情信息
        if st.session_state.rounds_data:
            st.subheader("轮次详情")
            rounds_tabs = st.tabs([f"轮次 {i+1}" for i in range(len(st.session_state.rounds_data))])
            
            for i, tab in enumerate(rounds_tabs):
                if i < len(st.session_state.rounds_data):
                    round_data = st.session_state.rounds_data[i]
                    with tab:
                        st.markdown(f"**轮次 {round_data['round']}**")
                        
                        # 显示观察和行动
                        col_obs, col_act = st.columns(2)
                        
                        # 左侧显示观察
                        with col_obs:
                            st.markdown("### 📝 观察数据")
                            if round_data['observations']:
                                for player_id, obs in round_data['observations'].items():
                                    player_type = "人类" if player_id in st.session_state.manager.human_player_ids else "AI"
                                    with st.expander(f"{player_type} {player_id} 的观察"):
                                        st.text_area("", obs, height=150, disabled=True, key=f"obs_{i}_{player_id}")
                        
                        # 右侧显示行动
                        with col_act:
                            st.markdown("### 🎮 玩家行动")
                            if round_data['actions']:
                                actions_data = []
                                for player_id, action in round_data['actions'].items():
                                    player_type = "人类" if player_id in st.session_state.manager.human_player_ids else "AI"
                                    actions_data.append({
                                        "玩家": f"{player_type} {player_id}",
                                        "行动": action
                                    })
                                
                                if actions_data:
                                    st.dataframe(actions_data, use_container_width=True)
                                    
                                    # 详细分析每个行动
                                    st.markdown("### 🧠 行动分析")
                                    for player_id, action in round_data['actions'].items():
                                        if player_id not in st.session_state.manager.human_player_ids:  # 只显示AI玩家
                                            with st.expander(f"AI {player_id} 的行动分析"):
                                                st.markdown(f"**行动内容:**")
                                                st.code(action, language="")
                                                
                                                if player_id in round_data['observations']:
                                                    st.markdown("**基于观察:**")
                                                    obs_preview = round_data['observations'][player_id]
                                                    if len(obs_preview) > 100:
                                                        obs_preview = obs_preview[:100] + "..."
                                                    st.text(obs_preview)
    
    with col2:
        st.subheader("游戏界面")
        
        # 显示当前观察
        if st.session_state.current_observation:
            st.markdown("#### 当前观察")
            st.text_area("观察", st.session_state.current_observation, height=200, disabled=True)
            
            # 如果在等待人类玩家输入
            if st.session_state.waiting_for_action:
                st.markdown("#### 你的行动")
                action = st.text_area("输入你的行动", height=100)
                
                if st.button("提交行动", key="submit_action_main_panel"):
                    if action:
                        if submit_human_action(action):
                            st.success("行动已提交!")
                            # 重新加载页面以刷新状态
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("无法提交行动，请检查游戏状态")
                    else:
                        st.warning("请输入行动内容")
            
            # 游戏结束
            elif st.session_state.game_over:
                st.markdown("### 🎮 游戏结束!")
                if st.button("开始新游戏"):
                    # 重置状态
                    for key in ['manager', 'game_state', 'game_log', 'current_observation', 
                                'waiting_for_action', 'game_over']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
        
        # 如果游戏尚未开始
        elif not st.session_state.manager:
            st.info("👈 请在左侧设置游戏参数并点击「开始游戏」按钮")
            
            with st.expander("游戏说明"):
                st.markdown("""
                **Mind Games**是一个多人智力博弈平台，目前支持以下游戏:
                
                1. **三人囚徒困境** - 经典囚徒困境的三人版本
                2. **Secret Mafia** - 基于社交推理的隐藏身份游戏
                3. **Colonel Blotto** - 资源分配策略游戏
                4. **Codenames** - 团队词汇关联游戏
                
                您可以设置人类玩家数量和AI代理配置，包括使用OpenAI API或本地大语言模型。
                """)

def main():
    """主函数"""
    # 检查是否安装了必要的依赖
    try:
        import streamlit
    except ImportError:
        st.error("请先安装Streamlit: pip install streamlit")
        return
        
    try:
        import openai
    except ImportError:
        st.warning("请安装OpenAI库以使用OpenAI功能: pip install openai")
    
    # 渲染侧边栏和主界面
    render_sidebar()
    render_main()

if __name__ == "__main__":
    main()
