from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from math import log, sqrt
import random
import time

from Evaluate_Vivado import Evaluate_main

class VivadoOptimizationActions:
    def __init__(self):
        self.actions: Dict[str, List[str]] = {
           
            "synth_design": [
                "synth_design -top top\n",
                "synth_design -top top -flatten_hierarchy rebuilt\n",
                "synth_design -top top -flatten_hierarchy full\n",
                "synth_design -top top -gated_clock_conversion on\n",
            ],

            "opt_design": [
                "opt_design\n",
                "opt_design -directive Explore\n",
            ],

            "phys_opt_design": [
                "phys_opt_design\n",
                "phys_opt_design -directive Explore\n",
                "phys_opt_design -retime\n",
            ],

            "place_design": [
                "place_design\n",
                "place_design -directive Explore\n",
                "place_design -directive ExtraNetDelay_high\n",
            ],
            
            "route_design": [
                "route_design\n",
                "route_design -directive Explore\n",
                "route_design -directive NoTimingRelaxation\n",
            ],
   
            "phys_opt_design_2": [
                "phys_opt_design\n",
                "phys_opt_design -directive AggressiveExplore\n",
            ],

            "opt_design_post": [
                "opt_design\n",
                "opt_design -retime\n",
            ],
        }
        self.order: List[str] = list(self.actions.keys())  
        self.all_moves: List[Tuple[int, int]] = []
        for i, op in enumerate(self.order):
            for j in range(len(self.actions[op])):
                self.all_moves.append((i, j))

    def sequence_len(self) -> int:
        return len(self.order)

    def get_snippet(self, pos: int, idx: int) -> str:
        op = self.order[pos]
        return self.actions[op][idx]

    def tokens_to_tcl(self, indices: List[int]) -> str:

        lines = []
        for pos, idx in enumerate(indices):
            lines.append(self.get_snippet(pos, idx))
        return "".join(lines)


@dataclass
class Node:
    indices: List[Optional[int]]  
    parent: Optional["Node"] = None
    action: Optional[Tuple[int, int]] = None  
    children: Dict[Tuple[int, int], "Node"] = field(default_factory=dict)
    untried: List[Tuple[int, int]] = field(default_factory=list)
    visits: int = 0
    value_sum: float = 0.0

    def q(self) -> float:
        return 0.0 if self.visits == 0 else self.value_sum / self.visits

    def is_fully_expanded(self) -> bool:
        return len(self.untried) == 0


@dataclass
class Rewarder:
    theta: float = 0.7   
    lam: float = 0.2     
    ema_beta: float = 0.9
    _Tavg: float = 1.0
    _init: bool = False

    def update_T(self, T: float):
        if not self._init:
            self._Tavg = max(T, 1e-3)
            self._init = True
        else:
            self._Tavg = self.ema_beta * self._Tavg + (1 - self.ema_beta) * T

    def penalty(self, T: float) -> float:
        return max(0.0, T / max(self._Tavg, 1e-3) - 1.0)

    def to_reward(self, faults: int, timeouts: int, elapsed: float) -> float:
        base = self.theta * (faults / (faults + 1.0)) - (1 - self.theta) * (timeouts / (timeouts + 1.0))
        return base - self.lam * self.penalty(elapsed)

