# Gemgem (a Bejeweled clone)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license

# Game Modifications and solving algorithms
# by Daniel Hadar & Oren Samuel
# Written for 2014-2015 Intro to AI course
# Hebrew University of Jerusalem

"""
This program has "gem data structures", which are basically dictionaries
with the following keys:
  'x' and 'y' - The location of the gem on the board. 0,0 is the top left.
                There is also a ROWABOVEBOARD row that 'y' can be set to,
                to indicate that it is above the board.
  'direction' - one of the four constant variables UP, DOWN, LEFT, RIGHT.
                This is the direction the gem is moving.
  'imageNum'  - The integer index into GEMIMAGES to denote which image
                this gem uses.
"""

import random, time, pygame, sys, copy
from pygame.locals import *
from optparse import OptionParser
import math
import datetime

FPS = 20000 # frames per second to update the screen
WINDOWWIDTH = 600  # width of the program's window, in pixels
WINDOWHEIGHT = 600 # height in pixels

BOARDWIDTH = 8 # how many columns in the board
BOARDHEIGHT = 8 # how many rows in the board
GEMIMAGESIZE = 64 # width & height of each space in pixels

# NUMGEMIMAGES is the number of gem types. You will need .png image
# files named gem0.png, gem1.png, etc. up to gem(N-1).png.
NUMGEMIMAGES = 4
assert NUMGEMIMAGES >= 4 # game needs at least 5 types of gems to work

# NUMMATCHSOUNDS is the number of different sounds to choose from when
# a match is made. The .wav files are named match0.wav, match1.wav, etc.
NUMMATCHSOUNDS = 6

MOVERATE = 25 # 1 to 100, larger num means faster animations
DEDUCTSPEED = 0.8 # reduces score by 1 point every DEDUCTSPEED seconds.

#             R    G    B
PURPLE    = (255,   0, 255)
GREEN     = (0,   255,  50)
LIGHTBLUE = (170, 190, 255)
BLUE      = (  0,   0, 255)
RED       = (255, 100, 100)
BLACK     = (  0,   0,   0)
BROWN     = ( 85,  65,   0)
HIGHLIGHTCOLOR = PURPLE # color of the selected gem's border
BGCOLOR = LIGHTBLUE # background color on the screen
GRIDCOLOR = BLUE # color of the game board
GAMEOVERCOLOR = RED # color of the "Game over" text.
GAMEOVERBGCOLOR = BLACK # background color of the "Game over" text.
SCORECOLOR = BROWN # color of the text for the player's score
MOVESCOLOR =  RED # color of the text for the number of moves

# The amount of space to the sides of the board to the edge of the window
# is used several times, so calculate it once here and store in variables.
XMARGIN = int((WINDOWWIDTH - GEMIMAGESIZE * BOARDWIDTH) / 2)
YMARGIN = int((WINDOWHEIGHT - GEMIMAGESIZE * BOARDHEIGHT) / 2)

# constants for direction values
UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

EMPTY_SPACE = -1 # an arbitrary, nonpositive value
ROWABOVEBOARD = 'row above board' # an arbitrary, noninteger value

SMART_GREEDY = 'smart_greedy'
STUPID_GREEDY = 'stupid_greedy'
LBFS = 'lbfs'
ALGOS = {1:STUPID_GREEDY, 2:SMART_GREEDY, 3:LBFS}

GOAL_SCORE = 100
SEND_MULTIPLE = False

J = False

class BoardMove(object):

    def __init__(self, source_board, x, y, direction, random_fall, cascade):
        self.first = self.second = self.dest_board = None
        self.score = 0
        self.random_fall = random_fall
        self.cascade = cascade
        self.source_board = copy.deepcopy(source_board)
        self.create_dicts(x, y, direction)
        if self.second is not None:
            self.perform_move()

    def create_dicts(self, x, y, direction):

        gem = getGemAt(self.source_board, x, y)
        gem_right = getGemAt(self.source_board, x + 1, y)
        gem_down = getGemAt(self.source_board, x, y + 1)

        self.first = {'x':x, 'y':y, 'imageNum': gem, 'direction':direction}
        if direction == RIGHT and gem_right is not None:
            self.second = {'x':x+1, 'y':y, 'imageNum': gem_right, 'direction':LEFT}
        elif direction == DOWN and gem_down is not None:
            self.second = {'x':x, 'y':y+1, 'imageNum': gem_down, 'direction':UP}

    def perform_move(self):
        if self.cascade:
            self.dest_board, self.score = perform_move(copy.deepcopy(self.source_board), self.first, self.second,
                                                       score=0, simulation=True, random_fall=self.random_fall)
        else:
            self.dest_board, self.score = perform_single_move(copy.deepcopy(self.source_board), self.first, self.second,
                                                              score=0, simulation=True, random_fall=self.random_fall)

    def __str__(self):
        return "MOVE: (x, y): (%d, %d); Direction %s; Score: %d" %(self.first['x'], self.first['y'],
                                                                   self.first['direction'], self.score)

    def __cmp__(self, other):
        if self.score < other.score:
            return -1
        if self.score > other.score:
            return 1
        return 0


