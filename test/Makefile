TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../cocotb

WPWD=$(shell pwd)

TOPLEVEL := div
MODULE := test_div

VERILOG_SOURCES = $(WPWD)/../src/div.v
COMPILE_ARGS=-P div.PERIOD=10

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
