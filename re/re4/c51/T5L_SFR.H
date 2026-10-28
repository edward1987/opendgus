/* T5L OS-core (8051) SFR definitions.
 * Source: Development-Guide-of-T5L-ASIC-2024-09-25 sec 3.1-3.9 (PDF p.14-35).
 * Register map is Infineon C51x/80C517-style (ADCON, SRELx, IEN0/1/2, IP0/1).
 * Hand-written for this RE effort; DWIN ships its own T5L51.H/.INC (not on disk). */
#ifndef T5L_SFR_H
#define T5L_SFR_H

/* --- standard 8051 core --- */
sfr P0   = 0x80;  sfr SP   = 0x81;  sfr DPL  = 0x82;  sfr DPH  = 0x83;
sfr PCON = 0x87;  sfr TCON = 0x88;  sfr TMOD = 0x89;  sfr TL0  = 0x8A;
sfr TL1  = 0x8B;  sfr TH0  = 0x8C;  sfr TH1  = 0x8D;  sfr P1   = 0x90;
sfr P2   = 0xA0;  sfr P3   = 0xB0;  sfr PSW  = 0xD0;  sfr ACC  = 0xE0;
sfr B    = 0xF0;

/* --- T5L system --- */
sfr CKON      = 0x8E;  /* write 0x00: 1T mode */
sfr DPC       = 0x93;  /* MOVX DPTR auto-step: MUST be 0x00 for C51 */
sfr PAGESEL   = 0x94;  /* write 0x01: 64KB code space */
sfr D_PAGESEL = 0x95;  /* write 0x02: XDATA 0x8000-0xFFFF (32KB) */
sfr MUX_SEL   = 0xC9;  /* .7 CAN .6 UART2 .5 UART3 pin mux, .1 WDT on, .0 WDT feed */
sfr PORTDRV   = 0xF9;  /* IO drive 0=4mA 1=8mA 2=16mA 3=32mA */
sfr P0MDOUT   = 0xB7;  sfr P1MDOUT = 0xBC;  sfr P2MDOUT = 0xBD;  sfr P3MDOUT = 0xBE;

/* --- DGUS variable memory window --- */
sfr RAMMODE = 0xF8;    /* bit addressable */
sbit APP_REQ = RAMMODE^7;  /* 1 = request bus */
sbit APP_EN  = RAMMODE^6;  /* 1 = start one 4-byte transfer, HW clears */
sbit APP_RW  = RAMMODE^5;  /* 1 = read, 0 = write */
sbit APP_ACK = RAMMODE^4;  /* HW: 1 = bus granted */
sfr ADR_H   = 0xF1;    /* A23..A16 (0x00 for DGUS vars, 0xFF for CAN) */
sfr ADR_M   = 0xF2;    /* A15..A8 */
sfr ADR_L   = 0xF3;    /* A7..A0  (unit = 4 bytes = 2 VP words) */
sfr ADR_INC = 0xF4;    /* auto-increment after each transfer */
sfr DATA3   = 0xFA;    /* high byte of even VP  */
sfr DATA2   = 0xFB;    /* low  byte of even VP  */
sfr DATA1   = 0xFC;    /* high byte of odd VP   */
sfr DATA0   = 0xFD;    /* low  byte of odd VP   */

/* --- extended SFR / MDU --- */
sfr EXADR  = 0xFE;  sfr EXDATA = 0xFF;  sfr MAC_CN = 0xE5;  sfr DIV_CN = 0xE6;

/* --- timers --- */
sfr T2CON = 0xC8;      /* init 0x70; .0 = TR2, .7 = /12 vs /24 */
sbit TR2  = T2CON^0;
sfr TRL2L = 0xCA;  sfr TRL2H = 0xCB;   /* T2 reload (a.k.a. CRCL/CRCH in DWIN asm example) */
sfr TL2   = 0xCC;  sfr TH2   = 0xCD;

/* --- interrupts --- */
sfr IEN0 = 0xA8;  sfr IEN1 = 0xB8;  sfr IEN2 = 0x9A;  sfr IEN3 = 0xD1;
sfr IP0  = 0xA9;  sfr IP1  = 0xB9;
sbit EA  = IEN0^7;  sbit ET2 = IEN0^5;  sbit ES0 = IEN0^4;  sbit ET1 = IEN0^3;
sbit EX1 = IEN0^2;  sbit ET0 = IEN0^1;  sbit EX0 = IEN0^0;
sbit ES3R = IEN1^5; sbit ES3T = IEN1^4; sbit ES2R = IEN1^3; sbit ES2T = IEN1^2; sbit ECAN = IEN1^1;
sbit TF1 = TCON^7;  sbit TR1 = TCON^6;  sbit TF0 = TCON^5;  sbit TR0 = TCON^4;

/* --- UART2 (OS core, P0.4 TX / P0.5 RX) --- */
sfr SCON0  = 0x98;  sfr SBUF0  = 0x99;
sbit RI0 = SCON0^0; sbit TI0 = SCON0^1; sbit REN0 = SCON0^4;
sfr ADCON  = 0xD8;  /* 0x80 = UART2 baud from SREL0 */
sfr SREL0H = 0xBA;  sfr SREL0L = 0xAA;
/* --- UART3 (P0.6/P0.7) --- */
sfr SCON1  = 0x9B;  sfr SBUF1  = 0x9C;  sfr SREL1H = 0xBB;  sfr SREL1L = 0x9D;
/* --- UART4 --- */
sfr SCON2T = 0x96;  sfr SCON2R = 0x97;  sfr SBUF2_TX = 0x9E;  sfr SBUF2_RX = 0x9F;
sfr BODE2_DIV_H = 0xD9;  sfr BODE2_DIV_L = 0xD7;
/* --- UART5 --- */
sfr SCON3T = 0xA7;  sfr SCON3R = 0xAB;  sfr SBUF3_TX = 0xAC;  sfr SBUF3_RX = 0xAD;
sfr BODE3_DIV_H = 0xAE;  sfr BODE3_DIV_L = 0xAF;
/* --- CAN --- */
sfr CAN_CR = 0x8F;  sfr CAN_IR = 0x91;  sfr CAN_ET = 0xE8;

/* Keil interrupt numbers = (vector-3)/8 */
#define INT_EX0   0   /* 0x0003 */
#define INT_T0    1   /* 0x000B */
#define INT_EX1   2   /* 0x0013 */
#define INT_T1    3   /* 0x001B */
#define INT_UART2 4   /* 0x0023 */
#define INT_T2    5   /* 0x002B */
#define INT_CAN   9   /* 0x004B */
#define INT_U4TX 10   /* 0x0053 */
#define INT_U4RX 11   /* 0x005B */
#define INT_U5TX 12   /* 0x0063 */
#define INT_U5RX 13   /* 0x006B */
#define INT_UART3 16  /* 0x0083 */

#define FOSC 206438400UL   /* 11.0592 MHz * 56/3 */
#endif
