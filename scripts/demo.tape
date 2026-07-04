Output assets/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1000
Set Height 480
Set Theme "Catppuccin Mocha"
Set Framerate 15
Set TypingSpeed 45ms

Type "dictionary-tui"
Enter
Wait+Screen@5s /Dictionaries/
Sleep 0.8s
Down
Sleep 0.4s
Enter
Wait+Screen@5s /Collapsed/
Sleep 1s
Space
Wait+Screen@3s /Expanded/
Sleep 1.5s
Space
Wait+Screen@3s /Collapsed/
Sleep 0.8s
Type "/xing"
Sleep 1s
Wait+Screen@5s /Search: xing/
Sleep 0.8s
Down
Sleep 0.3s
Enter
Sleep 2s
Escape
Sleep 0.5s
Type "q"
