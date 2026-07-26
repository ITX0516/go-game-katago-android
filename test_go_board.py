#!/usr/bin/env python3
import unittest
from go_board import GoBoard, BLACK, WHITE, EMPTY


class TestGoBoard(unittest.TestCase):
    def test_initialization(self):
        board = GoBoard(9)
        self.assertEqual(board.size, 9)
        self.assertEqual(board.current_player, BLACK)
        for i in range(9):
            for j in range(9):
                self.assertEqual(board.get_stone_color(i, j), EMPTY)

    def test_play_move(self):
        board = GoBoard(9)
        success, captured = board.play_move(3, 3)
        self.assertTrue(success)
        self.assertEqual(board.get_stone_color(3, 3), BLACK)
        self.assertEqual(board.current_player, WHITE)

    def test_invalid_move_on_occupied(self):
        board = GoBoard(9)
        board.play_move(3, 3)
        success, _ = board.play_move(3, 3)
        self.assertFalse(success)

    def test_capture(self):
        board = GoBoard(9)
        board.play_move(0, 0)
        board.play_move(0, 1)
        board.play_move(2, 2)
        board.play_move(1, 0)
        self.assertEqual(board.captures[WHITE], 1)
        self.assertEqual(board.get_stone_color(0, 0), EMPTY)
        success, _ = board.play_move(0, 0)
        self.assertFalse(success)

    def test_ko_rule(self):
        board = GoBoard(9)
        board.board[0][2] = BLACK
        board.board[1][1] = BLACK
        board.board[1][3] = BLACK
        board.board[2][2] = BLACK
        board.board[0][1] = WHITE
        board.board[1][0] = WHITE
        board.board[2][1] = WHITE
        board.current_player = WHITE
        board.last_move = None
        board.ko_point = None
        board.move_count = 6
        success, captured = board.play_move(1, 2)
        self.assertTrue(success)
        self.assertEqual(board.captures[WHITE], 1)
        self.assertIsNotNone(board.ko_point)
        self.assertEqual(board.ko_point, (1, 1))
        self.assertFalse(board.is_valid_move(1, 1, BLACK))

    def test_pass(self):
        board = GoBoard(9)
        board.pass_move()
        self.assertEqual(board.current_player, WHITE)
        self.assertEqual(board.passes, 1)
        board.pass_move()
        self.assertTrue(board.game_over)

    def test_undo(self):
        board = GoBoard(9)
        board.play_move(3, 3)
        board.play_move(5, 5)
        self.assertEqual(board.move_count, 2)
        board.undo()
        self.assertEqual(board.move_count, 1)
        self.assertEqual(board.current_player, WHITE)
        self.assertEqual(board.get_stone_color(5, 5), EMPTY)

    def test_gtp_conversion(self):
        coord = GoBoard.gtp_to_coord('D4', 19)
        self.assertEqual(coord, (15, 3))
        gtp = GoBoard.coord_to_gtp(15, 3, 19)
        self.assertEqual(gtp, 'D4')
        coord2 = GoBoard.gtp_to_coord('T19', 19)
        self.assertEqual(coord2, (0, 18))

    def test_territory_count(self):
        board = GoBoard(9)
        for i in range(3):
            for j in range(9):
                board.board[i][j] = BLACK
        for i in range(6, 9):
            for j in range(9):
                board.board[i][j] = WHITE
        territory = board.count_territory()
        self.assertEqual(territory['black_stones'], 27)
        self.assertEqual(territory['white_stones'], 27)

    def test_color_strings(self):
        self.assertEqual(GoBoard.color_to_str(BLACK), 'black')
        self.assertEqual(GoBoard.color_to_str(WHITE), 'white')
        self.assertEqual(GoBoard.str_to_color('b'), BLACK)
        self.assertEqual(GoBoard.str_to_color('W'), WHITE)

    def test_copy(self):
        board = GoBoard(9)
        board.play_move(3, 3)
        board.play_move(5, 5)
        copy = board.copy()
        self.assertEqual(copy.get_stone_color(3, 3), BLACK)
        self.assertEqual(copy.get_stone_color(5, 5), WHITE)
        self.assertEqual(copy.move_count, 2)
        copy.undo()
        self.assertEqual(board.move_count, 2)
        self.assertEqual(copy.move_count, 1)


if __name__ == '__main__':
    unittest.main()
