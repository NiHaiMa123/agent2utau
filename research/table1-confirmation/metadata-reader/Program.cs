// Offline PE metadata/IL reader. Never loads the inspected assembly, resolves
// dependencies, initializes OpenUtau, reads preferences, or executes its methods.
using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

if (args.Length != 2) throw new ArgumentException("usage: MetadataReader <dll> <output.json>");
byte[] file = File.ReadAllBytes(args[0]);
using var pe = new PEReader(new MemoryStream(file));
var md = pe.GetMetadataReader();
string Name(EntityHandle h) {
    switch (h.Kind) {
        case HandleKind.TypeDefinition:
            var t = md.GetTypeDefinition((TypeDefinitionHandle)h);
            var parent = t.GetDeclaringType();
            return parent.IsNil ? md.GetString(t.Namespace) + "." + md.GetString(t.Name)
                : Name(parent) + "+" + md.GetString(t.Name);
        case HandleKind.TypeReference:
            var tr = md.GetTypeReference((TypeReferenceHandle)h);
            return md.GetString(tr.Namespace) + "." + md.GetString(tr.Name);
        case HandleKind.MethodDefinition:
            var m = md.GetMethodDefinition((MethodDefinitionHandle)h);
            return Name(m.GetDeclaringType()) + "::" + md.GetString(m.Name);
        case HandleKind.FieldDefinition:
            var f = md.GetFieldDefinition((FieldDefinitionHandle)h);
            return Name(f.GetDeclaringType()) + "::" + md.GetString(f.Name);
        case HandleKind.MemberReference:
            var mr = md.GetMemberReference((MemberReferenceHandle)h);
            return Name(mr.Parent) + "::" + md.GetString(mr.Name);
        case HandleKind.MethodSpecification:
            return Name(md.GetMethodSpecification((MethodSpecificationHandle)h).Method) + "<spec>";
        case HandleKind.TypeSpecification:
            return "TypeSpec:" + Convert.ToHexString(md.GetBlobBytes(md.GetTypeSpecification((TypeSpecificationHandle)h).Signature));
        default: return h.Kind + ":" + MetadataTokens.GetToken(h).ToString("X8");
    }
}
var opcodes = typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)
    .Where(f => f.FieldType == typeof(OpCode)).Select(f => (OpCode)f.GetValue(null)!)
    .ToDictionary(o => unchecked((ushort)o.Value));
List<object> Decode(MethodDefinition m) {
    var output = new List<object>();
    if (m.RelativeVirtualAddress == 0) return output;
    byte[] b = pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;
    int p = 0;
    int I32() { int v = BitConverter.ToInt32(b, p); p += 4; return v; }
    while (p < b.Length) {
        int start = p;
        ushort key = b[p++];
        if (key == 0xfe) key = (ushort)(0xfe00 | b[p++]);
        if (!opcodes.TryGetValue(key, out var op)) throw new BadImageFormatException($"Unknown IL opcode {key:X}");
        object? operand = null;
        switch (op.OperandType) {
            case OperandType.InlineNone: break;
            case OperandType.ShortInlineI: operand = (sbyte)b[p++]; break;
            case OperandType.ShortInlineVar: operand = b[p++]; break;
            case OperandType.InlineVar: operand = BitConverter.ToUInt16(b, p); p += 2; break;
            case OperandType.InlineI: operand = I32(); break;
            case OperandType.InlineI8: operand = BitConverter.ToInt64(b, p); p += 8; break;
            case OperandType.ShortInlineR: operand = BitConverter.ToSingle(b, p); p += 4; break;
            case OperandType.InlineR: operand = BitConverter.ToDouble(b, p); p += 8; break;
            case OperandType.ShortInlineBrTarget: { int v = (sbyte)b[p++]; operand = p + v; break; }
            case OperandType.InlineBrTarget: { int v = I32(); operand = p + v; break; }
            case OperandType.InlineSwitch: {
                int n = I32(); int end = p + n * 4;
                var targets = new int[n]; for (int i = 0; i < n; i++) targets[i] = end + I32();
                operand = targets; break;
            }
            case OperandType.InlineString: {
                int token = I32(); operand = md.GetUserString(MetadataTokens.UserStringHandle(token & 0xffffff)); break;
            }
            case OperandType.InlineSig: operand = "Signature:" + I32().ToString("X8"); break;
            case OperandType.InlineField:
            case OperandType.InlineMethod:
            case OperandType.InlineType:
            case OperandType.InlineTok: operand = Name(MetadataTokens.EntityHandle(I32())); break;
            default: throw new BadImageFormatException("Unhandled operand " + op.OperandType);
        }
        output.Add(new { offset = start, opcode = op.Name, operand });
    }
    return output;
}
var types = md.TypeDefinitions.Select(h => {
    var t = md.GetTypeDefinition(h);
    string name = Name(h);
    // Complete type/member inventory; IL only for relevant paths, including
    // compiler-generated nested closures and async state machines.
    bool il = new[] { "SignalChain", "PlaybackManager", "Render.RenderEngine", "MusicMath",
        "Ustx.UNote", "Ustx.PitchPointShape", "Ustx.UTrack", "Ustx.UCurve", "Ustx.UProject",
        "Ustx.UWavePart", "Pipeline.PhraseSourceBuilder", "Util.Preferences", "DiffSinger.DiffSingerPitch", "Format.Wave", "DocManager",
        "NAudioOutput", "Views.MainWindow", "ViewModels.TrackHeaderViewModel", "OpenUtau.App.App",
        "OpenUtau.App.Program", "DiffSinger.DsPitch", "DiffSinger.DsVariance", "DiffSinger.DiffSingerRenderer" }.Any(name.Contains);
    return new {
        name,
        fields = t.GetFields().Select(fh => {
            var f = md.GetFieldDefinition(fh);
            var ch = f.GetDefaultValue();
            return new { name = md.GetString(f.Name), attributes = f.Attributes.ToString(),
                constant_type = ch.IsNil ? null : md.GetConstant(ch).TypeCode.ToString(),
                constant_bytes = ch.IsNil ? null : Convert.ToHexString(md.GetBlobBytes(md.GetConstant(ch).Value)) };
        }).ToArray(),
        methods = t.GetMethods().Select(mh => {
            var m = md.GetMethodDefinition(mh);
            return new { name = md.GetString(m.Name), token = MetadataTokens.GetToken(mh).ToString("X8"),
                signature = Convert.ToHexString(md.GetBlobBytes(m.Signature)),
                il = il ? Decode(m) : null };
        }).ToArray()
    };
}).ToArray();
var assembly = md.GetAssemblyDefinition();
File.WriteAllText(args[1], JsonSerializer.Serialize(new {
    schema_version = 1, mode = "offline_PE_metadata_and_IL_no_target_execution",
    assembly = md.GetString(assembly.Name), version = assembly.Version.ToString(),
    mvid = md.GetGuid(md.GetModuleDefinition().Mvid),
    sha256 = Convert.ToHexString(SHA256.HashData(file)).ToLowerInvariant(), types
}, new JsonSerializerOptions { WriteIndented = true,
    NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.AllowNamedFloatingPointLiterals }));
Console.WriteLine($"{md.GetString(assembly.Name)} {assembly.Version}; {types.Length} types; offline only");
