; Minimal T5L OS-core startup (replaces Keil STARTUP.A51).
; - T5L-specific SFR init BEFORE any C code (DPC must be 0 before ?C_START uses MOVX)
; - clears IDATA 0..FF and XDATA 8000..FFFF
; - places the mandatory "DWINT5" code mark at 0x00F8 (ASIC guide p.15, p.32/39)
$NOMOD51
        NAME    ?C_STARTUP
?C_C51STARTUP   SEGMENT CODE
?STACK          SEGMENT IDATA
                RSEG    ?STACK
                DS      1
                EXTRN CODE (?C_START)
                PUBLIC  ?C_STARTUP

SP_      DATA 81H
DPC_     DATA 93H
CKON_    DATA 8EH
PAGESEL_ DATA 94H
DPAGE_   DATA 95H
T2CON_   DATA 0C8H
MUXSEL_  DATA 0C9H
PORTDRV_ DATA 0F9H
RAMMODE_ DATA 0F8H
IEN0_    DATA 0A8H
IEN1_    DATA 0B8H
IEN2_    DATA 09AH
IEN3_    DATA 0D1H

                CSEG    AT 0
?C_STARTUP:     LJMP    STARTUP1

                CSEG    AT 0F8H          ; JMARK enable (FFFF) + "DWINT5" id
                DB      0FFH, 0FFH, 'DWINT5'

                RSEG    ?C_C51STARTUP
STARTUP1:
                MOV     IEN0_,#0
                MOV     IEN1_,#0
                MOV     IEN2_,#0
                MOV     IEN3_,#0
                MOV     CKON_,#00H       ; 1T
                MOV     T2CON_,#70H      ; ext. interrupt system, T2 autoload
                MOV     DPC_,#00H        ; MOVX does not touch DPTR (C51 requirement)
                MOV     PAGESEL_,#01H    ; 64KB code
                MOV     DPAGE_,#02H      ; XDATA = 0x8000-0xFFFF
                MOV     MUXSEL_,#60H     ; UART2+UART3 pins on, CAN off, WDT off
                MOV     PORTDRV_,#01H    ; 8mA
                MOV     RAMMODE_,#00H
; clear IDATA
                MOV     R0,#0FFH
                CLR     A
IDLOOP:         MOV     @R0,A
                DJNZ    R0,IDLOOP
; clear XDATA 8000h..FFFFh
                MOV     DPTR,#8000H
                MOV     R7,#00H          ; 256 * 128 = 32768
                MOV     R6,#80H
XDLOOP:         MOVX    @DPTR,A
                INC     DPTR
                DJNZ    R7,XDLOOP
                DJNZ    R6,XDLOOP
                MOV     SP_,#?STACK-1
                LJMP    ?C_START
                END
