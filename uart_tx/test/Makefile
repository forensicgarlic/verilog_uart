TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../../cocotb

WPWD=$(shell pwd)

TOPLEVEL := uart_tx
MODULE := test_uart_tx

VERILOG_SOURCES = $(WPWD)/../src/uart_tx.v $(WPWD)/../../div/src/div.v
#COMPILE_ARGS=-P div.PERIOD=10

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
