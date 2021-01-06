from collections import namedtuple
import random
import tensorflow as tf
import numpy as np

Transition = namedtuple("Transition", ("state", "action", "reward", "next_state", "terminal"))

class ReplayMemory:
    def __init__(self, capacity, bsize=32, h_len=4):
        self.capacity = capacity
        self.h_len = h_len
        self.bsize = bsize
        self._memory = []
        self._pos = 0
        self._full = False
    def __len__(self):
        return len(self._memory)
    
    def __getitem__(self, idx):
        return self._memory[idx]
    
    def __repr__(self):
        return self.__class__.__name__ + '(%d)' % (self.capacity)
    
    def cur_index(self):
        return self._pos

    def push(self, *args):
        if len(self._memory) < self.capacity:
            self._memory.append(None)
        self._memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity

    def sample_idx(self, batch_size):
        return random.sample(self.memory, self.bsize)
    
    def sample(self, idx):
        

    def __len__(self):
        return len(self.memory)
