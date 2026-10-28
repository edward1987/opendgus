# Text / data family (14.bin types 0x12-0x18): stubs + verbatim Id/GetData extraction. Sourced by gen_harness.sh ($D, ext).
# Expression-bodied Ids ("public override ushort Id => N;") are single lines that ext skips, so grep them
# and rewrite to a C# 5 getter (the .NET Framework csc predates "=>" members).
text_idl() { grep -m1 "public override ushort Id =>" "$1" | sed -E 's/=> *([0-9]+);/{ get { return \1; } }/' || true; }
text_cls() {   # text_cls CLASS "stub members"
  echo "public class $1 : ShowBase {"; echo "  $2"
  text_idl $D/BizDraw.ConfigShow/$1.cs
  ext $D/BizDraw.ConfigShow/$1.cs "public override ushort Id"
  ext $D/BizDraw.ConfigShow/$1.cs "public override void GetData()"
  echo "}"
}
text_cls RtcTextShow "public Cpoint Var_Position{get;set;} public ushort Color{get;set;} public byte Lib_Id{get;set;} public byte Modify{get;set;} public byte FontSize{get;set;} public string String_Uint{get;set;}"
text_cls Clock_Dis "public ushort Var_Point{get;set;} public ushort Xc{get;set;} public ushort Yc{get;set;} public ushort Icon_Hour{get;set;} public Cpoint Icon_Hour_Central{get;set;} public ushort Icon_Minute{get;set;} public Cpoint Icon_Minute_Central{get;set;} public ushort Icon_Second{get;set;} public Cpoint Icon_Second_Central{get;set;} public byte Icon_lib{get;set;}"
text_cls TimeDisplay "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort Color{get;set;} public byte Byte_Num{get;set;} public byte BCD{get;set;} public byte Lib_Id{get;set;} public byte FontSize{get;set;} public string String_Code{get;set;}" \
  | sed -e 's/NumberStyles\.HexNumber/System.Globalization.NumberStyles.HexNumber/' \
        -e 's/out var result/out result/' -e 's/int num2;/int num2; ushort result;/'   # C# 5 has no out-var
text_cls ScrTextShow "public ushort Var_Point{get;set;} public byte Rolling_Mode{get;set;} public byte Rolling_Dis{get;set;} public byte Adjust_Mode{get;set;} public byte runControl{get;set;} public ushort Color{get;set;} public Cpoint Text_Start{get;set;} public Cpoint Text_End{get;set;} public byte Font0_Id{get;set;} public byte Font1_Id{get;set;} public byte FontX_Dot{get;set;} public byte FontY_Dot{get;set;} public byte Encode_Mode{get;set;} public byte Hor_Dis{get;set;} public byte Speed_Set{get;set;}"
# Data_Window.GetData calls the native DWINDLL.dll SetData(21, ushort[32], ref Data[0]). The nested Globel class below
# shadows the harness Globel inside Data_Window and is our own transcription of that native routine
# (vendor/re/dwindll_setdata_disasm.txt, 0x100bf445-0x100bf5e1). The caller sets Globel.Target = Data first
# (plain C# cannot index from a "ref byte").
text_cls Data_Window "public short V_Min{get;set;} public short V_Max{get;set;} public ushort Var_Point{get;set;} public Cpoint Var_Center_Position{get;set;} public ushort Step_Adj{get;set;} public byte NUM_I{get;set;} public byte NUM_F{get;set;} public byte NUM_Digit{get;set;} public byte Display_Mode{get;set;} public byte Font0_X_DotS{get;set;} public byte Font0_Y_DotS{get;set;} public ushort Font0_Color{get;set;} public byte Font1_X_DotS{get;set;} public byte Font1_Y_DotS{get;set;} public ushort Font1_Color{get;set;} public byte Lib_Id{get;set;}
  public static class Globel {
    public static byte[] Target;
    public static void SetData(int code, ushort[] w, ref byte d0) {
      byte[] d = Target; if (code != 21) return;
      d[4] = 0; d[5] = 0x0C;
      d[6] = (byte)(w[2] >> 8); d[7] = (byte)w[2];      // VP
      d[8] = (byte)(w[0] >> 8); d[9] = (byte)w[0];      // V_Min
      d[10] = (byte)(w[1] >> 8); d[11] = (byte)w[1];    // V_Max
      d[16] = (byte)(w[3] >> 8); d[17] = (byte)w[3];    // X
      d[18] = (byte)(w[4] >> 8); d[19] = (byte)w[4];    // Y
      d[20] = (byte)(w[5] >> 8); d[21] = (byte)w[5];    // Step
      d[12] = (byte)w[6]; d[13] = (byte)w[7]; d[14] = (byte)w[8]; d[15] = (byte)w[9];
      if (w[11] < w[10] * 2) w[11] = (byte)(w[10] * 2);
      d[22] = (byte)w[10]; d[23] = (byte)w[11];
      d[24] = (byte)(w[12] >> 8); d[25] = (byte)w[12];
      if (w[14] < w[13] * 2) w[14] = (byte)(w[13] * 2);
      d[26] = (byte)w[13]; d[27] = (byte)w[14];
      d[28] = (byte)(w[15] >> 8); d[29] = (byte)w[15];
    }
  }"
text_cls TextShowII "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort Color{get;set;} public Cpoint Text_Start{get;set;} public Cpoint Text_End{get;set;} public ushort Text_Length{get;set;} public ushort Font_ID{get;set;} public byte DisAdjust{get;set;} public ushort FontHeight{get;set;} public byte Display_Mode; public byte Hor_Dis{get;set;} public byte Ver_Dis{get;set;} public byte Align{get;set;}"
text_cls Roller_character "public ushort Var_Point{get;set;} public byte dataType{get;set;} public byte dataLine{get;set;} public byte NUM_I{get;set;} public byte NUM_F{get;set;} public byte charLen{get;set;} public ushort dataGap{get;set;} public ushort VPString{get;set;} public short V_Min{get;set;} public short V_Max{get;set;} public byte Display_0_Mode{get;set;} public byte Display_Add_Mode{get;set;} public byte Display_BK{get;set;} public byte Duiqi_Type{get;set;} public byte Speed_Set{get;set;} public byte Data_changeSpeed{get;set;} public ushort Font_ID{get;set;} public byte Font_Set0{get;set;} public Cpoint Var_Position1{get;set;} public Cpoint Var_Position2{get;set;} public byte Line_Gap0{get;set;} public byte Line_Gap1{get;set;} public byte Line_Gap2{get;set;} public byte Line_Gap3{get;set;} public byte DIM1{get;set;} public byte Line_Height0{get;set;} public byte Font_1{get;set;} public byte Font_2{get;set;} public byte Font_3{get;set;} public byte Font_4{get;set;}"
text_cls GTFShow "public ushort Var_Point{get;set;} public ushort GFT_ID{get;set;} public ushort Font_ID{get;set;} public Cpoint Var_Position{get;set;} public Cpoint Var_Position2{get;set;} public byte HOR_Dis{get;set;} public byte VER_Dis{get;set;} public byte back_set{get;set;} public byte GTF_Reload{get;set;} public byte ico_recover{get;set;} public byte duiqi{get;set;}"
