import time
import random

from engine import (
    P1, P2, KIND_KING, generate_all_moves, apply_move, sq_to_rc,
)

random.seed(12345)

ZOBRIST_TABLE = [[random.getrandbits(64) for _ in range(8)] for _ in range(32)]
ZOBRIST_SIDE = random.getrandbits(64)


def _piece_code(piece):
    owner_idx = 0 if piece.owner == P1 else 1
    kind_idx = 1 if piece.kind == KIND_KING else 0
    marko_idx = 1 if piece.marko else 0
    return owner_idx * 4 + kind_idx * 2 + marko_idx


def zobrist_hash(state):
    h = 0
    for sq in range(32):
        pid = state.board[sq]
        if pid is not None:
            h ^= ZOBRIST_TABLE[sq][_piece_code(state.pieces[pid])]
    if state.current_player == P2:
        h ^= ZOBRIST_SIDE
    return h


def evaluate(state):
    if state.winner == P1:
        return 10000.0
    if state.winner == P2:
        return -10000.0
    if state.winner == "draw":
        return 0.0

    score = 0.0
    for sq in range(32):
        pid = state.board[sq]
        if pid is None:
            continue
        p = state.pieces[pid]
        r, c = sq_to_rc(sq)

        if p.marko:
            val = 6.0
        elif p.kind == KIND_KING:
            val = 3.0
        else:
            val = 1.0
            if p.owner == P1:
                val += 0.05 * r
            else:
                val += 0.05 * (7 - r)

        center_bonus = 0.02 * (4 - abs(c - 3.5))

        bonus = 0.0
        if p.armor > 0:
            bonus += 0.3
        if p.topuz:
            bonus += 0.15
        if p.sarac:
            bonus += 0.1
        if p.mesina_lock > 0:
            bonus -= 0.25 

        total = val + center_bonus + bonus
        score += total if p.owner == P1 else -total

    p1_moves = len(generate_all_moves(state, P1))
    p2_moves = len(generate_all_moves(state, P2))
    score += 0.05 * (p1_moves - p2_moves)

    return score


EXACT, LOWER, UPPER = 0, 1, 2


class SearchContext:
    def __init__(self, time_limit):
        self.start = time.time()
        self.time_limit = time_limit
        self.tt = {}
        self.nodes = 0

    def time_up(self):
        return (time.time() - self.start) > self.time_limit


def _order_moves(state, moves, tt_move_key=None):
    def score(m):
        s = 0
        if tt_move_key is not None and m.key() == tt_move_key:
            s += 1000
        s += len(m.captures) * 10
        return -s
    return sorted(moves, key=score)


def alphabeta(state, depth, alpha, beta, maximizing, ctx):
    ctx.nodes += 1
    if ctx.time_up():
        raise TimeoutError()

    h = zobrist_hash(state)
    tt_entry = ctx.tt.get(h)
    tt_move_key = None
    if tt_entry is not None and tt_entry[0] >= depth:
        tt_depth, tt_score, tt_flag, tt_move_key = tt_entry
        if tt_flag == EXACT:
            return tt_score, tt_move_key
        elif tt_flag == LOWER:
            alpha = max(alpha, tt_score)
        elif tt_flag == UPPER:
            beta = min(beta, tt_score)
        if alpha >= beta:
            return tt_score, tt_move_key
    elif tt_entry is not None:
        tt_move_key = tt_entry[3]

    player = P1 if maximizing else P2
    moves = generate_all_moves(state, player)

    if state.winner is not None or not moves:
        return evaluate(state), None

    if depth == 0:
        return evaluate(state), None

    moves = _order_moves(state, moves, tt_move_key)

    best_move = moves[0]
    if maximizing:
        value = float("-inf")
        for m in moves:
            ns = apply_move(state, m, relic_choice="front")
            score, _ = alphabeta(ns, depth - 1, alpha, beta, False, ctx)
            if score > value:
                value = score
                best_move = m
            alpha = max(alpha, value)
            if alpha >= beta:
                break
    else:
        value = float("inf")
        for m in moves:
            ns = apply_move(state, m, relic_choice="front")
            score, _ = alphabeta(ns, depth - 1, alpha, beta, True, ctx)
            if score < value:
                value = score
                best_move = m
            beta = min(beta, value)
            if alpha >= beta:
                break

    flag = EXACT
    if value <= alpha:
        flag = UPPER
    elif value >= beta:
        flag = LOWER
    ctx.tt[h] = (depth, value, flag, best_move.key() if best_move else None)

    return value, best_move


def find_best_move(state, time_limit=3.0, max_depth=20):
    ctx = SearchContext(time_limit)
    maximizing = state.current_player == P1
    moves = generate_all_moves(state, state.current_player)
    if not moves:
        return None
    best_overall = moves[0]
    depth = 1
    while depth <= max_depth:
        try:
            score, best_move_key = alphabeta(state, depth, float("-inf"), float("inf"), maximizing, ctx)
        except TimeoutError:
            break
        if best_move_key is not None:
            for m in moves:
                if m.key() == best_move_key:
                    best_overall = m
                    break
        depth += 1
        if ctx.time_up():
            break
    return best_overall
