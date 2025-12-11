import streamlit as st
import collections
import time
import random
import matplotlib.pyplot as plt
import numpy as np

# --- [1. 알고리즘 로직 클래스] ---

class Item:
    def __init__(self, item_id, entry_price, item_type, state="Recruit"):
        self.id = item_id
        self.entry_price = entry_price
        self.item_type = item_type  # "Call" or "Put"
        self.state = state          # Recruit, Combat, Wounded, Defeated
        self.real_profit = 0
        self.virtual_profit = 0     # 가상수익

class BalancedBoxLogic:
    def __init__(self, verbose=True):
        self.call_queue = collections.deque()
        self.put_queue = collections.deque()
        
        # 우선순위 Pool
        self.wounded_pool = collections.deque()
        self.defeated_pool = collections.deque()
        
        # [변경 1] Recruit Pool 크기 제거 (무한 카운터 사용)
        self.next_recruit_id = 0
        
        self.current_price = 1000.0
        self.logs = []
        self.total_realized_profit = 0
        self.verbose = verbose # 로깅 여부 (시뮬레이션 속도 최적화용)
        
        # 초기화 시 자동 실행 (Call/Put 1개씩)
        self.initialize_queues()

    def log(self, msg):
        if self.verbose:
            timestamp = time.strftime("%H:%M:%S")
            self.logs.insert(0, f"[{timestamp}] {msg}")

    def get_soldier_id(self):
        # 진입 우선순위 로직
        if self.wounded_pool:
            return self.wounded_pool.popleft(), "🚑부상병"
        elif self.defeated_pool:
            return self.defeated_pool.popleft(), "🎖️패잔병"
        else:
            new_id = self.next_recruit_id
            self.next_recruit_id += 1
            return new_id, "👶신병"

    def initialize_queues(self):
        # 초기 세팅: Call/Put 각각 1개씩 진입 상태로 시작
        if not self.call_queue:
            cid, origin = self.get_soldier_id()
            self.call_queue.append(Item(cid, self.current_price, "Call", "Combat"))
            self.log(f"🏁 초기 세팅: Call Item({cid}) 투입")
        
        if not self.put_queue:
            pid, origin = self.get_soldier_id()
            self.put_queue.append(Item(pid, self.current_price, "Put", "Combat"))
            self.log(f"🏁 초기 세팅: Put Item({pid}) 투입")

    def get_unrealized_profit(self):
        call_p = sum(i.real_profit for i in self.call_queue)
        put_p = sum(i.real_profit for i in self.put_queue)
        return call_p + put_p

    def can_enter(self, queue):
        if not queue: return True
        for item in queue:
            if item.real_profit > 0 or item.virtual_profit > 0:
                return True
        return False

    def pop_item(self, queue, reason):
        if not queue: return
        item = queue.popleft()
        
        if item.real_profit < 0:
            item.state = "Wounded"
            self.wounded_pool.appendleft(item.id) # 부상병은 Queue Front로
            self.log(f"💥 POP(손실): {item.item_type}{item.id} (R:{item.real_profit}) -> 부상병 이동")
        else:
            item.state = "Defeated"
            self.defeated_pool.append(item.id)
            self.total_realized_profit += item.real_profit
            self.log(f"💰 POP(이익): {item.item_type}{item.id} (R:{item.real_profit}) -> 이익 확정")

    def update_profits(self, is_up):
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

    def check_balance(self, is_up):
        # 1. 수량 균형
        while len(self.call_queue) >= len(self.put_queue) + 2:
            self.pop_item(self.call_queue, "균형조절(수량)")
        while len(self.put_queue) >= len(self.call_queue) + 2:
            self.pop_item(self.put_queue, "균형조절(수량)")

        # 2. 방향성 제한
        if not is_up: # 하락장
             while len(self.call_queue) > len(self.put_queue):
                 self.pop_item(self.call_queue, "방향성제한(Call축소)")
        if is_up: # 상승장
            while len(self.put_queue) > len(self.call_queue):
                self.pop_item(self.put_queue, "방향성제한(Put축소)")

    def step(self, direction):
        is_up = (direction == "UP")
        price_change = 10 if is_up else -10
        self.current_price += price_change
        
        arrow = "🔺" if is_up else "🟦"
        self.log(f"{arrow} 가격변동: {direction} (현재가: {self.current_price})")

        self.update_profits(is_up)

        if is_up:
            if self.can_enter(self.call_queue):
                sid, origin = self.get_soldier_id()
                self.call_queue.append(Item(sid, self.current_price, "Call", "Combat"))
                self.log(f"➕ Call 진입 (ID:{sid}, {origin})")
            else:
                self.log("✋ Call 진입 대기 (조건 미충족)")
        else:
            if self.can_enter(self.put_queue):
                sid, origin = self.get_soldier_id()
                self.put_queue.append(Item(sid, self.current_price, "Put", "Combat"))
                self.log(f"➕ Put 진입 (ID:{sid}, {origin})")
            else:
                self.log("✋ Put 진입 대기 (조건 미충족)")

        self.check_balance(is_up)


# --- [2. Streamlit UI 구성] ---

st.set_page_config(page_title="Balanced Box Pro Simulator", layout="wide")

