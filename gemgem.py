# Gemgem (a Bejeweled clone)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license

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

FPS = 20 # frames per second to update the screen
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

GREEDY = 'greedy'
ASTAR = 'a*'
GOAL_SCORE = 100


class BoardMove(object):

    def __init__(self, source_board, x, y, direction, random_fall):
        self.first = self.second = self.dest_board = None
        self.score = 0
        self.random_fall = random_fall
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
        self.dest_board, self.score = perform_move(copy.deepcopy(self.source_board), self.first, self.second,
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

    def __cmp__(self, other):
        my_score = self.getMovesScore()
        other_score = other.getMovesScore()
        if my_score < other_score:
            return -1
        if my_score > other_score:
            return 1
        return 0

class Solver(object):

    def __init__(self, random_fall, solver_type):
        self.random_fall = random_fall
        self.type = solver_type
        self.uncertainty_thres = 0.1
        self.expanded_nodes = 0

    def getSwaps(self, board, cur_score=0):
        if self.type == GREEDY:
            return [self.getSwapGreedy(board)]
        elif self.type == ASTAR:
            return self.getSwapsAstar(board, cur_score)

    def getSwapsUsingSearch(self, start_board, fringe, cur_score):
        visited = []
        start_state = FringeState(start_board, total_score=cur_score)
        best = start_state
        fringe.append(start_state)

        while not self.isCutoff(fringe):
            print len(fringe)

            cur = fringe.pop(0)
            if self.isGoal(cur):
                return cur.moves

            if cur.board in visited:
                continue

            possible_moves = self.getPossibleMoves(cur.board)
            if not possible_moves:
                best = max([best, cur])

            for move in possible_moves:
                fringe.append(FringeState(move.dest_board, cur.moves + [move], 'CHANGETHIS',
                                          cur.total_score + move.score))
                self.expanded_nodes += 1

            visited.append(cur.board)

        best = max(fringe + [best])
        return best.moves

    def isGoal(self, fringe_state):
        return fringe_state.total_score >= GOAL_SCORE

    def getSwapsAstar(self, board, cur_score):
        fringe = []
        return self.getSwapsUsingSearch(board, fringe, cur_score)

    def isCutoff(self, states):
        """
        All boards are either above uncertainty threshold, or without possible moves
        """

        res = [self.isUncertain(state.board) or not canMakeMove(state.board) for state in states]
        return all(res)


        # for state in states:
        #     if not self.isUncertain(state.board) or canMakeMove(state.board):
        #         return False
        # return True

    def isUncertain(self, board):
        #import pdb; pdb.set_trace()
        uncertainty = reduce(lambda s1, s2: s1 + s2, board).count(-1) / float((BOARDHEIGHT * BOARDWIDTH))
        if uncertainty > self.uncertainty_thres:
            return True
        return False

    def getPossibleMoves(self, board):
        moves = []
        for y in range(BOARDHEIGHT):
            for x in range(BOARDWIDTH):

                move_right = BoardMove(copy.deepcopy(board), x, y, RIGHT, self.random_fall)
                move_down = BoardMove(copy.deepcopy(board), x, y, DOWN, self.random_fall)

                for move in (move_right, move_down):
                    if move.score > 0:
                        moves.append(move)

        return moves

    def getSwapGreedy(self, board):

        moves = self.getPossibleMoves(board)

        if moves:
            best = max(moves)
            print
            print "MOVES:"
            for move in moves:
                print move
            print
            print "BEST:"
            print best
            print
            import pdb; pdb.set_trace()
            return best.first, best.second, best.score
        else:
            return None, None, None

def main(is_manual=False, random_fall=False):

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
        if gemImage.get_size() != (GEMIMAGESIZE, GEMIMAGESIZE):
            gemImage = pygame.transform.smoothscale(gemImage, (GEMIMAGESIZE, GEMIMAGESIZE))
        GEMIMAGES.append(gemImage)

    # Load the sounds.
    GAMESOUNDS = {}
    GAMESOUNDS['bad swap'] = pygame.mixer.Sound('badswap.wav')
    GAMESOUNDS['match'] = []
    for i in range(NUMMATCHSOUNDS):
        GAMESOUNDS['match'].append(pygame.mixer.Sound('match%s.wav' % i))

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

    game_solver = Solver(random_fall, ASTAR)
    while True:
        runGame(is_manual, game_solver)


def runGame(is_manual=False, game_solver=None):
    # Plays through a single game. When the game is over, this function returns.

    # initalize the board
    gameBoard = getBlankBoard()
    score = 0
    fillBoardAndAnimate(gameBoard, [], score, simulation=False, random_fall=True) # Drop the initial gems.
    # initialize variables for the start of a new game
    firstSelectedGem = None
    lastMouseDownX = None
    lastMouseDownY = None
    gameIsOver = False
    clickContinueTextSurf = None

    swap_list = []

    while True: # main game loop

        do_move = True

        if not is_manual and not gameIsOver:
            if not swap_list:
                swap_list = game_solver.getSwaps(copy.deepcopy(gameBoard), score)

                print "Retrieving new swap list:"
                for move in swap_list: print move
                print
                # import pdb; pdb.set_trace()

            if not swap_list:
                firstSelectedGem = None
                clickedSpace = None
                gameIsOver = True
                print '** Total Number Of Nodes Expanded:' , game_solver.expanded_nodes , ' **'
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
                        return # after games ends, click to start a new game

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

            new_board, score = perform_move(gameBoard, firstSwappingGem, secondSwappingGem,
                                 score, simulation=False, random_fall=True)

            firstSelectedGem = None

        if not canMakeMove(gameBoard):
            gameIsOver = True

        # Draw the board.
        DISPLAYSURF.fill(BGCOLOR)
        drawBoard(gameBoard)
        if firstSelectedGem != None:
            highlightSpace(firstSelectedGem['x'], firstSelectedGem['y'])
        if gameIsOver:
            if clickContinueTextSurf == None:
                # Only render the text once. In future iterations, just
                # use the Surface object already in clickContinueTextSurf
                clickContinueTextSurf = BASICFONT.render('Final Score: %s (Click to continue)' % (score), 1, GAMEOVERCOLOR, GAMEOVERBGCOLOR)
                clickContinueTextRect = clickContinueTextSurf.get_rect()
                clickContinueTextRect.center = int(WINDOWWIDTH / 2), int(WINDOWHEIGHT / 2)
            DISPLAYSURF.blit(clickContinueTextSurf, clickContinueTextRect)

        drawScore(score)
        pygame.display.update()
        FPSCLOCK.tick(FPS)

def perform_move(gameBoard, firstSwappingGem, secondSwappingGem, score=0, simulation=True, random_fall=False):
    # Show the swap animation on the screen.

    # if simulation:
    #     print "START PERFORM MOVE ON:"
    #     print firstSwappingGem
    #     print secondSwappingGem
    boardCopy = getBoardCopyMinusGems(gameBoard, (firstSwappingGem, secondSwappingGem))

    if not simulation:
        animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score)

    # Swap the gems in the board data structure.
    gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = secondSwappingGem['imageNum']
    gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = firstSwappingGem['imageNum']

    # See if this is a matching move.
    matchedGems = findMatchingGems(gameBoard)
    if not matchedGems:
        # Was not a matching move; swap the gems back
        # GAMESOUNDS['bad swap'].play()
        if not simulation:
            animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score)

        gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = firstSwappingGem['imageNum']
        gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = secondSwappingGem['imageNum']
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
            fillBoardAndAnimate(gameBoard, points, score, simulation, random_fall)

            # if simulation:
            #     print
            #     printBoard(gameBoard)

            # Check if there are any new matches.
            # import pdb; pdb.set_trace()
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


