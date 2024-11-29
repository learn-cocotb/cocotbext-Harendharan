"""Testbench for the Wishbone interface using Cocotb."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from typing import Any, Dict


@cocotb.coroutine
def wishbone_write(dut, address: int, data: int):
    """Perform a write operation on the Wishbone interface."""
    dut.wishbone_address <= address
    dut.wishbone_data <= data
    dut.wishbone_stb <= 1
    yield RisingEdge(dut.clk)
    dut.wishbone_stb <= 0


@cocotb.coroutine
def wishbone_read(dut, address: int) -> int:
    """Perform a read operation on the Wishbone interface and return data."""
    dut.wishbone_address <= address
    dut.wishbone_stb <= 1
    yield RisingEdge(dut.clk)
    dut.wishbone_stb <= 0
    return dut.wishbone_data.value


@cocotb.coroutine
def reset(dut):
    """Apply reset to the DUT."""
    dut.reset <= 1
    yield RisingEdge(dut.clk)
    dut.reset <= 0
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def run_wishbone_test(dut):
    """Run a simple test for the Wishbone interface."""
    # Initialize clock
    clk = Clock(dut.clk, 10, units="ns")
    cocotb.fork(clk.start())

    # Apply reset
    yield reset(dut)

    # Perform write operations
    yield wishbone_write(dut, 0x00, 0xABCD)
    yield wishbone_write(dut, 0x04, 0x1234)

    # Perform read operations and verify data
    read_data = yield wishbone_read(dut, 0x00)
    assert read_data == 0xABCD, f"Expected 0xABCD, but got {hex(read_data)}"

    read_data = yield wishbone_read(dut, 0x04)
    assert read_data == 0x1234, f"Expected 0x1234, but got {hex(read_data)}"

    # Additional operations and assertions can be added here.
