import streamlit as st
import collections
import time
import pandas as pd
import random
import matplotlib.pyplot as plt

# --- [1. 알고리즘 로직 클래스 (상세 로그 & 단계별 실행 지원)] ---

class Item:
    def __init__(self, item_id, entry_price, item_type, state="Recruit", initial_profit=0):
        self.id = item_id
        self.entry_price = entry_price
        self.item_type = item_type  # "Call" or "Put"
        self.state = state          # Recruit, Combat, Wounded, Defeated
        self.real_profit = initial_profit # [NEW] 초기 수익 설정 가능 (부상병 -2)
        self.virtual_profit = 0     # 가상수익

class BalancedBoxLogic:
    def __init__(self, verbose=True):
        self.call_queue = collections.deque()
        self.put_queue = collections.deque()
        
        self.wounded_pool = collections.deque()
        self.defeated_pool = collections.deque()
        self.next_recruit_id = 0
        
        self.current_price = 1000.0
        self.logs = []
        self.total_realized_profit = 0
        self.last_direction = None 
        self.verbose = verbose
        
        # [NEW] 수익 그래프를 위한 히스토리 데이터
        # 초기 상태: 0 profit
        self.profit_history = [{'step': 0, 'profit': 0}]
        self.step_count = 0
        
        # 단계별 실행을 위한 상태 변수
        self.pending_direction = None
        self.execution_phase = 0  # 0:Idle, 1:Update, 2:Reversal, 3:Entry, 4:Balance

        # 초기 세팅
        self.initialize_queues()

    def log(self, msg, category="INFO"):
        if not self.verbose: return
        timestamp = time.strftime("%H:%M:%S")
        icon = "📝"
        if category == "PROFIT": icon = "💰"
        elif category == "LOSS": icon = "💥"
        elif category == "ENTRY": icon = "➕"
        elif category == "REASON": icon = "💡"
        
        self.logs.insert(0, f"[{timestamp}] {icon} {msg}")

    def record_profit(self):
        # 현재 스텝의 누적 수익 저장
        # 중복 스텝 방지: 이미 현재 스텝 기록이 있다면 업데이트, 없으면 추가
        if self.profit_history and self.profit_history[-1]['step'] == self.step_count:
             self.profit_history[-1]['profit'] = self.total_realized_profit
        else:
            self.profit_history.append({
                'step': self.step_count,
                'profit': self.total_realized_profit
            })

    def get_soldier_id(self):
        if self.wounded_pool: 
            return self.wounded_pool.popleft(), "🚑부상병"
        elif self.defeated_pool: 
            return self.defeated_pool.popleft(), "🎖️패잔병"
        else:
            new_id = self.next_recruit_id
            self.next_recruit_id += 1
            return new_id, "👶신병"

    def initialize_queues(self):
        if not self.call_queue:
            cid, _ = self.get_soldier_id()
            self.call_queue.append(Item(cid, self.current_price, "Call", "Combat"))
            self.log("🏁 초기 세팅: Call Item(0) 투입", "ENTRY")
        if not self.put_queue:
            pid, _ = self.get_soldier_id()
            self.put_queue.append(Item(pid, self.current_price, "Put", "Combat"))
            self.log("🏁 초기 세팅: Put Item(0) 투입", "ENTRY")

    def get_unrealized_profit(self):
        return sum(i.real_profit for i in self.call_queue) + sum(i.real_profit for i in self.put_queue)

    def can_enter(self, queue):
        if not queue: return True, "초기 진입 허용"
        for item in queue:
            if item.real_profit > 0:
                return True, f"ID({item.item_type[0]}{item.id})의 실수익({item.real_profit}) > 0"
            if item.virtual_profit > 0:
                return True, f"ID({item.item_type[0]}{item.id})의 가상수익({item.virtual_profit}) > 0"
        return False, "양수 수익(실/가상)인 아이템 없음"

    def pop_item(self, queue, reason):
        if not queue: return
        item = queue.popleft()
        
        if item.real_profit < 0:
            item.state = "Wounded"
            self.wounded_pool.appendleft(item.id)
            self.log(f"POP(손실): {item.item_type}{item.id} (R:{item.real_profit}) -> 부상병 이동 || 사유: {reason}", "LOSS")
        else:
            item.state = "Defeated"
            self.defeated_pool.append(item.id)
            # [Logic] 부상병이 -2에서 시작했으므로, 여기서 더해지는 item.real_profit은
            # 이미 페널티가 반영된 최종 수익입니다. (별도 차감 불필요)
            self.total_realized_profit += item.real_profit
            self.log(f"POP(이익): {item.item_type}{item.id} (R:{item.real_profit}) -> 이익 확정 || 사유: {reason}", "PROFIT")
        
        # Pop 발생 시 수익 기록 업데이트 (중요: 실현 손익 변화 시점)
        self.record_profit()

    # --- [단계별 실행 함수들] ---

    # [Phase 1] 가격 및 수익 업데이트
    def step_1_update_profits(self):
        direction = self.pending_direction
        is_up = (direction == "UP")
        price_change = 10 if is_up else -10
        self.current_price += price_change
        
        self.step_count += 1 # 스텝 증가
        
        # 수익 계산 logic
        if is_up:
            for i in self.call_queue:
                i.real_profit += 1
                i.virtual_profit += 1
            for i in self.put_queue:
                i.real_profit -= 1
                i.virtual_profit = max(0, i.virtual_profit - 1) if i.virtual_profit > 0 else 0
        else:
            for i in self.call_queue:
                i.real_profit -= 1
                i.virtual_profit = max(0, i.virtual_profit - 1) if i.virtual_profit > 0 else 0
            for i in self.put_queue:
                i.real_profit += 1
                i.virtual_profit += 1
                
        arrow = "🔺" if is_up else "🟦"
        self.log(f"가격 변동: {arrow} {direction} (현재가: {self.current_price})", "INFO")
        self.log("전체 아이템의 실/가상 수익이 업데이트 되었습니다.", "INFO")

    # [Phase 2] 장 역전 체크
    def step_2_handle_reversal(self):
        direction = self.pending_direction
        if self.last_direction is None or self.last_direction == direction:
            self.log("장 흐름 유지됨 (역전 아님) -> 특별 조치 없음", "REASON")
            return

        is_up = (direction == "UP")
        self.log(f"🔄 장 역전 감지! ({self.last_direction} -> {direction})", "REASON")
        
        count = 0
        if not is_up: # UP -> DOWN
            while self.call_queue and self.call_queue[0].real_profit > 0:
                self.pop_item(self.call_queue, "장 역전(하락반전)으로 인한 Call 수익청산")
                count += 1
        else: # DOWN -> UP
            while self.put_queue and self.put_queue[0].real_profit > 0:
                self.pop_item(self.put_queue, "장 역전(상승반전)으로 인한 Put 수익청산")
                count += 1
        
        if count == 0:
            self.log("장 역전되었으나, 즉시 청산할 수익 아이템이 없습니다.", "REASON")

    # [Phase 3] 신규 진입 (Push)
    def step_3_entry(self):
        direction = self.pending_direction
        is_up = (direction == "UP")
        
        target_queue = self.call_queue if is_up else self.put_queue
        queue_name = "Call" if is_up else "Put"
        
        can_enter, reason = self.can_enter(target_queue)
        
        if can_enter:
            sid, origin = self.get_soldier_id()
            
            # [NEW] 부상병일 경우 초기 수익 -2 설정
            initial_p = -2 if origin == "🚑부상병" else 0
            
            new_item = Item(sid, self.current_price, queue_name, "Combat", initial_profit=initial_p)
            target_queue.append(new_item)
            
            log_msg = f"{queue_name} 진입 성공 (ID:{sid}, {origin})"
            if initial_p < 0:
                log_msg += f" [패널티 적용: {initial_p}]"
            
            self.log(f"{log_msg} || 근거: {reason}", "ENTRY")
        else:
            self.log(f"{queue_name} 진입 실패 (대기) || 사유: {reason}", "REASON")

    # [Phase 4] 균형 조절 (Pop)
    def step_4_balance(self):
        direction = self.pending_direction
        is_up = (direction == "UP")
        
        # 1. 수량 균형
        while len(self.call_queue) >= len(self.put_queue) + 2:
            self.pop_item(self.call_queue, f"Call({len(self.call_queue)}) > Put({len(self.put_queue)}) + 2 (수량과다)")
        
        while len(self.put_queue) >= len(self.call_queue) + 2:
            self.pop_item(self.put_queue, f"Put({len(self.put_queue)}) > Call({len(self.call_queue)}) + 2 (수량과다)")

        # 2. 방향성 제한
        if not is_up: # 하락장
             while len(self.call_queue) > len(self.put_queue):
                 self.pop_item(self.call_queue, "하락장에서 Call 큐가 Put 큐보다 김 (방향성 위배)")
        if is_up: # 상승장
            while len(self.put_queue) > len(self.call_queue):
                self.pop_item(self.put_queue, "상승장에서 Put 큐가 Call 큐보다 김 (방향성 위배)")
        
        self.log("균형 조절(Balancing) 완료", "INFO")
        
        # 턴 종료 처리
        self.last_direction = direction
        self.pending_direction = None
        self.record_profit() # 턴 종료시 기록

    def full_step_auto(self, direction):
        # 몬테카를로/자동실행 용 (로그 없이 한방에 실행)
        self.pending_direction = direction
        self.step_1_update_profits()
        self.step_2_handle_reversal()
        self.step_3_entry()
        self.step_4_balance()

