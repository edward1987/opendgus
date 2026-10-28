D="${DGUS_DECOMPILED:-$(cd "$(dirname "$0")/../.." && pwd)/vendor/decompiled/DwinTerminal}"
ext() { awk -v pat="$2" '!p && index($0, pat) { if (pat ~ / Id$/ && $0 !~ / Id[ \t\r]*$/) next; p=1; depth=0 } p { print; n=gsub(/{/,"{"); m=gsub(/}/,"}"); depth+=n-m; if (depth==0 && n+m>0) exit }' "$1"; }
{
cat <<'EOF'
// Verbatim-transplant harness: GetByte/GetData/Id bodies are extracted mechanically from the ILSpy output.
using System; using System.Collections.Generic; using System.Text;
public struct Cpoint { public ushort X; public ushort Y; }
public static class Globel { public static int Width = 800; public static int Height = 480; }
public class JProperty { public JProperty(string n, object v){} }
public class JObject { public void Add(object o){} }
public class Coords { public int Count; public void Add(object o){Count++;} }
public class JsonTool { static JsonTool i = new JsonTool(); public Coords coords = new Coords(); public static JsonTool getInstance(){return i;} }
public class InputBase {
  public ushort tp_code = 65280;
  public short Pic_Id {get;set;} public bool Keying{get;set;} public byte KeyCode{get;set;}
  public bool IVRing{get;set;} public byte IVRCode{get;set;}
  public Cpoint AreaStart{get;set;} public Cpoint AreaEnd{get;set;}
  public short Pic_Next{get;set;} public short Pic_On{get;set;}
  public virtual ushort Tp_Code { get { return tp_code; } set {} }
  public virtual byte[] TargetBytes { get { return new byte[16]; } }
EOF
ext $D/BizDraw.ConfigInput/InputBase.cs "public virtual byte[] GetByte()"
cat <<'EOF'
}
public class KeyCodeReturn : InputBase {
  public byte ConstByte = 254; public bool BaseTouch{get;set;} public ushort Var_Point{get;set;} public byte VP_Mode{get;set;} public ushort Key_Code{get;set;} public byte Hold_Time{get;set;}
  public ushort _Tp_Code = 65029; public override ushort Tp_Code { get { return _Tp_Code; } set { _Tp_Code = value; } }
  public override byte[] TargetBytes { get { return BaseTouch ? new byte[16] : new byte[32]; } }
EOF
ext $D/BizDraw.ConfigInput/KeyCodeReturn.cs "public override byte[] GetByte()"
cat <<'EOF'
}
public class VarInput : InputBase {
  public byte ConstCode = 254; byte[] byt = new byte[64]; public override byte[] TargetBytes { get { return byt; } }
  public ushort _Tp_Code = 65024; public override ushort Tp_Code { get { return _Tp_Code; } set { _Tp_Code = value; } }
  public ushort VarPoint{get;set;} public byte Var_Type; public byte N_Int{get;set;} public byte N_Dot{get;set;} public Cpoint InShowPoint{get;set;}
  public ushort InShowColor{get;set;} public byte Lib_Id; public byte Font_Hor{get;set;} public byte Cusor_Color{get;set;} public byte Hide_En{get;set;}
  public byte KB_Source{get;set;} public short Pic_KB{get;set;} public Cpoint Area_KB_Start{get;set;} public Cpoint Area_KB_End{get;set;} public Cpoint Area_KB_Positon{get;set;}
  public ushort Limits_En{get;set;} public int V_min{get;set;} public int V_max{get;set;} public byte Return_Set{get;set;} public ushort Return_VP{get;set;} public int Return_DATA{get;set;} public byte Layer_Gama{get;set;}
EOF
ext $D/BizDraw.ConfigInput/VarInput.cs "public override byte[] GetByte()"
cat <<'EOF'
}
public class TextInput : InputBase {
  public byte ConstCode = 254; byte[] byt = new byte[64]; public override byte[] TargetBytes { get { return byt; } }
  public ushort _Tp_Code = 65030; public override ushort Tp_Code { get { return _Tp_Code; } set { _Tp_Code = value; } }
  public ushort VarPoint{get;set;} public byte VP_Len_Max; public byte Scan_Mode{get;set;} public byte Lib_Id; public byte Font_Hor{get;set;} public byte Font_Ver{get;set;}
  public byte Cusor_Color{get;set;} public ushort DisColor{get;set;} public Cpoint Scan_Area_Start{get;set;} public Cpoint Scan_Area_End{get;set;} public byte Scan_Return_Mode{get;set;}
  public byte KB_Source{get;set;} public short PIC_KB{get;set;} public Cpoint Area_KB_Start{get;set;} public Cpoint Area_KB_End{get;set;} public Cpoint Area_KB_Positon{get;set;} public byte DISPLAY_EN{get;set;} public byte Layer_Gama{get;set;}
EOF
ext $D/BizDraw.ConfigInput/TextInput.cs "public override byte[] GetByte()"
cat <<'EOF'
}
public class ShowBase {
  public byte[] Data = new byte[32]; public ushort Desc_Point{get;set;} public bool IsShowOnPopMenu{get;set;}
  public virtual ushort Id { get { return 23040; } }
EOF
ext $D/BizDraw.ConfigShow/ShowBase.cs "public virtual void GetData()"
cat <<'EOF'
}
public class IconShow : ShowBase {
  public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort V_Min{get;set;} public ushort V_Max{get;set;} public ushort Icon_Min{get;set;} public ushort Icon_Max{get;set;}
  public byte Icon_lib{get;set;} public byte Mode{get;set;} public byte BackMode{get;set;} public byte ICONLight{get;set;} public byte BackLight{get;set;} public byte Filter_Set{get;set;} public bool GroupEnable{get;set;}
EOF
ext $D/BizDraw.ConfigShow/IconShow.cs "public override ushort Id"
ext $D/BizDraw.ConfigShow/IconShow.cs "public override void GetData()"
cat <<'EOF'
}
public class DataTextShow : ShowBase {
  public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort Color{get;set;} public byte Lib_Id; public byte FontSize{get;set;}
  public byte Modify{get;set;} public byte zeroDisplay{get;set;} public byte Align{get;set;} public byte N_Int; public byte N_Dot; public byte VarType; public byte V_Len{get;set;} public string String_Uint{get;set;}
EOF
ext $D/BizDraw.ConfigShow/DataTextShow.cs "public override ushort Id"
ext $D/BizDraw.ConfigShow/DataTextShow.cs "public override void GetData()"
cat <<'EOF'
}
public class TextShow : ShowBase {
  public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort Color{get;set;} public Cpoint Text_Start{get;set;} public Cpoint Text_End{get;set;}
  public ushort Text_Length; public byte Font0_Id; public byte Font1_Id; public byte FontX_Dot{get;set;} public byte FontY_Dot{get;set;} public byte Encode_Mode{get;set;}
  public byte duiqi{get;set;} public byte verticalDuiqi{get;set;} public bool IsAdjust{get;set;} public byte Hor_Dis{get;set;} public byte Ver_Dis{get;set;}
EOF
ext $D/BizDraw.ConfigShow/TextShow.cs "public override ushort Id"
ext $D/BizDraw.ConfigShow/TextShow.cs "public override void GetData()"
echo "}"
for fam in "$(dirname "$0")"/families/*.sh; do if [ -e "$fam" ]; then . "$fam"; fi; done
}
