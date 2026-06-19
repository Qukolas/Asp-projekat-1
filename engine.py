import copy
from collections import deque

P1 = 1   
P2 = 2   

KIND_MAN = "man"
KIND_KING = "king"

BRAZDE = set()

RELIC_TOK = "TOK"       
RELIC_MESINA = "MESINA"  
RELIC_TOPUZ = "TOPUZ"    
RELIC_SARAC = "SARAC"    
RELIC_TRI = "TRI"        

RELIC_NAMES = {
    RELIC_TOK: "Tok od celika (Oklop)",
    RELIC_MESINA: "Mesina rujnog vina (Pogled ispod obrva)",
    RELIC_TOPUZ: "Topuz (Razorni udarac)",
    RELIC_SARAC: "Sarac (Sarcev skok)",
    RELIC_TRI: "Tri tovara blaga (Krunisanje)",
}

RELIC_CYCLE = [RELIC_TOK, RELIC_MESINA, RELIC_TOPUZ, RELIC_SARAC, RELIC_TRI]

DRAW_LIMIT = 40  

def rc_to_sq(r, c):
    if (r + c) % 2 == 0:
        return None
    return r * 4 + c // 2


def sq_to_rc(sq):
    r = sq // 4
    idx = sq % 4
    if r % 2 == 0:
        c = idx * 2 + 1
    else:
        c = idx * 2
    return r, c


BRAZDE.add(rc_to_sq(3, 0))
BRAZDE.add(rc_to_sq(4, 7))


def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8


class Piece:
    __slots__ = ("owner", "kind", "marko", "armor", "mesina_lock", "topuz",
                  "sarac", "relics_triggered")

    def __init__(self, owner, kind=KIND_MAN):
        self.owner = owner
        self.kind = kind
        self.marko = False
        self.armor = 0
        self.mesina_lock = 0
        self.topuz = False
        self.sarac = False
        self.relics_triggered = set()

    def copy(self):
        p = Piece(self.owner, self.kind)
        p.marko = self.marko
        p.armor = self.armor
        p.mesina_lock = self.mesina_lock
        p.topuz = self.topuz
        p.sarac = self.sarac
        p.relics_triggered = set(self.relics_triggered)
        return p


class GameState:
    def __init__(self):
        self.board = [None] * 32 
        self.pieces = {}          
        self.next_id = 1
        self.current_player = P1
        self.drum = deque(maxlen=5)   
        self.cycle_idx = 0
        self.no_progress = 0      
        self.winner = None        

    def copy(self):
        ns = GameState()
        ns.board = list(self.board)
        ns.pieces = {pid: p.copy() for pid, p in self.pieces.items()}
        ns.next_id = self.next_id
        ns.current_player = self.current_player
        ns.drum = deque(self.drum, maxlen=5)
        ns.cycle_idx = self.cycle_idx
        ns.no_progress = self.no_progress
        ns.winner = self.winner
        return ns

    def add_piece(self, sq, owner, kind=KIND_MAN):
        pid = self.next_id
        self.next_id += 1
        self.pieces[pid] = Piece(owner, kind)
        self.board[sq] = pid
        return pid


def initial_state():
    st = GameState()
    for sq in range(32):
        r, c = sq_to_rc(sq)
        if r <= 2:
            st.add_piece(sq, P1, KIND_MAN)
        elif r >= 5:
            st.add_piece(sq, P2, KIND_MAN)
    for _ in range(5):
        st.drum.appendleft(RELIC_CYCLE[st.cycle_idx % len(RELIC_CYCLE)])
        st.cycle_idx += 1
    return st


class Move:

    def __init__(self, from_sq, to_sq, captures=None, path=None,
                 is_topuz=False, is_sarac=False):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.captures = captures or []
        self.path = path or [from_sq, to_sq]
        self.is_topuz = is_topuz
        self.is_sarac = is_sarac

    def __repr__(self):
        return f"Move({self.from_sq}->{self.to_sq}, cap={self.captures})"

    def key(self):
        return (self.from_sq, self.to_sq, tuple(self.captures), self.is_topuz,
                self.is_sarac)


DIAG_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _slide_squares(r, c, dr, dc):
    out = []
    while True:
        r += dr
        c += dc
        if not in_bounds(r, c):
            break
        out.append((r, c))
    return out


