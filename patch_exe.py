#!/usr/bin/env python3
"""Patch Bug!'s exe in place (the retail disc's WIN95\\BUG!.EXE, 537,088 bytes,
MD5 bd4b0370131c2e33abd89b58da1c6670, "Bug! for Windows" 0.10 24 June 1996).

  patch_exe.py BUG!.EXE      (build.py runs it for you)

Applies every patch not yet applied and reports each; refuses (writes nothing) on unexpected bytes.
docs/TECHNICAL.md has more on each one.

  nocd    0x4113b0 (the CD hunt: drives A: to Z:, first one of type DRIVE_CDROM becomes the "CD root"
          at 0x45af20) returns 1 at once, and the root's default "." becomes ".\\". The root is used
          only for the WIN95\\BUG!.CFG probe and the movie folders VBFMV\\ / VBFMVLO\\, so both now
          resolve in the working directory. The levels come from the folder named in BUG!.INF.
  depth   0x413840 (GetDeviceCaps test: desktop must be palettised, RASTERCAPS & RC_PALETTE, at least
          8 bpp and at most 1024 pixels wide, else "Bug will only run in a 256 color mode" and quit)
          returns 1. It runs after window creation and on every WM_PAINT.
  full    the full-screen flag 0x45c234 starts at 1, so the first DD_Create (0x415e50) takes the
          exclusive path: SetCooperativeLevel 0x53 + SetDisplayMode(w, h, 8) from the 8-bit modes
          of width <= 640 and height >= 240 (320x240 preferred). F4 still toggles back to a window.
          The flag is never read from or written to BUG!.CFG.
  vsync   0x4116d9: the movie player's three loops polling VGA port 0x3DA (in al, dx: wait for vertical
          retrace) before each palette upload (0x416a90) become a jump straight to the upload. Windows 95
          let a Win32 program read that port; NT and Wine raise EXCEPTION_PRIV_INSTRUCTION, which killed
          the game at its first movie (the Realtime Associates logo). The only port access in the exe.
  hires   0x415ce0 / 0x415ce7: the start-up pick of the full-screen mode looks for 640x480 instead of
          320x240 (else it keeps index 0, the smallest). The Video Settings slider still changes it for
          the session; the choice is never saved to BUG!.CFG, so without this every launch was 320x240.
  aspect  the 3D was 4/3 too wide (square gems drawn as wide rectangles; the 2D HUD was fine). The polygon
          clipper (0x404750) builds outcodes against a square frustum, |x| <= 0.75z and |y| <= 0.75z, and
          the projection then spreads both onto the full screen: x * w/2, y * h/2. Fix, keeping the
          vertical view: each vertex's x is multiplied by 0.75 as the clipper stores it (0x404812: the two
          fstp become a call to a 13-byte cave at 0x405c81 in the int3 padding: fmul [0.75], fstp x,
          fstp y, ret), so the side planes sit at |x| <= z and the polygon projection (0x404ebb) gets
          x * 0.75 * w/2. The sprite projection (0x4045d4) takes h/2 (0x4685c4) instead of w/2 (0x4685b8)
          as its x scale: the same 0.75 * w/2 in the 4:3 modes. The view shows a third more at the sides.
  onsize  the WM_SIZE handler's full-screen branch (0x416737) set the 3D view size from the mode table
          with width and height swapped (0x41677b loads the height into 0x4b23c8, 0x41678f the width into
          0x4b23cc; DD_Create at 0x4163b9 has them right). A resize message arriving in full screen
          (timing-dependent) left a 480-wide view on a 640 screen: picture shifted left, right-hand
          strip undrawn, until F4 re-ran DD_Create. The two table offsets are exchanged.
  idle    the main loop (0x41ba20) holds the game at 30 fps by spinning on timeGetTime until 33 ms have
          passed since the frame began (0x41bb41..0x41bb59), with a Sleep(1) only every 64th frame: one
          core flat out all the time (hot Deck, fans on). The wait from 0x41bb3b now sleeps 1 ms at a time
          while under 17 ms have passed, then spins the rest, so pacing stays exact even where Sleep(1)
          lasts a 15.6 ms timer tick (Windows without timeBeginPeriod; 17 + 15.6 < 33). The frame
          counter 0x458e14 still counts (0x41bb2b..0x41bb3a untouched). The moved absolute address
          [0x4a18c0] no longer sits where .reloc points; harmless, the exe always loads at 0x400000.
  cursor  the main window class (BUGWINDOW_CLASS, 0x4153cd) gets no cursor: LoadCursorA(NULL, IDC_ARROW)
          becomes add esp, 8 / xor eax, eax, so hCursor = NULL and the arrow no longer shows over the
          game (Sub Culture's fix). Dialogs (Load, Save, Options) are their own windows and keep theirs.
          Enough under Wine; on Windows a class without a cursor leaves the last shape up (the busy
          "app starting" arrow), hence setcursor.
  setcursor  the main window class's WndProc (0x4153a8) becomes a stub at 0x4113b6, in the CD hunt's body
          that nocd left dead: WM_SETCURSOR with LOWORD(lParam) = HTCLIENT -> SetCursor(NULL) (found
          through GetModuleHandleA("USER32.dll") + GetProcAddress, both imported; the exe imports neither
          SetCursor nor ShowCursor), return TRUE; every other message jumps to the real WndProc 0x414460.
          No cursor over the picture on Windows too; the menu bar (windowed) and dialogs keep the arrow.
  padskip  movies (0x411550) are skipped only by GetAsyncKeyState Esc or Enter (0x41173c). The Enter test
          (0x41174b) becomes a call to 0x413846, in the colour check's body that depth left dead: Enter as
          before, else the game's own pad read 0x412f80 (joyGetPosEx) and a test of the buttons against
          the configured JoyStart | JoyJump masks (0x45b780 | 0x45b770: Menu or A as shipped).
  escquit  Esc (and Game > Exit) send WM_CLOSE; its handler 0x414640 dropped to a window (0x416c10) for an
          "Are you sure you want to Exit?" box, a switch that left the game in a strange state and then
          crashed. 0x414649 jumps straight to PostQuitMessage.
"""
import os, sys

