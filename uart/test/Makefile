TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../../cocotb

WPWD=$(shell pwd)

TOPLEVEL := uart
MODULE := test_uart

VERILOG_SOURCES = $(WPWD)/../src/uart.v $(WPWD)/../../uart_rx/src/uart_rx.v $(WPWD)/../../div/src/div.v $(WPWD)/../../uart_tx/src/uart_tx.v 
#COMPILE_ARGS=-P div.PERIOD=10

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