def _find_captures_from(state, sq, owner, kind, captured_so_far, path_so_far):
    r, c = sq_to_rc(sq)
    sequences = []
    found_continuation = False

    capture_dirs = DIAG_DIRS
    if kind == KIND_MAN:
        forward = 1 if owner == P1 else -1
        capture_dirs = [(dr, dc) for (dr, dc) in DIAG_DIRS if dr == forward]

    for dr, dc in capture_dirs:
        if kind == KIND_MAN:
            mr, mc = r + dr, c + dc
            lr, lc = r + 2 * dr, c + 2 * dc
            if not in_bounds(lr, lc):
                continue
            mid_sq = rc_to_sq(mr, mc)
            land_sq = rc_to_sq(lr, lc)
            if mid_sq is None or land_sq is None:
                continue
            mid_pid = state.board[mid_sq]
            if mid_pid is None or mid_sq in captured_so_far:
                continue
            mid_piece = state.pieces[mid_pid]
            if mid_piece.owner == owner or mid_piece.armor > 0:
                continue
            if state.board[land_sq] is not None:
                continue
            found_continuation = True
            new_cap = captured_so_far + [mid_sq]
            new_path = path_so_far + [land_sq]
            sub = _find_captures_from(state, land_sq, owner, kind, new_cap, new_path)
            sequences.extend(sub)
        else: 
            squares = _slide_squares(r, c, dr, dc)
            blocked = False
            for (sr, sc) in squares:
                s_sq = rc_to_sq(sr, sc)
                pid = state.board[s_sq]
                if pid is None:
                    continue 
               
                piece = state.pieces[pid]
                if piece.owner == owner or s_sq in captured_so_far or piece.armor > 0:
                    blocked = True
                    break
                
                idx = squares.index((sr, sc))
                landing_squares = squares[idx + 1:]
                landed_any = False
                for (lr, lc) in landing_squares:
                    l_sq = rc_to_sq(lr, lc)
                    if state.board[l_sq] is not None:
                        break
                    landed_any = True
                    found_continuation = True
                    new_cap = captured_so_far + [s_sq]
                    new_path = path_so_far + [l_sq]
                    sub = _find_captures_from(state, l_sq, owner, kind, new_cap, new_path)
                    sequences.extend(sub)
                blocked = True
                break

    if not found_continuation and captured_so_far:
        sequences.append((path_so_far[-1], list(captured_so_far), list(path_so_far)))
    return sequences


def _topuz_captures(state, sq, owner, kind, piece):
    out = []
    if not piece.topuz:
        return out
    dirs = DIAG_DIRS
    if kind == KIND_MAN:
        forward = 1 if owner == P1 else -1
        dirs = [(dr, dc) for (dr, dc) in DIAG_DIRS if dr == forward]
    r, c = sq_to_rc(sq)
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        if not in_bounds(nr, nc):
            continue
        n_sq = rc_to_sq(nr, nc)
        if n_sq is None:
            continue
        pid = state.board[n_sq]
        if pid is None:
            continue
        target = state.pieces[pid]
        if target.owner == owner or target.armor > 0:
            continue
        out.append(Move(sq, n_sq, captures=[n_sq], path=[sq, n_sq], is_topuz=True))
    return out


def _normal_moves_for_piece(state, sq, owner, kind, piece):
    out = []
    r, c = sq_to_rc(sq)
    if kind == KIND_MAN:
        forward = 1 if owner == P1 else -1
        for dc in (-1, 1):
            nr, nc = r + forward, c + dc
            if not in_bounds(nr, nc):
                continue
            n_sq = rc_to_sq(nr, nc)
            if n_sq is not None and state.board[n_sq] is None:
                out.append(Move(sq, n_sq))
    else:  
        for dr, dc in DIAG_DIRS:
            for (sr, sc) in _slide_squares(r, c, dr, dc):
                s_sq = rc_to_sq(sr, sc)
                if state.board[s_sq] is not None:
                    break
                out.append(Move(sq, s_sq))

    if piece.sarac:
        for dr, dc in DIAG_DIRS:
            mr, mc = r + dr, c + dc
            lr, lc = r + 2 * dr, c + 2 * dc
            if not in_bounds(lr, lc):
                continue
            mid_sq = rc_to_sq(mr, mc)
            land_sq = rc_to_sq(lr, lc)
            if mid_sq is None or land_sq is None:
                continue
            mid_pid = state.board[mid_sq]
            if mid_pid is None:
                continue
            if state.pieces[mid_pid].owner != owner:
                continue
            if state.board[land_sq] is not None:
                continue
            out.append(Move(sq, land_sq, path=[sq, land_sq], is_sarac=True))
    return out


def generate_moves_for_piece(state, sq):
    pid = state.board[sq]
    if pid is None:
        return []
    piece = state.pieces[pid]

    if piece.mesina_lock > 0:
        return []

    owner = piece.owner
    kind = piece.kind

    moves = []
    seqs = _find_captures_from(state, sq, owner, kind, [], [sq])
    for (to_sq, captured, path) in seqs:
        moves.append(Move(sq, to_sq, captures=captured, path=path))
    moves.extend(_topuz_captures(state, sq, owner, kind, piece))

    if moves:
        return moves 

    return _normal_moves_for_piece(state, sq, owner, kind, piece)


