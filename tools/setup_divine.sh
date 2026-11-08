#!/usr/bin/env bash
# Rebuild the macOS port of LSLib's `divine` (pack/unpack/convert only) into tools/divine/.
# Pinned to a known commit of team-waldo/lslib; re-applies the port edits and verifies them.
# Fails loudly if any edit doesn't apply or the round-trip check fails.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/lslib-src"
OUT="$HERE/divine"
COMMIT="f47f8242144f5ea5a511487cce9ec1f885ea417f"

if [ ! -d "$SRC/.git" ]; then
  git clone https://github.com/team-waldo/lslib.git "$SRC"
fi
git -C "$SRC" fetch --depth 1 origin "$COMMIT" >/dev/null 2>&1 || true
git -C "$SRC" checkout -q --force "$COMMIT"
git -C "$SRC" clean -qfdx

# --- project files: net8.0, drop Windows-only parts (OpenTK, gppg parser generators, Granny, Story, Stats parsers)
cat > "$SRC/LSLib/LSLib.csproj" <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <OutputType>Library</OutputType>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <PlatformTarget>AnyCPU</PlatformTarget>
  </PropertyGroup>
  <ItemGroup>
    <Compile Remove="Granny/**" />
    <Compile Remove="LS/Story/**" />
    <Compile Remove="LS/Stats/**" />
    <Compile Remove="VirtualTextures/**" />
    <Compile Remove="LS/Save/**" />
    <Compile Remove="LS/Mods/**" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="K4os.Compression.LZ4" Version="1.3.6" />
    <PackageReference Include="K4os.Compression.LZ4.Streams" Version="1.3.6" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
  </ItemGroup>
</Project>
EOF
cat > "$SRC/Divine/Divine.csproj" <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <OutputType>Exe</OutputType>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <PlatformTarget>AnyCPU</PlatformTarget>
  </PropertyGroup>
  <ItemGroup>
    <Compile Remove="CLI/CommandLineGR2Processor.cs" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\LSLib\LSLib.csproj" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="CommandLineArgumentsParser" Version="3.0.19" />
  </ItemGroup>
</Project>
EOF

# --- source edits (each must apply exactly once)
python3 -I - "$SRC" <<'PY'
import sys, pathlib
src = pathlib.Path(sys.argv[1])

def edit(rel, old, new):
    p = src / rel
    s = p.read_text(encoding="utf-8-sig")
    n = s.count(old)
    if n != 1:
        sys.exit(f"EDIT FAILED ({n} matches): {rel}: {old[:60]!r}")
    p.write_text(s.replace(old, new), encoding="utf-8")

# unused Story import (Story is excluded from the build)
edit("LSLib/LS/Resources/LSJ/LSJResourceConverter.cs", "using LSLib.LS.Story;\n", "")

# zlib.net (.NET Framework only) -> System.IO.Compression.ZLibStream
edit("LSLib/LS/BinUtils.cs", "using zlib;\n", "")
edit("LSLib/LS/BinUtils.cs",
"""                    using (var stream = new ZInputStream(compressedStream))
                    {
                        byte[] buf = new byte[0x10000];
                        int length = 0;
                        while ((length = stream.read(buf, 0, buf.Length)) > 0)
                        {
                            decompressedStream.Write(buf, 0, length);
                        }

                        return decompressedStream.ToArray();
                    }""",
"""                    using (var stream = new System.IO.Compression.ZLibStream(compressedStream, System.IO.Compression.CompressionMode.Decompress))
                    {
                        stream.CopyTo(decompressedStream);
                        return decompressedStream.ToArray();
                    }""")
edit("LSLib/LS/BinUtils.cs",
"""        int level = zlibConst.Z_DEFAULT_COMPRESSION;
        switch (compressionLevel)
        {
            case CompressionLevel.FastCompression:
                level = zlibConst.Z_BEST_SPEED;
                break;

            case CompressionLevel.DefaultCompression:
                level = zlibConst.Z_DEFAULT_COMPRESSION;
                break;

            case CompressionLevel.MaxCompression:
                level = zlibConst.Z_BEST_COMPRESSION;
                break;
        }

        using var outputStream = new MemoryStream();
        using var compressor = new ZOutputStream(outputStream, level);

        compressor.Write(uncompressed, 0, uncompressed.Length);
        compressor.finish();
        return outputStream.ToArray();""",
"""        var level = compressionLevel switch
        {
            CompressionLevel.FastCompression => System.IO.Compression.CompressionLevel.Fastest,
            CompressionLevel.MaxCompression => System.IO.Compression.CompressionLevel.SmallestSize,
            _ => System.IO.Compression.CompressionLevel.Optimal,
        };

        using var outputStream = new MemoryStream();
        using (var compressor = new System.IO.Compression.ZLibStream(outputStream, level, leaveOpen: true))
        {
            compressor.Write(uncompressed, 0, uncompressed.Length);
        }
        return outputStream.ToArray();""")

# upstream bug: LZ4 frame encoder wrapped around the *source* stream, then read from (write-only)
edit("LSLib/LZ4Wrapper.cs",
"""        using var source = new MemoryStream(data);
        using var encoder = LZ4Stream.Encode(source);
        using var target = new MemoryStream();
        encoder.CopyTo(target);
        return target.ToArray();
    }

    public static byte[] LZ4FrameDecompress""",
"""        using var target = new MemoryStream();
        using (var encoder = LZ4Stream.Encode(target, leaveOpen: true))
        {
            encoder.Write(data, 0, data.Length);
        }
        return target.ToArray();
    }

    public static byte[] LZ4FrameDecompress""")
print("EDITS_OK")
PY

rm -rf "$OUT"
dotnet build "$SRC/Divine/Divine.csproj" -c Release -o "$OUT" -v quiet -nologo
[ -s "$OUT/Divine.dll" ] || { echo "Divine.dll missing"; exit 1; }

# --- verify: zlib pak round trip + LSX->LSF->LSX (exercises the LZ4 frame fix)
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/src/Mods/Smoke"
head -c 200000 /dev/urandom | base64 > "$T/src/Mods/Smoke/data.txt"
dotnet "$OUT/Divine.dll" -g bg3 -a create-package -s "$T/src" -d "$T/smoke.pak" -c zlib >/dev/null
dotnet "$OUT/Divine.dll" -g bg3 -a extract-package -s "$T/smoke.pak" -d "$T/back" >/dev/null
diff -r "$T/src" "$T/back" >/dev/null || { echo "pak round trip FAILED"; exit 1; }
cat > "$T/t.lsx" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<save>
	<version major="4" minor="0" revision="9" build="0" lslib_meta="v1,bswap_guids" />
	<region id="Templates"><node id="Templates"><children>
		<node id="GameObjects"><attribute id="Name" type="LSString" value="SmokeTestTemplate" /></node>
	</children></node></region>
</save>
EOF
dotnet "$OUT/Divine.dll" -g bg3 -a convert-resource -s "$T/t.lsx" -d "$T/t.lsf" >/dev/null
dotnet "$OUT/Divine.dll" -g bg3 -a convert-resource -s "$T/t.lsf" -d "$T/t2.lsx" >/dev/null
grep -q SmokeTestTemplate "$T/t2.lsx" || { echo "LSF round trip FAILED"; exit 1; }
echo "DIVINE_OK $OUT/Divine.dll"
