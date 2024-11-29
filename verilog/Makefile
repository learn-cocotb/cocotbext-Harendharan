 SIM ?= icarus
TOPLEVEL_LANG ?= verilog
#VERILOG_SOURCES += ./verilog/wishbone.v
#TOPLEVEL = wishbone
#MODULE = wishbone_tb
VERILOG_SOURCES += ./verilog/dpll.sv
TOPLEVEL = dpll
MODULE = dpll_tb
include $(shell cocotb-config --makefiles)/Makefile.sim
