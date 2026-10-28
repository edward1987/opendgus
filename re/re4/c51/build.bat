@echo off
rem Build T5L51.bin with Keil C51 command-line tools. Run from this folder.
set K=C:\Keil_v5\C51
set C51INC=%K%\INC
set C51LIB=%K%\LIB
"%K%\BIN\C51.exe" main.c OPTIMIZE(8,SPEED) SMALL OBJECTEXTEND CODE
"%K%\BIN\A51.EXE" STARTUP_T5L.A51
rem T5L XDATA = 0x8000-0xFFFF (D_PAGESEL=2); code 0x0000-0xFFFF
"%K%\BIN\BL51.EXE" STARTUP_T5L.obj, main.obj TO t5l51 RAMSIZE(256) XDATA(0x8000)
"%K%\BIN\OH51.EXE" t5l51
