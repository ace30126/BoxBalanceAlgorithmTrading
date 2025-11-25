from collections import deque
import time

class BalanceBoxLogic:
    def __init__(self, box_size=2, unit_point=10, strategy_type="diff"):
        """
        strategy_type: 
            - "diff": Gap Balance (두 큐의 길이 '차이'가 box_size 이상이면 청산)
            - "fixed": Fixed Limit (각 큐의 '길이'가 box_size를 초과하면 청산)
        """
        self.box_size = box_size
        self.unit_point = unit_point
        self.strategy_type = strategy_type
        
        # Data Structures
        self.call_q = deque() # Queue for Call IDs
        self.put_q = deque()  # Queue for Put IDs
        self.manage_dict = {} # {ID: [Real, Virtual]}
        
        # State Variables
        self.total_profit = 0
        self.c_counter = 0 # ID Generator
        self.p_counter = 0
        self.logs = []
        self.history_balance = [0]
        self.step_count = 0
        
        # Init: Always start with 1 Call and 1 Put
        self._entry_call()
        self._entry_put()
        self.add_log(f"🏁 초기화 완료 ({self.strategy_type}): Call 1개, Put 1개 진입")

    def add_log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.insert(0, f"[{timestamp}] {message}") # Add to top

    def _entry_call(self):
        c_id = f"C{self.c_counter}"
        self.call_q.append(c_id)
        self.manage_dict[c_id] = [0, 0] # [Real, Virtual]
        self.c_counter += 1
        return c_id

    def _entry_put(self):
        p_id = f"P{self.p_counter}"
        self.put_q.append(p_id)
        self.manage_dict[p_id] = [0, 0] # [Real, Virtual]
        self.p_counter += 1
        return p_id

    def _update_gains(self, direction):
        # direction: 1 (Up), -1 (Down)
        calls = list(self.call_q)
        puts = list(self.put_q)

        if direction == 1: # UP
            # Rule 4: Real Gain Update
            for c in calls: self.manage_dict[c][0] += 1
            for p in puts:  self.manage_dict[p][0] -= 1
            
            # Rule 6: Virtual Gain Update (Head only)
            if calls: 
                self.manage_dict[calls[0]][1] += 1
            if puts: 
                # Decrease Virtual, but clamp at 0
                curr = self.manage_dict[puts[0]][1]
                self.manage_dict[puts[0]][1] = max(0, curr - 1)

        else: # DOWN
            # Rule 5: Real Gain Update
            for p in puts:  self.manage_dict[p][0] += 1
            for c in calls: self.manage_dict[c][0] -= 1
            
            # Rule 6: Virtual Gain Update (Head only)
            if puts: 
                self.manage_dict[puts[0]][1] += 1
            if calls:
                # Decrease Virtual, but clamp at 0
                curr = self.manage_dict[calls[0]][1]
                self.manage_dict[calls[0]][1] = max(0, curr - 1)

    def _try_pop(self, queue, queue_name):
        """Helper to pop from a specific queue if condition met"""
        if not queue: return False
        
        target_id = queue[0]
        real_gain = self.manage_dict[target_id][0]
        
        # Rule 8: 실 증감량이 0 이상인 경우만 pop
        if real_gain >= 0:
            popped = queue.popleft()
            profit_val = self.manage_dict[popped][0]
            self.total_profit += profit_val
            del self.manage_dict[popped]
            
            self.add_log(f"✂️ [청산-{queue_name}] {popped} 제거! 실현손익: {profit_val}")
            return True
        else:
            self.add_log(f"⚠️ [대기-{queue_name}] 청산 조건이나 {target_id} 손실중({real_gain})이라 유지")
            return False

    def _check_imbalance(self):
        """Check logic based on Strategy Type"""
        
        # [Strategy 1] Gap Balance (기존)
        # 두 큐의 길이 차이가 box_size 이상이면 큰 쪽을 청산
        if self.strategy_type == "diff":
            len_c = len(self.call_q)
            len_p = len(self.put_q)
            diff = len_c - len_p
            
            if abs(diff) >= self.box_size:
                if diff > 0: # Call > Put
                    return self._try_pop(self.call_q, "Call")
                else: # Put > Call
                    return self._try_pop(self.put_q, "Put")
                    
        # [Strategy 2] Fixed Limit (신규)
        # 각 큐의 길이가 box_size를 초과하면 해당 큐를 청산
        elif self.strategy_type == "fixed":
            popped_any = False
            # Call Queue Check
            if len(self.call_q) > self.box_size:
                if self._try_pop(self.call_q, "Call"):
                    popped_any = True
            
            # Put Queue Check
            if len(self.put_q) > self.box_size:
                if self._try_pop(self.put_q, "Put"):
                    popped_any = True
            
            return popped_any

        return False

    def next_step(self, direction):
        self.step_count += 1
        dir_str = "상승 🔺" if direction == 1 else "하락 🔻"
        self.add_log(f"Step {self.step_count}: {self.unit_point}Point {dir_str}")
        
        # 1. Update Gains
        self._update_gains(direction)
        
        # 2. Push New Position
        if direction == 1:
            self._entry_call()
        else:
            self._entry_put()
            
        # 3. Check Imbalance & Pop (based on strategy)
        self._check_imbalance()
        
        # Record History
        self.history_balance.append(self.total_profit * self.unit_point)

    def get_queue_display_data(self):
        # Helper for UI Visualization
        c_list = []
        for i, cid in enumerate(self.call_q):
            vals = self.manage_dict[cid]
            c_list.append({"ID": cid, "Real": vals[0], "Virtual": vals[1], "IsHead": (i==0)})
            
        p_list = []
        for i, pid in enumerate(self.put_q):
            vals = self.manage_dict[pid]
            p_list.append({"ID": pid, "Real": vals[0], "Virtual": vals[1], "IsHead": (i==0)})
            
        return c_list, p_list

    def get_unrealized_pnl(self):
        """현재 큐에 보유 중인 모든 포지션의 평가 손익 합계 계산"""
        unrealized_sum = 0
        for cid in self.call_q:
            unrealized_sum += self.manage_dict[cid][0] # Real Gain 누적
        for pid in self.put_q:
            unrealized_sum += self.manage_dict[pid][0] # Real Gain 누적
        return unrealized_sum