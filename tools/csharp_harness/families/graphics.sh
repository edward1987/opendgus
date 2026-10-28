# Graphics / special family (14.bin types 0x20-0x26, 0x30, 0x31): stubs + verbatim Id/GetData extraction.
# Sourced by gen_harness.sh ($D, ext). Expression-bodied Ids ("=> N;") are single lines that ext skips, so grep them and
# rewrite them to a C# 5 getter. "out var" and NumberStyles are rewritten for the .NET Framework csc (C# 5).
graphics_idl() { grep -m1 "public override ushort Id =>" "$1" | sed -E 's/=> *([0-9]+);/{ get { return \1; } }/' || true; }
graphics_cls() {   # graphics_cls CLASS BASE "stub members"
  echo "public class $1 : $2 {"; echo "  $3"
  graphics_idl $D/BizDraw.ConfigShow/$1.cs
  ext $D/BizDraw.ConfigShow/$1.cs "public override ushort Id"
  ext $D/BizDraw.ConfigShow/$1.cs "public override void GetData()" \
    | sed -E 's/NumberStyles\.HexNumber/System.Globalization.NumberStyles.HexNumber/; s/^(\s*)if \(ushort\.TryParse\((.*), out var result\)\)/\1ushort result; if (ushort.TryParse(\2, out result))/'
  echo "}"
}
# ZoneScrolling / ZoneLightSetting call the native DWINDLL.dll SetData(36/38, ushort[32], ref Data[0]). The nested
# Globel class shadows the harness Globel inside those classes; it forwards Width/Height and routes SetData to
# GraphicsDll, our own transcription of the native routine (vendor/re/dwindll_setdata_disasm.txt 0x100bf5e6-0x100bf74d).
GRAPHICS_DLL='public static class Globel {
    public static byte[] Target;
    public static int Width { get { return global::Globel.Width; } }
    public static int Height { get { return global::Globel.Height; } }
    public static void SetData(int code, ushort[] w, ref byte d0) { GraphicsDll.SetData(code, w, Target); }
  }'
