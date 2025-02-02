from collections import deque
from datetime import datetime

import gym
import imageio
import numpy as np
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras.optimizers import Adam

import dqn.networks.networks as networks
from dqn.environment.atari_env import Environment
from dqn.utils.memory import ReplayMemory, Transition

def build_network(network_type: str, num_actions, agent_history_length):
    if network_type is None: # default setting
        return networks.DQNNetwork(num_actions, agent_history_length)
    elif network_type == "duel":
        return networks.DuelDQNNetwork(num_actions, num_actions, agent_history_length)
    else: raise KeyError("The network type {} does not exist!".format(network_type))

class Agent:
    """
    Class for DQN model architecture.
    """
    def __init__(self, 
                 game_id,
                 network_type = None,
                 discount_factor = 0.99,
                 minibatch_size = 32,
                 update_frequency = 4,
                 target_network_update_freq = 1000,
                 optimizer = Adam(learning_rate=1e-4, epsilon=1e-6),
                 init_explr = 1.0,
                 final_explr = 0.1,
                 final_explr_frame = 1000000,
                 replay_start_size = 10000,
                 loss = tf.keras.losses.Huber(),
                 training_frames = int(1e7),
                 log_path = "./log/",
                 print_log_interval = 10,
                 save_weight_interval = 10):

        self.game_id = game_id
        self.env = Environment(game_id, train=True)
        self.discount_factor = discount_factor
        self.minibatch_size = minibatch_size
        self.update_frequency = update_frequency
        self.target_network_update_freq = target_network_update_freq
        self.agent_history_length = 16
        self.main_network = build_network(network_type, self.env.get_action_space_size(), self.agent_history_length)
        self.target_network = build_network(network_type, self.env.get_action_space_size(), self.agent_history_length)
        self.optimizer = optimizer
        self.init_explr = init_explr
        self.final_explr = final_explr
        self.final_explr_frame = final_explr_frame
        self.replay_start_size = replay_start_size
        self.loss = loss
        self.training_frames = training_frames
        self.log_path = log_path + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + self.game_id
        self.print_log_interval = print_log_interval
        self.save_weight_interval = save_weight_interval
        self.memory = ReplayMemory(capacity=10000, minibatch_size=self.minibatch_size)
        self.loss_metric = tf.keras.metrics.Mean(name="loss")
        self.q_metric = tf.keras.metrics.Mean(name="Q_value")
        self.summary_writer = tf.summary.create_file_writer(self.log_path + "/summary/")
        self.life_game = None

        self.env.reset()
        _, _, _, info = self.env.step(0)
        if info["ale.lives"] > 0:
            self.life_game = True
        else:
            self.life_game = False    

    @tf.function
    def get_action(self, state, exploration_rate):
        """Get action by ε-greedy method.

        Args:
            state (np.uint8): recent self.agent_history_length frames. (Default: (84, 84, 4))
            exploration_rate (int): Exploration rate for deciding random or optimal action.

        Returns:
            action (tf.int32): Action index
        """
        recent_state = tf.expand_dims(state, axis=0) # e.g. shape: (84, 84, 4) -> (1, 84, 84, 4)
        if tf.random.uniform((), minval=0, maxval=1, dtype=tf.float32) < exploration_rate:
            action = tf.random.uniform((), minval=0, maxval=self.env.get_action_space_size(), dtype=tf.int32)
        else:
            q_value = self.main_network(tf.cast(recent_state, tf.float32))
            action = tf.cast(tf.squeeze(tf.math.argmax(q_value, axis=1)), dtype=tf.int32)
        return action
        
    @tf.function
    def get_eps(self, current_step, terminal_eps=0.01, terminal_frame_factor=25):
        """Use annealing schedule similar like: https://openai.com/blog/openai-baselines-dqn/ .

        Args:
            current_step (int): Number of entire steps agent experienced.
            terminal_eps (float): Final exploration rate arrived at terminal_frame_factor * self.final_explr_frame.
            terminal_frame_factor (int): Final exploration frame, which is terminal_frame_factor * self.final_explr_frame.

        Returns:
            eps (float): Calculated epsilon for ε-greedy at current_step.
        """
        terminal_eps_frame = self.final_explr_frame * terminal_frame_factor

        if current_step < self.replay_start_size:
            eps = self.init_explr
        elif self.replay_start_size <= current_step and current_step < self.final_explr_frame:
            eps = (self.final_explr - self.init_explr) / (self.final_explr_frame - self.replay_start_size) * (current_step - self.replay_start_size) + self.init_explr
        elif self.final_explr_frame <= current_step and current_step < terminal_eps_frame:
            eps = (terminal_eps - self.final_explr) / (terminal_eps_frame - self.final_explr_frame) * (current_step - self.final_explr_frame) + self.final_explr
        else:
            eps = terminal_eps
        return eps
    
    @tf.function
    def update_main_q_network(self, state_batch, action_batch, reward_batch, next_state_batch, terminal_batch):
        """Update main q network by experience replay method.

        Args:
            state_batch (tf.float32): Batch of states.
            action_batch (tf.int32): Batch of actions.
            reward_batch (tf.float32): Batch of rewards.
            next_state_batch (tf.float32): Batch of next states.
            terminal_batch (tf.bool): Batch or terminal status.

        Returns:
            loss (tf.float32): Huber loss of temporal difference.
        """

        with tf.GradientTape() as tape:
            next_state_q = self.target_network(next_state_batch)
            next_state_max_q = tf.math.reduce_max(next_state_q, axis=1)
            expected_q = reward_batch + self.discount_factor * next_state_max_q * (1.0 - tf.cast(terminal_batch, tf.float32))
            main_q = tf.reduce_sum(self.main_network(state_batch) * tf.one_hot(action_batch, self.env.get_action_space_size(), 1.0, 0.0), axis=1)
            loss = self.loss(tf.stop_gradient(expected_q), main_q)

        gradients = tape.gradient(loss, self.main_network.trainable_variables)
        clipped_gradients = [tf.clip_by_norm(grad, 10) for grad in gradients]
        self.optimizer.apply_gradients(zip(clipped_gradients, self.main_network.trainable_variables))

        self.loss_metric.update_state(loss)
        self.q_metric.update_state(main_q)

        return loss

    @tf.function
    def update_target_network(self):
        """Synchronize weights of target network by those of main network."""
        
        main_vars = self.main_network.trainable_variables
        target_vars = self.target_network.trainable_variables
        for main_var, target_var in zip(main_vars, target_vars):
            target_var.assign(main_var)

    def train(self):
        
        total_step = 0
        episode = 0
        latest_100_score = deque(maxlen=100)

        while total_step < self.training_frames:
            
            state = self.env.reset()
            episode_step = 0
            episode_score = 0.0
            done = False

            while not done:
                
                eps = self.get_eps(tf.constant(total_step, tf.float32))
                action = self.get_action(tf.constant(state), tf.constant(eps, tf.float32))
            
                next_state, reward, done, info = self.env.step(action)
                episode_score += reward

                self.memory.push(state, action, reward, next_state, done)
                state = next_state

                if (total_step % self.update_frequency == 0) and (total_step > self.replay_start_size): # time to update the Q-network
                    indices = self.memory.get_minibatch_indices()
                    state_batch, action_batch, reward_batch, next_state_batch, terminal_batch = self.memory.generate_minibatch_samples(indices)
                    self.update_main_q_network(state_batch, action_batch, reward_batch, next_state_batch, terminal_batch)

                if (total_step % self.target_network_update_freq == 0) and (total_step > self.replay_start_size): # time to update target network
                    loss = self.update_target_network()
                
                total_step += 1
                episode_step += 1

                if done:
                    latest_100_score.append(episode_score)
                    self.write_summary(episode, latest_100_score, episode_score, total_step, eps)
                    episode += 1

                    if episode % self.print_log_interval == 0:
                        print("Episode: ", episode)
                        print("Latest 100 avg: {:.4f}".format(np.mean(latest_100_score)))
                        print("Progress: {} / {} ( {:.2f} % )".format(total_step, self.training_frames, 
                        np.round(total_step / self.training_frames, 3) * 100))

                    if episode % self.save_weight_interval == 0:
                        print("Saving weights...")
                        self.main_network.save_weights(self.log_path + "/weights/episode_{}".format(episode))
                        self.play(self.log_path + "/weights/", episode=episode)

    def save_gif(self, episode, trial, max_playing_time=10):

        load_dir = "./log/20210110_190115_BreakoutNoFrameskip-v4/weights/"
        episode = int(episode)

        if load_dir:
            loaded_ckpt = tf.train.latest_checkpoint(load_dir)
            self.main_network.load_weights(loaded_ckpt)
        
        frame_set = []
        reward_set = []
        test_env = Environment(self.game_id, train=False) # play the original game without clipping the rewards
        for _ in range(trial):

            state = test_env.reset()
            frames = []
            test_step = 0
            test_reward = 0
            done = False
            test_memory = ReplayMemory(10000, verbose=False)

            while not done:

                frames.append(test_env.render())

                action = self.get_action(tf.constant(state, tf.float32), tf.constant(0.0, tf.float32))
     
                next_state, reward, done, info = test_env.step(action)
                test_reward += reward

                test_memory.push(state, action, reward, next_state, done)
                state = next_state

                test_step += 1

                if done and self.life_game and (info["ale.lives"] != 0):
                    test_env.reset()
                    test_step = 0
                    done = False

                if len(frames) > 15 * 60 * max_playing_time: # To prevent falling infinite repeating sequences.
                    print("Playing takes {} minutes. Force termination.".format(max_playing_time))
                    break

            reward_set.append(test_reward)
            frame_set.append(frames)

        best_score = np.max(reward_set)
        print("Best score of current network ({} trials): {}".format(trial, best_score))
        best_score_ind = np.argmax(reward_set)
        imageio.mimsave("./gif/"+str(episode)+".gif", frame_set[best_score_ind], fps=15)

        if episode is not None:
            with self.summary_writer.as_default():
                tf.summary.scalar("Test score", best_score, step=episode)



    def play(self, load_dir=None, episode=None, trial=5, max_playing_time=10):
        
        if load_dir:
            loaded_ckpt = tf.train.latest_checkpoint(load_dir)
            self.main_network.load_weights(loaded_ckpt)
        
        frame_set = []
        reward_set = []
        test_env = Environment(self.game_id, train=False) # play the original game without clipping the rewards
        for _ in range(trial):

            state = test_env.reset()
            frames = []
            test_step = 0
            test_reward = 0
            done = False
            test_memory = ReplayMemory(10000, verbose=False)

            while not done:

                frames.append(test_env.render())

                action = self.get_action(tf.constant(state, tf.float32), tf.constant(0.0, tf.float32))
     
                next_state, reward, done, info = test_env.step(action)
                test_reward += reward

                test_memory.push(state, action, reward, next_state, done)
                state = next_state

                test_step += 1

                if done and self.life_game and (info["ale.lives"] != 0):
                    test_env.reset()
                    test_step = 0
                    done = False

                if len(frames) > 15 * 60 * max_playing_time: # To prevent falling infinite repeating sequences.
                    print("Playing takes {} minutes. Force termination.".format(max_playing_time))
                    break

            reward_set.append(test_reward)
            frame_set.append(frames)

        best_score = np.max(reward_set)
        print("Best score of current network ({} trials): {}".format(trial, best_score))
        best_score_ind = np.argmax(reward_set)
        imageio.mimsave("current_best_replay.gif", frame_set[best_score_ind], fps=15)

        if episode is not None:
            with self.summary_writer.as_default():
                tf.summary.scalar("Test score", best_score, step=episode)

    def write_summary(self, episode, latest_100_score, episode_score, total_step, eps):

        with self.summary_writer.as_default():
            tf.summary.scalar("Reward (clipped)", episode_score, step=episode)
            tf.summary.scalar("Latest 100 avg reward (clipped)", np.mean(latest_100_score), step=episode)
            tf.summary.scalar("Loss", self.loss_metric.result(), step=episode)
            tf.summary.scalar("Average Q", self.q_metric.result(), step=episode)
            tf.summary.scalar("Total Frames", total_step, step=episode)
            tf.summary.scalar("Epsilon", eps, step=episode)

        self.loss_metric.reset_states()
        self.q_metric.reset_states()
