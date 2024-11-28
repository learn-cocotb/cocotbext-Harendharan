TOPLEVEL_LANG ?= verilog
SIM ?= icarus
VERILOG_SOURCES = $(shell pwd)/wb_interface.v
TOPLEVEL := wb_interface # Verilog or SystemVerilog TOP file module name
MODULE   := testbench # Python file name


include $(shell cocotb-config --makefiles)/Makefile.sim 
