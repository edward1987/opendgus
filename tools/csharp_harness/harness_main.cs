using System; using System.Collections.Generic; using System.IO; using System.Text;
public static class Program {
  static string Hex(byte[] b){ var sb=new StringBuilder(); foreach(var x in b) sb.Append(x.ToString("X2")); return sb.ToString(); }
  static Cpoint P(int x,int y){ var c=new Cpoint(); c.X=(ushort)x; c.Y=(ushort)y; return c; }
  // Transcription of DWINDLL.dll Func02/Func03 (see doc, disassembly at 0x100bf940 / 0x100bfa30)
  static void Func02(int max, byte[] bb){ bb[0]=0x14; bb[1]=0x44; bb[2]=0x47; bb[3]=0x55; bb[4]=0x53; bb[5]=0x5f; bb[6]=0x32; bb[7]=0x10; bb[8]=(byte)(max>>8); bb[9]=(byte)(max&0xff); for(int i=10;i<16;i++) bb[i]=0; }
  static int Func03(int n1, byte b1, byte[] bb){ bb[0]=b1; bb[1]=(byte)(n1>>16); bb[2]=(byte)((n1>>8)&0xff); bb[3]=(byte)(n1&0xff); return b1*32+n1; }
  // Transcription of TDocumentSpace.BuildShowBinFile, nJiami==2 (Project_Custom) path, record part only
  static byte[] Build14(SortedDictionary<int, List<ShowBase>> pages){
    var list=new List<byte>(); byte[] array2=new byte[4092]; ushort num4=0;
    foreach(var kv in pages){ array2[kv.Key]=(byte)kv.Value.Count; if(kv.Key>num4) num4=(ushort)kv.Key; }
    byte[] h=new byte[16]; Func02(num4,h); list.AddRange(h);
    int num8=16384; for(int i=0;i<4092;i++){ byte[] a4=new byte[4]; num8=Func03(num8,array2[i],a4); list.AddRange(a4); }
    for(int p=0;p<=num4;p++){ if(!pages.ContainsKey(p)) continue; byte[] a3=new byte[32*array2[p]]; int j=0;
      foreach(var sb in pages[p]){ sb.GetData(); sb.Data.CopyTo(a3, j*32); j++; } list.AddRange(a3); }
    for(int i=0;i<32;i++) list.Add(0xFF);
    return list.ToArray();
  }
  public static void Main(string[] args){
    var o=new StringBuilder();
    var bt=new KeyCodeReturn(); bt.BaseTouch=true; bt.Pic_Id=3; bt.AreaStart=P(10,20); bt.AreaEnd=P(110,60); bt.Pic_Next=-1; bt.Pic_On=5; bt.Key_Code=0x0031;
    o.AppendLine("basic_touch "+Hex(bt.GetByte()));
    var rk=new KeyCodeReturn(); rk.Pic_Id=1; rk.AreaStart=P(0,0); rk.AreaEnd=P(200,100); rk.Pic_Next=2; rk.Pic_On=-1; rk.Var_Point=0x5000; rk.VP_Mode=0x10; rk.Key_Code=0x5A03; rk.Hold_Time=3;
    o.AppendLine("return_key "+Hex(rk.GetByte()));
    var rk2=new KeyCodeReturn(); rk2.Pic_Id=0x105; rk2.IVRing=true; rk2.IVRCode=3; rk2.AreaStart=P(5,6); rk2.AreaEnd=P(7,8); rk2.Pic_Next=-1; rk2.Pic_On=-1; rk2.Var_Point=0x1234; rk2.Key_Code=1; rk2._Tp_Code=0xFD05;
    o.AppendLine("return_key_fd_ivr "+Hex(rk2.GetByte()));
    var vi=new VarInput(); vi.Pic_Id=4; vi.AreaStart=P(100,100); vi.AreaEnd=P(300,140); vi.Pic_Next=-1; vi.Pic_On=-1; vi.VarPoint=0x5100; vi.Var_Type=1; vi.N_Int=5; vi.N_Dot=2; vi.InShowPoint=P(290,105);
    vi.InShowColor=0xF800; vi.Lib_Id=0; vi.Font_Hor=16; vi.Cusor_Color=1; vi.Hide_En=1; vi.KB_Source=1; vi.Pic_KB=9; vi.Area_KB_Start=P(0,0); vi.Area_KB_End=P(900,272); vi.Area_KB_Positon=P(50,200);
    vi.Limits_En=0xFF; vi.V_min=-100; vi.V_max=100000; vi.Return_Set=0x5A; vi.Return_VP=0x5200; vi.Return_DATA=0x1234; vi.Layer_Gama=50;
    o.AppendLine("var_input "+Hex(vi.GetByte()));
    var ti=new TextInput(); ti.Pic_Id=6; ti.AreaStart=P(10,10); ti.AreaEnd=P(400,50); ti.Pic_Next=-1; ti.Pic_On=-1; ti.VarPoint=0x6000; ti.VP_Len_Max=20; ti.Scan_Mode=1; ti.Lib_Id=0; ti.Font_Hor=8; ti.Font_Ver=16;
    ti.Cusor_Color=1; ti.DisColor=0x001F; ti.Scan_Area_Start=P(12,12); ti.Scan_Area_End=P(800,48); ti.Scan_Return_Mode=0x55; ti.KB_Source=1; ti.PIC_KB=10; ti.Area_KB_Start=P(0,200); ti.Area_KB_End=P(799,479); ti.Area_KB_Positon=P(0,240); ti.DISPLAY_EN=0; ti.Layer_Gama=100;
    o.AppendLine("text_input "+Hex(ti.GetByte()));
    var ic=new IconShow(); ic.Desc_Point=0x9000; ic.Var_Point=0x5012; ic.Var_Position=P(30,40); ic.V_Min=0; ic.V_Max=10; ic.Icon_Min=1; ic.Icon_Max=11; ic.Icon_lib=48; ic.Mode=0; ic.BackMode=1; ic.ICONLight=50; ic.BackLight=100; ic.Filter_Set=0x10; ic.GroupEnable=true;
    ic.GetData(); o.AppendLine("var_icon "+Hex(ic.Data));
    var dt=new DataTextShow(); dt.Desc_Point=0xFFFF; dt.Var_Point=0x5420; dt.Var_Position=P(100,200); dt.Color=0xFFFF; dt.Lib_Id=0; dt.FontSize=16; dt.Modify=1; dt.zeroDisplay=1; dt.Align=1; dt.N_Int=3; dt.N_Dot=1; dt.VarType=5; dt.V_Len=2; dt.String_Uint="mV";
    dt.GetData(); o.AppendLine("data_var "+Hex(dt.Data));
    var tx=new TextShow(); tx.Desc_Point=0x8800; tx.Var_Point=0x5020; tx.Var_Position=P(10,300); tx.Color=0x07E0; tx.Text_Start=P(10,300); tx.Text_End=P(800,340); tx.Text_Length=40; tx.Font0_Id=0; tx.Font1_Id=0; tx.FontX_Dot=12; tx.FontY_Dot=24; tx.Encode_Mode=2; tx.duiqi=2; tx.verticalDuiqi=1; tx.IsAdjust=true; tx.Hor_Dis=1; tx.Ver_Dis=2;
    tx.GetData(); o.AppendLine("text "+Hex(tx.Data));
    var pages=new SortedDictionary<int, List<ShowBase>>();
    var ic2=new IconShow(); ic2.Desc_Point=0xFFFF; ic2.Var_Point=0x5000; ic2.Var_Position=P(0,0); ic2.V_Max=1; ic2.Icon_Max=1; ic2.Icon_lib=48;
    pages[0]=new List<ShowBase>{ ic2, dt }; pages[2]=new List<ShowBase>{ tx };
    File.WriteAllBytes(Path.Combine(args[0],"cs_14.bin"), Build14(pages));
    File.WriteAllText(Path.Combine(args[0],"cs_vectors.txt"), o.ToString());
    Console.Write(o.ToString());
  }
}