class MCTS:
    def __init__(self, actions: VivadoOptimizationActions,
                 exploration: float = 1.414, iteration_budget: int = 200,
                 time_budget: Optional[float] = None, rng: Optional[random.Random] = None):
        assert iteration_budget or time_budget
        self.A = actions
        self.c = exploration
        self.iteration_budget = iteration_budget
        self.time_budget = time_budget
        self.rng = rng or random.Random()
        self.rewarder = Rewarder()
        self.cache: Dict[Tuple[int, ...], Tuple[int, int]] = {}  # indices tuple -> (faults, timeouts)

    def search(self, episode: int, k_best: int = 5) -> List[Tuple[float, str]]:
        root = Node(indices=[None] * self.A.sequence_len())
        root.untried = self._gen_untried(root.indices)
        start = time.perf_counter()
        it = 0
        top: List[Tuple[float, str]] = []  

        while True:
            if self.iteration_budget and it >= self.iteration_budget:
                break
            if self.time_budget and (time.perf_counter() - start) >= self.time_budget:
                break
            it += 1

            node = root
            indices = list(node.indices)

            # Selection
            node, indices = self._select(node, indices)
            # Expansion
            if (not self._is_terminal(indices)) and (not node.is_fully_expanded()):
                node, indices = self._expand(node, indices)


            full_indices = self._rollout(indices)
            key = tuple(x for x in full_indices)

            t0 = time.perf_counter()
            if key in self.cache:
                faults, timeouts = self.cache[key]
            else:
                tcl_cmd = self.A.tokens_to_tcl(full_indices)

                faults, timeouts = Evaluate_main(episode, tcl_cmd)
                self.cache[key] = (faults, timeouts)
            elapsed = time.perf_counter() - t0
            self.rewarder.update_T(elapsed)
            reward = self.rewarder.to_reward(faults, timeouts, elapsed)

            # Backprop
            self._backprop(node, reward)

            # 维护 top-k
            tcl_cmd = self.A.tokens_to_tcl(full_indices)
            if len(top) < k_best:
                top.append((reward, tcl_cmd))
                top.sort(key=lambda x: x[0], reverse=True)
            else:
                if reward > top[-1][0]:
                    top[-1] = (reward, tcl_cmd)
                    top.sort(key=lambda x: x[0], reverse=True)

        return top

    # ---- 内部方法 ----
    def _gen_untried(self, indices: List[Optional[int]]) -> List[Tuple[int, int]]:
        for pos, v in enumerate(indices):
            if v is None:
                return [(pos, j) for j in range(len(self.A.actions[self.A.order[pos]]))]
        return []

    def _uct(self, parent: Node, child: Node) -> float:
        if child.visits == 0:
            return float("inf")
        return child.q() + self.c * sqrt(log(max(1, parent.visits)) / child.visits)

    def _select(self, node: Node, indices: List[Optional[int]]):
        while (not self._is_terminal(indices)) and node.is_fully_expanded():
            best_a, best_ch, best_s = None, None, -1e18
            for a, ch in node.children.items():
                s = self._uct(node, ch)
                if s > best_s:
                    best_a, best_ch, best_s = a, ch, s
            node = best_ch
            pos, idx = best_a
            indices[pos] = idx
        return node, indices

    def _expand(self, node: Node, indices: List[Optional[int]]):
        i = self.rng.randrange(len(node.untried))
        pos, idx = node.untried.pop(i)
        new_indices = list(indices)
        new_indices[pos] = idx
        ch = Node(indices=new_indices, parent=node, action=(pos, idx))
        ch.untried = self._gen_untried(new_indices)
        node.children[(pos, idx)] = ch
        return ch, new_indices

    def _rollout(self, indices: List[Optional[int]]) -> List[int]:
        filled = list(indices)
        for pos, idx in enumerate(filled):
            if idx is None:
                filled[pos] = self.rng.randrange(len(self.A.actions[self.A.order[pos]]))
        return [int(x) for x in filled]

    def _backprop(self, node: Node, reward: float):
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.value_sum += reward
            cur = cur.parent

    def _is_terminal(self, indices: List[Optional[int]]) -> bool:
        return all(x is not None for x in indices)

# ---------- 4) 入口函数 ----------
def main_mcts_vivado(episodes: int = 3, iters_per_episode: int = 50, k_best: int = 5):

    A = VivadoOptimizationActions()
    mcts = MCTS(A, iteration_budget=iters_per_episode, exploration=1.414)

    all_results: List[Tuple[float, str]] = []
    for ep in range(episodes):
        print("=" * 70)
        print(f"[MCTS Vivado] Episode {ep + 1}/{episodes}")
        topk = mcts.search(episode=ep+1, k_best=k_best)
        for rank, (rw, tcl) in enumerate(topk, 1):
            print(f"  #{rank} reward={rw:.4f}\n----- TCL -----\n{tcl.strip()}\n--------------\n")
        all_results.extend(topk)


    uniq = {}
    for rw, tcl in all_results:
        uniq.setdefault(tcl, rw)
        if rw > uniq[tcl]:
            uniq[tcl] = rw
    final = sorted([(rw, tcl) for tcl, rw in uniq.items()], key=lambda x: x[0], reverse=True)

    print("=" * 70)
    print("[MCTS Vivado] Final Top:")
    for rank, (rw, tcl) in enumerate(final[:k_best], 1):
        print(f"  #{rank} reward={rw:.4f}\n{tcl.strip()}\n")


    return [tcl for _, tcl in final[:k_best]]

if __name__ == "__main__":

    best_cmds = main_mcts_vivado(episodes=1, iters_per_episode=20, k_best=3)
    print("[BEST CMDS]")
    for c in best_cmds:
        print(c)
