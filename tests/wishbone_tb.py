import cocotb
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge


class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, dut: cocotb.regression.TestFactory):
        """
        Initialize the Wishbone driver.

        Args:
            dut: The device under test.
        """
        self.dut = dut

    async def write(self, address: int, data: int) -> None:
        """Perform a write operation on the Wishbone bus.

        Args:
            address (int): The address to write to.
            data (int): The data to write.
        """
        self.dut.start_i.value = 1
        self.dut.we_i.value = 1  # Write enable
        self.dut.address_i.value = address
        self.dut.data_i.value = data
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0

    async def ack(self) -> None:
        """Wait for the acknowledgment signal from the DUT."""
        while True:
            await RisingEdge(self.dut.clk)
            if self.dut.ack_o.value:
                break

    async def read(self, address: int) -> int:
        """Perform a read operation on the Wishbone bus.

        Args:
            address (int): The address to read from.

        Returns:
            int: The data read from the address.
        """
        self.dut.start_i.value = 1
        self.dut.we_i.value = 0  # Read enable
        self.dut.address_i.value = address
        await RisingEdge(self.dut.clk)
        return int(self.dut.data_o.value)


class WishboneMonitor:
    """Monitor for Wishbone bus. Captures signals and stores monitored data."""

    def __init__(self, dut: cocotb.regression.TestFactory):
        """
        Initialize the Wishbone monitor.

        Args:
            dut: The device under test.
        """
        self.dut = dut
        self.data = {}

    async def monitor(self) -> None:
        """Continuously monitor signals on the Wishbone bus."""
        while True:
            await RisingEdge(self.dut.clk)
            self.data[self.dut.address_i.value] = self.dut.data_o.value


class WishboneScoreboard:
    """Scoreboard for Wishbone bus. Compares expected values with actual values."""

    def __init__(self):
        """
        Initialize the Wishbone scoreboard.
        """
        self.expected = {}

    def check(self, address: int, expected_data: int):
        """Check the read data from the Wishbone bus against expected values.

        Args:
            address (int): The address to check.
            expected_data (int): The expected data.
        """
        if address in self.expected:
            assert self.expected[address] == expected_data, f"Data mismatch at address {address}"
        else:
            self.expected[address] = expected_data


@cocotb.test()
async def test_wb_interface(dut):
    """Test the Wishbone interface with both read and write operations."""
    
    # Initialize driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Start the monitor in a coroutine
    cocotb.start_soon(monitor.monitor())

    # Test 1: Write operation
    address = 0x10
    data_to_write = 0x55
    await driver.write(address, data_to_write)

    # Test 2: Read operation
    data_read = await driver.read(address)
    
    # Check if the value read matches what was written
    scoreboard.check(address, data_to_write)
    
    # Test 3: Write and read more data
    address = 0x20
    data_to_write = 0xAA
    await driver.write(address, data_to_write)
    data_read = await driver.read(address)
    scoreboard.check(address, data_to_write)

    # Wait for all operations to complete
    await cocotb.triggers.First(
        cocotb.trigger.RisingEdge(dut.clk),
        cocotb.trigger.Timer(2)
    )

    # Final check to confirm all the written data has been verified correctly
    for addr, expected_data in scoreboard.expected.items():
        assert monitor.data[addr] == expected_data, f"Mismatch at address {addr}. Expected {expected_data}, got {monitor.data[addr]}"

