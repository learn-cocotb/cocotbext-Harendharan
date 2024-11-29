import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from typing import Any, Dict

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, dut: Any) -> None:
        """Initialize the driver with the device under test (DUT)."""
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        """Write data to a given address on the Wishbone bus."""
        # Set address and data to write
        self.dut.wishbone_address <= address
        self.dut.wishbone_data <= data
        self.dut.wishbone_stb <= 1  # Assert the strobe to start the transaction
        
        # Wait for the rising edge of the clock to propagate the signals
        await RisingEdge(self.dut.clk)
        
        # Wait for the acknowledgment from the Wishbone interface
        await RisingEdge(self.dut.wishbone_ack)
        
        # Deassert the strobe after the acknowledgment
        self.dut.wishbone_stb <= 0

    async def read(self, address: int) -> int:
        """Read data from a given address on the Wishbone bus."""
        # Set the address to read from
        self.dut.wishbone_address <= address
        self.dut.wishbone_stb <= 1  # Assert the strobe to start the transaction
        
        # Wait for the rising edge of the clock
        await RisingEdge(self.dut.clk)
        
        # Wait for the acknowledgment from the Wishbone interface
        await RisingEdge(self.dut.wishbone_ack)
        
        # Read the data after acknowledgment
        read_data = self.dut.wishbone_data.value
        
        # Deassert the strobe after the acknowledgment
        self.dut.wishbone_stb <= 0
        
        return read_data

class WishboneMonitor:
    """Monitor for Wishbone bus. Captures signals and stores monitored data."""

    def __init__(self, dut: Any) -> None:
        """Initialize the monitor with the device under test (DUT)."""
        self.dut = dut
        self.data = []

    async def monitor(self) -> None:
        """Monitor the Wishbone signals and store the data."""
        while True:
            await RisingEdge(self.dut.clk)
            # Capture data only when the strobe is active, indicating a transaction
            if self.dut.wishbone_stb == 1:
                self.data.append({
                    "address": self.dut.wishbone_address.value,
                    "data": self.dut.wishbone_data.value,
                    "ack": self.dut.wishbone_ack.value,
                })

class WishboneScoreboard:
    """Scoreboard for validating the Wishbone interface."""

    def __init__(self) -> None:
        """Initialize the Wishbone scoreboard."""
        self.expected: Dict[str, int] = {}

    def validate(self, address: int, data: int) -> None:
        """Validate the received data against the expected values."""
        if address in self.expected:
            expected_data = self.expected[address]
            assert expected_data == data, f"Mismatch at address {hex(address)}: expected {hex(expected_data)}, got {hex(data)}"
        else:
            print(f"Unexpected address {hex(address)}: received data {hex(data)}")

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
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Start the monitor in the background
    cocotb.start_soon(monitor.monitor())

    # Perform write and read operations
    await driver.write(0x1000, 0xABCD)  # Write data
    read_data = await driver.read(0x1000)  # Read data

    # Set expected value for validation
    scoreboard.expected[0x1000] = 0xABCD
    
    # Validate the read data
    scoreboard.validate(0x1000, read_data)