class FringeState(object):
    def __init__(self, board, moves=[], total_move_num=0, total_score=0):
        self.board = board
        self.moves = moves[:]
        self.total_move_num = total_move_num
        self.total_score = total_score

    def getMovesScore(self):
        return sum([m.score for m in self.moves])

    def getMovesFactor(self):
        if not self.moves:
            return 0
        return self.getMovesScore() / len(self.moves)

    def getCompareValue(self):
        return self.getMovesFactor()

    def __cmp__(self, other):
        my_score = self.getCompareValue()
        other_score = other.getCompareValue()
        if my_score < other_score:
            return -1
        if my_score > other_score:
            return 1
        return 0


class Solver(object):

    def __init__(self, random_fall, solver_type, weights):
        self.random_fall = random_fall
        self.type = solver_type
        self.uncertainty_thres = 0.15
        self.expanded_nodes = 0

        # Heuristics Weights
        self.w_score = weights[0]
        self.w_pairs = weights[1]
        self.w_nmoves = weights[2]
        self.w_depth = weights[3]
        self.w_touching = weights[4]

        self.h_score_list = []
        self.h_pairs_list = []
        self.h_nmoves_list = []
        self.h_depth_list = []
        self.h_touching_list = []

    def getSwaps(self, board, cur_score=0):

        if self.type == STUPID_GREEDY:
            return self.getSwapStupidGreedy(board)

        elif self.type == SMART_GREEDY:
            return self.getSwapSmartGreedy(board)

        elif self.type == LBFS:
            return self.getSwapsLBFS(board, cur_score)

    def getSwapsLBFS(self, start_board, cur_score):
        fringe = [] # In practice - a queue.
        visited = set()
        leaves = []
        start_state = FringeState(start_board, total_score=cur_score)
        best = start_state
        fringe.append(start_state)

        while fringe:

            cur = fringe.pop(0)

            board_tuple = boardTuple(cur.board)
            if board_tuple in visited:
                continue
            visited.add(board_tuple)

            possible_moves = self.getPossibleMoves(cur.board, True)
            is_uncertain = self.isUncertain(cur)
            if not possible_moves or is_uncertain:
                leaves.append(cur)
                continue

            for move in possible_moves:
                fringe.append(FringeState(move.dest_board, cur.moves + [move],
                                          cur.total_move_num + 1,
                                          cur.total_score + move.score))
                self.expanded_nodes += 1

        # Find goal
        goal_states = [state for state in leaves if self.isGoal(state)]
        if goal_states:
            best = min(goal_states, key=lambda g:len(g.moves))
        else:
            # Find move that brings us closest to goal
            best = max(leaves, key=lambda fs: self.getStateHeuristic(fs))

        if SEND_MULTIPLE:
            return best.moves
        else:
            return best.moves[0:1]

    def isGoal(self, fringe_state):
        return fringe_state.total_score >= GOAL_SCORE

    def isUncertain(self, fs):
        uncertainty = sum([m.score for m in fs.moves]) / float((BOARDHEIGHT * BOARDWIDTH))
        if uncertainty > self.uncertainty_thres:
            return True
        return False

    def getPossibleMoves(self, board, cascade):
        moves = []
        for y in range(BOARDHEIGHT):
            for x in range(BOARDWIDTH):
                move_right = BoardMove(copy.deepcopy(board), x, y, RIGHT, self.random_fall, cascade)
                move_down = BoardMove(copy.deepcopy(board), x, y, DOWN, self.random_fall, cascade)
                for move in (move_right, move_down):
                    if move.score > 0:
                        moves.append(move)
        return moves

    def getSwapStupidGreedy(self, board):
        moves = self.getPossibleMoves(board, cascade=False)
        if moves:
            random.shuffle(moves)
            best = max(moves)
            # print
            # print "MOVES:"
            # for move in moves:
            #     print move
            # print
            # print "BEST:"
            # print best
            # print
            return [best]
        else:
            return []

    def getSwapSmartGreedy(self, board):

        moves = self.getPossibleMoves(board, cascade=True)

        if moves:
            random.shuffle(moves)
            best = max(moves, key=lambda m: self.getMoveHeuristic(m))

            # print "MOVES:"
            # for move in moves:
            #     print move
            # print
            # print "BEST:"
            # print best
            # print
            return [best]
        else:
            return []

    def getMoveHeuristic(self, move):

        dest_board = move.dest_board

        h_score = self.w_score * move.score if self.w_score else 0
        h_pairs = self.w_pairs * self.getPairs(dest_board) if self.w_pairs else 0
        h_nmoves = self.w_nmoves * self.getMoveNumber(dest_board) if self.w_nmoves else 0
        h_depth = self.w_depth * self.getDepthFactor(move) if self.w_depth else 0
        h_touching = self.w_touching * self.getTouchingGemsNum(dest_board) if self.w_touching else 0

        self.h_score_list.append(h_score)
        self.h_pairs_list.append(h_pairs)
        self.h_nmoves_list.append(h_nmoves)
        self.h_depth_list.append(h_depth)
        self.h_touching_list.append(h_touching)

        res = h_score + h_pairs + h_nmoves + h_depth + h_touching

        return res


    def getStateHeuristic(self, fs):

        if not fs.moves:
            return 0

        dest_board = fs.moves[-1].dest_board

        h_score = self.w_score * fs.getMovesFactor() if self.w_score else 0
        h_pairs = self.w_pairs * self.getPairs(dest_board) if self.w_pairs else 0
        h_nmoves = self.w_nmoves * self.getMoveNumber(dest_board) if self.w_nmoves else 0
        h_depth = self.w_depth * self.getStateDepthFactor(fs) if self.w_depth else 0
        h_touching = self.w_touching * self.getTouchingGemsNum(dest_board) if self.w_touching else 0

        self.h_score_list.append(h_score)
        self.h_pairs_list.append(h_pairs)
        self.h_nmoves_list.append(h_nmoves)
        self.h_depth_list.append(h_depth)
        self.h_touching_list.append(h_touching)

        res = h_score + h_pairs + h_nmoves + h_depth + h_touching
        return res

    #### Heuristics ####

    def getTouchingGemsNum(self, board):
        perimeter = set()
        for y in range(BOARDHEIGHT):
            for x in range(BOARDWIDTH):
                if getGemAt(board, x, y) == -1:
                    p = [(a,b) for (a,b) in [(x+1, y), (x, y+1), (x-1, y), (x, y-1)]]
                    perimeter |= set([(a,b) for (a,b) in p if getGemAt(board, a, b) not in (-1, None)])
        num_of_touching = len(perimeter)
        return num_of_touching

    def getDepthFactor(self, move):
        line = max((move.first['y']+1, move.second['y']+1))
        return line

    def getStateDepthFactor(self, fs):
        avg = mean([self.getDepthFactor(m) for m in fs.moves])
        return avg

    def getPairs(self, board):
        num_of_pairs = 0
        for y in range(BOARDHEIGHT):
            for x in range(BOARDWIDTH):
                gem = getGemAt(board, x, y)
                if gem == -1: continue
                if gem == getGemAt(board, x + 1, y):
                    num_of_pairs += 1
                if gem == getGemAt(board, x, y + 1):
                    num_of_pairs += 1
        return num_of_pairs

    def getEntropy(self, board):
        counts = [0] * NUMGEMIMAGES
        for col in board:
            for gem in col:
                counts[gem] += 1
        tot = sum(counts)
        probs = [float(c)/tot for c in counts]
        entropy = -sum([p * math.log(p, 2) for p in probs if p > 0])
        # print "Expected entropy: %.3f" %entropy
        return entropy

    def getMoveNumber(self, board):
        res = len(self.getPossibleMoves(board, False))
        return res


