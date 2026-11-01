#!/bin/bash
# Bug! (Sega / Realtime Associates / Beam Software, PC 1996) Steam Deck / Proton launch wrapper.
#
# Steam > Bug! > Properties > Launch Options:
#   /home/deck/Games/Bug/bug_launch.sh %command%
# Shortcut target: /home/deck/Games/Bug/game/BUG!.EXE, Start In: /home/deck/Games/Bug/game/
#
# BUG!.EXE is patched (patch_exe.py): no CD hunt (the movies and the WIN95\BUG!.CFG probe resolve in
# game/), no 256-colour desktop check, and it starts full screen. Levels come from the folder named in
# game/BUG!.INF ("."). So no fake CD-ROM drive and no registry are needed.
#
# Every launch sets DLL overrides so Wine loads the wrappers sitting beside the exe:
#   winmm.dll   ogg-winmm: CD audio from Music/TrackNN.ogg
#   ddraw.dll   dgVoodoo2 2.79.3: 8-bit DirectDraw -> D3D11 -> DXVK, scaled 4:3 to the screen
#
# RENDERER (set before the script path in Launch Options, default dgvoodoo):
#   dgvoodoo  ddraw from dgVoodoo2
#   wined3d   plain Wine ddraw
#   Example:  RENDERER=wined3d /home/deck/Games/Bug/bug_launch.sh %command%

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/launch.log"
# A file RENDERER beside this script holding e.g. wined3d wins over the default (switch it from Desktop Mode).
[ -z "${RENDERER:-}" ] && [ -s "$HERE/RENDERER" ] && RENDERER="$(tr -d ' \n' < "$HERE/RENDERER")"
RENDERER="${RENDERER:-dgvoodoo}"
log() { echo "[$(date '+%H:%M:%S')] $*" >>"$LOG"; }
: >"$LOG"
log "args: $*"
log "RENDERER=$RENDERER  STEAM_COMPAT_DATA_PATH=${STEAM_COMPAT_DATA_PATH:-unset}"

# Proton appends its own overrides after ours.
OVR="winmm=n,b"
case "$RENDERER" in
  dgvoodoo) OVR="$OVR;ddraw=n,b" ;;
  wined3d)  OVR="$OVR;ddraw=b" ;;
  *)        log "unknown RENDERER '$RENDERER', using dgvoodoo"; OVR="$OVR;ddraw=n,b" ;;
esac
export WINEDLLOVERRIDES="${OVR}${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
log "WINEDLLOVERRIDES=$WINEDLLOVERRIDES"

# Debugging: if a file named PROTON_LOG exists beside this script, Proton writes
# steam-<appid>.log here (crash addresses, exceptions). Create / delete it from Desktop Mode; no launch-option edit.
if [ -e "$HERE/PROTON_LOG" ]; then
  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE"
  log "PROTON_LOG on -> $HERE/steam-*.log"
  # Extra Wine debug channels for that log: a file WINEDEBUG beside this script holding e.g. +ddraw
  if [ -s "$HERE/WINEDEBUG" ]; then
    export WINEDEBUG="+timestamp,+tid,+seh,+loaddll,$(tr -d ' \n' < "$HERE/WINEDEBUG")"
    log "WINEDEBUG=$WINEDEBUG"
  fi
fi

# Frame rate / GPU load overlay (DXVK, on top of dgVoodoo's D3D11): a file DXVK_HUD beside this script
# holding e.g. fps,gpuload. Create / delete it from Desktop Mode.
if [ -s "$HERE/DXVK_HUD" ]; then
  export DXVK_HUD="$(tr -d ' \n' < "$HERE/DXVK_HUD")"
  log "DXVK_HUD=$DXVK_HUD"
fi

for f in 'BUG!.EXE' 'BUG!.INF' 'BUG!.CFG' 'WIN95/BUG!.CFG' L01.LVL W00.SND VBFMV/MV0.VB winmm.dll winmm.ini ddraw.dll dgVoodoo.conf Music/Track02.ogg; do
  [ -e "$HERE/game/$f" ] || log "WARNING: game/$f missing"
done

log "exec: $*"
exec "$@"