def getDropSlots(board, random_fall=False):
    # Creates a "drop slot" for each column and fills the slot with a
    # number of gems that that column is lacking. This function assumes
    # that the gems have been gravity dropped already.


    dropSlots = []
    for i in range(BOARDWIDTH):
        dropSlots.append([])

    if not random_fall:
        return dropSlots

    boardCopy = copy.deepcopy(board)
    pullDownAllGems(boardCopy)

    # count the number of empty spaces in each column on the board
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT-1, -1, -1): # start from bottom, going up
            if boardCopy[x][y] == EMPTY_SPACE:
                possibleGems = list(range(len(GEMIMAGES)))
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


def animateMovingGems(board, gems, pointsText, score):
    # pointsText is a dictionary with keys 'x', 'y', and 'points'
    progress = 0 # progress at 0 represents beginning, 100 means finished.
    while progress < 100: # animation loop
        DISPLAYSURF.fill(BGCOLOR)
        drawBoard(board)
        for gem in gems: # Draw each gem.
            drawMovingGem(gem, progress)
        drawScore(score)
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


def fillBoardAndAnimate(board, points, score, simulation=True, random_fall=False):

    if simulation and not random_fall:
        pullDownAllGems(board)
        return

    dropSlots = getDropSlots(board, random_fall)
    while dropSlots != ([[]] * BOARDWIDTH):
        # do the dropping animation as long as there are more gems to drop
        movingGems = getDroppingGems(board)
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) != 0:
                # cause the lowest gem in each slot to begin moving in the DOWN direction
                movingGems.append({'imageNum': dropSlots[x][0], 'x': x, 'y': ROWABOVEBOARD, 'direction': DOWN})

        boardCopy = getBoardCopyMinusGems(board, movingGems)
        if not simulation:
            animateMovingGems(boardCopy, movingGems, points, score)

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
            try:
                boardCopy[gem['x']][gem['y']] = EMPTY_SPACE
            except:
                import pdb; pdb.set_trace()

    return boardCopy


def drawScore(score):
    scoreImg = BASICFONT.render(str(score), 1, SCORECOLOR)
    scoreRect = scoreImg.get_rect()
    scoreRect.bottomleft = (10, WINDOWHEIGHT - 6)
    DISPLAYSURF.    blit(scoreImg, scoreRect)

def printBoard(board):
    for y in range(BOARDHEIGHT):
        for x in range(BOARDWIDTH):
            print "%3d" %board[x][y],
        print

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-m", "--manual",
                      action="store_true", dest="IS_MANUAL", default=False,
                      help="Run game with manual control")
    parser.add_option("-s", "--size",
                      type="int", dest="BOARD_SIZE", default=8,
                      help="Size of game board")
    parser.add_option("-g", "--gems",
                      type="int", dest="GEM_NUM", default=4,
                      help="Number of gem types")
    parser.add_option("-r", "--random-fall",
                      action="store_true", dest="RANDOM_FALL", default=False,
                      help="Simulate cascade with using simulation of random gems falling from top")
    parser.add_option("-c", "--score",
                      type="int", dest="GOAL", default=100,
                      help="Goal score")

    (options, args) = parser.parse_args()

    BOARDWIDTH = BOARDHEIGHT = options.BOARD_SIZE
    NUMGEMIMAGES = options.GEM_NUM
    GOAL_SCORE = options.GOAL

    main(options.IS_MANUAL, options.RANDOM_FALL)