def main(is_manual, random_fall, ngames, algo, weights, no_graphics, logfile):

    print
    games_str = "%d games" %ngames
    if ngames == 0:
        games_str = "forever"
    if ngames == 1:
        games_str = "1 game"
    print "Running %s in %s mode" %(games_str, 'manual' if is_manual else 'auto')
    if not is_manual:
        print "Using solver algorithm: %s" %algo
    print

    global FPSCLOCK, DISPLAYSURF, GEMIMAGES, GAMESOUNDS, BASICFONT, BOARDRECTS

    # Initial set up.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()

    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('Gemgem')

    BASICFONT = pygame.font.Font('freesansbold.ttf', 36)

    # Load the images
    GEMIMAGES = []
    for i in range(1, NUMGEMIMAGES+1):

        gemImage = pygame.image.load('gem%s.png' % i)

        # Easter egg
        if J and i==1:
            gemImage = pygame.image.load('gem8.png')

        if gemImage.get_size() != (GEMIMAGESIZE, GEMIMAGESIZE):
            gemImage = pygame.transform.smoothscale(gemImage, (GEMIMAGESIZE, GEMIMAGESIZE))
        GEMIMAGES.append(gemImage)

    # Load the sounds.
    #GAMESOUNDS = {}
    #GAMESOUNDS['bad swap'] = pygame.mixer.Sound('badswap.wav')
    #GAMESOUNDS['match'] = []
    #for i in range(NUMMATCHSOUNDS):
    #    GAMESOUNDS['match'].append(pygame.mixer.Sound('match%s.wav' % i))

    # Create pygame.Rect objects for each board space to
    # do board-coordinate-to-pixel-coordinate conversions.
    BOARDRECTS = []
    for x in range(BOARDWIDTH):
        BOARDRECTS.append([])
        for y in range(BOARDHEIGHT):
            r = pygame.Rect((XMARGIN + (x * GEMIMAGESIZE),
                             YMARGIN + (y * GEMIMAGESIZE),
                             GEMIMAGESIZE,
                             GEMIMAGESIZE))
            BOARDRECTS[x].append(r)

    game_solver = Solver(random_fall, algo, weights)

    if ngames == 0:
        ngames = float('inf')
    game_counter = 1

    log_header = ','.join(['board_size', 'gem_number',
                           'w_score', 'w_pairs',
                           'w_nmoves', 'w_depth', 'w_touching',
                           'avg_h_score', 'avg_h_pairs',
                           'avg_h_nmoves', 'avg_h_depth', 'avg_h_touching',
                           'goal_score', 'swaps', 'score', 'status', 'algorithm', 'algo_heuristic',
                           'time_seconds'])

    file_obj = open(logfile, 'w')
    file_obj.write(log_header + '\n')
    file_obj.close()

    times = []
    while game_counter <= ngames:
        try:
            print "Game %d started" %game_counter
            start = datetime.datetime.now()
            score, moves = runGame(is_manual, game_solver, no_graphics)
            end = datetime.datetime.now()
            diff = end - start
            log(logfile, score, moves, game_solver, diff.total_seconds())
            print "Game %d ended: %d points in %d moves" %(game_counter, score, moves)
            print "Game took %.2f seconds" % diff.total_seconds()
            if score >= GOAL_SCORE:
                times.append(diff.total_seconds())
            print
            game_counter += 1
        except KeyboardInterrupt:
            break

    print "Finished %d games." %(game_counter-1)
    print "Average time per finished game: %.2f seconds" %mean(times)
    file_obj.close()

