#!/usr/bin/env python
"""
Mind Games Challenge的WebUI界面
使用Gradio构建，允许用户通过浏览器与LLM代理对战
"""

import os
import sys
import argparse
import logging
import time
import gradio as gr
import threading
import queue
import json
from typing import Dict, List, Any, Optional, Tuple

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.game_manager import GameManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量
manager = None
game_state = {
    "started": False,
    "game_log": [],
    "current_player": None,
    "observation": "",
    "waiting_for_human": False,
    "game_result": None,
    "last_human_action": None
}

# 用于线程间通信的队列
action_queue = queue.Queue()
observation_queue = queue.Queue()

def initialize_manager():
    """初始化游戏管理器"""
    global manager
    if manager is None:
        manager = GameManager()
    return manager

def setup_game(game_name: str, model_name: str, human_count: int, seed: Optional[int] = None):
    """设置游戏"""
    global manager, game_state
    
    # 重置游戏状态
    game_state = {
        "started": False,
        "game_log": [],
        "current_player": None,
        "observation": "",
        "waiting_for_human": False,
        "game_result": None,
        "last_human_action": None
    }
    
    # 初始化管理器
    manager = initialize_manager()
    
    try:
        # 设置游戏
        game_env_name = manager.setup_game(game_name)
        
        # 计算需要的玩家数量
        required_players = manager.get_required_players()
        
        # 验证人类玩家数量
        if human_count > required_players:
            return f"错误: 游戏 {game_name} 最多支持 {required_players} 名玩家，但您要求 {human_count} 名人类玩家"
        
        # 添加人类玩家
        human_player_ids = []
        for i in range(human_count):
            player_id = manager.add_human_player()
            human_player_ids.append(player_id)
        
        # 添加LLM玩家填充剩余位置
        llm_count = required_players - human_count
        llm_player_ids = []
        for i in range(llm_count):
            player_id = manager.add_llm_player(model_name)
            llm_player_ids.append(player_id)
        
        setup_msg = f"游戏 {game_name} 设置成功!\n"
        setup_msg += f"- 环境: {game_env_name}\n"
        setup_msg += f"- 需要玩家数: {required_players}\n"
        setup_msg += f"- 人类玩家: {human_count} 名 (ID: {human_player_ids})\n"
        setup_msg += f"- LLM玩家: {llm_count} 名 (ID: {llm_player_ids})\n"
        setup_msg += f"- 模型: {model_name}\n"
        
        if seed is not None:
            setup_msg += f"- 随机种子: {seed}\n"
        
        return setup_msg
    
    except Exception as e:
        logger.error(f"设置游戏时出错: {e}")
        return f"错误: {str(e)}"

def observation_callback(player_id: int, observation: str) -> None:
    """处理观察事件"""
    global game_state
    
    game_state["current_player"] = player_id
    game_state["observation"] = observation
    
    log_entry = {
        "type": "observation",
        "player_id": player_id,
        "content": observation[:200] + "..." if len(observation) > 200 else observation,
        "timestamp": time.time()
    }
    
    game_state["game_log"].append(log_entry)
    
    # 如果是人类玩家，需要等待输入
    if player_id in manager.human_player_ids:
        game_state["waiting_for_human"] = True
        # 将观察放入队列，通知UI线程
        observation_queue.put((player_id, observation))
    else:
        game_state["waiting_for_human"] = False

def action_callback(player_id: int, action: str) -> None:
    """处理动作事件"""
    log_entry = {
        "type": "action",
        "player_id": player_id,
        "content": action,
        "timestamp": time.time()
    }
    
    game_state["game_log"].append(log_entry)
    
    # 记录最后的人类动作
    if player_id in manager.human_player_ids:
        game_state["last_human_action"] = action

def step_complete_callback(done: bool, info: Dict[str, Any]) -> None:
    """处理步骤完成事件"""
    if done:
        log_entry = {
            "type": "system",
            "content": "游戏结束!",
            "timestamp": time.time()
        }
        game_state["game_log"].append(log_entry)

