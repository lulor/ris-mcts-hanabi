from model import Model, GameMove
from .tree import Tree, Node
from functools import reduce
import numpy as np

DEBUG = False


def find(pred, iterable):
    for element in iterable:
        if pred(element):
            return element
    return None


class GameNode:
    def __init__(self, move: GameMove) -> None:
        self.move = move
        self.value = 0
        self.simulations = 0

    # TODO: REIMPLEMENT AS __copy__ or remove typing
    def copy(self) -> GameNode:
        new_game_node = GameNode(None if self.move == None else self.move.copy())
        new_game_node.value = self.value
        new_game_node.simulations = self.simulations
        return new_game_node


class MCTS:
    def __init__(self, model: Model, current_player: str):
        self.model = model
        prev_player = model.state.get_prev_player_name(current_player)
        root = Node(
            GameNode(GameMove(prev_player, action_type=None))
        )  # dummy game-move
        self.tree = Tree(root)

    def run_search(self, iterations=50):
        # each iteration represents the select, expand, simulate, backpropagate iteration
        for _ in range(iterations):
            self.run_search_iteration()

        # selecting from the direct children of the root the one containing the move with most number of simulations
        best_move_node = reduce(
            lambda a, b: a if a.data.simulations > b.data.simulations else b,
            self.tree.get_children(self.tree.get_root()),
        )
        # TODO: unresolved reference position
        return best_move_node.data.move.position

    def run_search_iteration(self):
        select_leaf, select_model = self.select(self.model.copy())

        # print('selected node ', select_leaf)
        expand_leaf, expand_model = self.expand(select_leaf, select_model)

        ## added
        simulation_score = self.simulate(expand_leaf, expand_model)
        self.backpropagate(expand_leaf, simulation_score)
        if DEBUG:
            print(
                "children list of ",
                self.tree.get_root(),
                " simulations ",
                self.tree.get_root().data.simulations,
            )
            for child in self.tree.get_children(self.tree.get_root()):
                print(child)
                print("simulations ", child.data.simulations)
                print("value ", child.data.value)
                print("UCB1 ", self.UCB1(child, self.tree.get_root()))
                # TODO: unresolved reference position
                print("position", child.data.move.position)
                print("player", child.data.move.player)
                print(
                    "---------------------------------------------------------------------------------"
                )
            input("Enter...")
        return

    def select(self, model: Model):
        node = self.tree.get_root()
        while not node.is_leaf() and self.is_fully_explored(node, model):
            player = model.state.get_next_player_name(node.data.move.player)
            model.exit_node(player)  # re-determinize hand
            node = self.get_best_child_UCB1(node)
            model.make_move(node.data.move)
            model.enter_node(player)  # restore hand
        return node, model

    def is_fully_explored(self, node: Node, model: Model):
        """
        return True if there is no more moves playable at a certain level that has not been tried yet
        """
        # this function needs to be changed for the hanabi case
        return len(self.get_available_plays(node, model)) == 0

    def get_available_plays(self, node: Node, model):
        children = self.tree.get_children(node)
        player = model.state.get_next_player_name(node.data.move.player)
        # return only valid moves which haven't been already tried in children
        return list(
            filter(
                lambda move: not find(lambda child: child.data.move == move, children),
                model.valid_moves(player),
            )
        )

    def expand(self, node: Node, model: Model):
        expanded_node = None

        # model.check_win should check if the match is over, not if it is won (see simulation and backpropagation function)
        if not model.check_ended()[0]:
            legal_moves = self.get_available_plays(node, model)
            random_move = np.random.choice(legal_moves)
            model.make_move(random_move)
            expanded_node = Node(GameNode(random_move))
            self.tree.insert(expanded_node, node)
        else:
            expanded_node = node
            if DEBUG:
                print("winning node")
        if DEBUG:
            print("expanding..")
        return expanded_node, model

    def simulate(self, node: Node, model: Model):
        current_player = node.data.move.player

        # here random moves are made until someone wins, then the winning player is passed to backpropagation function
        # the problem is that in hanabi there is no winner (and probably moves can't be random)
        # so this function need some changes (at the end it needs to return the score)

        # only one simulation has been run, probably it is better to run a bunch of simulations
        while not model.check_ended()[0]:
            current_player = model.state.get_next_player_name(current_player)
            # if there are no more legal moves (=> draw)
            if not model.make_random_move(current_player):
                break
        score = model.check_ended()[1]

        return score

    # def backpropagate(self, node, winner: int):
    def backpropagate(self, node: Node, score: int):
        # as the simulation function, this one needs to be changed
        # here nodes value is incremented if it leads to a winning game for the agent
        # but in our case need to be evalueted in proportion to the score
        # just to give and idea I implemented a simple version
        while not node.is_root():
            node.data.simulations += 1
            # it maps the score to [0, 1]
            node.data.value += score / 25
            node = self.tree.get_parent(node)
            # print('parent node ', node)
            # print('is ', node.data.move.position, ' root? ', node.is_root())
        node.data.simulations += 1
        return

    def UCB1(self, node: Node, parent: Node, c: float = 0.1):
        exploitation = node.data.value / node.data.simulations
        if parent.data.simulations == 0:
            exploration = 0
        else:
            exploration = np.sqrt(
                np.log(parent.data.simulations) / node.data.simulations
            )
        return exploitation + c * exploration

    def get_best_child_UCB1(self, node: Node):
        node_scores = map(
            lambda f: [f, self.UCB1(f, node)], self.tree.get_children(node)
        )
        return reduce(lambda a, b: a if a[1] > b[1] else b, list(node_scores))[0]


## TODO
# in mcts.py
# adapt function is_fully_explored (medium)
# actually the problem is when it calls get_available_plays
# adapt function simulate (hard)
# adapt function backpropagate (easy)

# in model.py
# adapt valid_moves (medium)
# adapt make_move (medium)
# adapt make_random_move (that should be changed to make_intentional_move) (hard)
# adapt check_win (that should be changed to check_if_ended) (medium)
#