def mean(lst):
    return sum(lst) / float(len(lst)) if lst else 0

def log(logfile, score, moves, solver, seconds):
    status = "win" if score >= GOAL_SCORE else "lose"
    if solver.type == STUPID_GREEDY:
        algo_h = STUPID_GREEDY
    else:
        algo_h = '%s_s%.2f_p%.2f_n%.2f_d%.2f_t%.2f' %(solver.type, solver.w_score, solver.w_pairs, solver.w_nmoves,
                                                      solver.w_depth, solver.w_touching)

    line = "%d,%d,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%d,%s,%s,%s,%.2f" \
            %(BOARDWIDTH, NUMGEMIMAGES,

              solver.w_score, solver.w_pairs,
              solver.w_nmoves, solver.w_depth, solver.w_touching,

              mean(solver.h_score_list), mean(solver.h_pairs_list),
              mean(solver.h_nmoves_list), mean(solver.h_depth_list), mean(solver.h_touching_list),

              GOAL_SCORE, moves, score, status, solver.type, algo_h, seconds)

    file_obj = open(logfile, 'a')
    file_obj.write(line + '\n')
    file_obj.close()

def runGame(is_manual=False, game_solver=None, no_graphics=False):
    # Plays through a single game. When the game is over, this function returns.

    # initalize the board
    gameBoard = getBlankBoard()
    score = 0
    total_moves = 0
    fillBoardAndAnimate(gameBoard, [], score, total_moves, simulation=no_graphics, random_fall=True, is_first=True) # Drop the initial gems.
    # Draw the board.
    draw_window(gameBoard, None, score, total_moves, simulation=no_graphics)

    # initialize variables for the start of a new game
    firstSelectedGem = None
    lastMouseDownX = None
    lastMouseDownY = None
    gameIsOver = False
    clickContinueTextSurf = None

    swap_list = []

    while True: # main game loop

        do_move = True
        if score >= GOAL_SCORE:
            firstSelectedGem = None
            clickedSpace = None
            gameIsOver = True

        if not is_manual and not gameIsOver:
            if not swap_list:
                #print "START SOLVER"
                swap_list = game_solver.getSwaps(copy.deepcopy(gameBoard), score)
                #print "END SOLVER"

                # print "Swap list:"
                # for move in swap_list: print move
                # print

            if not swap_list:
                firstSelectedGem = None
                clickedSpace = None
                gameIsOver = True
                # print "** Total moves: %d" %total_moves
                # print '** Total Number Of Nodes Expanded:' , game_solver.expanded_nodes , ' **'
            else:
                move = swap_list.pop(0)
                firstSelectedGem = move.first
                clickedSpace = move.second

            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                    pygame.quit()
                    sys.exit()

        else:
            clickedSpace = None
            for event in pygame.event.get(): # event handling loop
                if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYUP and event.key == K_BACKSPACE:
                    return # start a new game

                elif event.type == MOUSEBUTTONUP:
                    if gameIsOver:
                        return score, total_moves # after games ends, click to start a new game

                    if event.pos == (lastMouseDownX, lastMouseDownY):
                        # This event is a mouse click, not the end of a mouse drag.
                        clickedSpace = checkForGemClick(event.pos)
                    else:
                        # this is the end of a mouse drag
                        firstSelectedGem = checkForGemClick((lastMouseDownX, lastMouseDownY))
                        clickedSpace = checkForGemClick(event.pos)
                        if not firstSelectedGem or not clickedSpace:
                            # if not part of a valid drag, deselect both
                            firstSelectedGem = None
                            clickedSpace = None
                elif event.type == MOUSEBUTTONDOWN:
                    # this is the start of a mouse click or mouse drag
                    lastMouseDownX, lastMouseDownY = event.pos

            if clickedSpace and not firstSelectedGem:
                # This was the first gem clicked on.
                firstSelectedGem = clickedSpace
                do_move = False

        if clickedSpace and firstSelectedGem and do_move:
            # Two gems have been clicked on and selected. Swap the gems.
            firstSwappingGem, secondSwappingGem = getSwappingGems(gameBoard, firstSelectedGem, clickedSpace)
            if firstSwappingGem == None and secondSwappingGem == None:
                # If both are None, then the gems were not adjacent
                firstSelectedGem = None # deselect the first gem
                continue

            new_board, new_score = perform_move(gameBoard, firstSwappingGem, secondSwappingGem,
                                            score, total_moves, simulation=no_graphics, random_fall=True)

            if new_score is not None:
                total_moves += 1
                score = new_score

            firstSelectedGem = None

        if not canMakeMove(gameBoard):
            gameIsOver = True

        if gameIsOver:
            if is_manual:
                # Only render the text once. In future iterations, just
                # use the Surface object already in clickContinueTextSurf
                clickContinueTextSurf = BASICFONT.render('Final Score: %s (Click to continue)' % (score), 1, GAMEOVERCOLOR, GAMEOVERBGCOLOR)
                clickContinueTextRect = clickContinueTextSurf.get_rect()
                clickContinueTextRect.center = int(WINDOWWIDTH / 2), int(WINDOWHEIGHT / 2)
                DISPLAYSURF.blit(clickContinueTextSurf, clickContinueTextRect)
                pygame.display.update()
                FPSCLOCK.tick(FPS)
            if not is_manual:
                return score, total_moves
        else:
            # Draw the board.
            draw_window(gameBoard, firstSelectedGem, score, total_moves, simulation=no_graphics)

