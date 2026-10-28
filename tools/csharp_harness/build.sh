#!/usr/bin/env bash
# Regenerate tests/vectors from the DGUS editor's own C# code.
# Needs: a local ILSpy decompile of DwinTerminal.dll in vendor/decompiled/DwinTerminal (not redistributed)
#        and the .NET Framework C# compiler (Windows).
# The generated harness_classes.cs contains DWIN code, so it stays in out/ (git-ignored).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/out"; mkdir -p "$out"
csc="${CSC:-/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe}"
bash "$here/gen_harness.sh" > "$out/harness_classes.cs"
w() { cygpath -w "$1" 2>/dev/null || echo "$1"; }
"$csc" -nologo -out:"$(w "$out/harness.exe")" "$(w "$out/harness_classes.cs")" "$(w "$here/harness_main.cs")"
"$out/harness.exe" "$(w "$here/../../tests/vectors")"