cat <<'EOF'
public class GraphicsShowBaseRect : ShowBase { public int start_x{get;set;} public int start_y{get;set;} public int end_x{get;set;} public int end_y{get;set;} }
public static class GraphicsDll {
  public static void SetData(int code, ushort[] w, byte[] d) {
    if (code == 36) {             // zone scrolling
      d[4] = 0; d[5] = 7;
      d[6] = (byte)(w[2] >> 8); d[7] = (byte)w[2];      // VP
      d[8] = (byte)(w[0] >> 8); d[9] = (byte)w[0];      // Xs
      d[10] = (byte)(w[1] >> 8); d[11] = (byte)w[1];    // Ys
      d[12] = (byte)(w[3] >> 8); d[13] = (byte)w[3];    // Xe
      d[14] = (byte)(w[4] >> 8); d[15] = (byte)w[4];    // Ye
      d[16] = (byte)(w[6] >> 8); d[17] = (byte)w[6];    // Dis_Move
      d[18] = (byte)w[5];                               // Mode_Move (low byte only)
    } else if (code == 38) {      // zone brightness
      d[4] = 0; d[5] = 5;
      d[6] = (byte)(w[2] >> 8); d[7] = (byte)w[2];
      d[8] = (byte)(w[0] >> 8); d[9] = (byte)w[0];
      d[10] = (byte)(w[1] >> 8); d[11] = (byte)w[1];
      d[12] = (byte)(w[3] >> 8); d[13] = (byte)w[3];
      d[14] = (byte)(w[4] >> 8); d[15] = (byte)w[4];
      d[16] = 0; d[17] = 0;                             // w[5] (LightNess) is ignored
    }
  }
}
EOF
graphics_cls ChartShow ShowBase "public Cpoint Chart_Area_Start{get;set;} public Cpoint Chart_Area_End{get;set;} public ushort Y_Central{get;set;} public ushort VD_Central{get;set;} public ushort Color{get;set;} public ushort MUL_Y{get;set;} public byte Move_Dir{get;set;} public byte Display_Mode{get;set;} public byte CHANEL{get;set;} public byte Dis_HOR{get;set;} public byte Pixel_Scale{get;set;} public byte ColorMode{get;set;} public ushort ColorVP{get;set;}"
graphics_cls BaseGraphs ShowBase "public ushort Var_Point{get;set;} public Cpoint Start_xy{get;set;} public Cpoint End_xy{get;set;} public byte Format1{get;set;} public byte Format2{get;set;} public byte Format3{get;set;} public byte Format4{get;set;} public byte Rashed{get;set;}"
graphics_cls ListingShow ShowBase "public ushort Var_Point{get;set;} public ushort Color_Text{get;set;} public ushort Color_Line{get;set;} public Cpoint Text_Start{get;set;} public Cpoint Text_End{get;set;} public byte Font0_Id; public byte Font1_Id; public byte FEncode_Mode; public byte FontX_Dot{get;set;} public byte FontY_Dot{get;set;} public bool Encode_CharSpacing{get;set;} public bool AutoFormat{get;set;} public bool Disborder{get;set;} public byte Tab_X_Num{get;set;} public byte Tab_Y_Num{get;set;} public byte Tab_X_Start{get;set;} public byte Tab_Y_Start{get;set;} public byte Unit_Data_Num{get;set;} public byte Tab_X_Adj_Mod{get;set;} public byte Tab_Y_Adj_Mod{get;set;}"
graphics_cls DW_ProcessBar ShowBase "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public Cpoint End_Position{get;set;} public byte Orientation{get;set;} public ushort BorderColor{get;set;} public ushort ForeColor{get;set;} public ushort BackColor{get;set;} public short V_Min{get;set;} public short V_Max{get;set;} public byte VarType{get;set;} public bool IsShowRate{get;set;} public bool IsShowBorder{get;set;} public bool IsFillBack{get;set;} public ushort VP_RT{get;set;} public string VP_RT_s{get;set;}"
graphics_cls ZoneScrolling ShowBase "public ushort Dis_Move{get;set;} public byte Mode_Move{get;set;} public ushort Var_Point{get;set;} public Cpoint Var_Position1{get;set;} public Cpoint Var_Position2{get;set;}
  $GRAPHICS_DLL"
graphics_cls Two_Dimension ShowBase "public byte Byte_Num{get;set;} public byte Fix_Mode{get;set;} public byte Display_Mode{get;set;} public ushort Bg_color{get;set;} public ushort Code_color{get;set;} public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;}"
graphics_cls ZoneLightSetting ShowBase "public ushort LightNess{get;set;} public ushort Var_Point{get;set;} public Cpoint Var_Position1{get;set;} public Cpoint Var_Position2{get;set;}
  $GRAPHICS_DLL"
graphics_cls AuxiliaryDisplay ShowBase "public byte AUTO_COM_En{get;set;} public string String_Code{get;set;} public ushort Var_Point{get;set;} public Cpoint Var_Position1{get;set;} public Cpoint Var_Position2{get;set;}"
graphics_cls VideoShow GraphicsShowBaseRect "public ushort VP_video{get;set;} public Cpoint ShowPosition{get;set;} public ushort Width{get;set;} public ushort Height{get;set;} public byte FPS_video{get;set;} public byte Type{get;set;} public ushort ICL_id{get;set;} public ushort WAE_id{get;set;}"
graphics_cls CameraShow ShowBase "public byte Camera_ID{get;set;} public Cpoint ShowPosition{get;set;} public ushort Width{get;set;} public ushort Height{get;set;} public byte Light{get;set;} public byte Mirror{get;set;} public byte AdjustMode{get;set;} public byte Light_Set{get;set;} public byte Resolution{get;set;} public ushort VP_Image{get;set;} public byte DisplayScale{get;set;}"
