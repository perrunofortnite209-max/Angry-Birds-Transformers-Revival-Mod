# XOX2 XML codec

`tools/xox2_codec.py` encodes and decodes individual Exient XOX2 XML containers. It is intended for controlled research on the game's UI resources.

## Usage

Encode a plain UTF-8 XML file:

```bash
python tools/xox2_codec.py settings.xml settings.xox2
```

Decode an XOX2 file to plain XML:

```bash
python tools/xox2_codec.py --decode settings.xox2 settings.xml
```

Run the local round-trip fixtures:

```bash
python tools/xox2_codec.py --self-test
```

The encoder writes the XOX2 header, offset table, NUL-terminated string table, base-115 token stream and native `x` wrapper. Structural whitespace is kept outside token runs. The output is decoded again locally and parsed as XML before the CLI writes it.

## Validation

GitHub Actions runs:
- Python syntax and local encode/decode round-trip fixtures.
- An interoperability check against the independent `abgtool` XOX2 decoder, pinned to commit `7cd02d36d42b58b652fdc98848de08221d1a0469`.

These checks validate the codec format on test XML. They do **not** prove that an edited UI resource loads in Angry Birds Transformers.

## Safety limits

- The tool handles standalone XML containers only.
- It does not extract, rebuild, recompress, or patch PAK archives.
- It does not alter the APK or native libraries.
- Do not replace files inside the game PAK until a separate PAK repacker has been validated and a modified resource has been tested in-game.
