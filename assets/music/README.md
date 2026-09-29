Drop .m4a (AAC, 96kbps) music files in this folder.
List each track in playlist.json as {"file":"song.m4a","title":"Display Title"}; the game plays
them as a shuffled, no-repeat-until-exhausted playlist and shows the title in the now-playing
toast, the pause sheet and the Settings > Music credits list. Plain filename strings still work
(no title shown, falls back to the filename).
dogfight.m4a (not listed in playlist.json) loops during the Red Flag Dogfight arcade mode.
