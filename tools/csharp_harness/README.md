# C# harness: byte-exact reference vectors

The DGUS editor turns each control into bytes in `GetByte()` (touch) or `GetData()` (display).
`gen_harness.sh` copies those method bodies verbatim from your **local** ILSpy decompile into a small console
program. `harness_main.cs` builds sample controls, and the program writes `tests/vectors/`.
`tests/test_controls_csharp.py` then checks that every OpenDGUS encoder produces exactly the same bytes.

```bash
bash tools/csharp_harness/build.sh     # Windows + .NET Framework csc; needs vendor/decompiled (see vendor/README.md)
```

Only the vectors (bytes) are committed. The generated C# file in `out/` contains DWIN code and is git-ignored.

## Adding control families

To add a control family, create two files:
- `families/<name>.sh` prints more harness classes. It can use the `ext FILE "signature"` helper and `$D` (the
  decompile root) from `gen_harness.sh`.
- `families/<name>.cs` contains `public static class Family_<name> { public static string Run() { ... } }`. It returns
  lines of the form `vector_name HEX`.

`build.sh` compiles every family. Each family's vectors go to `tests/vectors/<name>.txt`.