def game_thread_function(seed: Optional[int] = None):
    """游戏线程函数，运行游戏逻辑"""
    global manager, game_state
    
    try:
        # 设置回调
        callbacks = {
            "on_observation": observation_callback,
            "on_action": action_callback,
            "on_step_complete": step_complete_callback
        }
        
        # 启动游戏
        manager.start_game(seed=seed)
        game_state["started"] = True
        
        # 运行游戏
        result = manager.play_game(callbacks=callbacks)
        game_state["game_result"] = result
        
        logger.info("游戏线程结束")
    
    except Exception as e:
        logger.error(f"游戏线程出错: {e}")
        game_state["game_log"].append({
            "type": "error",
            "content": f"错误: {str(e)}",
            "timestamp": time.time()
        })

def start_game(seed_str: str = ""):
    """开始游戏"""
    if manager is None:
        return "请先设置游戏!"
    
    if game_state["started"]:
        return "游戏已经开始!"
    
    seed = None
    if seed_str:
        try:
            seed = int(seed_str)
        except ValueError:
            return "随机种子必须是整数!"
    
    # 开始游戏线程
    game_thread = threading.Thread(target=game_thread_function, args=(seed,))
    game_thread.daemon = True
    game_thread.start()
    
    return "游戏已开始！等待游戏状态更新..."

def submit_human_action(action: str):
    """提交人类玩家的动作"""
    global game_state
    
    if not game_state["started"]:
        return "游戏尚未开始!"
    
    if not game_state["waiting_for_human"]:
        return "当前不需要人类玩家输入!"
    
    # 将动作放入队列
    action_queue.put(action)
    game_state["waiting_for_human"] = False
    
    return f"已提交动作: {action}"

def get_current_observation():
    """获取当前观察"""
    if not game_state["started"]:
        return "游戏尚未开始"
    
    if game_state["waiting_for_human"]:
        return f"轮到您行动，玩家 {game_state['current_player']}!\n\n{game_state['observation']}"
    
    return f"玩家 {game_state['current_player']} 正在行动...\n\n{game_state['observation']}"

def get_game_log():
    """获取游戏日志"""
    log_text = ""
    
    for entry in game_state["game_log"][-20:]:  # 只显示最后20条记录
        entry_type = entry["type"]
        timestamp = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
        
        if entry_type == "observation":
            log_text += f"[{timestamp}] 👁️ 玩家 {entry['player_id']} 收到观察:\n"
            content_preview = entry["content"]
            log_text += f"{content_preview}\n\n"
        
        elif entry_type == "action":
            log_text += f"[{timestamp}] 🎮 玩家 {entry['player_id']} 执行动作:\n"
            log_text += f"{entry['content']}\n\n"
        
        elif entry_type == "system" or entry_type == "error":
            log_text += f"[{timestamp}] ⚙️ 系统: {entry['content']}\n\n"
    
    if game_state["game_result"]:
        log_text += "\n===== 游戏结果 =====\n"
        log_text += f"总步数: {game_state['game_result']['steps']}\n"
        log_text += f"奖励: {json.dumps(game_state['game_result']['rewards'], ensure_ascii=False)}\n"
    
    if not log_text:
        log_text = "游戏日志为空"
    
    return log_text

# 人类代理类，用于与WebUI交互
class WebUIHumanAgent:
    def __call__(self, observation: str) -> str:
        # 等待UI线程提供动作
        action = action_queue.get()
        return action

# 替换HumanAgent
from src.agent import HumanAgent
HumanAgent = WebUIHumanAgent

def ui_observation_monitor(state):
    """监控观察队列，更新UI状态"""
    try:
        # 非阻塞检查队列
        if not observation_queue.empty():
            player_id, observation = observation_queue.get_nowait()
            state["current_player"] = player_id
            state["observation"] = observation
            state["waiting_for_human"] = True
            return state, f"轮到您行动，玩家 {player_id}!", observation, get_game_log()
    except queue.Empty:
        pass
    
    # 检查游戏是否结束
    if game_state["game_result"] and game_state["game_result"] != state.get("game_result"):
        state["game_result"] = game_state["game_result"]
        return state, "游戏结束!", get_current_observation(), get_game_log()
    
    return state, "", get_current_observation(), get_game_log()