def draw_window(board, firstSelectedGem, score, moves, simulation=True):
    if simulation:
        return
    DISPLAYSURF.fill(BGCOLOR)
    drawBoard(board)
    if firstSelectedGem != None:
        highlightSpace(firstSelectedGem['x'], firstSelectedGem['y'])
    drawScore(score)
    drawMoves(moves)
    pygame.display.update()
    FPSCLOCK.tick(FPS)

def perform_single_move(gameBoard, firstSwappingGem, secondSwappingGem, score=0, moves=0, simulation=True, random_fall=False):
    boardCopy = getBoardCopyMinusGems(gameBoard, (firstSwappingGem, secondSwappingGem))
    gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = secondSwappingGem['imageNum']
    gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = firstSwappingGem['imageNum']

    # See if this is a matching move.
    matchedGems = findMatchingGems(gameBoard)
    if not matchedGems:
        gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = firstSwappingGem['imageNum']
        gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = secondSwappingGem['imageNum']
    else:
        scoreAdd = len(matchedGems)
        refGem = list(matchedGems)[0]
        for gem in matchedGems:
            gameBoard[gem[0]][gem[1]] = EMPTY_SPACE
        score += scoreAdd
        # Drop the new gems.
        fillBoardAndAnimate(gameBoard, [], score, moves, simulation, random_fall)
    return gameBoard, score

def perform_move(gameBoard, firstSwappingGem, secondSwappingGem, score=0, moves=0, simulation=True, random_fall=False):
    # Show the swap animation on the screen.

    # if simulation:
    #     print "START PERFORM MOVE ON:"
    #     print firstSwappingGem
    #     print secondSwappingGem
    boardCopy = getBoardCopyMinusGems(gameBoard, (firstSwappingGem, secondSwappingGem))

    if not simulation:
        animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score, moves)

    # Swap the gems in the board data structure.
    gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = secondSwappingGem['imageNum']
    gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = firstSwappingGem['imageNum']

    # See if this is a matching move.
    matchedGems = findMatchingGems(gameBoard)
    if not matchedGems:
        # Was not a matching move; swap the gems back
        # GAMESOUNDS['bad swap'].play()
        if not simulation:
            animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score, moves)

        gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = firstSwappingGem['imageNum']
        gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = secondSwappingGem['imageNum']

        return gameBoard, None

    else:
        # This was a matching move.
        while matchedGems:
            # Remove matched gems, then pull down the board.

            # points is a list of dicts that tells fillBoardAndAnimate()
            # where on the screen to display text to show how many
            # points the player got. points is a list because if
            # the playergets multiple matches, then multiple points text should appear.
            scoreAdd = len(matchedGems)
            refGem = list(matchedGems)[0]
            points = []
            points.append({'points': scoreAdd,
                           'x': refGem[0] * GEMIMAGESIZE + XMARGIN,
                           'y': refGem[1] * GEMIMAGESIZE + YMARGIN})
            for gem in matchedGems:
                #scoreAdd += (10 + (len(gemSet) - 3) * 10)
                #for gem in gemSet:
                gameBoard[gem[0]][gem[1]] = EMPTY_SPACE

            # Dont play sounds
            #random.choice(GAMESOUNDS['match']).play()
            score += scoreAdd

            # Drop the new gems.
            fillBoardAndAnimate(gameBoard, points, score, moves, simulation, random_fall)

            # if simulation:
            #     print
            #     printBoard(gameBoard)

            # Check if there are any new matches.
            matchedGems = findMatchingGems(gameBoard)

    return gameBoard, score

