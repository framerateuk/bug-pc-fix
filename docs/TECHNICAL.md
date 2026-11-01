# How it works

Notes on the PC release of Bug! (Sega; Realtime Associates / Beam Software, 1996), `WIN95\BUG!.EXE`
537,088 bytes, "Bug! for Windows" 0.10 of 24 June 1996, MD5 `bd4b0370131c2e33abd89b58da1c6670`.
Addresses are virtual addresses in that exe. `patch_exe.py`'s header describes each patch in detail.

## The disc and the installer

Track 1 is the data track; tracks 2-11 are the music. The retail installer (`SETUP95.EXE`) copied
`WIN95\` to the hard disk and wrote `BUG!.INF` with the CD's path; the game then read the levels and
movies from the disc. `build.py` puts everything in one folder, which is also the working
directory: the levels `Lnn.LVL`, both movie folders (`VBFMV\` high detail, `VBFMVLO\` low), the sound
banks `Wnn.SND` (from `WIN95\`), `WIN95\BUG!.CFG` (only probed for), the English help file, and
`BUG!.INF` holding `.`.

## Disc check and file lookup (nocd)

0x4113b0 scans drives A: to Z: and copies the first CD-ROM drive's root into a global at 0x45af20,
initially `"."`; with none, "Could not detect CDROM". 0x411320 opens `<CD root>WIN95\BUG!.CFG`
("Please insert the BUG CD" if missing), at start-up and before every movie. The CD root is used for
nothing else but the movies (`<CD root>VBFMV\MVn.VB`). Levels come from the folder named in
`BUG!.INF` (0x408590); sound banks, `BUG!.CFG` and saves are bare names. `nocd` makes the hunt return
at once with the root `".\"`, so the probe and the movies resolve in the game folder.

## Graphics (depth, full, hires)

A software renderer into 8-bit DirectDraw surfaces, written to run in a window on a 256-colour
desktop with F4 for full screen. 0x413840 (after window creation and on every `WM_PAINT`) demanded a
palettised desktop of at most 1024 pixels wide, else "Bug will only run in a 256 color mode" and
quit; no modern desktop passes. `depth` makes it pass. `full` starts the full-screen flag (0x45c234)
at 1, so `DD_Create` (0x415e50) goes straight to exclusive full screen with an 8-bit mode from the
list (width <= 640, height >= 240). `hires` makes the start-up pick 640x480 instead of 320x240; the
Video Settings slider is never saved, so every start was 320x240 before.

dgVoodoo2 2.79.3's `ddraw.dll`: full screen, `stretched_ar` (4:3 with bars), bilinear, no frame cap
(the game times itself), `DesktopBitDepth = 8` so the moments in a window (while a dialog is open)
see the 8-bit desktop they expect.

## Movies (vsync)

Before each palette upload (0x416a90) the movie player waited for vertical retrace by polling VGA
port 0x3DA with `in al, dx` (0x4116d9, three loops). Windows 95 let a Win32 program read that port;
NT and Wine raise a privileged-instruction exception, which killed the game at its first movie. The
loops now jump straight to the upload. It's the exe's only port access.

## 3D aspect (aspect)

The 3D was drawn a third too wide, while the 2D HUD (its own Saturn-style 320x224 layout) was right.
The polygon clipper (0x404750) tests vertices against a square frustum, `|x| <= 0.75z` and
`|y| <= 0.75z`, and both projections spread that square over the whole screen, `x * w/2` and
`y * h/2`. The patch keeps the vertical view and widens the horizontal one: the clipper multiplies
each vertex's x by 0.75 as it stores it (a 13-byte routine at 0x405c81 in the int3 padding), which
moves the side planes to `|x| <= z`, and the sprite projection (0x4045d4) takes h/2 as its x scale,
the same 0.75 * w/2 in 4:3 modes. 3D and sprites stay aligned.

## Half-drawn screen and busy wait (onsize, idle)

Now and then the 3D sat shifted left with its right-hand strip undrawn. The `WM_SIZE` handler's
full-screen branch (0x416737) read the view size from the mode table with width and height swapped
(0x41677b / 0x41678f); `DD_Create` reads them the right way round. The two offsets are exchanged.

The main loop (0x41ba20) holds 30 fps by spinning on `timeGetTime` for 33 ms, sleeping only every
64th frame. `idle` sleeps 1 ms at a time while under 17 ms have passed and spins the rest, so pacing
stays exact even where `Sleep(1)` lasts a 15.6 ms timer tick.

## Pointer (cursor, setcursor)

The main window class had the arrow cursor. `cursor` gives it none, enough under Wine; on Windows a
window with no class cursor leaves the last shape on screen (the busy arrow), so `setcursor` routes
the window procedure through a stub (0x4113b6, in the dead CD-hunt body) that answers
`WM_SETCURSOR` over the client area with `SetCursor(NULL)`, looked up with `GetProcAddress` since the
exe doesn't import it. Dialogs keep their own arrow.

## Pad and quitting (padskip, escquit)

The game reads joystick 0 with `joyGetPosEx` (X, Y and buttons, no hat), only while its window has
focus; past a quarter of the way is a direction. Movies (0x411550) skipped only on Esc or Enter;
`padskip` adds the configured Start and Jump buttons (a routine at 0x413846, the colour check's dead
body, using the game's own pad read 0x412f80). Esc and Game > Exit sent `WM_CLOSE`, whose handler
(0x414640) dropped to a window for an "Are you sure?" box that left the game in a strange state and
then crashed; `escquit` goes straight to `PostQuitMessage`.

The kit's `BUG!.CFG` has `Joystick = ON` and `JoystickConfig = OFF` (the disc's ON asks "Are you
using a joystick?" at the next start), with the buttons as bit masks: A 1 jump, B 2 spit, X 4 zap,
Y 8 duck, Menu 128 start.

## CD audio

`mciSendCommandA` opens the `cdaudio` device by type id, the standard case ogg-winmm handles. Each
track is ripped from its INDEX 01 to the next track's start.
