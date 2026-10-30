import glob

paths = (sorted(glob.glob("scratch/bridge_pub*/a2u-bridge.dll"))
         + sorted(glob.glob("scratch/bridge_publish*/a2u-bridge.dll"))
         + [r"bridge/OuBridge/bin/Release/net10.0/win-x64/a2u-bridge.dll"])
for p in paths:
    try:
        b = open(p, "rb").read()
        # UTF-16LE strings live in .NET metadata
        u16 = b.decode("utf-16-le", "ignore")
        print("%-58s autopitch=%-5s (utf16)  %-5s (raw)" % (
            p, "export-autopitch" in u16, b"export-autopitch" in b))
    except Exception as e:
        print(p, "ERR", e)
