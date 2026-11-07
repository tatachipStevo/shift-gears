import sys
from game import Game

if __name__ == "__main__":
    Game(selftest=("--selftest" in sys.argv or "--selftest-all" in sys.argv)).run()
