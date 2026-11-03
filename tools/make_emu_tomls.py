#!/usr/bin/env python3
"""pacman-nx: the emulator's test tomls in out/emu, made from the package's tomls (tools/make_pacman_tomls.py) so they keep
its settings. Each adds the scripted pad, captures every 15 s and what the test needs:
  emu_verify.toml   configs/renut_verify.toml: every verify key on, the pad to gameplay
  emu_attract.toml  the same with no pad input: the game's title and attract loop
  emu_profile.toml  renut_play.toml: no diagnostics, the pad to gameplay, the sampling profiler on
  emu_ab.toml       renut_ab.toml: the in-run A/B, the pad to gameplay
  emu_tour.toml     configs/renut_verify.toml: tools/tour_script.txt (menus, courses, the Visuals skins)
  emu_game.toml     configs/renut_verify.toml: a whole game and its results screens
  emu_abv.toml      configs/renut_verify.toml: the A/B list flipping on 8 s halves, the pad to gameplay
  python tools/make_emu_tomls.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist', 'switch', 'pacman-nx')
OUT = os.path.join(ROOT, 'out', 'emu')
# More A presses than the menus need (they do nothing in a game): a slow start moves where they land.
PAD = 'input_script = "45:START,55:A,65:A,75:A,85:A,95:A,105:A,115:A,125:A,135:A,145:A"\ninput_script_sticks = 155\n'
NO_PAD = 'input_script = ""\ninput_script_sticks = 0\n'
CAPTURES = 'nfsmw_captura_cada_s = 15\nnfsmw_captura_max = 60\n'
TOUR = 'input_script = "' + open(os.path.join(ROOT, 'tools', 'tour_script.txt'), encoding='utf-8').read().strip() + \
       '"\ninput_script_sticks = 227\n'
# A whole game: the 5-minute score attack from 115 s, the results screens after it. The tour's skin changes stay apart: its
# random stick would move the start menu's cursor.
# A slow start moves where the presses land: more A presses than the menus need (they do nothing in a game), and the
# stick only after them, which would otherwise wander the mode list.
GAME = ('input_script = "45:START,55:A,65:A,75:A,85:A,95:A,105:A,115:A,125:A,135:A,145:A,480:A,490:A,500:A,510:A,520:A"\n'
        'input_script_sticks = 155\n')
# The request's check of each enhancement: its A/B target flipping with the verify keys on (0 differences either way). 8 s
# halves over the shipped list: a check of the picture and the counts, not a measurement (that is renut_ab.toml's, on the console).
AB_LIST = next(l for l in open(os.path.join(DIST, 'renut_ab.toml'), encoding='utf-8') if l.startswith('banjo_renut_ab_targets'))
TESTS = {
    'emu_abv.toml': (os.path.join('configs', 'renut_verify.toml'), PAD + CAPTURES + AB_LIST + 'banjo_renut_ab_s = 8\n'),
    'emu_verify.toml': (os.path.join('configs', 'renut_verify.toml'), PAD + CAPTURES),
    'emu_game.toml': (os.path.join('configs', 'renut_verify.toml'), GAME + CAPTURES),
    'emu_attract.toml': (os.path.join('configs', 'renut_verify.toml'), NO_PAD + CAPTURES),
    'emu_tour.toml': (os.path.join('configs', 'renut_verify.toml'), TOUR + CAPTURES),
    # Shipping conditions (no guard, no verify keys), a whole game and its results, the stack sampler on and nothing else.
    'emu_profile.toml': ('renut_play.toml', GAME + CAPTURES + 'switch_profile_stacks = true\n'),
    'emu_ab.toml': ('renut_ab.toml', PAD),
    # The start's "[boot]" line and the main menu's Exit Game, as the user's console run: the toml the SD folder ships.
    'emu_exit.toml': ('renut.toml', 'input_script = "45:START,55:DOWN,58:DOWN,61:DOWN,64:DOWN,67:DOWN,70:A,76:A,82:A,86:UP,88:LEFT,90:A"\n'
                                    'input_script_sticks = 0\nnfsmw_captura_cada_s = 5\nnfsmw_captura_max = 60\n'),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (source, extra) in TESTS.items():
        lines = open(os.path.join(DIST, source), encoding='utf-8').read().split('\n')
        keys = {l.split('=', 1)[0].strip() for l in extra.split('\n') if '=' in l}
        kept = [l for l in lines if not ('=' in l and l.split('=', 1)[0].strip() in keys)]
        # Before the first [table]: a key after one belongs to that table and the game never reads it.
        at = next((i for i, l in enumerate(kept) if l.startswith('[')), len(kept))
        kept[at:at] = ['# tools/make_emu_tomls.py'] + extra.rstrip('\n').split('\n') + ['']
        with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(kept).rstrip('\n') + '\n')
        print(name, 'from', source, 'keys at line', at + 2)


if __name__ == '__main__':
    main()
