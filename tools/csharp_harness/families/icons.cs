// Icon family sample controls (14.bin types 0x00-0x09). Inputs are mirrored in tests/test_specs_icons.py.
using System; using System.Text;
public static class Family_icons {
  static string Hex(byte[] b){ var sb=new StringBuilder(); foreach(var x in b) sb.Append(x.ToString("X2")); return sb.ToString(); }
  static Cpoint P(int x,int y){ var c=new Cpoint(); c.X=(ushort)x; c.Y=(ushort)y; return c; }
  static string L(string n, ShowBase s){ s.GetData(); return n+" "+Hex(s.Data)+"\n"; }
  public static string Run(){
    var o=new StringBuilder();
    var an=new AnimateShow(); an.Desc_Point=0x9100; an.Var_Point=0x5030; an.Var_Position=P(120,64); an.RestartMode=1; an.V_Stop=0; an.V_Start=1;
    an.Icon_Stop=5; an.Icon_Start=6; an.Icon_End=20; an.Icon_lib=40; an.Mode=0; an.BackMode=2; an.ICONLight=60; an.BackLight=30; an.ShowTime=25; an.ShowMode=1; an.Filter_Set=0x20;
    o.Append(L("animation_icon", an));
    var an2=new AnimateShow(); an2.Desc_Point=0xFFFF; an2.Var_Point=0x5031; an2.Var_Position=P(900,480); an2.Icon_End=3; an2.Icon_lib=23; an2.Mode=1; an2.ShowTime=1;
    o.Append(L("animation_icon_clamp", an2));
    var sl=new SliderShow(); sl.Desc_Point=0xFFFF; sl.Var_Point=0x5040; sl.V_Begin=-50; sl.V_End=300; sl.X_Begin=100; sl.X_End=700; sl.Icon_Id=7; sl.Y=200; sl.X_Adj=12;
    sl.Mode=1; sl.Icon_lib=41; sl.Icon_Mod=1; sl.VP_Mod=2; sl.BackMode=1; sl.ICONLight=100; sl.BackLight=50; sl.Filter_Set=3;
    o.Append(L("slider_display", sl));
    var ar=new ArtTextShow(); ar.Desc_Point=0x9200; ar.Var_Point=0x5011; ar.Var_Position=P(808,188); ar.Icon0=40; ar.Icon_lib=48; ar.Icon_Mod=1; ar.N_Int=2; ar.N_Dot=1;
    ar.VarType=5; ar.TxtAlign=1; ar.isShow0=true; ar.BackMode=2; ar.ICONLight=50; ar.BackLight=25; ar.Filter_Set=0x3F;
    o.Append(L("art_var", ar));
    var ia=new ImageAnimateShow(); ia.Desc_Point=0xFFFF; ia.Pic_Begin=10; ia.Pic_End=0x123; ia.Frame_Time=12; ia.ICL_LIB_ID=33; ia.Pic_End_Exp=0x0204;
    o.Append(L("image_animation", ia));
    var ro=new ICONRotate(); ro.Desc_Point=0x9300; ro.Var_Point=0x5050; ro.ICon_ID=3; ro.ICon_Xc=50; ro.ICon_Yc=60; ro.Xc=400; ro.Yc=240; ro.V_Begain=-100; ro.V_End=1000;
    ro.AL_Begain=0; ro.AL_End=540; ro.VP_Mode=1; ro.Icon_lib=44; ro.Mode=1; ro.Filter_Set=7;
    o.Append(L("icon_rotation", ro));
    var bi=new bitIcon(); bi.Desc_Point=0xFFFF; bi.Var_Point=0x5060; bi.VP_AUX=0x5100; bi.Act_Bit_Set=0x00F0; bi.Display_Mode=3; bi.Move_mode=1; bi.Icon_Mode=1; bi.Icon_lib=45;
    bi.ICON0S=1; bi.ICON0E=4; bi.ICON1S=5; bi.ICON1E=8; bi.Var_Position=P(810,100); bi.DIS_MOV=40; bi.Filter_Set=9;
    o.Append(L("bit_icon", bi));
    var pt=new IconPageTrans(); pt.Desc_Point=0xFFFF; pt.Var_Point=0x5070; pt.Icon_lib=46; pt.Mode=1; pt.Filter_Set=2; pt.Move_Mode=1; pt.ICON_ID=9;
    pt.Var_Position1=P(10,20); pt.Var_Position2=P(410,220);
    o.Append(L("icon_page_trans", pt));
    var vj=new VariableJpeg(); vj.Desc_Point=0x9400; vj.Var_Point=0x5080; vj.Var_Position1=P(30,40); vj.Wide_X=200; vj.Wide_Y=150; vj.ICONLight=200; vj.Mode=1; vj.Filter_Set=4; vj.JpgFormat=1; vj.VPAddr=0x22;
    o.Append(L("icon_overlay", vj));
    var bt=new BatchIconShow(); bt.Desc_Point=0xFFFF; bt.Var_Point=0x5090; bt.Var_Point1=0x5100; bt.Var_Point2=0x5200; bt.Data_Num=16; bt.Icon_Source=1; bt.Icon_lib=47; bt.Icon_ID=12;
    var r=new IconsRect(); r.X=20; r.Y=30; r.Width=300; r.Height=100; bt.DrawRect=r;
    o.Append(L("batch_icon", bt));
    var ml=new MultiLanguage(); ml.Desc_Point=0x9500; ml.Var_Point=0x50A0; ml.Var_Position=P(5,6); ml.V_Min=0; ml.V_Max=3; ml.Icon_Min=10; ml.Icon_Max=13; ml.Icon_lib=49;
    ml.Mode=1; ml.BackMode=1; ml.ICONLight=80; ml.BackLight=20; ml.Filter_Set=1;
    o.Append(L("multi_language", ml));
    return o.ToString();
  }
}