def getSwappingGems(board, firstXY, secondXY):
    # If the gems at the (X, Y) coordinates of the two gems are adjacent,
    # then their 'direction' keys are set to the appropriate direction
    # value to be swapped with each other.
    # Otherwise, (None, None) is returned.
    firstGem = {'imageNum': board[firstXY['x']][firstXY['y']],
                'x': firstXY['x'],
                'y': firstXY['y']}
    secondGem = {'imageNum': board[secondXY['x']][secondXY['y']],
                 'x': secondXY['x'],
                 'y': secondXY['y']}
    highlightedGem = None
    if firstGem['x'] == secondGem['x'] + 1 and firstGem['y'] == secondGem['y']:
        firstGem['direction'] = LEFT
        secondGem['direction'] = RIGHT
    elif firstGem['x'] == secondGem['x'] - 1 and firstGem['y'] == secondGem['y']:
        firstGem['direction'] = RIGHT
        secondGem['direction'] = LEFT
    elif firstGem['y'] == secondGem['y'] + 1 and firstGem['x'] == secondGem['x']:
        firstGem['direction'] = UP
        secondGem['direction'] = DOWN
    elif firstGem['y'] == secondGem['y'] - 1 and firstGem['x'] == secondGem['x']:
        firstGem['direction'] = DOWN
        secondGem['direction'] = UP
    else:
        # These gems are not adjacent and can't be swapped.
        return None, None
    return firstGem, secondGem

def getBlankBoard():
    # Create and return a blank board data structure.
    board = []
    for x in range(BOARDWIDTH):
        board.append([EMPTY_SPACE] * BOARDHEIGHT)
    return board

def canMakeMove(board):
    # Return True if the board is in a state where a matching
    # move can be made on it. Otherwise return False.

    # The patterns in oneOffPatterns represent gems that are configured
    # in a way where it only takes one move to make a triplet.
    oneOffPatterns = (((0,1), (1,0), (2,0)),
                      ((0,1), (1,1), (2,0)),
                      ((0,0), (1,1), (2,0)),
                      ((0,1), (1,0), (2,1)),
                      ((0,0), (1,0), (2,1)),
                      ((0,0), (1,1), (2,1)),
                      ((0,0), (0,2), (0,3)),
                      ((0,0), (0,1), (0,3)))

    # The x and y variables iterate over each space on the board.
    # If we use + to represent the currently iterated space on the
    # board, then this pattern: ((0,1), (1,0), (2,0))refers to identical
    # gems being set up like this:
    #
    #     +A
    #     B
    #     C
    #
    # That is, gem A is offset from the + by (0,1), gem B is offset
    # by (1,0), and gem C is offset by (2,0). In this case, gem A can
    # be swapped to the left to form a vertical three-in-a-row triplet.
    #
    # There are eight possible ways for the gems to be one move
    # away from forming a triple, hence oneOffPattern has 8 patterns.

    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            for pat in oneOffPatterns:
                # check each possible pattern of "match in next move" to
                # see if a possible move can be made.
                if (getGemAt(board, x+pat[0][0], y+pat[0][1]) == \
                    getGemAt(board, x+pat[1][0], y+pat[1][1]) == \
                    getGemAt(board, x+pat[2][0], y+pat[2][1]) != None) or \
                   (getGemAt(board, x+pat[0][1], y+pat[0][0]) == \
                    getGemAt(board, x+pat[1][1], y+pat[1][0]) == \
                    getGemAt(board, x+pat[2][1], y+pat[2][0]) != None):
                    return True # return True the first time you find a pattern
    return False

def drawMovingGem(gem, progress):
    # Draw a gem sliding in the direction that its 'direction' key
    # indicates. The progress parameter is a number from 0 (just
    # starting) to 100 (slide complete).

    movex = 0
    movey = 0
    progress *= 0.01

    if gem['direction'] == UP:
        movey = -int(progress * GEMIMAGESIZE)
    elif gem['direction'] == DOWN:
        movey = int(progress * GEMIMAGESIZE)
    elif gem['direction'] == RIGHT:
        movex = int(progress * GEMIMAGESIZE)
    elif gem['direction'] == LEFT:
        movex = -int(progress * GEMIMAGESIZE)

    basex = gem['x']
    basey = gem['y']
    if basey == ROWABOVEBOARD:
        basey = -1

    pixelx = XMARGIN + (basex * GEMIMAGESIZE)
    pixely = YMARGIN + (basey * GEMIMAGESIZE)
    r = pygame.Rect( (pixelx + movex, pixely + movey, GEMIMAGESIZE, GEMIMAGESIZE) )
    DISPLAYSURF.blit(GEMIMAGES[gem['imageNum']], r)

def pullDownAllGems(board):
    # pulls down gems on the board to the bottom to fill in any gaps
    for x in range(BOARDWIDTH):
        gemsInColumn = []
        for y in range(BOARDHEIGHT):
            if board[x][y] != EMPTY_SPACE:
                gemsInColumn.append(board[x][y])
        board[x] = ([EMPTY_SPACE] * (BOARDHEIGHT - len(gemsInColumn))) + gemsInColumn

def getGemAt(board, x, y):
    if x < 0 or y < 0 or x >= BOARDWIDTH or y >= BOARDHEIGHT:
        return None
    else:
        return board[x][y]

