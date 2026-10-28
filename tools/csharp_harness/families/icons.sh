# Icon family (14.bin types 0x00-0x09): stubs + verbatim Id/GetData extraction. Sourced by gen_harness.sh ($D, ext).
# Expression-bodied Ids ("public override ushort Id => N;") are single lines that ext skips, so grep them
# and rewrite to a C# 5 getter (the .NET Framework csc predates "=>" members).
icons_idl() { grep -m1 "public override ushort Id =>" "$1" | sed -E 's/=> *([0-9]+);/{ get { return \1; } }/' || true; }
icons_cls() {   # icons_cls CLASS BASE "stub members"
  echo "public class $1 : $2 {"; echo "  $3"
  icons_idl $D/BizDraw.ConfigShow/$1.cs
  ext $D/BizDraw.ConfigShow/$1.cs "public override ushort Id"
  ext $D/BizDraw.ConfigShow/$1.cs "public override void GetData()"
  echo "}"
}
cat <<'EOF'
public struct IconsRect { public int X; public int Y; public int Width; public int Height; }
public class IconsShowBaseRect : ShowBase { public int start_x{get;set;} public int start_y{get;set;} public int end_x{get;set;} public int end_y{get;set;} public IconsRect DrawRect{get;set;} }
EOF
ICONS_L="public byte Icon_lib{get;set;} public byte Mode{get;set;} public byte BackMode{get;set;} public byte ICONLight{get;set;} public byte BackLight{get;set;} public byte Filter_Set{get;set;}"
icons_cls AnimateShow ShowBase "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort RestartMode{get;set;} public ushort V_Stop{get;set;} public ushort V_Start{get;set;} public ushort Icon_Stop{get;set;} public ushort Icon_Start{get;set;} public ushort Icon_End{get;set;} public byte ShowTime{get;set;} public byte ShowMode{get;set;} $ICONS_L"
icons_cls SliderShow ShowBase "public ushort Var_Point{get;set;} public short V_Begin{get;set;} public short V_End{get;set;} public ushort X_Begin{get;set;} public ushort X_End{get;set;} public ushort Icon_Id{get;set;} public ushort Y{get;set;} public byte X_Adj{get;set;} public byte Icon_Mod{get;set;} public byte VP_Mod{get;set;} $ICONS_L"
icons_cls ArtTextShow ShowBase "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort Icon0{get;set;} public byte Icon_lib{get;set;} public byte Icon_Mod{get;set;} public byte N_Int{get;set;} public byte N_Dot{get;set;} public byte VarType{get;set;} public byte TxtAlign{get;set;} public bool isShow0{get;set;} public byte BackMode{get;set;} public byte ICONLight{get;set;} public byte BackLight{get;set;} public byte Filter_Set{get;set;}"
icons_cls ImageAnimateShow ShowBase "public ushort Pic_Begin{get;set;} public ushort Pic_End{get;set;} public byte Frame_Time{get;set;} public byte ICL_LIB_ID{get;set;} public ushort Pic_End_Exp{get;set;}"
icons_cls ICONRotate ShowBase "public ushort Var_Point{get;set;} public ushort ICon_ID{get;set;} public ushort ICon_Xc{get;set;} public ushort ICon_Yc{get;set;} public ushort Xc{get;set;} public ushort Yc{get;set;} public int V_Begain{get;set;} public int V_End{get;set;} public ushort AL_Begain{get;set;} public ushort AL_End{get;set;} public byte VP_Mode{get;set;} public byte Icon_lib{get;set;} public byte Mode{get;set;} public byte Filter_Set{get;set;}"
icons_cls bitIcon ShowBase "public ushort Var_Point{get;set;} public ushort VP_AUX{get;set;} public ushort Act_Bit_Set{get;set;} public byte Display_Mode{get;set;} public byte Move_mode{get;set;} public byte Icon_Mode{get;set;} public byte Icon_lib{get;set;} public ushort ICON0S{get;set;} public ushort ICON0E{get;set;} public ushort ICON1S{get;set;} public ushort ICON1E{get;set;} public Cpoint Var_Position{get;set;} public ushort DIS_MOV{get;set;} public byte Filter_Set{get;set;}"
icons_cls IconPageTrans ShowBase "public ushort Var_Point{get;set;} public byte Icon_lib{get;set;} public byte Mode{get;set;} public byte Filter_Set{get;set;} public byte Move_Mode{get;set;} public ushort ICON_ID{get;set;} public Cpoint Var_Position1{get;set;} public Cpoint Var_Position2{get;set;}"
icons_cls VariableJpeg ShowBase "public ushort Var_Point{get;set;} public Cpoint Var_Position1{get;set;} public ushort Wide_X{get;set;} public ushort Wide_Y{get;set;} public byte ICONLight{get;set;} public byte Mode{get;set;} public byte Filter_Set{get;set;} public byte JpgFormat{get;set;} public byte VPAddr{get;set;}"
icons_cls BatchIconShow IconsShowBaseRect "public ushort Var_Point{get;set;} public ushort Var_Point1{get;set;} public ushort Var_Point2{get;set;} public ushort Data_Num{get;set;} public byte Icon_Source{get;set;} public byte Icon_lib{get;set;} public ushort Icon_ID{get;set;}"
icons_cls MultiLanguage ShowBase "public ushort Var_Point{get;set;} public Cpoint Var_Position{get;set;} public ushort V_Min{get;set;} public ushort V_Max{get;set;} public ushort Icon_Min{get;set;} public ushort Icon_Max{get;set;} $ICONS_L"
