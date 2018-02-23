TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../../cocotb

WPWD=$(shell pwd)

TOPLEVEL := uart_rx
MODULE := test_uart_rx

VERILOG_SOURCES = $(WPWD)/../src/uart_rx.v $(WPWD)/../../div/src/div.v
#COMPILE_ARGS=-P div.PERIOD=10

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
