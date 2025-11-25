import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from logic import BalanceBoxLogic  # 분리된 로직 파일(logic.py) import

# ==========================================
# [Module 2] UI Rendering & Logic
# ==========================================
st.set_page_config(layout="wide", page_title="Balance Box Algo")

# --- Custom CSS for Box Visualization ---
# 큐(Queue) 시각화를 위한 스타일 정의
st.markdown("""
<style>
    .box-container {
        display: flex;
        flex-direction: column-reverse; /* 아래에서 위로 쌓이는 스택 구조 */
        align_items: center;
        gap: 5px;
        padding: 10px;
        border-radius: 5px;
        min-height: 300px;
        justify-content: flex-start;
    }
    .algo-box {
        width: 100%;
        padding: 10px;
        text-align: center;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        font-size: 0.9em;
    }
    .box-call { background-color: #FF4B4B; border: 1px solid #b30000; }
    .box-put { background-color: #1E90FF; border: 1px solid #0050b3; }
    .box-head { border: 3px solid #FFD700; position: relative; } /* Head(0번 인덱스) 강조 */
    .box-head::after { content: "HEAD"; position: absolute; top:-10px; right:-5px; background:gold; color:black; font-size:0.6em; padding:2px; border-radius:3px;}
    .stat-metric { font-size: 1.5rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Balance Box Algorithm Presentation")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # 전략 선택 (Strategy Selection)
    st.subheader("1. Strategy Type")
    strategy_option = st.radio(
        "Select Algorithm Strategy",
        ["Gap Balance (Original)", "Fixed Size Limit (New)"],
        index=0,
        help="Gap Balance: 큐 길이 '차이'가 Box Size 초과 시 청산\nFixed Limit: 각 큐 '길이'가 Box Size 초과 시 청산"
    )
    
    # UI 선택값을 로직 내부 코드로 매핑
    strat_map = {"Gap Balance (Original)": "diff", "Fixed Size Limit (New)": "fixed"}
    selected_strat = strat_map[strategy_option]

    st.subheader("2. Parameters")
    # 사용자 입력 설정
    setting_box_size = st.number_input("Balance Box Size (N)", value=2, min_value=1, help="청산 기준이 되는 임계값 (차이 또는 절대 길이)")
    setting_unit = st.number_input("Unit Point Value", value=10, min_value=1)
    
    st.divider()
    st.markdown("### 📊 Simulation Mode")
    mode = st.radio("Mode", ["Manual Presentation", "Monte Carlo Sim"])
    
    st.divider()
    # 리셋 버튼
    if st.button("🔄 Reset System"):
        if 'logic' in st.session_state:
            del st.session_state.logic
        st.rerun()

# --- Initialize Logic ---
# 로직 인스턴스 생성 또는 불러오기 (초기화 시 전략 타입 전달)
if 'logic' not in st.session_state:
    st.session_state.logic = BalanceBoxLogic(setting_box_size, setting_unit, selected_strat)

# 현재 세션의 로직 인스턴스
algo = st.session_state.logic

# 설정값(전략, 파라미터)이 변경되면 로직 리셋 (Hot Reload)
# 기존 인스턴스의 설정과 현재 사이드바 설정이 다르면 재생성
if (algo.box_size != setting_box_size or 
    algo.unit_point != setting_unit or 
    algo.strategy_type != selected_strat):
    
    st.session_state.logic = BalanceBoxLogic(setting_box_size, setting_unit, selected_strat)
    st.toast(f"Strategy changed to '{selected_strat}' & Reset!", icon="✅")
    st.rerun()

# ==========================================
# MODE 1: Manual Presentation (수동 시연 모드)
# ==========================================
if mode == "Manual Presentation":
    
    # --- [개선된 상단 지표] ---
    # 실시간 금융 데이터 계산 (logic.py에 get_unrealized_pnl 메서드가 추가되어야 합니다)
    realized_pnl = algo.total_profit * algo.unit_point
    try:
        unrealized_pnl_points = algo.get_unrealized_pnl()
        unrealized_pnl = unrealized_pnl_points * algo.unit_point
    except AttributeError:
         # logic.py가 아직 업데이트되지 않았을 경우를 대비한 예외처리
         unrealized_pnl = 0
         st.error("⚠️ 'logic.py' 파일에 'get_unrealized_pnl' 메서드 추가가 필요합니다.")

    total_equity = realized_pnl + unrealized_pnl

    # 5개의 컬럼으로 확장하여 상세 정보 표시
    m1, m2, m3, m4, m5 = st.columns(5)
    
    m1.metric("💰 Realized Profit", f"${realized_pnl:,}", help="청산이 완료되어 확정된 수익")
    # 평가 손익은 음수일 때 빨간색(inverse)으로 표시
    m2.metric("📉 Unrealized PnL", f"${unrealized_pnl:,}", delta=f"{unrealized_pnl:,}", delta_color="inverse", help="현재 보유 중인 포지션들의 평가 손익 합계")
    m3.metric("💵 Total Equity", f"${total_equity:,}", help="확정 수익 + 평가 손익 (실제 계좌 가치)")
    
    # 전략에 따른 불균형 지표
    if algo.strategy_type == "diff":
        m4.metric("Queue Imbalance", f"{len(algo.call_q) - len(algo.put_q)}", delta_color="off", help="Call - Put (기준: Gap Balance)")
    else:
        m4.metric("Max Queue Size", f"{max(len(algo.call_q), len(algo.put_q))}", delta_color="off", help="최대 큐 길이 (기준: Fixed Limit)")
        
    m5.metric("Total Positions", f"{len(algo.call_q) + len(algo.put_q)}", help="현재 보유 중인 총 포지션 수")

    st.divider()

    # 2. 메인 조작 및 시각화 영역
    col_vis, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.subheader("🕹️ Market Action")
        st.write("시장의 움직임을 선택하세요.")
        
        # 조작 버튼
        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button(f"📈 상승 (+{algo.unit_point})", use_container_width=True, type="primary"):
            algo.next_step(1)
            st.rerun()
            
        if btn_col2.button(f"📉 하락 (-{algo.unit_point})", use_container_width=True, type="primary"):
            algo.next_step(-1)
            st.rerun()
            
        # 시스템 로그 출력창
        st.subheader("📜 System Log")
        log_container = st.container(height=400)
        for log in algo.logs:
            if "청산" in log:
                log_container.markdown(f":red[{log}]")
            elif "대기" in log:
                log_container.markdown(f":orange[{log}]")
            else:
                log_container.text(log)

    with col_vis:
        st.subheader("🏗️ Queue Visualization")
        
        # 큐 데이터 가져오기 (UI용 Helper 함수 사용)
        c_list, p_list = algo.get_queue_display_data()
        
        v_col1, v_col2 = st.columns(2)
        
        # --- Call Stack Visualization ---
        with v_col1:
            st.markdown(f"<h4 style='text-align:center; color:#FF4B4B;'>Call Queue ({len(c_list)})</h4>", unsafe_allow_html=True)
            # 기준선 표시 (Fixed Limit 모드일 때만)
            if algo.strategy_type == "fixed":
                st.caption(f"📏 Limit Line: {algo.box_size}")
                
            html_calls = '<div class="box-container">'
            for item in c_list:
                head_cls = "box-head" if item['IsHead'] else ""
                # f-string 내부 들여쓰기 제거 (Markdown Code Block 방지)
                html_calls += f"""<div class="algo-box box-call {head_cls}">{item['ID']}<br><small>R:{item['Real']} / V:{item['Virtual']}</small></div>"""
            html_calls += "</div>"
            st.markdown(html_calls, unsafe_allow_html=True)

        # --- Put Stack Visualization ---
        with v_col2:
            st.markdown(f"<h4 style='text-align:center; color:#1E90FF;'>Put Queue ({len(p_list)})</h4>", unsafe_allow_html=True)
            if algo.strategy_type == "fixed":
                st.caption(f"📏 Limit Line: {algo.box_size}")
                
            html_puts = '<div class="box-container">'
            for item in p_list:
                head_cls = "box-head" if item['IsHead'] else ""
                # f-string 내부 들여쓰기 제거 (Markdown Code Block 방지)
                html_puts += f"""<div class="algo-box box-put {head_cls}">{item['ID']}<br><small>R:{item['Real']} / V:{item['Virtual']}</small></div>"""
            html_puts += "</div>"
            st.markdown(html_puts, unsafe_allow_html=True)
            
    # 3. 수익 곡선 차트
    st.subheader("📈 Profit Curve (Realized)")
    if len(algo.history_balance) > 0:
        fig = px.line(y=algo.history_balance, x=range(len(algo.history_balance)), 
                      labels={'x': 'Step', 'y': 'Total Profit'}, title="Accumulated Realized Profit")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODE 2: Monte Carlo Simulation (자동 시뮬레이션 모드)
# ==========================================
else:
    st.subheader("🎲 Monte Carlo Simulation")
    
    mc_col1, mc_col2 = st.columns(2)
    with mc_col1:
        sim_count = st.slider("Number of Sims", 10, 500, 50)
        sim_steps = st.slider("Steps per Sim", 10, 200, 100)
    
    if st.button("🚀 Start Simulation"):
        all_results = []
        progress_bar = st.progress(0)
        
        for i in range(sim_count):
            # 시뮬레이션용 독립 인스턴스 생성 (현재 선택된 전략 적용)
            sim_algo = BalanceBoxLogic(setting_box_size, setting_unit, selected_strat)
            
            # 랜덤 워크 생성 (50% 확률로 상승/하락)
            random_moves = np.random.choice([1, -1], size=sim_steps)
            
            for move in random_moves:
                sim_algo.next_step(move)
            
            all_results.append(sim_algo.history_balance)
            progress_bar.progress((i + 1) / sim_count)
            
        st.success(f"Simulation Complete! (Strategy: {selected_strat})")
        
        # 결과 시각화
        results_df = pd.DataFrame(all_results).T
        
        st.write("### 1. Asset Paths (자산 변동 경로)")
        st.line_chart(results_df)
        
        final_values = results_df.iloc[-1]
        st.write("### 2. Distribution of Final Profit (최종 손익 분포)")
        fig_hist = px.histogram(final_values, nbins=20, title="Final Profit Distribution")
        fig_hist.add_vline(x=0, line_color="red")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.write(f"**Average Profit:** ${final_values.mean():,.2f}")
        st.write(f"**Max Profit:** ${final_values.max():,.2f}")
        st.write(f"**Min Profit:** ${final_values.min():,.2f}")