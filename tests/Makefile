# regression:
#	echo Running regression
# .PHONY: regression
# include $(shell cocotb-config --makefiles)/Makefile.sim
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES += $(PWD)/../verilog/wishbone.v
TOPLEVEL = wishbone
MODULE = wishbone_tb
include $(shell cocotb-config --makefiles)/Makefile.sim
