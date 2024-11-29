from typing import Any, Dict
import cocotb
from cocotb.regression import TestFactory
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


# Define the Wishbone interface driver
class WishboneDriver:
    def __init__(self, dut: Any) -> None:
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        self.dut.wishbone.adr = address
        self.dut.wishbone.dat = data
        self.dut.wishbone.we = 1
        await RisingEdge(self.dut.clk)
        self.dut.wishbone.we = 0

    async def read(self, address: int) -> int:
        self.dut.wishbone.adr = address
        self.dut.wishbone.cyc = 1
        self.dut.wishbone.stb = 1
        await RisingEdge(self.dut.clk)
        return self.dut.wishbone.dat.value

# Define the monitor class to capture the signals
class WishboneMonitor:
    def __init__(self, dut: Any) -> None:
        self.dut = dut
        self.data = []

    async def monitor(self) -> None:
        while True:
            await RisingEdge(self.dut.clk)
            self.data.append(self.dut.wishbone.dat)

# Define the scoreboard for validating read/write operations
class WishboneScoreboard:
    def __init__(self) -> None:
        self.expected: Dict[int, int] = {}

    def add_expected(self, address: int, data: int) -> None:
        self.expected[address] = data

    def validate(self, address: int, data: int) -> None:
        if address in self.expected:
            assert self.expected[address] == data, f"Mismatch at address {address}: expected {self.expected[address]}, got {data}"

# Define the test coroutine using cocotb
@cocotb.test()
async def test_wb_interface(dut: Any) -> None:
    """Test the Wishbone interface by performing write and read operations and validating results using a scoreboard.

    Args:
        dut: The device under test.
    """
    # Initialize clock and start it
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Initialize the Wishbone driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    scoreboard = WishboneScoreboard()

    # Add expected values for validation
    scoreboard.add_expected(0x1000, 0xABCD)
    scoreboard.add_expected(0x2000, 0x1234)

    # Perform write and read operations, validate results
    await driver.write(0x1000, 0xABCD)
    read_data = await driver.read(0x1000)
    scoreboard.validate(0x1000, read_data)

    await driver.write(0x2000, 0x1234)
    read_data = await driver.read(0x2000)
    scoreboard.validate(0x2000, read_data)

# Generate the testbench for the Wishbone interface
test_factory = TestFactory(test_wb_interface)
test_factory.generate_tests()
