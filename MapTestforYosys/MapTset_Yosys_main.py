
import random
import numpy as np
from collections import namedtuple
import os
 import Evaluate_Yosys  


class YosysOptimizationActions:
    def __init__(self):
        self.actions = {

            'abc': [
                "abc -dress; ", "abc -markgroups; ", "abc -showtmp; ", "abc -nocleanup; ",
                "abc -keepff; ", "abc -dff; ", "abc -sop; ", "abc -fast; "
            ],

            'opt_expr': [
                "opt_expr; ", "opt_expr -mux_undef; ", "opt_expr -mux_bool; ", "opt_expr -undriven; ",
                "opt_expr -noclkinv; ", "opt_expr -fine; ", "opt_expr -full; ", "opt_expr -keepdc; "
            ],
            'opt_clean': ["opt_clean; ", "opt_clean -purge; "],
            'opt_demorgan': ["opt_demorgan; "],
            'opt_dff': [
                "opt_dff; ", "opt_dff -nodffe; ", "opt_dff -nosdff; ",
                "opt_dff -keepdc; ", "opt_dff -sat; "
            ],
            'opt_lut': ["opt_lut; "],
            'opt_lut_ins': ["opt_lut_ins; "],
            'opt_merge': ["opt_merge; ", "opt_merge -share_all; "],
            'opt_muxtree': ["opt_muxtree; "],
            'opt_reduce': ["opt_reduce; ", "opt_reduce -fine; ", "opt_reduce -full; "],
            'opt_share': ["opt_share; "],
            'opt_ffinv': ["opt_ffinv; "],
            'opt_mem': ["opt_mem; "],
            'opt_mem_feedback': ["opt_mem_feedback; "],
            'opt_mem_priority': ["opt_mem_priority; "],
            'opt_mem_widen': ["opt_mem_widen; "],

            'memory_share': ["memory_share; "],
            'memory_collect': ["memory_collect; "],
            'memory_bmux2rom': ["memory_bmux2rom; "],
            'memory_bram': ["memory_bram; "],
            'memory_dff': ["memory_dff; "],
            'memory_libmap': ["memory_libmap; "],
            'memory_map': ["memory_map; "],
            'memory_memx': ["memory_memx; "],
            'memory_narrow': ["memory_narrow; "],
            'memory_nordff': ["memory_nordff; "],
            'memory_unpack': ["memory_unpack; "],
        }
        self.all_operations = list(self.actions.keys())

    def get_action_space(self):
        return self.all_operations

    def get_param_count(self, operation):
        return len(self.actions[operation])

    def get_command(self, action):
       
        operation, index = action
        if operation in self.actions and 0 <= index < len(self.actions[operation]):
            return self.actions[operation][index]
        return ""

    def enumerate_all_moves(self):
        
        moves = []
        for op in self.all_operations:
            for idx in range(self.get_param_count(op)):
                moves.append((op, idx))
        return moves


class OptimizationEnvironment:
    def __init__(self, y_optimization_actions):
        self.actions = y_optimization_actions
        self.history = []

    def reset(self):
        self.history = []
        return None

    def evaluate_action(self, actions, episode):

        new_episode = episode + 1
        command_sequence = "hierarchy; proc; "
        for operation, index in actions:
            command_sequence += self.actions.get_command((operation, index)) + " "
        command_sequence = command_sequence.strip()

        fault_number, timeout_number = Evaluate_Yosys.Evaluate_main(new_episode, command_sequence)

        theta = 0.7
        reward = (theta * (fault_number) / (fault_number + 1)) - ((1 - theta) * (timeout_number) / (timeout_number + 1))

        print(f"[Eval] episode={episode+1} faults={fault_number} timeouts={timeout_number} -> reward={reward:.4f}")
        return reward, command_sequence



class MCTSNode:
    __slots__ = ("parent", "children", "untried_moves", "visits", "value_sum", "partial_actions")

    def __init__(self, parent, untried_moves, partial_actions):
        self.parent = parent
        self.children = []              
        self.untried_moves = list(untried_moves)  
        self.visits = 0
        self.value_sum = 0.0
        self.partial_actions = list(partial_actions) 

    def q(self):
        return 0.0 if self.visits == 0 else self.value_sum / self.visits

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def add_child(self, move, all_moves):
        
        new_partial = self.partial_actions + [move]
        child = MCTSNode(parent=self, untried_moves=all_moves, partial_actions=new_partial)
        self.children.append(child)
        return child


class MCTS:
    def __init__(self, all_moves, sequence_len, uct_c=1.414, iteration_budget=1000, rollout_random=True, rng=None):

        self.all_moves = list(all_moves)
        self.sequence_len = sequence_len
        self.c = uct_c
        self.iteration_budget = iteration_budget
        self.rollout_random = rollout_random
        self.rng = rng or random.Random()

    def search(self, env, episode):

        root = MCTSNode(parent=None, untried_moves=self.all_moves, partial_actions=[])
        best_reward = -1e9
        best_actions = None
        best_command = ""

        for _ in range(self.iteration_budget):
            node = root

           
            while node.children and node.is_fully_expanded() and len(node.partial_actions) < self.sequence_len:
                node = self._select_uct(node)

            
            if len(node.partial_actions) < self.sequence_len and node.untried_moves:
                move = node.untried_moves.pop(self.rng.randrange(len(node.untried_moves)))
                node = node.add_child(move, self.all_moves)

           
            completed = list(node.partial_actions)
            while len(completed) < self.sequence_len:
                completed.append(self.all_moves[self.rng.randrange(len(self.all_moves))])

          
            reward, cmd = env.evaluate_action(completed, episode)

            
            if reward > best_reward:
                best_reward = reward
                best_actions = completed
                best_command = cmd

            
            self._backprop(node, reward)

        return best_actions, best_reward, best_command

    def _select_uct(self, node):
       
        best_score = -1e18
        best_child = None
        for ch in node.children:
            if ch.visits == 0:
                score = float("inf")
            else:
                score = ch.q() + self.c * np.sqrt(np.log(max(1, node.visits)) / ch.visits)
            if score > best_score:
                best_score = score
                best_child = ch
        return best_child

    def _backprop(self, node, reward):
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.value_sum += reward
            cur = cur.parent



def train_with_mcts(num_agents=9, episodes=10, iters_per_episode=300):
  
    y_actions = YosysOptimizationActions()
    env = OptimizationEnvironment(y_actions)
    all_moves = y_actions.enumerate_all_moves()
    mcts = MCTS(all_moves=all_moves, sequence_len=num_agents, iteration_budget=iters_per_episode, uct_c=1.414)

    for ep in range(episodes):
        print("=" * 60)
        print(f"Episode {ep + 1}/{episodes}")
        env.reset()

        best_actions, best_reward, best_cmd = mcts.search(env, episode=ep)

        print(f"[MCTS] best_reward={best_reward:.4f}")
        print("[MCTS] best_actions (op, idx):", best_actions)
        print("[MCTS] Yosys command sequence:")
        print("hierarchy; proc; " + " ".join(y_actions.get_command(a) for a in best_actions))

    print("=" * 60)
    print("Done.")


if __name__ == "__main__":

    train_with_mcts(num_agents=9, episodes=10, iters_per_episode=300)
