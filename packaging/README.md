# Desktop packaging

The desktop UI remains dependency-free for normal development. To create a
standalone desktop build, install PyInstaller in a separate environment and run:

```bash
python -m pip install pyinstaller
pyinstaller --clean mahjong_card_reader.spec
```

The result is written to `dist/MahjongCardReader` (or
`dist/MahjongCardReader.exe` on Windows). The spec does not bundle background
artwork. API keys and `.env` files are not bundled.

Before distributing a build, test it on the target operating system, verify the
Tk font rendering, and keep the original Python version available for debugging.
