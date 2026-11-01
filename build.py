#!/usr/bin/env python3
"""Build a ready-to-run Bug! folder for modern PCs from your own CD.

Usage:
  python3 build.py DISC.cue|DISC.ccd --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip [--out DIR] [--windows]

  DISC          your Bug! PC CD (Sega, 1996, Windows 95) as .cue + .bin or .ccd + .img, with its audio tracks
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm release zip (or folder)
  --out         where to create Bug/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, patch_exe

EXE_MD5 = "bd4b0370131c2e33abd89b58da1c6670"            # WIN95\BUG!.EXE, "Bug! for Windows" 0.10, 24 June 1996
PATCHED_MD5 = "37775dd66a81edce3f83b378e08cc579"


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def rip(tracks, music):
    enc = encoder(); os.makedirs(music, exist_ok=True); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)          # INDEX 01 to the next track's start: lengths match the disc's TOC
            wav = os.path.join(tmp, f"track{t.n:02d}.wav")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, os.path.join(music, f"Track{t.n:02d}.ogg")), check=True); os.remove(wav)
            print(f"  Music/Track{t.n:02d}.ogg  {len(data) / 2352 / 75:6.1f} s"); n += 1
    if n != 10: sys.exit(f"expected 10 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.upper(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk()}
    if "WIN95/BUG!.EXE" not in entries: sys.exit("no WIN95\\BUG!.EXE on this CD: it isn't the Bug! PC disc")
    got = md5(dt.read_file(*entries["WIN95/BUG!.EXE"][2:]))
    if got != EXE_MD5:
        sys.exit(f"this CD's BUG!.EXE is not the 24 June 1996 one the kit was made for (MD5 {got}); "
                 "nothing else is supported yet")

    pkg = os.path.join(os.path.abspath(a.out), "Bug"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    # The disc's layout with the installed files beside it, the root also being the working directory: the levels
    # and both movie folders at the root, the sound banks too, and WIN95\BUG!.CFG (the CD probe's file, never read)
    print("1/5 game files from the CD")
    for key, (p, is_dir, l, s) in entries.items():
        top = key.split("/")[0]
        if is_dir: continue
        if "/" not in key and key.startswith("L") and key.endswith(".LVL") or top in ("VBFMV", "VBFMVLO"):
            dt.copy_file(l, s, os.path.join(game, *p.split("/")))
        elif top == "WIN95" and key[6:7] == "W" and key.endswith(".SND"):
            dt.copy_file(l, s, os.path.join(game, p.split("/")[1]))
    dt.copy_file(*entries["WIN95/BUG!.CFG"][2:], os.path.join(game, "WIN95", "BUG!.CFG"))
    dt.copy_file(*entries["BUGHELPE.HLP"][2:], os.path.join(game, "BUGHELP.HLP"))    # Help > Help Contents (English)
    dt.copy_file(*entries["WIN95/BUG!.EXE"][2:], os.path.join(game, "_spare", "BUG!_retail.exe"))
    with open(os.path.join(game, "BUG!.INF"), "wb") as f: f.write(b".\r\n")     # the level folder: here
    shutil.copyfile(os.path.join(HERE, "config", "BUG!.CFG"), os.path.join(game, "BUG!.CFG"))   # pad on, A/B/X/Y

    print("2/5 exe patches")
    out = patch_exe.patch(dt.read_file(*entries["WIN95/BUG!.EXE"][2:]))
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected BUG!.EXE")
    open(os.path.join(game, "BUG!.EXE"), "wb").write(out)

    print("3/5 soundtrack")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    open(os.path.join(game, "ddraw.dll"), "wb").write(take(a.dgvoodoo, "MS/x86/DDraw.dll"))
    for name in ("winmm.dll", "winmm.ini"):
        open(os.path.join(game, name), "wb").write(take(a.ogg_winmm, name))
    shutil.copyfile(os.path.join(HERE, "config", "dgVoodoo.conf"), os.path.join(game, "dgVoodoo.conf"))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "bug_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "bug_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
