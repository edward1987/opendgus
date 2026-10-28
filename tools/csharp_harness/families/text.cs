// Text / data family sample controls (14.bin types 0x12-0x18). Inputs are mirrored in tests/test_specs_text.py.
using System; using System.Text;
public static class Family_text {
  static string Hex(byte[] b){ var sb=new StringBuilder(); foreach(var x in b) sb.Append(x.ToString("X2")); return sb.ToString(); }
  static Cpoint P(int x,int y){ var c=new Cpoint(); c.X=(ushort)x; c.Y=(ushort)y; return c; }
  static string L(string n, ShowBase s){ s.Data=new byte[32]; if (s is Data_Window) Data_Window.Globel.Target=s.Data; s.GetData(); return n+" "+Hex(s.Data)+"\n"; }
  public static string Run(){
    var o=new StringBuilder();
    var rt=new RtcTextShow(); rt.Desc_Point=0x9300; rt.Var_Position=P(400,20); rt.Color=0xFFE0; rt.Lib_Id=3; rt.Modify=1; rt.FontSize=12; rt.String_Uint="Y-M-D H:Q:S";
    o.Append(L("rtc_text", rt));
    var rt2=new RtcTextShow(); rt2.Desc_Point=0xFFFF; rt2.Var_Position=P(0,0); rt2.Color=0x001F; rt2.Lib_Id=0; rt2.FontSize=8; rt2.String_Uint="20Y-M-D W H:Q:S xyz";
    o.Append(L("rtc_text_long", rt2));
    var ck=new Clock_Dis(); ck.Desc_Point=0xFFFF; ck.Var_Point=0x1234; ck.Xc=400; ck.Yc=240; ck.Icon_Hour=1; ck.Icon_Hour_Central=P(5,60); ck.Icon_Minute=2; ck.Icon_Minute_Central=P(4,90);
    ck.Icon_Second=3; ck.Icon_Second_Central=P(2,110); ck.Icon_lib=42;
    o.Append(L("analog_clock", ck));
    var hx=new TimeDisplay(); hx.Desc_Point=0x9400; hx.Var_Point=0x5060; hx.Var_Position=P(50,60); hx.Color=0xF81F; hx.Byte_Num=6; hx.BCD=1; hx.Lib_Id=0; hx.FontSize=16; hx.String_Code="2D2D203A3A";
    o.Append(L("hex_data", hx));
    var hx2=new TimeDisplay(); hx2.Desc_Point=0xFFFF; hx2.Var_Point=0x5062; hx2.Var_Position=P(1,2); hx2.Color=0x0000; hx2.Byte_Num=0x13; hx2.BCD=0; hx2.Lib_Id=1; hx2.FontSize=8;
    hx2.String_Code="3AZZ2E0102030405060708090A0B0C0D0E0F";
    o.Append(L("hex_data_bad_long", hx2));
    var sc=new ScrTextShow(); sc.Desc_Point=0x9500; sc.Var_Point=0x5100; sc.Rolling_Mode=2; sc.Rolling_Dis=3; sc.Adjust_Mode=2; sc.runControl=4; sc.Color=0x07FF;
    sc.Text_Start=P(10,400); sc.Text_End=P(900,500); sc.Font0_Id=0; sc.Font1_Id=1; sc.FontX_Dot=12; sc.FontY_Dot=24; sc.Encode_Mode=5; sc.Hor_Dis=2; sc.Speed_Set=7;
    o.Append(L("scroll_text", sc));
    var dw=new Data_Window(); dw.Desc_Point=0x9600; dw.Var_Point=0x5200; dw.V_Min=-20; dw.V_Max=120; dw.NUM_I=3; dw.NUM_F=1; dw.NUM_Digit=5; dw.Display_Mode=0x0B;
    dw.Var_Center_Position=P(300,200); dw.Step_Adj=5; dw.Font0_X_DotS=16; dw.Font0_Y_DotS=40; dw.Font0_Color=0xF800; dw.Font1_X_DotS=12; dw.Font1_Y_DotS=10; dw.Font1_Color=0x8410; dw.Lib_Id=24;
    o.Append(L("data_window", dw));
    var dw2=new Data_Window(); dw2.Desc_Point=0xFFFF; dw2.Var_Point=0x5202; dw2.V_Min=0; dw2.V_Max=9; dw2.NUM_I=1; dw2.Display_Mode=4;
    dw2.Var_Center_Position=P(10,20); dw2.Step_Adj=1; dw2.Font0_X_DotS=200; dw2.Font0_Y_DotS=100; dw2.Font0_Color=0xFFFF; dw2.Font1_X_DotS=8; dw2.Font1_Y_DotS=16; dw2.Font1_Color=0x1234; dw2.Lib_Id=0;
    o.Append(L("data_window_font_clamp", dw2));
    var t2=new TextShowII(); t2.Desc_Point=0x9700; t2.Var_Point=0x5300; t2.Var_Position=P(20,30); t2.Color=0x7BEF; t2.Text_Start=P(20,30); t2.Text_End=P(820,90); t2.Text_Length=64;
    t2.Font_ID=0x0102; t2.DisAdjust=1; t2.FontHeight=32; t2.Hor_Dis=1; t2.Ver_Dis=4; t2.Align=2;
    o.Append(L("dgus2_text", t2));
    var t3=new TextShowII(); t3.Desc_Point=0xFFFF; t3.Var_Point=0x5310; t3.Var_Position=P(0,0); t3.Color=0; t3.Text_Start=P(0,0); t3.Text_End=P(100,500); t3.Text_Length=8;
    t3.Font_ID=5; t3.DisAdjust=0; t3.FontHeight=1000; t3.Align=1;
    o.Append(L("dgus2_text_big", t3));
    var ro=new Roller_character(); ro.Desc_Point=0x9800; ro.Var_Point=0x5400; ro.dataType=0; ro.dataLine=5; ro.NUM_I=2; ro.NUM_F=1; ro.dataGap=3; ro.V_Min=-10; ro.V_Max=50;
    ro.Display_0_Mode=1; ro.Display_Add_Mode=1; ro.Display_BK=0; ro.Duiqi_Type=0; ro.Speed_Set=20; ro.Data_changeSpeed=2; ro.Font_ID=7; ro.Font_Set0=5;
    ro.Var_Position1=P(100,100); ro.Var_Position2=P(201,301); ro.Line_Gap0=4; ro.Line_Gap1=5; ro.Line_Gap2=6; ro.Line_Gap3=7; ro.DIM1=0x80; ro.Line_Height0=40;
    ro.Font_1=1; ro.Font_2=2; ro.Font_3=3; ro.Font_4=4;
    o.Append(L("roll_character", ro));
    var rs=new Roller_character(); rs.Desc_Point=0xFFFF; rs.Var_Point=0x5410; rs.dataType=15; rs.dataLine=3; rs.charLen=10; rs.VPString=0x6000; rs.NUM_I=9; rs.NUM_F=9; rs.dataGap=99;
    rs.V_Min=0; rs.V_Max=4; rs.Display_BK=1; rs.Duiqi_Type=2; rs.Speed_Set=63; rs.Data_changeSpeed=1; rs.Font_ID=0x0203; rs.Font_Set0=2;
    rs.Var_Position1=P(10,20); rs.Var_Position2=P(110,80); rs.DIM1=50; rs.Line_Height0=24; rs.Font_1=15; rs.Font_4=9;
    o.Append(L("roll_character_text", rs));
    var rl=new Roller_character(); rl.Desc_Point=0xFFFF; rl.Var_Point=0x5420; rl.dataType=1; rl.dataLine=1; rl.NUM_I=3; rl.Duiqi_Type=1;
    rl.Var_Position1=P(50,60); rl.Var_Position2=P(150,61); rl.V_Max=-1;
    o.Append(L("roll_character_left", rl));
    var gt=new GTFShow(); gt.Desc_Point=0x9900; gt.Var_Point=0x5500; gt.GFT_ID=0x0040; gt.Font_ID=12; gt.Var_Position=P(30,40); gt.Var_Position2=P(330,140);
    gt.HOR_Dis=2; gt.VER_Dis=3; gt.back_set=1; gt.GTF_Reload=1; gt.ico_recover=0; gt.duiqi=2;
    o.Append(L("gtf_text", gt));
    var gl=new GTFShow(); gl.Desc_Point=0xFFFF; gl.Var_Point=0x5502; gl.GFT_ID=1; gl.Font_ID=13; gl.Var_Position=P(5,6); gl.Var_Position2=P(70,80); gl.ico_recover=1; gl.duiqi=0;
    o.Append(L("gtf_text_left", gl));
    return o.ToString();
  }
}