def getDropSlots(board, simulation=True, random_fall=False, is_first=False):
    # Creates a "drop slot" for each column and fills the slot with a
    # number of gems that that column is lacking. This function assumes
    # that the gems have been gravity dropped already.


    dropSlots = []
    for i in range(BOARDWIDTH):
        dropSlots.append([])

    if simulation and not random_fall:
        return dropSlots

    boardCopy = copy.deepcopy(board)
    pullDownAllGems(boardCopy)

    # count the number of empty spaces in each column on the board
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT-1, -1, -1): # start from bottom, going up
            if boardCopy[x][y] == EMPTY_SPACE:
                possibleGems = list(range(len(GEMIMAGES)))
                if is_first:
                    for offsetX, offsetY in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                        # Narrow down the possible gems we should put in the
                        # blank space so we don't end up putting an two of
                        # the same gems next to each other when they drop.
                        neighborGem = getGemAt(boardCopy, x + offsetX, y + offsetY)
                        if neighborGem != None and neighborGem in possibleGems:
                            possibleGems.remove(neighborGem)

                newGem = random.choice(possibleGems)
                boardCopy[x][y] = newGem
                dropSlots[x].append(newGem)
    return dropSlots

def findMatchingGems(board):
    gemsToRemove = set() # a list of lists of gems in matching triplets that
    # should be removed
    boardCopy = copy.deepcopy(board)

    # loop through each space, checking for 3 adjacent identical gems
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):

            # look for horizontal matches
            if getGemAt(boardCopy, x, y) == getGemAt(boardCopy, x + 1, y) == getGemAt(boardCopy, x + 2, y) and getGemAt(boardCopy, x, y) != EMPTY_SPACE:
                targetGem = boardCopy[x][y]
                offset = 0
                while getGemAt(boardCopy, x + offset, y) == targetGem:
                    # keep checking if there's more than 3 gems in a row
                    gemsToRemove.add((x + offset, y))
                    offset += 1

            # look for vertical matches
            if getGemAt(boardCopy, x, y) == getGemAt(boardCopy, x, y + 1) == getGemAt(boardCopy, x, y + 2) and getGemAt(boardCopy, x, y) != EMPTY_SPACE:
                targetGem = boardCopy[x][y]
                offset = 0
                while getGemAt(boardCopy, x, y + offset) == targetGem:
                    # keep checking, in case there's more than 3 gems in a row
                    gemsToRemove.add((x, y + offset))
                    offset += 1

    return gemsToRemove

def highlightSpace(x, y):
    pygame.draw.rect(DISPLAYSURF, HIGHLIGHTCOLOR, BOARDRECTS[x][y], 4)

def getDroppingGems(board):
    # Find all the gems that have an empty space below them
    boardCopy = copy.deepcopy(board)
    droppingGems = []
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT - 2, -1, -1):
            if boardCopy[x][y + 1] == EMPTY_SPACE and boardCopy[x][y] != EMPTY_SPACE:
                # This space drops if not empty but the space below it is
                droppingGems.append( {'imageNum': boardCopy[x][y], 'x': x, 'y': y, 'direction': DOWN} )
                boardCopy[x][y] = EMPTY_SPACE
    return droppingGems

def animateMovingGems(board, gems, pointsText, score, moves):
    # pointsText is a dictionary with keys 'x', 'y', and 'points'
    progress = 0 # progress at 0 represents beginning, 100 means finished.
    while progress < 100: # animation loop
        DISPLAYSURF.fill(BGCOLOR)
        drawBoard(board)
        for gem in gems: # Draw each gem.
            drawMovingGem(gem, progress)
        drawScore(score)
        drawMoves(moves)
        for pointText in pointsText:
            pointsSurf = BASICFONT.render(str(pointText['points']), 1, SCORECOLOR)
            pointsRect = pointsSurf.get_rect()
            pointsRect.center = (pointText['x'], pointText['y'])
            DISPLAYSURF.blit(pointsSurf, pointsRect)

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        progress += MOVERATE # progress the animation a little bit more for the next frame

def moveGems(board, movingGems):
    # movingGems is a list of dicts with keys x, y, direction, imageNum
    for gem in movingGems:
        if gem['y'] != ROWABOVEBOARD:
            board[gem['x']][gem['y']] = EMPTY_SPACE
            movex = 0
            movey = 0
            if gem['direction'] == LEFT:
                movex = -1
            elif gem['direction'] == RIGHT:
                movex = 1
            elif gem['direction'] == DOWN:
                movey = 1
            elif gem['direction'] == UP:
                movey = -1
            board[gem['x'] + movex][gem['y'] + movey] = gem['imageNum']
        else:
            # gem is located above the board (where new gems come from)
            board[gem['x']][0] = gem['imageNum'] # move to top row

def fillBoardAndAnimate(board, points, score, moves, simulation=True, random_fall=False, is_first=False):

    if simulation and not random_fall:
        pullDownAllGems(board)
        return

    dropSlots = getDropSlots(board, simulation, random_fall, is_first)

    while dropSlots != ([[]] * BOARDWIDTH):
        # do the dropping animation as long as there are more gems to drop
        movingGems = getDroppingGems(board)
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) != 0:
                # cause the lowest gem in each slot to begin moving in the DOWN direction
                movingGems.append({'imageNum': dropSlots[x][0], 'x': x, 'y': ROWABOVEBOARD, 'direction': DOWN})

        boardCopy = getBoardCopyMinusGems(board, movingGems)
        if not simulation:
            animateMovingGems(boardCopy, movingGems, points, score, moves)

        moveGems(board, movingGems)

        # Make the next row of gems from the drop slots
        # the lowest by deleting the previous lowest gems.
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) == 0:
                continue
            board[x][0] = dropSlots[x][0]
            del dropSlots[x][0]

