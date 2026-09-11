# First-iteration verification

## Update 0.2

Eight tests pass, including generated A4 audio at 440 Hz, silence before onset, pedal/repeated-note behavior, treble clefs on both staves, and agreement between written-score playback events and re-parsed MusicXML. For the saved 126-note user recording, notation rest objects decreased from 125 to 17; both staves now contain substantive note material. This measures a layout change, not musical accuracy. Raw performance MIDI remained byte-for-byte unchanged. The previous score was preserved beside the regenerated score.

The initial audio player played the uploaded source, not generated MIDI. This was a misleading omission in the original interface. The two new output players are generated solely from event data with no access to the uploaded audio file.

Verified locally on Windows / Python 3.12 / CPU.

- Five automated tests passed: chord/voice preservation and barline ties, silent and invalid audio, API input validation and cross-origin rejection, local asset references, and asynchronous failure handling.
- The local server returned HTTP 200 and was opened in Codex.
- Real inference completed on the authors' 40-second `cut_liszt.mp3` example: 507 detected notes, 25 detected pedal events, 147.44 seconds elapsed including initial setup. MusicXML was re-parsed successfully as two parts. MIDI was generated separately from score quantization.
- Sample source: https://github.com/bytedance/piano_transcription/blob/master/resources/cut_liszt.mp3
- Checkpoint checksum verified against Zenodo: `md5:22b961b77c1878239fec963362097045`.
- JavaScript syntax and Python compilation checks passed.

These checks establish that the implementation executes and exports valid files. They do **not** establish note accuracy, pedal accuracy, score readability across repertoire, or the correctness of estimated key/tempo. No browser visual or interaction testing was requested or performed. Optional WebMCP status-tool validation was unavailable in a supported browser context.

The smoke-test files are in `data/check/smoke/`; these generated files and the downloaded research example are excluded from Git. The sample is for local verification, not a bundled product demo or training dataset.