# --- [2. Streamlit UI] ---

st.set_page_config(page_title="Balanced Box V6 Step-by-Step", layout="wide")

# CSS: 카드 UI & 로그 스타일
st.markdown("""
<style>
    .card-container {
        display: flex;
        flex-direction: column; 
        gap: 6px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 8px;
        min-height: 400px;
        max-height: 500px;
        overflow-y: auto;
    }
    .trade-card {
        padding: 8px 12px;
        border-radius: 6px;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 5px solid #ccc;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: sans-serif;
        color: #333 !important;
    }
    .profit-plus { border-left-color: #4CAF50 !important; background-color: #e8f5e9; }
    .profit-minus { border-left-color: #FF5252 !important; background-color: #ffebee; }
    
    .metric-val { font-weight: bold; color: #333 !important; }
    .val-plus { color: #2E7D32 !important; }
    .val-minus { color: #C62828 !important; }
    
    /* Step Indicator Style */
    .step-box {
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        background-color: #eee;
        color: #aaa;
    }
    .step-active {
        background-color: #2196F3;
        color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Balanced Box V6: 상세 분석 모드")
st.markdown("알고리즘의 동작을 **4단계(수익갱신 -> 장역전 -> 진입 -> 균형)**로 나누어 실행하며 상세한 이유를 확인합니다.")

if 'sim' not in st.session_state:
    st.session_state.sim = BalancedBoxLogic()

sim = st.session_state.sim

# --- [Controller Logic] ---
def set_direction(direction):
    if sim.execution_phase == 0: # Idle 상태일 때만 방향 설정 가능
        sim.pending_direction = direction
        sim.execution_phase = 1 # 첫 단계 진입

def execute_next_step():
    phase = sim.execution_phase
    if phase == 1:
        sim.step_1_update_profits()
        sim.execution_phase = 2
    elif phase == 2:
        sim.step_2_handle_reversal()
        sim.execution_phase = 3
    elif phase == 3:
        sim.step_3_entry()
        sim.execution_phase = 4
    elif phase == 4:
        sim.step_4_balance()
        sim.execution_phase = 0 # Idle로 복귀

# --- [Sidebar: Control Panel] ---
with st.sidebar:
    st.header("🎮 컨트롤러")
    
    tab_manual, tab_mc = st.tabs(["👆 수동 조작", "🎲 시뮬레이션(MC)"])

    # --- Manual Tab ---
    with tab_manual:
        # Phase 0: 방향 선택
        if sim.execution_phase == 0:
            st.info("다음 시장 방향을 선택하세요.")
            c1, c2 = st.columns(2)
            if c1.button("📈 상승 준비 (UP)", use_container_width=True):
                set_direction("UP")
                st.rerun()
            if c2.button("📉 하락 준비 (DOWN)", use_container_width=True):
                set_direction("DOWN")
                st.rerun()
        else:
            # Phase 1~4: 단계별 실행
            dir_text = "상승(UP)" if sim.pending_direction == "UP" else "하락(DOWN)"
            st.warning(f"현재 **{dir_text}** 처리 중입니다.")
            
            # 다음 단계 버튼
            btn_label = ""
            if sim.execution_phase == 1: btn_label = "1️⃣ 수익 업데이트 실행"
            elif sim.execution_phase == 2: btn_label = "2️⃣ 장 역전 체크 실행"
            elif sim.execution_phase == 3: btn_label = "3️⃣ 신규 진입(Push) 실행"
            elif sim.execution_phase == 4: btn_label = "4️⃣ 균형 조절(Pop) 실행"
            
            if st.button(f"▶ {btn_label}", type="primary", use_container_width=True):
                execute_next_step()
                st.rerun()
    
    # --- Monte Carlo Tab ---
    with tab_mc:
        st.markdown("### 몬테카를로 시뮬레이션")
        mc_cases = st.number_input("반복 횟수", 1, 100, 10)
        mc_steps = st.number_input("스텝 수", 10, 500, 100)
        
        if st.button("🚀 실행"):
            # MC 실행 로직
            results = []
            
            # 진행상황 표시
            progress_bar = st.progress(0)
            
            for i in range(mc_cases):
                mc_sim = BalancedBoxLogic(verbose=False)
                # 랜덤 워크 실행
                for _ in range(mc_steps):
                    direction = "UP" if random.random() > 0.5 else "DOWN"
                    mc_sim.full_step_auto(direction)
                
                # 최종 데이터 저장 (히스토리 포함)
                results.append(mc_sim.profit_history)
                progress_bar.progress((i + 1) / mc_cases)
            
            st.session_state['mc_results'] = results
            st.success("시뮬레이션 완료! 결과 탭을 확인하세요.")

    st.divider()
    if st.button("🔄 리셋"):
        st.session_state.sim = BalancedBoxLogic()
        if 'mc_results' in st.session_state:
            del st.session_state['mc_results']
        st.rerun()

    st.markdown("### 💰 자산 현황")
    unrealized = sim.get_unrealized_profit()
    total = sim.total_realized_profit + unrealized
    st.metric("실현 수익", f"{sim.total_realized_profit:+d}")
    st.metric("미실현 수익", f"{unrealized:+d}")
    st.metric("총 자산", f"{total:+d}")

# --- [Main Display Area] ---

# 1. 몬테카를로 결과가 있으면 그래프 표시
if 'mc_results' in st.session_state and st.session_state['mc_results']:
    st.subheader("📊 몬테카를로 시뮬레이션 결과")
    
    # 모든 케이스의 profit history를 하나의 차트에 그림
    # 데이터프레임 변환 (각 케이스를 컬럼으로)
    all_profits = {}
    for idx, history in enumerate(st.session_state['mc_results']):
        df = pd.DataFrame(history)
        # 중복된 step 제거 및 인덱스 설정 (안전장치)
        df = df.drop_duplicates(subset=['step'])
        all_profits[f'Case {idx+1}'] = df.set_index('step')['profit']
    
    df_chart = pd.DataFrame(all_profits)
    st.line_chart(df_chart, height=400)
    
    # 통계
    final_profits = df_chart.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("평균 수익", f"{final_profits.mean():.1f}")
    c2.metric("최고 수익", f"{final_profits.max():.0f}")
    c3.metric("최저 수익", f"{final_profits.min():.0f}")
    
    if st.button("결과 닫기"):
        del st.session_state['mc_results']
        st.rerun()

else:
    # 2. 기본 수동 모드 화면 (카드 UI)
    
    # 단계 표시기
    steps = ["대기(Idle)", "① 수익갱신", "② 장역전체크", "③ 진입(Push)", "④ 균형조절"]
    cols = st.columns(5)
    for i, col in enumerate(cols):
        css_class = "step-box step-active" if i == sim.execution_phase else "step-box"
        col.markdown(f'<div class="{css_class}">{steps[i]}</div>', unsafe_allow_html=True)

    st.divider()

    # Queue 렌더링 함수
    def render_html_card(queue):
        html_parts = ['<div class="card-container">']
        if not queue:
            html_parts.append('<div style="text-align:center; color:#999; padding:20px;">비어있음</div>')
        
        for item in queue:
            status_cls = "profit-plus" if item.real_profit > 0 else ("profit-minus" if item.real_profit < 0 else "")
            real_cls = "val-plus" if item.real_profit > 0 else ("val-minus" if item.real_profit < 0 else "")
            virt_cls = "val-plus" if item.virtual_profit > 0 else ""
            
            card_html = (
                f'<div class="trade-card {status_cls}">'
                f'<div style="font-weight:bold;">{item.item_type[0]}{item.id:02d}</div>'
                f'<div>'
                f'<span style="font-size:12px; color:#555;">실:</span><span class="metric-val {real_cls}">{item.real_profit:+d}</span> '
                f'<span style="font-size:12px; color:#555;">가:</span><span class="metric-val {virt_cls}">{item.virtual_profit:+d}</span>'
                f'</div>'
                f'</div>'
            )
            html_parts.append(card_html)
        html_parts.append('</div>')
        return "".join(html_parts)

    c_call, c_vs, c_put = st.columns([4, 0.5, 4])

    with c_call:
        st.subheader(f"🔴 Call ({len(sim.call_queue)})")
        st.markdown(render_html_card(sim.call_queue), unsafe_allow_html=True)

    with c_vs:
        st.markdown("<div style='height:400px; border-left:2px dashed #ddd; margin:0 auto; width:2px;'></div>", unsafe_allow_html=True)

    with c_put:
        st.subheader(f"🔵 Put ({len(sim.put_queue)})")
        st.markdown(render_html_card(sim.put_queue), unsafe_allow_html=True)

    st.divider()

    # Pools & Logs
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### 🏥 병사 대기열")
        wounded = ", ".join([f"🚑{id}" for id in sim.wounded_pool]) if sim.wounded_pool else "-"
        st.info(f"**부상병 (1순위):** {wounded} (재진입시 -2 패널티)")
        st.write(f"패잔병 대기: {len(sim.defeated_pool)} | 신병 대기: ∞")

    with c2:
        st.markdown("### 📝 상세 동작 로그")
        with st.container(height=300, border=True):
            for l in sim.logs:
                st.text(l)