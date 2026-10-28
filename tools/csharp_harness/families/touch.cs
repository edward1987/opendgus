// Touch family sample controls (13.bin). Inputs are mirrored in tests/test_specs_touch.py.
using System; using System.Text;
public static class Family_touch {
  static Cpoint P(int x, int y) { var c = new Cpoint(); c.X = (ushort)x; c.Y = (ushort)y; return c; }
  static StringBuilder o;
  static void Add(string name, InputBase c) { var sb = new StringBuilder(); foreach (var x in c.GetByte()) sb.Append(x.ToString("X2")); o.Append(name + " " + sb + "\n"); }
  static void Head(InputBase c, int page, int x1, int y1, int x2, int y2, int next, int on) {
    c.Pic_Id = (short)page; c.AreaStart = P(x1, y1); c.AreaEnd = P(x2, y2); c.Pic_Next = (short)next; c.Pic_On = (short)on;
  }
  public static string Run() {
    o = new StringBuilder();

    var inc = new IncManager(); Head(inc, 2, 10, 20, 60, 70, -1, 3);
    inc.Var_Point = 0x5010; inc.VP_Mode = 0x13; inc.Adj_Mode = 1; inc.Return_Mode = 1; inc.Adj_Step = 5; inc.V_Min = -10; inc.V_Max = 300; inc.Key_Mode = 0; inc.Key_Delay = 7;
    Add("inc_adjust", inc);
    var inc2 = new IncManager(); Head(inc2, 0x123, 0, 0, 800, 480, 4, -1); inc2._Tp_Code = 64770;
    inc2.Var_Point = 0x1000; inc2.Adj_Mode = 0; inc2.Adj_Step = 1; inc2.V_Min = 0; inc2.V_Max = 1; inc2.Key_Mode = 1;
    Add("inc_adjust_fd", inc2);

    var pm = new PopMenu(); Head(pm, 1, 100, 100, 200, 140, -1, -1);
    pm.Var_Point = 0x5100; pm.VP_Mode = 2; pm.Pic_Menu = 12; pm.Area_Menu_Start = P(100, 50); pm.Area_Menu_End = P(900, 500);
    pm.Menu_Position_X = 300; pm.Menu_Position_Y = 600; pm.Layer_Gama = 40;
    Add("popup_menu", pm);
    var pm2 = new PopMenu(); Head(pm2, 5, 1, 2, 3, 4, 6, 7); pm2._Tp_Code = 64769;
    pm2.Var_Point = 0x2000; pm2.VP_Mode = 0x1F; pm2.Pic_Menu = 0x105; pm2.Area_Menu_Start = P(10, 20); pm2.Area_Menu_End = P(300, 200);
    pm2.Menu_Position_X = 799; pm2.Menu_Position_Y = 10; pm2.Layer_Gama = 100;
    Add("popup_menu_fd", pm2);

    var dh = new DragManager(); Head(dh, 3, 0, 0, 1, 1, -1, -1);
    dh.Var_Point = 0x5200; dh.Adj_Mode = 0x10; dh.Adj_Area_Start = P(20, 100); dh.Adj_Area_End = P(780, 140); dh.V_Begin = -50; dh.V_End = 1000;
    Add("drag_adjust_h", dh);
    var dv = new DragManager(); Head(dv, 3, 0, 0, 1, 1, 2, 9);
    dv.Var_Point = 0x5202; dv.Adj_Mode = 0x21; dv.Adj_Area_Start = P(400, 10); dv.Adj_Area_End = P(440, 470); dv.V_Begin = 100; dv.V_End = 0;
    Add("drag_adjust_v", dv);
    var dc = new DragManager(); Head(dc, 3, 0, 0, 1, 1, -1, -1); dc._Tp_Code = 64771;
    dc.Var_Point = 0x5204; dc.Adj_Mode = 0x00; dc.Adj_Area_Start = P(100, 300); dc.Adj_Area_End = P(900, 600); dc.V_Begin = 0; dc.V_End = 255;
    Add("drag_adjust_clamped", dc);

    var rtc = new RtcInput(); Head(rtc, 4, 50, 60, 250, 90, -1, 8);
    rtc.InShowPoint = P(100, 200); rtc.InShowColor = 0xF800; rtc.Lib_Id = 3; rtc.Font_Hor = 12; rtc.Cusor_Color = 1; rtc.KB_Source = 1; rtc.Pic_KB = 7;
    rtc.Area_KB_Start = P(0, 10); rtc.Area_KB_End = P(820, 300); rtc.Area_KB_Positon = P(50, 500);
    Add("rtc_input", rtc);

    var gbk = new GBKInput(); Head(gbk, 6, 10, 10, 400, 50, -1, -1);
    gbk.VarPoint = 0x6000; gbk.VP_Len_Max = 30; gbk.Scan_Mode = 1; gbk.Lib_GBK1 = 0; gbk.Lib_GBK2 = 24; gbk.Font_Scale1 = 16; gbk.Font_Scale2 = 24; gbk.Cusor_Color = 1;
    gbk.Color0 = 0x001F; gbk.Color1 = 0xFFE0; gbk.PY_Disp_Mode = 1; gbk.Scan_Return_Mode = 0x55;
    gbk.Scan_Area_Start = P(12, 12); gbk.Scan_Area_End = P(398, 48); gbk.Scan_Area_Disp = P(20, 60); gbk.Scan_Dis = 4; gbk.KB_Source = 1; gbk.PIC_KB = 11;
    gbk.Area_KB_Start = P(0, 200); gbk.Area_KB_End = P(900, 479); gbk.Area_KB_Positon = P(0, 240);
    Add("gbk_input", gbk);

    var pc = new ParamCofig(); Head(pc, 7, 0, 0, 100, 100, -1, -1);
    pc.VP_Mode = 0x5A; pc.Data_pack = "0102A0FF5500000000000000007E";
    Add("param_config", pc);
    var pc2 = new ParamCofig(); Head(pc2, 7, 0, 0, 100, 100, 1, -1); pc2._Tp_Code = 64775;
    pc2.VP_Mode = 1; pc2.Data_pack = "ABC";
    Add("param_config_odd", pc2);

    var kd = new Key_DO_Ret(); Head(kd, 8, 30, 40, 130, 90, 9, -1);
    kd.TP_ON = 0x5A; kd.VP1S = 0x5300; kd.VP1T = 0x5400; kd.LEN1 = 4;
    kd.TP_ON_C = 0x5A; kd.VP2S = 0x5301; kd.VP2T = 0x5401; kd.LEN2 = 2;
    kd.TP_OFF = 0x00; kd.VP3S = 0x5302; kd.VP3T = 0x5402; kd.LEN3 = 1;
    Add("sync_return", kd);

    var ro = new Rotateadjust(); Head(ro, 9, 200, 100, 400, 300, -1, -1);
    ro.Var_Point = 0x5500; ro.Data_Format = 2; ro.CirclePosition = P(300, 200); ro.R0 = 40; ro.R1 = 100; ro.A0 = 90; ro.A1 = 630; ro.B_Value = -100; ro.E_Value = 100;
    Add("rotate_adjust", ro);

    var sa = new SwipeAdjust(); Head(sa, 10, 0, 100, 800, 200, -1, -1);
    sa.Var_Point = 0x5600; sa.Adj_Mode = 1; sa.Step_Dis = 20;
    Add("swipe_adjust", sa);

    var sp0 = new SwipePage(); Head(sp0, 11, 0, 50, 800, 470, -1, -1);
    sp0.Pic_Pre = 10; sp0.Pic_NextOne = 12; sp0.Adj_Mode = 0; sp0.Date_return = 1; sp0.Push_Speed_Set = 5; sp0.Push_Dis_Set = 300; sp0.End_animation = 1;
    Add("swipe_page_h", sp0);
    var sp1 = new SwipePage(); Head(sp1, 11, 20, 0, 900, 480, -1, -1); sp1._Tp_Code = 64779;
    sp1.Pic_Pre = 0x101; sp1.Pic_NextOne = 2; sp1.Adj_Mode = 1; sp1.Date_return = 0; sp1.Push_Speed_Set = 10; sp1.Push_Dis_Set = 0x1234; sp1.End_animation = 0;
    Add("swipe_page_v", sp1);

    var ic = new ICONDragManager(); Head(ic, 12, 0, 300, 800, 400, 5, 6);
    ic.Var_Point = 0x5700; ic.Adj_Mode = 1; ic.TP_Page_ID_ICON = 13; ic.Speed_Slide = 3;
    Add("slide_icon_select", ic);

    var bb = new BitButton(); Head(bb, 13, 10, 10, 60, 60, -1, 14);
    bb.Var_Point = 0x5800; bb.Bit_Pos = 15; bb.Adj_Mode = 2;
    Add("bit_button", bb);
    var bb2 = new BitButton(); Head(bb2, 13, 10, 10, 60, 60, -1, -1); bb2._Tp_Code = 65037;
    bb2.Var_Point = 0x5801; bb2.Bit_Pos = 3; bb2.Adj_Mode = 3;
    Add("bit_button_fe", bb2);

    return o.ToString();
  }
}
