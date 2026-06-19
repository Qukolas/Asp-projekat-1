import sys
import time
import pygame

from engine import (
    P1, P2, KIND_KING, BRAZDE, RELIC_NAMES,
    initial_state, sq_to_rc, rc_to_sq,
    generate_all_moves, apply_move,
    HistoryNode, collect_chronological,
)
from ai import find_best_move

CELL = 70
BOARD_PX = CELL * 8
PANEL_W = 320
WIN_W = BOARD_PX + PANEL_W
WIN_H = BOARD_PX + 40

COL_LIGHT = (235, 217, 179)
COL_DARK = (130, 90, 60)
COL_BRAZDA = (90, 130, 70)
COL_HILITE_FROM = (240, 220, 60)
COL_HILITE_DEST = (90, 200, 90)
COL_SELECTABLE = (200, 160, 60)
COL_PANEL_BG = (30, 30, 40)
COL_TEXT = (240, 240, 240)
COL_P1 = (245, 245, 245)
COL_P2 = (40, 40, 40)
COL_P1_RING = (200, 60, 60)
COL_P2_RING = (60, 120, 220)
COL_MARKO = (255, 200, 0)

FONT_NAME = None


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Junacki Megdan")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 20)
        self.font_small = pygame.font.SysFont(FONT_NAME, 16)
        self.font_big = pygame.font.SysFont(FONT_NAME, 30)

        self.state = initial_state()
        self.root = HistoryNode(self.state)
        self.current_node = self.root

        self.selected_sq = None
        self.available = []
        self.selected_moves = []
        self.message = "Beli (Vi) je na potezu."

        self.mode = "play"
        self.pending_move = None

        self.replay_list = []
        self.replay_idx = -1
        self.replay_last_time = 0

        self.human_player = P1
        self.ai_player = P2

        self.btn_undo = pygame.Rect(0, 0, 0, 0)
        self.btn_replay = pygame.Rect(0, 0, 0, 0)
        self.btn_front = pygame.Rect(0, 0, 0, 0)
        self.btn_rear = pygame.Rect(0, 0, 0, 0)

        self._refresh_available()

    def _refresh_available(self):
        self.available = generate_all_moves(self.state, self.state.current_player)
        self.selected_sq = None
        self.selected_moves = []
        if self.state.winner is not None:
            self.mode = "gameover"
            if self.state.winner == "draw":
                self.message = "REMI! (40 poteza bez napretka)"
            elif self.state.winner == P1:
                self.message = "Pobeda Belog (Vas)!"
            else:
                self.message = "Pobeda Crnog (AI)!"

    def draw_board(self):
        for r in range(8):
            for c in range(8):
                sq = rc_to_sq(r, c)
                x = c * CELL
                y = r * CELL
                if sq is None:
                    color = COL_LIGHT
                else:
                    color = COL_DARK
                    if sq in BRAZDE:
                        color = COL_BRAZDA
                pygame.draw.rect(self.screen, color, (x, y, CELL, CELL))

        if self.mode == "play" and self.state.current_player == self.human_player:
            from_squares = set(m.from_sq for m in self.available)
            for sq in from_squares:
                r, c = sq_to_rc(sq)
                rect = (c * CELL, r * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, COL_SELECTABLE, rect, 4)

        if self.selected_sq is not None:
            r, c = sq_to_rc(self.selected_sq)
            pygame.draw.rect(self.screen, COL_HILITE_FROM, (c * CELL, r * CELL, CELL, CELL), 5)
            for i, m in enumerate(self.selected_moves):
                r2, c2 = sq_to_rc(m.to_sq)
                rect = (c2 * CELL, r2 * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, COL_HILITE_DEST, rect, 5)
                num = self.font_big.render(str(i + 1), True, COL_HILITE_DEST)
                self.screen.blit(num, (c2 * CELL + CELL // 2 - 8, r2 * CELL + CELL // 2 - 14))

        for sq in range(32):
            pid = self.state.board[sq]
            if pid is None:
                continue
            piece = self.state.pieces[pid]
            r, c = sq_to_rc(sq)
            cx = c * CELL + CELL // 2
            cy = r * CELL + CELL // 2
            base_col = COL_P1 if piece.owner == P1 else COL_P2
            ring_col = COL_P1_RING if piece.owner == P1 else COL_P2_RING
            pygame.draw.circle(self.screen, base_col, (cx, cy), CELL // 2 - 8)
            pygame.draw.circle(self.screen, ring_col, (cx, cy), CELL // 2 - 8, 3)
            if piece.kind == KIND_KING:
                pygame.draw.circle(self.screen, ring_col, (cx, cy), CELL // 4)
            if piece.marko:
                pygame.draw.circle(self.screen, COL_MARKO, (cx, cy), CELL // 6)
            tags = []
            if piece.armor > 0:
                tags.append("O")
            if piece.topuz:
                tags.append("T")
            if piece.sarac:
                tags.append("S")
            if piece.mesina_lock > 0:
                tags.append("X")
            if tags:
                txt = self.font_small.render("".join(tags), True, (200, 30, 30))
                self.screen.blit(txt, (c * CELL + 4, r * CELL + 4))

    def draw_panel(self):
        panel_rect = (BOARD_PX, 0, PANEL_W, WIN_H)
        pygame.draw.rect(self.screen, COL_PANEL_BG, panel_rect)
        x = BOARD_PX + 14
        y = 16

        title = self.font_big.render("Junacki Megdan", True, COL_TEXT)
        self.screen.blit(title, (x, y))
        y += 44

        turn_txt = "Beli (Vi)" if self.state.current_player == P1 else "Crni (AI)"
        t = self.font.render(f"Na potezu: {turn_txt}", True, COL_TEXT)
        self.screen.blit(t, (x, y))
        y += 30

        np_txt = self.font.render(
            f"Bez napretka: {self.state.no_progress}/40", True, COL_TEXT)
        self.screen.blit(np_txt, (x, y))
        y += 34

        drum_title = self.font.render("Carev drum (front -> rear):", True, COL_TEXT)
        self.screen.blit(drum_title, (x, y))
        y += 26
        for i, relic in enumerate(self.state.drum):
            tag = "FRONT" if i == 0 else ("REAR" if i == len(self.state.drum) - 1 else "")
            line = self.font_small.render(f"{i+1}. {RELIC_NAMES[relic]} {tag}", True, COL_TEXT)
            self.screen.blit(line, (x, y))
            y += 20
        y += 14

        msg_lines = self._wrap(self.message, 38)
        for line in msg_lines:
            mtxt = self.font.render(line, True, (255, 255, 100))
            self.screen.blit(mtxt, (x, y))
            y += 24
        y += 10

        legend = [
            "Legenda oznaka na figuri:",
            "O = Oklop (Tok od celika)",
            "T = Topuz (hibridni udarac)",
            "S = Sarac (skok preko sopst.)",
            "X = blokiran skok (Mesina)",
            "zlatna tacka = Marko Kraljevic",
        ]
        for line in legend:
            ltxt = self.font_small.render(line, True, (180, 180, 180))
            self.screen.blit(ltxt, (x, y))
            y += 18
        y += 16

        self.btn_undo = pygame.Rect(x, y, 130, 36)
        self.btn_replay = pygame.Rect(x + 150, y, 130, 36)
        mx, my = pygame.mouse.get_pos()
        undo_col = (110, 110, 150) if self.btn_undo.collidepoint(mx, my) else (70, 70, 90)
        replay_col = (110, 110, 150) if self.btn_replay.collidepoint(mx, my) else (70, 70, 90)
        pygame.draw.rect(self.screen, undo_col, self.btn_undo)
        pygame.draw.rect(self.screen, replay_col, self.btn_replay)
        self.screen.blit(self.font.render("Undo", True, COL_TEXT), (self.btn_undo.x + 35, self.btn_undo.y + 6))
        self.screen.blit(self.font.render("Replay", True, COL_TEXT), (self.btn_replay.x + 28, self.btn_replay.y + 6))
        y += 50

        if self.mode == "choose_relic":
            self.btn_front = pygame.Rect(x, y, 280, 36)
            self.btn_rear = pygame.Rect(x, y + 44, 280, 36)
            front_relic = self.state.drum[0]
            rear_relic = self.state.drum[-1]
            pygame.draw.rect(self.screen, (90, 130, 70), self.btn_front)
            pygame.draw.rect(self.screen, (90, 130, 70), self.btn_rear)
            self.screen.blit(self.font_small.render(
                f"FRONT: {RELIC_NAMES[front_relic]}", True, COL_TEXT), (self.btn_front.x + 8, self.btn_front.y + 8))
            self.screen.blit(self.font_small.render(
                f"REAR: {RELIC_NAMES[rear_relic]}", True, COL_TEXT), (self.btn_rear.x + 8, self.btn_rear.y + 8))
            y += 100

        if self.mode == "gameover":
            over = self.font_big.render("KRAJ IGRE", True, (255, 80, 80))
            self.screen.blit(over, (x, y))

    def _wrap(self, text, width):
        words = text.split(" ")
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        return lines

    def make_move(self, move, relic_choice=None):
        if move.to_sq in BRAZDE and relic_choice is None:
            self.pending_move = move
            self.mode = "choose_relic"
            self.message = "Figura je stigla na Brazdu! Izaberite relikviju."
            return
        ns = apply_move(self.state, move, relic_choice=relic_choice)
        self.state = ns
        self.current_node = self.current_node.add_child(ns, move)
        self.pending_move = None
        self.mode = "play"
        if self.state.winner is None:
            who = "Vi" if self.state.current_player == self.human_player else "AI"
            self.message = f"Potez odigran. Na potezu: {who}."
        self._refresh_available()

    def handle_board_click(self, mx, my):
        if self.state.current_player != self.human_player or self.mode != "play":
            return
        c = mx // CELL
        r = my // CELL
        sq = rc_to_sq(r, c)
        if sq is None:
            return

        if self.selected_sq is not None:
            for m in self.selected_moves:
                if m.to_sq == sq:
                    self.make_move(m)
                    return

        from_squares = set(m.from_sq for m in self.available)
        if sq in from_squares:
            self.selected_sq = sq
            self.selected_moves = [m for m in self.available if m.from_sq == sq]
        else:
            self.selected_sq = None
            self.selected_moves = []

    def handle_number_key(self, n):
        if self.mode != "play" or self.state.current_player != self.human_player:
            return
        if self.selected_sq is None:
            return
        idx = n - 1
        if 0 <= idx < len(self.selected_moves):
            self.make_move(self.selected_moves[idx])

    def handle_relic_choice(self, choice):
        if self.pending_move is None:
            return
        self.make_move(self.pending_move, relic_choice=choice)

    def do_undo(self):
        if self.mode not in ("play", "gameover"):
            return
        steps = 2 if self.state.current_player == self.human_player else 1
        moved = False
        for _ in range(steps):
            if self.current_node.parent is not None:
                self.current_node = self.current_node.parent
                moved = True
            else:
                break
        if moved:
            self.state = self.current_node.state
            self.mode = "play"
            self.message = "Potez ponisten (Undo)."
            self._refresh_available()

    def start_replay(self):
        path = []
        node = self.current_node
        while node.parent is not None:
            path.append((node.state, node.move))
            node = node.parent
        path.reverse()
        self.replay_list = path
        if not self.replay_list:
            return
        self.replay_idx = 0
        self.mode = "replay"
        self.replay_last_time = time.time()
        self.message = "Reprodukcija partije u toku..."

    def update_replay(self):
        if self.replay_idx < 0:
            return
        now = time.time()
        if now - self.replay_last_time >= 1.0:
            state, move = self.replay_list[self.replay_idx]
            self.state = state
            self.replay_idx += 1
            self.replay_last_time = now
            if self.replay_idx >= len(self.replay_list):
                self.replay_idx = -1
                self.state = self.current_node.state
                self.mode = "gameover" if self.current_node.state.winner is not None else "play"
                self.message = "Reprodukcija zavrsena."
                self._refresh_available()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if self.mode == "choose_relic":
                        if self.btn_front.collidepoint(mx, my):
                            self.handle_relic_choice("front")
                        elif self.btn_rear.collidepoint(mx, my):
                            self.handle_relic_choice("rear")
                        continue
                    if self.btn_undo.collidepoint(mx, my):
                        self.do_undo()
                        continue
                    if self.btn_replay.collidepoint(mx, my):
                        self.start_replay()
                        continue
                    if mx < BOARD_PX and self.mode == "play":
                        self.handle_board_click(mx, my)
                elif event.type == pygame.KEYDOWN:
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        self.handle_number_key(event.key - pygame.K_0)

            if self.mode == "replay":
                self.update_replay()
            elif self.mode == "play" and self.state.current_player == self.ai_player and self.state.winner is None:
                self.message = "AI razmislja..."
                self.draw_all()
                pygame.display.flip()
                move = find_best_move(self.state, time_limit=3.0)
                if move is not None:
                    self.make_move(move, relic_choice="front")
                else:
                    self.state.winner = self.human_player
                    self._refresh_available()

            self.draw_all()
            pygame.display.flip()
            self.clock.tick(30)

        pygame.quit()
        sys.exit()

    def draw_all(self):
        self.screen.fill((0, 0, 0))
        self.draw_board()
        self.draw_panel()


if __name__ == "__main__":
    App().run()
