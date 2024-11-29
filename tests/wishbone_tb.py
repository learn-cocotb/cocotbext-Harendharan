import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from typing import Any, Dict

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""
    def __init__(self, dut: Any) -> None:
        """Initialize the Wishbone driver with the given DUT (Device Under Test)."""
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        """Write data to a given address on the Wishbone bus."""
        # Set the address and data lines (adjust according to your DUT's interface)
        self.dut.wishbone.adr <= address
        self.dut.wishbone.dat <= data
        self.dut.wishbone.we <= 1  # Set write enable
        await RisingEdge(self.dut.clk)  # Wait for a clock edge
        self.dut.wishbone.we <= 0  # Clear write enable after operation

    async def read(self, address: int) -> int:
        """Read data from a given address on the Wishbone bus."""
        # Set the address for the read operation
        self.dut.wishbone.adr <= address
        self.dut.wishbone.cyc <= 1  # Set cycle active
        self.dut.wishbone.stb <= 1  # Set strobe active
        await RisingEdge(self.dut.clk)  # Wait for a clock edge
        #data = self.dut.wishbone.dat  # Read data from the bus
        #return data

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
            # Capture and store data from the bus (adjust according to your DUT)
            self.data.append(self.dut.wishbone.dat)  # Example signal, modify as needed

class WishboneScoreboard:
    """Scoreboard for validating the Wishbone interface."""

    def __init__(self) -> None:
        """Initialize the Wishbone scoreboard."""
        self.expected: Dict[int, int] = {}  # Use int for address keys instead of string

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
    # Initialize clock and start it
    clock = Clock(dut.clk, 10, units="ns")  # 10 ns clock period
    cocotb.start_soon(clock.start())

    # Create the driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    #monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Add expected values to the scoreboard
    scoreboard.add_expected(0x1000, 0xABCD)
    scoreboard.add_expected(0x2000, 0x1234)

    # Perform write and read operations
    await driver.write(0x1000, 0xABCD)
    read_data = await driver.read(0x1000)

    # Validate the read data
    scoreboard.validate(0x1000, read_data)

    # Perform additional operations as needed
    await driver.write(0x2000, 0x1234)
    read_data = await driver.read(0x2000)
    scoreboard.validate(0x2000, read_data)