def s(text, size):                     # string patch, NUL-padded to the original's room
    b = text.encode() + b"\0"
    assert len(b) <= size
    return b + b"\0" * (size - len(b))

RET1 = bytes.fromhex("b801000000c3")   # mov eax, 1 / ret

PATCHES = {
    "nocd":  [(0x107b0, bytes.fromhex("558bec83ec0c"), RET1),
              (0x58b20, s(".", 4), s(".\\", 4))],
    "depth": [(0x12c40, bytes.fromhex("558bec83ec08"), RET1)],
    "full":  [(0x59e34, bytes.fromhex("00000000"), bytes.fromhex("01000000"))],
    "hires": [(0x150e0, bytes.fromhex("baf0000000"), bytes.fromhex("bae0010000")),      # mov edx, 480
              (0x150e7, bytes.fromhex("81fb40010000"), bytes.fromhex("81fb80020000"))],  # cmp ebx, 640
    "aspect": [(0x3c12, bytes.fromhex("d95dc0d95dc4"), bytes.fromhex("e86a14000090")),  # call 0x405c81 / nop
               (0x5081, bytes.fromhex("cc" * 13),
                bytes.fromhex("d80d28564500" "d95dc0" "d95dc4" "c3")),   # fmul [0x455628] / fstp x / fstp y / ret
               (0x39d4, bytes.fromhex("d80db8854600"), bytes.fromhex("d80dc4854600"))],  # fmul [h/2]
    "onsize": [(0x15b7b, bytes.fromhex("8b148da4194a00"), bytes.fromhex("8b148da0194a00")),  # edx = mode width
               (0x15b8f, bytes.fromhex("8b88a0194a00"), bytes.fromhex("8b88a4194a00"))],      # ecx = mode height
    "idle":  [(0x1af3b, bytes.fromhex("75046a01ffd7ffd62b05c0184a0083f821730dffd62b05c0184a0083f82172f3"),
               bytes.fromhex("ffd6" "2b05c0184a00" "83f821" "7313" "83f811" "73ee" "6a01" "ffd7" "ebe8" + "90" * 8))],
    "cursor": [(0x147cd, bytes.fromhex("ff1554755200"), bytes.fromhex("83c40831c090"))],
    "setcursor": [(0x107b6, bytes.fromhex("535657b341bf40af4500b9ffffffff2bc0885df4c645f500f2aef7d12bf98bd18bf7b9ffffffff8d7df42bc0f2ae4f8bcac1e902f3a58bca83e103f3a48d45f450ff158073520083f8057409fec380fb5a7eb2eb"),
                   bytes.fromhex("837c240820753366837c241001752b68f5134100ff157073520085c0741c680014410050ff15c473520085c0740c6a00ffd0b801000000c21000e96b3000005553455233322e646c6c00536574437572736f7200")),
                  (0x147a8, bytes.fromhex("c745dc60444100"), bytes.fromhex("c745dcb6134100"))],  # WndProc = stub
    "padskip": [(0x12c46, bytes.fromhex("5356578b750856ff15a47452008bd86a26538b3d54735200ffd76a0c8945f853ffd76a088945fc53ffd78bf85356ff155875520081"), bytes.fromhex("6a0dffd6f6c480752683ec0c54e828f7ffff83c40485c07412a180b745000b0570b7450023042483c40cc383c40cc3b801000000c3")),
                (0x10b4b, bytes.fromhex("6a0dffd6f6c480750a"), bytes.fromhex("e8f620000085c0750a"))],
    "escquit": [(0x13a49, bytes.fromhex("6a00"), bytes.fromhex("eb1e"))],          # jmp 0x414669 PostQuitMessage
    "vsync": [(0x10ad9, bytes.fromhex("bada030000"), bytes.fromhex("eb2c909090"))],   # jmp 0x411707
}

def patch(data, label="BUG!.EXE"):
    """Returns `data` with every patch applied; exits (nothing written) on unexpected bytes."""
    data = bytearray(data)
    if len(data) != 537088: sys.exit(f"{label}: {len(data)} bytes, expected 537088; nothing written")
    for pname, edits in PATCHES.items():
        state = set()
        for off, old, new in edits:
            cur = bytes(data[off:off + len(old)])
            state.add("new" if cur == new else "old" if cur == old else "bad")
        if state == {"new"}: print(f"  {pname}: already applied"); continue
        if state != {"old"}: sys.exit(f"{label}: {pname}: unexpected bytes, not this exe? nothing written")
        for off, old, new in edits: data[off:off + len(new)] = new
        print(f"  {pname}: applied")
    return bytes(data)

def main(path):
    out = patch(open(path, "rb").read(), path)
    open(path, "wb").write(out)

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