def generate_all_moves(state, player):
    capture_moves = []
    normal_moves = []
    for sq in range(32):
        pid = state.board[sq]
        if pid is None:
            continue
        piece = state.pieces[pid]
        if piece.owner != player:
            continue
        mvs = generate_moves_for_piece(state, sq)
        for m in mvs:
            if m.captures:
                capture_moves.append(m)
            else:
                normal_moves.append(m)
    if capture_moves:
        return capture_moves
    return normal_moves


def _nearest_opponent(state, sq, owner):
    r, c = sq_to_rc(sq)
    best = None
    best_d = None
    for pid, p in state.pieces.items():
        if p.owner == owner:
            continue
        psq = None
        for s in range(32):
            if state.board[s] == pid:
                psq = s
                break
        if psq is None:
            continue
        pr, pc = sq_to_rc(psq)
        d = abs(pr - r) + abs(pc - c)
        if best is None or d < best_d:
            best = pid
            best_d = d
    return best


def activate_relic(state, piece_id, relic_type):
    piece = state.pieces[piece_id]
    piece.relics_triggered.add(relic_type)

    if relic_type == RELIC_TOK:
        piece.armor = 2 if piece.marko else 1
    elif relic_type == RELIC_MESINA:
        if not piece.marko:
            target_pid = _nearest_opponent(state, _find_square(state, piece_id), piece.owner)
            if target_pid is not None:
                target = state.pieces[target_pid]
                if not target.marko:
                    target.mesina_lock = 3
    elif relic_type == RELIC_TOPUZ:
        piece.topuz = True
    elif relic_type == RELIC_SARAC:
        piece.sarac = True
    elif relic_type == RELIC_TRI:
        piece.kind = KIND_KING

    needed = {RELIC_TRI, RELIC_SARAC, RELIC_TOPUZ, RELIC_MESINA}
    if piece.kind == KIND_KING and needed <= piece.relics_triggered:
        piece.marko = True


def _find_square(state, piece_id):
    for s in range(32):
        if state.board[s] == piece_id:
            return s
    return None


def apply_move(state, move, relic_choice=None):
    ns = state.copy()
    pid = ns.board[move.from_sq]
    piece = ns.pieces[pid]
    owner = piece.owner

    progress = False

    for cap_sq in move.captures:
        cap_pid = ns.board[cap_sq]
        if cap_pid is not None and cap_pid != pid:
            del ns.pieces[cap_pid]
            ns.board[cap_sq] = None
            progress = True

    ns.board[move.from_sq] = None
    ns.board[move.to_sq] = pid

    r, c = sq_to_rc(move.to_sq)
    last_row = 7 if owner == P1 else 0
    if piece.kind == KIND_MAN and r == last_row:
        piece.kind = KIND_KING
        progress = True

    if move.to_sq in BRAZDE and ns.drum:
        choice = relic_choice or "front"
        if choice == "front":
            relic = ns.drum.popleft()
        else:
            relic = ns.drum.pop()
        activate_relic(ns, pid, relic)
        progress = True  

    other = P2 if owner == P1 else P1
    for p in ns.pieces.values():
        if p.owner == other:
            if p.armor > 0:
                p.armor -= 1
            if p.mesina_lock > 0:
                p.mesina_lock -= 1

    if progress:
        ns.no_progress = 0
    else:
        ns.no_progress += 1
    if ns.no_progress >= DRAW_LIMIT:
        ns.winner = "draw"

    ns.current_player = other

    ns.drum.appendleft(RELIC_CYCLE[ns.cycle_idx % len(RELIC_CYCLE)])
    ns.cycle_idx += 1

    if ns.winner is None:
        if not generate_all_moves(ns, ns.current_player):
            ns.winner = owner 

    return ns


def piece_value_score(piece):
    if piece.marko:
        return 4.0
    if piece.kind == KIND_KING:
        return 3.0
    return 1.0


class HistoryNode:
    def __init__(self, state, move=None, parent=None):
        self.state = state
        self.move = move        
        self.parent = parent
        self.children = []

    def add_child(self, state, move):
        node = HistoryNode(state, move, self)
        self.children.append(node)
        return node


def collect_chronological(root):
    out = []

    def visit(node):
        if node.move is not None:
            out.append((node.state, node.move))
        for ch in node.children:
            visit(ch)

    visit(root)
    return out