def create_ui():
    """创建Gradio界面"""
    with gr.Blocks(title="Mind Games Challenge WebUI") as ui:
        gr.Markdown("# Mind Games Challenge WebUI")
        gr.Markdown("与强大的LLM代理对战四种不同的游戏环境")
        
        # 游戏设置部分
        with gr.Group():
            gr.Markdown("## 游戏设置")
            with gr.Row():
                with gr.Column():
                    game_dropdown = gr.Dropdown(
                        choices=["secret_mafia", "three_player_ipd", "colonel_blotto", "codenames"],
                        label="选择游戏",
                        value="three_player_ipd"
                    )
                    model_name = gr.Textbox(
                        label="LLM模型名称",
                        value="gpt-4o"
                    )
                    
                with gr.Column():
                    human_count = gr.Slider(
                        minimum=1,
                        maximum=7,
                        value=1,
                        step=1,
                        label="人类玩家数量"
                    )
                    seed = gr.Textbox(
                        label="随机种子 (可选)",
                        value=""
                    )
            
            setup_button = gr.Button("设置游戏")
            setup_output = gr.Textbox(label="设置结果", interactive=False)
            
            setup_button.click(
                fn=setup_game,
                inputs=[game_dropdown, model_name, human_count, seed],
                outputs=setup_output
            )
        
        # 游戏控制部分
        with gr.Group():
            gr.Markdown("## 游戏控制")
            start_button = gr.Button("开始游戏")
            start_output = gr.Textbox(label="开始结果", interactive=False)
            
            start_button.click(
                fn=start_game,
                inputs=[seed],
                outputs=start_output
            )
        
        # 游戏交互部分
        with gr.Group():
            gr.Markdown("## 游戏交互")
            
            # 创建一个隐藏的状态
            state = gr.State({
                "current_player": None,
                "observation": "",
                "waiting_for_human": False,
                "game_result": None
            })
            
            status_text = gr.Textbox(label="状态", interactive=False)
            observation_text = gr.Textbox(label="当前观察", interactive=False, lines=10)
            
            with gr.Row():
                action_input = gr.Textbox(label="输入动作", interactive=True, placeholder="输入您的动作...")
                submit_button = gr.Button("提交动作")
            
            action_output = gr.Textbox(label="动作结果", interactive=False)
            
            submit_button.click(
                fn=submit_human_action,
                inputs=[action_input],
                outputs=action_output
            )
            
            # 游戏日志
            game_log = gr.Textbox(label="游戏日志", interactive=False, lines=20)
        
        # 设置界面更新函数
        def periodic_update():
            return ui_observation_monitor(state)
            
        refresh_button = gr.Button("刷新状态", visible=True)
        refresh_button.click(fn=periodic_update, inputs=[state], outputs=[state, status_text, observation_text, game_log])
        
        # 自动刷新 - 新版Gradio不支持every，使用JavaScript替代
        gr.Markdown("*状态每5秒自动更新一次，或点击刷新按钮手动更新*")
        
        # 添加JavaScript定时器实现自动刷新
        ui.load(js="""() => {
            const refreshInterval = setInterval(() => {
                const refreshButton = document.querySelector('button[aria-label="刷新状态"]');
                if (refreshButton) {
                    refreshButton.click();
                    console.log('自动刷新UI');
                } else {
                    console.log('找不到刷新按钮');
                }
            }, 5000);
            return () => clearInterval(refreshInterval);
        }""")
    
    return ui

def main():
    parser = argparse.ArgumentParser(description="Mind Games Challenge WebUI")
    parser.add_argument("--port", type=int, default=7860, help="服务器端口")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="服务器主机")
    parser.add_argument("--share", action="store_true", help="创建公共链接")
    
    args = parser.parse_args()
    
    # 创建UI
    ui = create_ui()
    
    # 启动Gradio服务器
    ui.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=True
    )

if __name__ == "__main__":
    main()
