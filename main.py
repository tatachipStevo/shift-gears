import sys
from game import Game

if __name__ == "__main__":
    Game(selftest="--selftest" in sys.argv).run()
