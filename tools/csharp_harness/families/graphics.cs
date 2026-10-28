// Graphics / special family sample controls (14.bin types 0x20-0x26, 0x30, 0x31).
// Inputs are mirrored in tests/test_specs_graphics.py.
using System; using System.Text;
public static class Family_graphics {
  static string Hex(byte[] b){ var sb=new StringBuilder(); foreach(var x in b) sb.Append(x.ToString("X2")); return sb.ToString(); }
  static Cpoint P(int x,int y){ var c=new Cpoint(); c.X=(ushort)x; c.Y=(ushort)y; return c; }
  static string L(string n, ShowBase s){ s.GetData(); return n+" "+Hex(s.Data)+"\n"; }
  public static string Run(){
    var o=new StringBuilder();
    var ch=new ChartShow(); ch.Desc_Point=0x9400; ch.Move_Dir=1; ch.Display_Mode=1; ch.ColorMode=0; ch.Chart_Area_Start=P(10,20); ch.Chart_Area_End=P(790,460);
    ch.Y_Central=240; ch.VD_Central=0x8000; ch.Color=0xF800; ch.ColorVP=0x5555; ch.MUL_Y=0x0180; ch.CHANEL=3; ch.Dis_HOR=2; ch.Pixel_Scale=1;
    o.Append(L("curve", ch));
    var ch2=new ChartShow(); ch2.Desc_Point=0xFFFF; ch2.ColorMode=1; ch2.Color=0x1234; ch2.ColorVP=0x5600; ch2.Chart_Area_Start=P(0,0); ch2.Chart_Area_End=P(800,480);
    ch2.Y_Central=100; ch2.MUL_Y=0x0100; ch2.CHANEL=7; ch2.Dis_HOR=1;
    o.Append(L("curve_colorvp_clamp", ch2));
    var bg=new BaseGraphs(); bg.Desc_Point=0xFFFF; bg.Var_Point=0x6000; bg.Start_xy=P(5,6); bg.End_xy=P(400,300); bg.Rashed=90; bg.Format1=4; bg.Format2=2; bg.Format3=6; bg.Format4=3;
    o.Append(L("basic_graphics", bg));
    var bg2=new BaseGraphs(); bg2.Desc_Point=0x9500; bg2.Var_Point=0x6100; bg2.Start_xy=P(0,0); bg2.End_xy=P(1000,480);
    o.Append(L("basic_graphics_clamp", bg2));
    var ls=new ListingShow(); ls.Desc_Point=0xFFFF; ls.Var_Point=0x7000; ls.Tab_X_Num=4; ls.Tab_Y_Num=5; ls.Tab_X_Start=1; ls.Tab_Y_Start=2; ls.Unit_Data_Num=8;
    ls.FEncode_Mode=0xE2; ls.Disborder=true; ls.AutoFormat=false; ls.Encode_CharSpacing=true; ls.Text_Start=P(10,10); ls.Text_End=P(900,470);
    ls.Color_Line=0x8410; ls.Color_Text=0x001F; ls.Font0_Id=1; ls.Font1_Id=2; ls.FontX_Dot=8; ls.FontY_Dot=16; ls.Tab_X_Adj_Mod=3; ls.Tab_Y_Adj_Mod=9;
    o.Append(L("table", ls));
    var pb=new DW_ProcessBar(); pb.Desc_Point=0x9600; pb.Var_Point=0x5100; pb.Var_Position=P(20,400); pb.End_Position=P(620,430); pb.BorderColor=0xFFFF; pb.ForeColor=0x07E0;
    pb.BackColor=0x2104; pb.V_Max=1000; pb.V_Min=-50; pb.IsShowRate=true; pb.IsFillBack=false; pb.IsShowBorder=true; pb.Orientation=1; pb.VarType=5; pb.VP_RT=0x1111; pb.VP_RT_s="5102";
    o.Append(L("progress_bar", pb));
    var pb2=new DW_ProcessBar(); pb2.Desc_Point=0xFFFF; pb2.Var_Point=0x5110; pb2.Var_Position=P(0,0); pb2.End_Position=P(30,200); pb2.V_Max=100; pb2.IsFillBack=true; pb2.IsShowBorder=false; pb2.VP_RT=0x2222;
    o.Append(L("progress_bar_plain", pb2));
    var zs=new ZoneScrolling(); zs.Desc_Point=0xFFFF; zs.Var_Point=0x5200; zs.Var_Position1=P(100,50); zs.Var_Position2=P(900,500); zs.Dis_Move=3; zs.Mode_Move=2;
    ZoneScrolling.Globel.Target=zs.Data; o.Append(L("zone_scroll", zs));
    var zs2=new ZoneScrolling(); zs2.Desc_Point=0x9700; zs2.Var_Point=0x5210; zs2.Var_Position1=P(0,0); zs2.Var_Position2=P(799,100); zs2.Dis_Move=0x0102; zs2.Mode_Move=1;
    ZoneScrolling.Globel.Target=zs2.Data; o.Append(L("zone_scroll_2", zs2));
    var qr=new Two_Dimension(); qr.Desc_Point=0xFFFF; qr.Var_Point=0x5300; qr.Var_Position=P(300,100); qr.Byte_Num=5; qr.Fix_Mode=1; qr.Display_Mode=1; qr.Bg_color=0xFFE0; qr.Code_color=0x001F;
    o.Append(L("qr_code", qr));
    var zl=new ZoneLightSetting(); zl.Desc_Point=0xFFFF; zl.Var_Point=0x5400; zl.Var_Position1=P(10,20); zl.Var_Position2=P(810,470); zl.LightNess=77;
    ZoneLightSetting.Globel.Target=zl.Data; o.Append(L("zone_brightness", zl));
    var ad=new AuxiliaryDisplay(); ad.Desc_Point=0xFFFF; ad.Var_Point=0x5500; ad.AUTO_COM_En=1; ad.Var_Position1=P(10,20); ad.Var_Position2=P(110,60); ad.String_Code="5AA5048301000ab";
    o.Append(L("data_transmit", ad));
    var ad2=new AuxiliaryDisplay(); ad2.Desc_Point=0x9800; ad2.Var_Point=0x5510; ad2.AUTO_COM_En=0; ad2.Var_Position1=P(1,2); ad2.Var_Position2=P(3,4); ad2.String_Code="01ZZ0203040506070809101112FF";
    o.Append(L("data_transmit_full", ad2));
    var vs=new VideoShow(); vs.Desc_Point=0xFFFF; vs.VP_video=0x5600; vs.ShowPosition=P(80,40); vs.Width=640; vs.Height=400; vs.FPS_video=30; vs.Type=0; vs.ICL_id=50; vs.WAE_id=51;
    o.Append(L("video", vs));
    var cm=new CameraShow(); cm.Desc_Point=0xFFFF; cm.VP_Image=0x3000; cm.ShowPosition=P(0,0); cm.Width=640; cm.Height=480; cm.Camera_ID=1; cm.Light=1; cm.Mirror=1; cm.AdjustMode=1; cm.Light_Set=40; cm.Resolution=2; cm.DisplayScale=1;
    o.Append(L("camera", cm));
    var cm2=new CameraShow(); cm2.Desc_Point=0x9900; cm2.VP_Image=0x1000; cm2.ShowPosition=P(10,10); cm2.Width=320; cm2.Height=240; cm2.Mirror=1; cm2.AdjustMode=0; cm2.Light_Set=40;
    o.Append(L("camera_vp_clamp", cm2));
    return o.ToString();
  }
}
