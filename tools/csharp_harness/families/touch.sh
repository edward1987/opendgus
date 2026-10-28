# Touch family (13.bin): remaining function controls. Sourced by gen_harness.sh (uses $D and ext).
# Only stubs here; every GetByte() body is extracted from the local decompile at build time.
TOUCH_C=$D/BizDraw.ConfigInput
touch_tp() { echo "  public ushort _Tp_Code = $1; public override ushort Tp_Code { get { return _Tp_Code; } set { _Tp_Code = value; } }"; }

cat <<'EOF'
public class IncManager : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte VP_Mode{get;set;} public byte Adj_Mode{get;set;} public byte Key_Mode{get;set;} public byte Return_Mode{get;set;}
  public ushort Adj_Step{get;set;} public short V_Min{get;set;} public short V_Max{get;set;} public byte Key_Delay{get;set;}
EOF
touch_tp 65026; ext $TOUCH_C/IncManager.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class PopMenu : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[48]; public override byte[] TargetBytes { get { return bbt; } }
  public byte Layer_Gama{get;set;} public ushort Var_Point{get;set;} public byte VP_Mode{get;set;} public short Pic_Menu{get;set;}
  public Cpoint Area_Menu_Start{get;set;} public Cpoint Area_Menu_End{get;set;} public ushort Menu_Position_X{get;set;} public ushort Menu_Position_Y{get;set;}
EOF
touch_tp 65025; ext $TOUCH_C/PopMenu.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class DragManager : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte Adj_Mode{get;set;} public Cpoint Adj_Area_Start{get;set;} public Cpoint Adj_Area_End{get;set;}
  public short V_Begin{get;set;} public short V_End{get;set;}
EOF
touch_tp 65027; ext $TOUCH_C/DragManager.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class RtcInput : InputBase {
  public byte ConstCode = 254; byte[] byt = new byte[48]; public override byte[] TargetBytes { get { return byt; } }
  public Cpoint InShowPoint{get;set;} public ushort InShowColor{get;set;} public byte Lib_Id{get;set;} public byte Font_Hor{get;set;} public byte Cusor_Color{get;set;}
  public byte KB_Source{get;set;} public short Pic_KB{get;set;} public Cpoint Area_KB_Start{get;set;} public Cpoint Area_KB_End{get;set;} public Cpoint Area_KB_Positon{get;set;}
EOF
touch_tp 65028; ext $TOUCH_C/RtcInput.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class GBKInput : InputBase {
  public byte ConstCode = 254; byte[] byt = new byte[64]; public override byte[] TargetBytes { get { return byt; } }
  public byte Scan_Return_Mode{get;set;} public ushort VarPoint{get;set;} public byte VP_Len_Max{get;set;} public byte Scan_Mode{get;set;}
  public byte Lib_GBK1{get;set;} public byte Lib_GBK2{get;set;} public byte Scan_Dis{get;set;} public byte PY_Disp_Mode{get;set;}
  public Cpoint Scan_Area_Start{get;set;} public Cpoint Scan_Area_End{get;set;} public Cpoint Scan_Area_Disp{get;set;}
  public ushort Color0{get;set;} public ushort Color1{get;set;} public byte Font_Scale1{get;set;} public byte Font_Scale2{get;set;} public byte Cusor_Color{get;set;}
  public byte KB_Source{get;set;} public short PIC_KB{get;set;} public Cpoint Area_KB_Start{get;set;} public Cpoint Area_KB_End{get;set;} public Cpoint Area_KB_Positon{get;set;}
EOF
touch_tp 65030; ext $TOUCH_C/GBKInput.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class ParamCofig : InputBase {
  public byte ConstByte = 254; public override byte[] TargetBytes { get { return new byte[32]; } }
  public string Data_pack{get;set;} public byte VP_Mode{get;set;}
EOF
touch_tp 65031; ext $TOUCH_C/ParamCofig.cs "public byte[] DataPack_Chk()"; ext $TOUCH_C/ParamCofig.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class Key_DO_Ret : InputBase {
  public byte ConstByte = 254; public override byte[] TargetBytes { get { return new byte[48]; } }
  public byte TP_ON{get;set;} public byte TP_ON_C{get;set;} public byte TP_OFF{get;set;}
  public ushort VP1S{get;set;} public ushort VP1T{get;set;} public byte LEN1{get;set;}
  public ushort VP2S{get;set;} public ushort VP2T{get;set;} public byte LEN2{get;set;}
  public ushort VP3S{get;set;} public ushort VP3T{get;set;} public byte LEN3{get;set;}
EOF
ext $TOUCH_C/Key_DO_Ret.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class Rotateadjust : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[48]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte Data_Format{get;set;} public Cpoint CirclePosition{get;set;}
  public ushort R0{get;set;} public ushort R1{get;set;} public ushort A0{get;set;} public ushort A1{get;set;} public short B_Value{get;set;} public short E_Value{get;set;}
EOF
touch_tp 65033; ext $TOUCH_C/Rotateadjust.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class SwipeAdjust : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte Adj_Mode{get;set;} public byte Step_Dis{get;set;}
EOF
touch_tp 65034; ext $TOUCH_C/SwipeAdjust.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class SwipePage : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public byte Adj_Mode{get;set;} public byte Date_return{get;set;} public byte End_animation{get;set;}
  public short Pic_Pre{get;set;} public short Pic_NextOne{get;set;} public byte Push_Speed_Set{get;set;} public ushort Push_Dis_Set{get;set;}
EOF
touch_tp 65035; ext $TOUCH_C/SwipePage.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class ICONDragManager : InputBase {
  public byte ConstByte = 254; byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte Adj_Mode{get;set;} public ushort TP_Page_ID_ICON{get;set;} public byte Speed_Slide{get;set;}
EOF
touch_tp 65036; ext $TOUCH_C/ICONDragManager.cs "public override byte[] GetByte()"; echo "}"

cat <<'EOF'
public class BitButton : InputBase {
  byte[] bbt = new byte[32]; public override byte[] TargetBytes { get { return bbt; } }
  public ushort Var_Point{get;set;} public byte Bit_Pos{get;set;} public byte Adj_Mode{get;set;}
EOF
touch_tp 64781; ext $TOUCH_C/BitButton.cs "public override byte[] GetByte()"; echo "}"
