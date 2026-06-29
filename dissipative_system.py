import random
import math
import matplotlib.pyplot as plt

class Node:
    def __init__(self, id, capacity, parent_traits=None):
        self.id = id
        self.capacity = capacity
        self.load = 0.0
        self.x = random.random()
        self.y = random.random()
        
        if parent_traits:
            self.base_metabolism = max(0.03, parent_traits['metabolism'] * random.gauss(1, 0.12))
            self.learning_rate = max(0.1, min(0.9, parent_traits['lr'] * random.gauss(1, 0.12)))
            self.exploration_drive = max(0.5, min(5.0, parent_traits['explore'] * random.gauss(1, 0.15)))
            self.model_transfer_rate = max(0.0, min(1.0, parent_traits['transfer'] * random.gauss(1, 0.15)))
            self.memory_weight = max(0.1, min(0.9, parent_traits['memory'] * random.gauss(1, 0.12)))
        else:
            self.base_metabolism = 0.08 + random.random() * 0.05
            self.learning_rate = 0.25 + random.random() * 0.25
            self.exploration_drive = 1.5 + random.random() * 2.0
            self.model_transfer_rate = 0.2 + random.random() * 0.3
            self.memory_weight = 0.4 + random.random() * 0.3
        
        self.traits = {
            'metabolism': self.base_metabolism,
            'lr': self.learning_rate,
            'explore': self.exploration_drive,
            'transfer': self.model_transfer_rate,
            'memory': self.memory_weight
        }
        
        self.model = {}
        self.history = []
        self.alive = True
        self.age = 0
        self.stress = 0.0
        self.wisdom = 0.0
        self.total_syntax = 0.0
        self.reproduced = False
        self.food_memory = []
        self.danger_memory = []
    
    def get_metabolism(self):
        return self.base_metabolism + len(self.model) * 0.00015 * max(0.15, 1.0 - self.wisdom)
    
    def predict(self, action_type, param):
        if not self.alive:
            return 0
        key = (action_type, str(param))
        if key not in self.model:
            return random.gauss(0, 0.8)
        mean, var, n, last = self.model[key]
        age_factor = 1 + 0.008 * (self.age - last)
        return random.gauss(mean, math.sqrt(var/(n+1)) * age_factor + 0.15 + self.stress * 0.3)
    
    def learn(self, action_type, param, effect):
        if not self.alive:
            return
        key = (action_type, str(param))
        lr = self.learning_rate + self.stress * 0.25
        if key not in self.model:
            self.model[key] = [effect, 1.2, 1, self.age]
            self.total_syntax += 1.0
        else:
            mean, var, n, last = self.model[key]
            n += 1
            mean = mean + lr * (effect - mean)
            var = var * 0.88 + 0.12 * (effect - mean)**2
            self.model[key] = [mean, max(var, 0.001), n, self.age]
            self.total_syntax += 0.1
        pred = self.model[key][0]
        self.wisdom = 0.95 * self.wisdom + 0.05 * max(0, 1 - abs(effect - pred))
    
    def learn_from_other(self, other):
        if not self.alive or not other.alive or other.id == self.id:
            return 0
        copied = 0
        for key, (mean, var, n, last) in other.model.items():
            if random.random() < self.model_transfer_rate * 0.15:
                if key not in self.model or self.model[key][2] < n:
                    if key not in self.model:
                        self.model[key] = [mean, var, max(1, n//2), self.age]
                        self.total_syntax += 0.5
                        copied += 1
                    else:
                        my_mean, my_var, my_n, my_last = self.model[key]
                        total_n = my_n + n
                        self.model[key] = [
                            (my_n * my_mean + n * mean) / total_n,
                            (my_n * my_var + n * var) / total_n,
                            total_n, self.age
                        ]
                        copied += 0.5
        return copied
    
    def update_memory(self, pos, success, amount=0):
        x, y = pos
        if success:
            self.food_memory.append((x, y, amount, self.age))
        else:
            self.danger_memory.append((x, y, amount, self.age))
        self.food_memory = [m for m in self.food_memory if self.age - m[3] < 60]
        self.danger_memory = [m for m in self.danger_memory if self.age - m[3] < 60]
    
    def get_memory_attractor(self):
        if not self.food_memory:
            return None
        weights = [(fx, fy, fa / (1 + 0.03 * (self.age - ft))) for fx, fy, fa, ft in self.food_memory]
        total_w = sum(w[2] for w in weights)
        if total_w == 0:
            return None
        return (
            sum(w[0] * w[2] for w in weights) / total_w,
            sum(w[1] * w[2] for w in weights) / total_w
        )
    
    def metabolize(self):
        if not self.alive:
            return
        self.load -= self.get_metabolism()
        if self.load <= 0:
            self.load = 0
            self.alive = False
        self.age += 1


class System:
    def __init__(self, n_nodes=6, noise_rate=0.25, noise_strength=2.0, food_rate=0.7):
        self.nodes = [Node(i, 10 + random.random() * 5) for i in range(n_nodes)]
        self.next_id = n_nodes
        self.time = 0
        self.noise_rate = noise_rate
        self.noise_strength = noise_strength
        self.food_rate = food_rate
        self.food_patches = []
        self.states = []
        self.death_log = []
        self.birth_log = []
        self.trait_history = []
        for n in self.nodes:
            n.load = 5.0 + random.random() * 4
    
    def dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)
    
    def spawn_food(self):
        if random.random() < self.food_rate:
            x, y = random.random(), random.random()
            alive = [n for n in self.nodes if n.alive]
            if alive and random.random() < 0.35:
                attr = random.choice(alive).get_memory_attractor()
                if attr:
                    x = max(0, min(1, attr[0] + random.gauss(0, 0.12)))
                    y = max(0, min(1, attr[1] + random.gauss(0, 0.12)))
            self.food_patches.append((x, y, 2.0 + random.random() * 3.0))
        self.food_patches = [(x, y, a * 0.93) for x, y, a in self.food_patches if a > 0.5]
    
    def inject_noise(self):
        for node in self.nodes:
            if not node.alive:
                continue
            if random.random() < self.noise_rate:
                delta = random.choice([-1, 1]) * random.random() * self.noise_strength
                node.load = max(0, min(node.capacity, node.load + delta))
    
    def reproduce(self, node):
        if (node.load > node.capacity * 0.5 and node.age > 20 and
            len(node.model) > 6 and not node.reproduced and random.random() < 0.1):
            
            cost = node.load * 0.3
            node.load -= cost
            node.reproduced = True
            
            child = Node(self.next_id, node.capacity * (0.9 + random.random() * 0.2), node.traits)
            child.x = max(0, min(1, node.x + random.gauss(0, 0.12)))
            child.y = max(0, min(1, node.y + random.gauss(0, 0.12)))
            child.load = cost * 0.8
            
            sorted_models = sorted(node.model.items(), key=lambda x: x[1][2], reverse=True)
            for key, (mean, var, n, last) in sorted_models[:min(5, len(sorted_models))]:
                child.model[key] = [mean, var * 1.3, max(1, n // 3), 0]
                child.total_syntax += 0.3
            
            self.nodes.append(child)
            self.next_id += 1
            self.birth_log.append((self.time, child.id, node.id, node.wisdom, len(node.model)))
            return True
        return False
    
    def act(self, node):
        if not node.alive:
            return ('dead', {})
        
        actions = []
        
        if self.food_patches:
            nearest = min(self.food_patches, key=lambda f: math.hypot(node.x - f[0], node.y - f[1]))
            attr = node.get_memory_attractor()
            target = attr if attr and random.random() < node.memory_weight else (nearest[0], nearest[1])
            actions.append(('seek_food', {'target': target}, node.predict('seek_food', target)))
        
        others = [n for n in self.nodes if n.id != node.id and n.alive]
        if others:
            teacher = max(others, key=lambda n: len(n.model))
            actions.append(('approach', {'target': (teacher.x, teacher.y), 'teacher': teacher.id},
                          node.predict('approach', (teacher.x, teacher.y))))
        
        poorer = [n for n in self.nodes if n.id != node.id and n.alive and n.load < node.load * 0.5]
        if poorer and node.load > 2.0:
            recipient = min(poorer, key=lambda n: n.load)
            amount = min(node.load * 0.2, 1.0)
            actions.append(('transfer', {'to': recipient.id, 'amount': amount},
                          node.predict('transfer', recipient.id)))
        
        actions.append(('forage', {}, node.predict('forage', None)))
        actions.append(('rest', {}, -0.04))
        
        best = None
        best_score = -float('inf')
        for action_type, params, pred in actions:
            key = (action_type, str(params))
            if key not in node.model:
                bonus = node.exploration_drive
            else:
                mean, var, n, last = node.model[key]
                bonus = math.sqrt(2 * math.log(max(node.age, 1) + 2) / (n + 1))
            score = pred + bonus
            if score > best_score:
                best_score = score
                best = (action_type, params)
        return best
    
    def execute(self, node, action_type, params):
        if not node.alive:
            return 0
        
        if action_type == 'seek_food':
            tx, ty = params['target']
            d = math.hypot(tx - node.x, ty - node.y)
            if d > 0.02:
                step = min(0.15, d)
                node.x += (tx - node.x) / d * step
                node.y += (ty - node.y) / d * step
            if d < 0.12:
                for i, (fx, fy, fa) in enumerate(self.food_patches):
                    if math.hypot(node.x - fx, node.y - fy) < 0.18:
                        eaten = min(fa, node.capacity - node.load, 2.5)
                        self.food_patches[i] = (fx, fy, fa - eaten)
                        node.load = min(node.capacity, node.load + eaten)
                        node.update_memory((fx, fy), True, eaten)
                        return eaten / node.capacity
            node.update_memory((tx, ty), False)
            return -0.06 - 0.015 * d
        
        elif action_type == 'approach':
            tx, ty = params['target']
            teacher_id = params.get('teacher')
            d = math.hypot(tx - node.x, ty - node.y)
            if d > 0.02:
                step = min(0.12, d)
                node.x += (tx - node.x) / d * step
                node.y += (ty - node.y) / d * step
            if d < 0.15 and teacher_id is not None:
                teacher = next((n for n in self.nodes if n.id == teacher_id and n.alive), None)
                if teacher:
                    copied = node.learn_from_other(teacher)
                    if copied > 0:
                        return copied * 0.25
            return -0.06 - 0.01 * d
        
        elif action_type == 'transfer':
            target = next((n for n in self.nodes if n.id == params['to'] and n.alive), None)
            if target and node.load >= params['amount']:
                node.load -= params['amount']
                target.load = min(target.capacity, target.load + params['amount'] * 0.85)
                node.learn_from_other(target)
                target.learn_from_other(node)
                return 0.5 if target.load < 2.0 else 0.1
            return -0.25
        
        elif action_type == 'forage':
            r = random.random()
            if r < 0.45:
                gain = 1.2 + random.random() * 2.5
                node.load = min(node.capacity, node.load + gain)
                node.update_memory((node.x, node.y), True, gain)
                return gain / node.capacity
            elif r < 0.65:
                node.update_memory((node.x, node.y), False)
                return -0.08
            else:
                loss = 0.4 + random.random() * 0.4
                node.load = max(0, node.load - loss)
                node.update_memory((node.x, node.y), False, loss)
                return -loss / node.capacity
        
        elif action_type == 'rest':
            node.load = min(node.capacity, node.load + 0.08)
            return 0.04
        
        return 0
    
    def tick(self):
        self.time += 1
        self.spawn_food()
        self.inject_noise()
        
        for node in list(self.nodes):
            if node.alive:
                self.reproduce(node)
        
        for node in list(self.nodes):
            if not node.alive:
                continue
            action_type, params = self.act(node)
            key = (action_type, str(params))
            predicted = node.model.get(key, [0, 0, 0, 0])[0] if key in node.model else 0.0
            actual = self.execute(node, action_type, params)
            node.learn(action_type, params, actual)
            error = actual - predicted
            node.history.append((action_type, error))
            node.stress = 0.88 * node.stress + 0.12 * abs(error)
            node.metabolize()
            if not node.alive:
                self.death_log.append((self.time, node.id, node.age, len(node.model), node.wisdom, node.total_syntax))
        
        alive_now = sum(1 for n in self.nodes if n.alive)
        recent_errors = [abs(e) for n in self.nodes if n.alive for _, e in n.history[-10:]]
        avg_error = sum(recent_errors) / max(len(recent_errors), 1)
        loads = [n.load for n in self.nodes if n.alive]
        entropy = math.sqrt(sum((l - sum(loads) / max(len(loads), 1))**2 for l in loads) / max(len(loads), 1)) if loads else 0
        
        total_syntax = sum(n.total_syntax for n in self.nodes if n.alive)
        total_models = sum(len(n.model) for n in self.nodes if n.alive)
        total_memory = sum(len(n.food_memory) + len(n.danger_memory) for n in self.nodes if n.alive)
        
        survival_ratio = min(1.0, alive_now / 5.0)
        avg_wisdom = sum(n.wisdom for n in self.nodes if n.alive) / max(alive_now, 1)
        awareness = (1.0 / (1.0 + avg_error)) * survival_ratio * min(1.0, total_models / 100) * (0.5 + 0.5 * avg_wisdom)
        
        total_energy = sum(n.load for n in self.nodes if n.alive)
        dissipation = total_syntax / max(total_energy, 1) if total_energy > 0 else 0
        
        if alive_now > 0:
            trait_avg = {
                'metabolism': sum(n.traits['metabolism'] for n in self.nodes if n.alive) / alive_now,
                'lr': sum(n.traits['lr'] for n in self.nodes if n.alive) / alive_now,
                'explore': sum(n.traits['explore'] for n in self.nodes if n.alive) / alive_now,
                'transfer': sum(n.traits['transfer'] for n in self.nodes if n.alive) / alive_now,
                'memory': sum(n.traits['memory'] for n in self.nodes if n.alive) / alive_now,
            }
        else:
            trait_avg = {'metabolism': 0, 'lr': 0, 'explore': 0, 'transfer': 0, 'memory': 0}
        self.trait_history.append(trait_avg)
        
        self.states.append({
            'time': self.time, 'alive': alive_now, 'total_nodes': len(self.nodes),
            'loads': [n.load if n.alive else 0 for n in self.nodes],
            'awareness': awareness, 'entropy': entropy,
            'avg_error': avg_error, 'food': len(self.food_patches),
            'stress': sum(n.stress for n in self.nodes if n.alive) / max(alive_now, 1),
            'wisdom': avg_wisdom, 'syntax': total_syntax,
            'models': total_models, 'memory': total_memory,
            'dissipation': dissipation
        })
    
    def run(self, ticks=1500, print_every=150):
        for t in range(ticks):
            self.tick()
            if t % print_every == 0:
                s = self.states[-1]
                print(f"t={t:4}: alive={s['alive']:2}, total={s['total_nodes']:2}, syntax={s['syntax']:8.1f}, models={s['models']:5}, dissipation={s['dissipation']:.2f}")
        return self
    
    def plot(self, filename='output.png'):
        fig, axes = plt.subplots(3, 3, figsize=(18, 14))
        times = [s['time'] for s in self.states]
        
        ax = axes[0, 0]
        ax.plot(times, [s['alive'] for s in self.states], color='green', linewidth=2, label='Alive')
        ax.plot(times, [s['total_nodes'] for s in self.states], color='gray', linewidth=1, alpha=0.5, label='Total ever')
        ax.set_title('Population')
        ax.legend()
        
        ax = axes[0, 1]
        ax.plot(times, [s['syntax'] for s in self.states], color='purple', linewidth=2)
        ax.set_title('Syntax')
        
        ax = axes[0, 2]
        ax.plot(times, [s['models'] for s in self.states], color='blue', linewidth=2)
        ax.set_title('Models')
        
        ax = axes[1, 0]
        ax.plot(times, [s['dissipation'] for s in self.states], color='red', linewidth=2)
        ax.set_title('Dissipation')
        
        ax = axes[1, 1]
        ax.plot(times, [s['awareness'] for s in self.states], color='orange', linewidth=2)
        ax.set_title('Awareness')
        
        ax = axes[1, 2]
        ax.plot(times, [s['entropy'] for s in self.states], color='teal', linewidth=2)
        ax.fill_between(times, [s['entropy'] for s in self.states], alpha=0.3, color='teal')
        ax.set_title('Entropy')
        
        ax = axes[2, 0]
        tt = range(len(self.trait_history))
        ax.plot(tt, [t['metabolism'] for t in self.trait_history], label='Metabolism', alpha=0.8)
        ax.plot(tt, [t['lr'] for t in self.trait_history], label='LR', alpha=0.8)
        ax.plot(tt, [t['explore'] for t in self.trait_history], label='Explore', alpha=0.8)
        ax.plot(tt, [t['transfer'] for t in self.trait_history], label='Transfer', alpha=0.8)
        ax.plot(tt, [t['memory'] for t in self.trait_history], label='Memory', alpha=0.8)
        ax.set_title('Traits')
        ax.legend(ncol=2, fontsize=8)
        
        ax = axes[2, 1]
        ax.plot(times, [s['avg_error'] for s in self.states], color='red', alpha=0.7, label='Error')
        ax.plot(times, [s['stress'] for s in self.states], color='orange', alpha=0.7, label='Stress')
        ax.set_title('Error & Stress')
        ax.legend()
        
        ax = axes[2, 2]
        ax.plot(times, [s['memory'] for s in self.states], color='brown', alpha=0.7, label='Memory')
        ax.plot(times, [s['wisdom'] * 100 for s in self.states], color='gold', alpha=0.7, label='Wisdomx100')
        ax.set_title('Memory & Wisdom')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.show()


if __name__ == '__main__':
    random.seed(42)
    sys = System(n_nodes=6, noise_rate=0.25, noise_strength=2.0, food_rate=0.7)
    sys.run(ticks=1500, print_every=150)
    sys.plot('dissipative_system.png')
    
    print(f"\nFinal: alive={sys.states[-1]['alive']}, total={sys.states[-1]['total_nodes']}")
    print(f"Births: {len(sys.birth_log)}, Deaths: {len(sys.death_log)}")
    print(f"Peak dissipation: {max(s['dissipation'] for s in sys.states):.1f}")
    print(f"Peak models: {max(s['models'] for s in sys.states)}")
