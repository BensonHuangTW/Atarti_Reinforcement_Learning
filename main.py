import argparse

from dqn.agent.dqn_agent import Agent


def args_parse():
    parser = argparse.ArgumentParser(description="Atari: DQN")
    parser.add_argument('--env', default="BreakoutNoFrameskip-v4", help='Should be NoFrameskip environment')
    parser.add_argument('--train', action="store_true", help='Train agent with given environment')
    parser.add_argument('--play', help="Play with a given weight directory")
    parser.add_argument('--save', help="Save episode gif")
    parser.add_argument('--log_interval', default=100, help="Interval of logging stdout", type=int)
    parser.add_argument('--save_weight_interval', default=1000, help="Interval of saving weights", type=int)
    parser.add_argument('--network', default=None, help="Network architecture to train")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = args_parse()
    agent = Agent(game_id=args.env, network_type=args.network)
    agent.print_log_interval = args.log_interval
    agent.save_weight_interval = args.save_weight_interval
    if args.train:
        print("Start training")
        agent.train()
    if args.play:
        print("Start playing")
        agent.play(args.play, trial=1)
    if args.save:
        print("Saving gif")
        agent.save_gif(args.save, trial=1)
    