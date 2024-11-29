from typing import Any, Dict

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""
    def __init__(self, dut: Any) -> None:
        """Initialize the Wishbone driver with the given DUT (Device Under Test)."""
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        """Write data to a given address on the Wishbone bus."""
        self.dut.wishbone.adr = address
        self.dut.wishbone.dat = data
        self.dut.wishbone.we = 1
        await RisingEdge(self.dut.clk)
        self.dut.wishbone.we = 0

    async def read(self, address: int) -> int:
        """Read data from a given address on the Wishbone bus."""
        self.dut.wishbone.adr = address
        self.dut.wishbone.cyc = 1
        self.dut.wishbone.stb = 1
        await RisingEdge(self.dut.clk)
        return self.dut.wishbone.dat.value

class WishboneMonitor:
    """Monitor for Wishbone bus. Captures signals and stores monitored data."""
    def __init__(self, dut: Any) -> None:
        """Initialize the monitor with the given DUT (Device Under Test)."""
        self.dut = dut
        self.data = []

    async def monitor(self) -> None:
        """Monitor the Wishbone signals and store the data."""
        while True:
            await RisingEdge(self.dut.clk)
            self.data.append(self.dut.wishbone.dat)

class WishboneScoreboard:
    """Scoreboard for validating the Wishbone interface."""
    def __init__(self) -> None:
        """Initialize the Wishbone scoreboard."""
        self.expected: Dict[int, int] = {}

    def add_expected(self, address: int, data: int) -> None:
        """Add expected data for a given address."""
        self.expected[address] = data

    def validate(self, address: int, data: int) -> None:
        """Validate the received data against the expected values."""
        if address in self.expected:
            assert self.expected[address] == data, f"Mismatch at address {address}: expected {self.expected[address]}, got {data}"

@cocotb.test()
async def test_wb_interface(dut: Any) -> None:
    """Test the Wishbone interface by performing write and read operations and validating results using a scoreboard.

    Args:
        dut: The device under test.
    """
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    driver = WishboneDriver(dut)
    scoreboard = WishboneScoreboard()

    scoreboard.add_expected(0x1000, 0xABCD)
    scoreboard.add_expected(0x2000, 0x1234)

    await driver.write(0x1000, 0xABCD)
    read_data = await driver.read(0x1000)
    scoreboard.validate(0x1000, read_data)

    await driver.write(0x2000, 0x1234)
    read_data = await driver.read(0x2000)
    scoreboard.validate(0x2000, read_data)
