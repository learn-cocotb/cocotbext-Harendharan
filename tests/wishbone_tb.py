import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing
    read and write operations."""

    def __init__(self, dut):
        """Initialize the Wishbone driver.

        Args:
            dut: The device under test."""
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        """Perform a write operation on the Wishbone bus.

        Args:
            address (int): The address to write to.
            data (int): The data to write."""
        self.dut.start_i.value = 1
        self.dut.we_i.value = 1  # Write enable
        self.dut.addr_i.value = address
        self.dut.data_i.value = data
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0

    async def ack(self) -> None:
        """Wait for the acknowledgment signal from the DUT."""
        while True:
            await RisingEdge(self.dut.clk)
            if self.dut.ack_o.value == 1:
                break

    async def read(self, address: int) -> int:
        """Perform a read operation on the Wishbone bus.

        Args:
            address (int): The address to read from.

        Returns:
            int: The data read from the address."""
        self.dut.start_i.value = 1
        self.dut.we_i.value = 0  # Read enable
        self.dut.addr_i.value = address
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0
        await self.ack()
        return int(self.dut.data_o.value)


class WishboneMonitor:
    """Monitor for Wishbone bus. Captures signals and stores monitored data."""
    def __init__(self, dut):
        """Initialize the Wishbone monitor.

        Args:
            dut: The device under test."""
        self.dut = dut
        self.data = {
            "addr_i": None,
            "data_i": None,
            "data_o": None,
            "we_i": None,
            "wb_ack_i": None,
            "busy_o": None,
        }

    async def monitor(self) -> None:
        """Continuously monitor signals on the Wishbone bus."""
        while True:
            await RisingEdge(self.dut.clk)
            self.data = {
                "addr_i": self.dut.addr_i.value,
                "data_i": self.dut.data_i.value,
                "data_o": self.dut.data_o.value,
                "we_i": self.dut.we_i.value,
                "wb_ack_i": self.dut.wb_ack_i.value,
                "busy_o": self.dut.busy_o.value,
            }


class WishboneScoreboard:
    """Scoreboard for Wishbone bus. Compares expected values with actual values."""

    def __init__(self):
        """Initialize the Wishbone scoreboard"""
        self.expected = {}

    def expect(self, signal: str, value: int) -> None:
        """Record the expected value of a signal.

        Args:
            signal (str): The signal name.
            value (int): The expected value."""
        self.expected[signal] = value

    def check(self, monitor_data: dict) -> None:
        """Check the monitored data against the expected values.

        Args:
            monitor_data (dict): The data captured by the monitor."""
        for signal, expected_value in self.expected.items():
            actual_value = monitor_data.get(signal)
            assert actual_value == expected_value, (
                f"Mismatch for {signal}: expected {expected_value}, got {actual_value}"
            )


@cocotb.test()
async def test_wb_interface(dut):
    """Test the Wishbone interface by performing write and read operations
    and validating results using a scoreboard.

    Args:
        dut: The device under test."""
    # Initialize clock and start it
    clock = Clock(dut.clk, 10, units="ns")  # 10 ns clock period
    cocotb.start_soon(clock.start())

    # Initialize driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Reset the DUT
    dut.rst.value = 1
    for _ in range(5):  # Wait for 5 clock cycles
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Start monitoring signals
    cocotb.start_soon(monitor.monitor())

    # Test Case: Write and Read
    write_address = 0x4
    write_data = 0xA5
    await driver.write(write_address, write_data)
    await driver.ack()  # Wait for acknowledgment

    # Expectation
    scoreboard.expect("addr_i", write_address)
    scoreboard.expect("data_i", write_data)
    scoreboard.expect("we_i", 1)  # Write enable

    # Check write operation
    scoreboard.check(monitor.data)

    # Test Case: Read from same address
    read_address = write_address
    read_data = await driver.read(read_address)

    # Verify read data
    assert read_data == write_data, f"Read data {read_data} does not match written data {write_data}!"

    # Expectation for read
    scoreboard.expect("addr_i", read_address)
    scoreboard.expect("we_i", 0)  # Read enable

    # Check read operation
    scoreboard.check(monitor.data)