def checkForGemClick(pos):
    # See if the mouse click was on the board
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            if BOARDRECTS[x][y].collidepoint(pos[0], pos[1]):
                return {'x': x, 'y': y}
    return None # Click was not on the board.

def drawBoard(board):
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            pygame.draw.rect(DISPLAYSURF, GRIDCOLOR, BOARDRECTS[x][y], 1)
            gemToDraw = board[x][y]
            if gemToDraw != EMPTY_SPACE:
                DISPLAYSURF.blit(GEMIMAGES[gemToDraw], BOARDRECTS[x][y])

def getBoardCopyMinusGems(board, gems):
    # Creates and returns a copy of the passed board data structure,
    # with the gems in the "gems" list removed from it.
    #
    # Gems is a list of dicts, with keys x, y, direction, imageNum

    boardCopy = copy.deepcopy(board)

    # Remove some of the gems from this board data structure copy.

    for gem in gems:
        if gem['y'] != ROWABOVEBOARD:
            boardCopy[gem['x']][gem['y']] = EMPTY_SPACE

    return boardCopy

def drawMoves(k):
    movesImg = BASICFONT.render(str(k), 1, MOVESCOLOR)
    movesRect = movesImg.get_rect()
    movesRect.bottomleft = (WINDOWWIDTH - 70, WINDOWHEIGHT - 6)
    DISPLAYSURF.blit(movesImg, movesRect)

def drawScore(score):
    scoreImg = BASICFONT.render(str(score), 1, SCORECOLOR)
    scoreRect = scoreImg.get_rect()
    scoreRect.bottomleft = (10, WINDOWHEIGHT - 6)
    DISPLAYSURF.blit(scoreImg, scoreRect)

def printBoard(board):
    for y in range(BOARDHEIGHT):
        for x in range(BOARDWIDTH):
            print "%3d" %board[x][y],
        print

def boardTuple(board):
    return tuple([tuple(col) for col in board])

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-m", "--manual",
                      action="store_true", dest="IS_MANUAL", default=False,
                      help="Run game with manual control")
    parser.add_option("-s", "--size",
                      type="int", dest="BOARD_SIZE", default=6,
                      help="Size of game board side (4..8)")
    parser.add_option("-g", "--gems",
                      type="int", dest="GEM_NUM", default=4,
                      help="Number of gem types (4..7)")
    parser.add_option("-c", "--score",
                      type="int", dest="GOAL", default=250,
                      help="Target (limit) score")
    parser.add_option("-f", "--fps",
                      type="int", dest="USER_FPS", default=30,
                      help="Game animation FPS")
    parser.add_option("-n", "--ngames",
                      type="int", dest="NGAMES", default=0,
                      help="Number of games to run. Set to 0 to run forever")
    parser.add_option("-O", "--output",
                      type="string", dest="LOGFILE", default="gemgem_log.csv",
                      help="Log file name. Output format is CSV")
    parser.add_option("-q", "--no-graphics",
                      action="store_true", dest="NO_GRAPHICS", default=False,
                      help="Run game(s) without graphics")
    parser.add_option("-a", "--algorithm",
                      type="int", dest="ALGO", default=1,
                      help="Algorithm: 1=SGS, 2=HGS, 3=L-BFS")
    parser.add_option("-w", "--weights",
                      type="string", dest="WEIGHTS", default="1 1 1 1 1",
                      help="Weights: [Score, Pairs, Moves, Depth, Touching]")
    parser.add_option("-j",
                      action="store_true", dest="JJ", default=False,
                      help="Who knows?")

    (options, args) = parser.parse_args()

    BOARDWIDTH = BOARDHEIGHT = options.BOARD_SIZE
    NUMGEMIMAGES = options.GEM_NUM
    GOAL_SCORE = options.GOAL
    FPS = options.USER_FPS
    J = options.JJ

    if BOARDWIDTH < 4 or BOARDWIDTH > 8:
        print "Board size must be in the range 4..8"
        parser.print_help()
        sys.exit(1)

    if NUMGEMIMAGES < 4 or NUMGEMIMAGES > 7:
        print "Number of gem types must be in the range 4..7"
        parser.print_help()
        sys.exit(1)

    if GOAL_SCORE < 0:
        print "Target score must be positive. Terminating"
        parser.print_help()
        sys.exit(1)

    if FPS < 10:
        print "FPS must be at least 10. Terminating"
        parser.print_help()
        sys.exit(1)

    if options.NGAMES < 0:
        print "Number of games must be non-negative. Terminating"
        parser.print_help()
        sys.exit(1)

    if options.ALGO not in (1,2,3):
        print "Algorithm must be 1 (SGS), 2 (HGS) or 3 (L-BFS). Terminating"
        parser.print_help()
        sys.exit(1)

    try:
        weights = [float(x) for x in options.WEIGHTS.split()]
    except:
        print "Weights must be numbers. Terminating"
        parser.print_help()
        sys.exit(1)

    if len(weights) != 5:
        print "Must input exactly 5 Weights. Terminating"
        parser.print_help()
        sys.exit(1)

    main(options.IS_MANUAL, False, options.NGAMES, ALGOS[options.ALGO], weights, options.NO_GRAPHICS, options.LOGFILE)
