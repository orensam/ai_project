          --------------------------------
          | GemGem - A Candy Crush Clone |
          |  Modified with an AI solver  |
          --------------------------------

Daniel Hadar (200380244) and Oren Samuel (200170694)
The Hebrew University of Jerusalem
2014-2015 Intro to AI Course
March 2015

This is a Match-3 game you can play in manual mode, or let the computer play (in auto mode).
The original game can be found here:
http://pygame.org/project-Gemgem+(Bejeweled+clone)-1922-.html

Prerequisites: Python 2.7 and pygame

To run in the default settings, simply invoke:
python gemgem.py
This will run the game in its default settings -
6x6 board, 4 gem types, auto mode with SGS algorithm, unlimited games, target score 250.

To play in manual mode, click and drag a gem such that a sequence is created.
A sequence is a vertical or horizontal chain of 3 or more consecutive gems of the same type.
The current score is displayed on the bottom left of the window, and the number of swaps on the bottom right.

The possible command line arguments:

  -h, --help                            show this help message and exit
  -m, --manual                          Run game with manual control (default - auto mode)
  -s BOARD_SIZE, --size=BOARD_SIZE      Size of game board side (4..8) (default 6)
  -g GEM_NUM, --gems=GEM_NUM            Number of gem types (4..7) (default 4)
  -c GOAL, --score=GOAL                 Target (limit) score (default 250)
  -f USER_FPS, --fps=USER_FPS           Game animation FPS (default 30)
  -n NGAMES, --ngames=NGAMES            Number of games to run. Set to 0 to run forever (default 0)
  -O LOGFILE, --output=LOGFILE          Log file name. Output format is CSV (default gemgem_log.csv)
  -q, --no-graphics                     Run game(s) without graphics (default - graphics on)
  -a ALGO, --algorithm=ALGO             Algorithm: 1=SGS, 2=HGS, 3=L-BFS (default 1)
  -w WEIGHTS, --weights=WEIGHTS         Weights: [Score, Pairs, Moves, Depth, Touching] (default "1 1 1 1 1")
  -j                                    Who knows?

For example, you can run:
python gemgem.py -s 7 -g 5 -c 100 -f 500 -n 10 -O results.csv -a 2 -w "1 0.2 0.3 0.4 0.5"   

This will result in:
- a 7x7 board
- 5 gem types
- Target score of 100
- Animation at 500 fps
- 10 consecutive games
- Output to file results.csv
- Using the HGS algorithm
- Using the heuristic weights: [Score: 1, Pairs: 0.2, Moves: 0.3, Depth: 0.4, Touching: 0.5]
