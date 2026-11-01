# Bug! (PC, 1996) on modern PCs and the Steam Deck

## Why this exists

Bug! was a Christmas present back in 1996, and the first proper 3D platformer I played: great music,
great sound, and it felt really fresh at the time. The Windows 95 version doesn't run on anything
newer: it demands a 256-colour desktop, looks for its CD, and crashes at its first movie. This kit
sorts that out, so it can be played again.

## What this does

Turns **your own** Bug! PC CD into a folder that runs on the Steam Deck (Proton) or on Windows
10/11, with no installer and no registry entries:

- **Copied straight from the CD**: the levels, movies and sound banks in one folder, so no CD is
  needed.
- **Starts full screen at 640x480**: it used to demand a 256-colour desktop no modern PC has, start
  in a window, and pick 320x240 every time.
- **The 3D in the right shape**: the PC port drew its 3D a third too wide (square gems came out as
  wide rectangles). Fixed, with a little more shown at the sides.
- **The movies no longer crash**: the movie player read a VGA hardware port directly, which only
  Windows 95 allowed.
- **DirectDraw through dgVoodoo2**, 4:3 with black bars.
- **CD soundtrack** from OGG files ripped from your disc.
- **Gamepad** set up from the start (A jump, B spit, X zap, Y duck, Start), and the pad skips the
  movies.
- **Smaller fixes**: a half-drawn screen that appeared now and then, a busy wait that kept a CPU core
  at 100%, the mouse pointer over the game, and an exit box that crashed (Esc now quits).

**No game files are in this repository.** Everything from the game comes from your disc when you
run `build.py`.

## What you need

| | |
|---|---|
| The game | The **Bug! PC CD** (Sega, 1996, Windows 95; `WIN95\BUG!.EXE` of 24 June 1996) as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its 10 audio tracks. `build.py` checks the exe and stops on another version. |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases) (tested with v2025.01.16). Keep the zip as downloaded. |

## Build

```
python3 build.py BUGPC.cue --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `Bug/` with `game/` and `bug_launch.sh` (for the Steam Deck), in under a minute. The same
`game/` folder runs on Windows; `--windows` leaves out the launch script. `--out DIR` puts the result
somewhere else. The disc's original exe is kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `Bug/` to the Deck, for example to `/home/deck/Games/Bug/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../Bug/game/BUG!.EXE`. Rename the
   shortcut "Bug!".
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/Bug/bug_launch.sh %command%
   ```
5. Controller layout: the standard **Gamepad** layout. The game reads the left stick but not the
   D-pad; to move with the D-pad too, set it to the arrow keys in Steam's controller settings.

## Play on Windows

Run `game/BUG!.EXE`. An Xbox pad works as on the Deck (left stick to move).

## Controls

| Pad | Does | Keyboard |
|---|---|---|
| Left stick | move | arrows |
| A | jump | Space |
| B | spit | S |
| X | zap | A |
| Y | duck | D |
| Start (Menu) | start; skips a movie | Enter |
| | pause | Pause |
| | quit at once | Esc |

A also skips a movie. Esc skips a movie too, but held it quits, so skip with Enter or the pad.
Options > Controls > Joystick > Configure rebinds the buttons (saved in `game/BUG!.CFG`). F4 switches
between full screen and a window.

## Settings

`game/BUG!.CFG` holds the options and bindings (the game rewrites it). The kit's copy turns the pad
on with the layout above and skips the "Are you using a joystick?" question.

- Resolution: Options > Video Settings > Full Screen Video Modes (8-bit modes up to 640 wide); the
  game forgets it at exit and starts at 640x480 again.
- Speed: Video Settings > Depth (draw distance) and Background.
- Sharp pixels: `Resampling = pointsampled` in `game/dgVoodoo.conf`.
- Music: Ctrl+M or the Audio menu turns it on and off; the volume is in the Audio dialog, or
  `CDDAVolume` in `game/winmm.ini`.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  DirectDraw instead of dgVoodoo.

## Troubleshooting

- *"Please insert the BUG CD"* or *"Bug will only run in a 256 color mode"*: you're running the
  unpatched exe from `_spare/`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=winmm=n,b;...` (no log: the
  launch option is missing `%command%`), and `game/Music/Track02.ogg` must exist.
- *The pad does nothing*: the game only reads it while its window has focus; click the game, or on
  the Deck check the shortcut uses a Gamepad layout.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, patches the exe, rips the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained; also runs on its own. |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 and audio tracks. |
| `config/` | The game's settings with the pad set up, and dgVoodoo2's. |
| `steamdeck/bug_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Realtime Associates** and **Beam Software** made the PC version of Bug!; **Sega** published it.
  Please own the game: this kit needs your disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