# CSS 수정: [1] raw tag 방지(코드에서는 f-string 들여쓰기 제거로 해결), [2] 글자색 강제 검정
st.markdown("""
<style>
    .card-container {
        display: flex;
        flex-direction: column; /* 카드가 위에서 아래로 쌓이도록 변경 */
        gap: 6px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 8px;
        min-height: 300px;
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
        color: #333 !important; /* 글자색 강제 검정 (Dark Mode 대응) */
    }
    .profit-plus { border-left-color: #4CAF50 !important; background-color: #e8f5e9; }
    .profit-minus { border-left-color: #FF5252 !important; background-color: #ffebee; }
    
    .card-id { font-weight: bold; font-size: 14px; color: #000 !important; }
    
    .metric-label { font-size: 12px; color: #555 !important; margin-right: 2px; }
    .metric-val { font-weight: bold; font-size: 13px; color: #333 !important; }
    
    .val-plus { color: #2E7D32 !important; }
    .val-minus { color: #C62828 !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Balanced Box Pro Simulator")

if 'sim' not in st.session_state:
    st.session_state.sim = BalancedBoxLogic()

sim = st.session_state.sim

# --- [사이드바] ---
with st.sidebar:
    st.header("🎮 컨트롤러")
    
    tab_manual, tab_mc = st.tabs(["👆 수동 조작", "🎲 몬테카를로"])
    
    with tab_manual:
        c1, c2 = st.columns(2)
        if c1.button("📈 상승 (UP)", use_container_width=True): sim.step("UP")
        if c2.button("📉 하락 (DOWN)", use_container_width=True): sim.step("DOWN")
        
        st.divider()
        if st.button("🔄 리셋 (초기화)", use_container_width=True):
            st.session_state.sim = BalancedBoxLogic()
            st.rerun()

    with tab_mc:
        st.markdown("### 시뮬레이션 설정")
        mc_cases = st.number_input("시뮬레이션 횟수", min_value=10, max_value=1000, value=100, step=10)
        mc_steps = st.number_input("케이스 당 스텝 수", min_value=10, max_value=500, value=50, step=10)
        up_prob = st.slider("상승 확률 (0.5=랜덤)", 0.0, 1.0, 0.5)
        
        run_mc = st.button("🚀 시뮬레이션 실행", use_container_width=True)

    st.divider()
    unrealized = sim.get_unrealized_profit()
    total_equity = sim.total_realized_profit + unrealized
    
    st.markdown("### 💰 자산 현황")
    st.metric("실현 수익 (Realized)", f"{sim.total_realized_profit:+d}")
    st.metric("미실현 수익 (Unrealized)", f"{unrealized:+d}", delta_color="off")
    st.metric("총 자산 (Total Equity)", f"{total_equity:+d}")

# --- [메인 화면] ---

if run_mc:
    st.subheader(f"📊 몬테카를로 시뮬레이션 결과 ({mc_cases}회)")
    results = []
    progress_bar = st.progress(0)
    
    for i in range(mc_cases):
        mc_sim = BalancedBoxLogic(verbose=False)
        for _ in range(mc_steps):
            direction = "UP" if random.random() < up_prob else "DOWN"
            mc_sim.step(direction)
        final_equity = mc_sim.total_realized_profit + mc_sim.get_unrealized_profit()
        results.append(final_equity)
        progress_bar.progress((i + 1) / mc_cases)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(results, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
    ax.axvline(np.mean(results), color='red', linestyle='dashed', linewidth=1, label=f'Mean: {np.mean(results):.1f}')
    ax.set_title(f"Profit Distribution (Steps: {mc_steps}, Prob: {up_prob})")
    ax.legend()
    st.pyplot(fig)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("평균 수익", f"{np.mean(results):.1f}")
    c2.metric("최대 수익", f"{np.max(results)}")
    c3.metric("최소 수익", f"{np.min(results)}")

else:
    # --- [HTML 렌더링 수정: Indentation 제거] ---
    def render_html_card(queue):
        # f-string의 들여쓰기를 제거하여 HTML이 Markdown 코드 블록으로 인식되지 않도록 함
        html_parts = ['<div class="card-container">']
        if not queue:
            html_parts.append('<div style="text-align:center; color:#999; padding:20px;">비어있음</div>')
        
        for item in queue:
            status_cls = "profit-plus" if item.real_profit > 0 else ("profit-minus" if item.real_profit < 0 else "")
            real_cls = "val-plus" if item.real_profit > 0 else ("val-minus" if item.real_profit < 0 else "")
            virt_cls = "val-plus" if item.virtual_profit > 0 else ""
            
            # 한 줄로 이어지거나 들여쓰기 없이 생성
            card_html = (
                f'<div class="trade-card {status_cls}">'
                f'<div class="card-id">{item.item_type[0]}{item.id:02d}</div>'
                f'<div>'
                f'<span class="metric-label">실:</span><span class="metric-val {real_cls}">{item.real_profit:+d}</span> '
                f'<span class="metric-label">가:</span><span class="metric-val {virt_cls}">{item.virtual_profit:+d}</span>'
                f'</div>'
                f'</div>'
            )
            html_parts.append(card_html)
        
        html_parts.append('</div>')
        return "".join(html_parts)

    col_call, col_center, col_put = st.columns([4, 0.5, 4])

    with col_call:
        st.subheader(f"🔴 Call Queue ({len(sim.call_queue)})")
        st.markdown(render_html_card(sim.call_queue), unsafe_allow_html=True)

    with col_center:
        st.markdown("<div style='height:300px; border-left: 2px dashed #ddd; margin: 0 auto; width: 2px;'></div>", unsafe_allow_html=True)

    with col_put:
        st.subheader(f"🔵 Put Queue ({len(sim.put_queue)})")
        st.markdown(render_html_card(sim.put_queue), unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🏥 병사 대기열")
        wounded_str = ", ".join([f"🚑{id}" for id in sim.wounded_pool]) if sim.wounded_pool else "없음"
        st.info(f"**부상병 (1순위):** {wounded_str}")
        st.write(f"**패잔병 (2순위):** {len(sim.defeated_pool)}명")
        st.write(f"**신병 (3순위):** (무제한)")

    with c2:
        st.markdown("### 📝 로그")
        with st.container(height=200, border=True):
            for log in sim.logs:
                st.text(log)