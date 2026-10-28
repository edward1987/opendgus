/* Minimal T5L OS-core (8051) application: read/write DGUS VPs.
 * Build: build.sh. Output T5L51.bin -> DWIN_SET (SD) or UART (VP 0x0006, type 0xA5). */
#include "T5L_SFR.H"

typedef unsigned char  u8;
typedef unsigned short u16;

/* VP (16-bit word address used by DGUS/UART 0x82/0x83) -> 8051 window:
 * window address = VP/2 (one window cell = 4 bytes = 2 VPs).
 * even VP -> DATA3:DATA2, odd VP -> DATA1:DATA0. */
static void vp_select(u16 vp)
{
    ADR_H = 0x00;
    ADR_M = (u8)(vp >> 9);
    ADR_L = (u8)(vp >> 1);
    ADR_INC = 1;
}

u16 vp_read(u16 vp)
{
    u16 v;
    bit ea = EA;
    EA = 0;                         /* guide: no interrupts during window access */
    vp_select(vp);
    RAMMODE = 0xAF;                 /* REQ | read | all 4 bytes */
    while (!APP_ACK);
    APP_EN = 1;
    while (APP_EN);                 /* HW clears when done */
    if (vp & 1) v = ((u16)DATA1 << 8) | DATA0;
    else        v = ((u16)DATA3 << 8) | DATA2;
    RAMMODE = 0x00;
    EA = ea;
    return v;
}

void vp_write(u16 vp, u16 val)
{
    bit ea = EA;
    EA = 0;
    vp_select(vp);
    RAMMODE = (vp & 1) ? 0x83 : 0x8C;   /* REQ | write | byte-enable mask */
    while (!APP_ACK);
    if (vp & 1) { DATA1 = (u8)(val >> 8); DATA0 = (u8)val; }
    else        { DATA3 = (u8)(val >> 8); DATA2 = (u8)val; }
    APP_EN = 1;
    while (APP_EN);
    RAMMODE = 0x00;
    EA = ea;
}

/* Page switch via system variable 0x0084: 5A 01 + page id */
void dgus_set_page(u16 page)
{
    vp_write(0x0085, page);
    vp_write(0x0084, 0x5A01);
}

/* UART2 on the OS core (P0.4/P0.5), 8N1, SMOD=0: SREL = 1024 - FOSC/(64*baud) */
void uart2_init(void)
{
    u16 srel = 1024 - (u16)(FOSC / 64UL / 115200UL);   /* 0x03E4 */
    MUX_SEL |= 0x40;
    P0MDOUT |= 0x10;                /* P0.4 TX push-pull */
    ADCON   = 0x80;                 /* baud from SREL0 */
    SCON0   = 0x50;                 /* mode 1, REN */
    SREL0H  = (u8)(srel >> 8);
    SREL0L  = (u8)srel;
}

void uart2_putc(u8 c)
{
    SBUF0 = c;
    while (!TI0);
    TI0 = 0;
}

void main(void)
{
    u16 counter = 0, k;
    long d;

    uart2_init();
    vp_write(0x1000, 0);

    for (;;) {
        /* 1. heartbeat counter for a Data Variable control on VP 0x1000 */
        vp_write(0x1000, ++counter);

        /* 2. whatever UI/host writes to 0x1002 appears doubled at 0x1003 */
        vp_write(0x1003, vp_read(0x1002) << 1);

        /* 3. Return-Key-Code control on VP 0x1010 -> switch to page <key> */
        k = vp_read(0x1010);
        if (k) {
            dgus_set_page(k);
            uart2_putc((u8)k);
            vp_write(0x1010, 0);
        }
        for (d = 0; d < 200000L; d++);   /* crude delay */
    }
}
