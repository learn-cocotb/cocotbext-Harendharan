import cocotb
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge
from typing import Any, Dict

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing
    read and write operations.
    """

    def __init__(self, dut: Any) -> None:
        """Initialize the Wishbone driver.

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
        self.dut.ack_o.value = 0
        self.dut.address_i.value = address
        self.dut.data_i.value = data
        await RisingEdge(self.dut.clk)
        self.dut.ack_o.value = 1
        await RisingEdge(self.dut.clk)
        self.dut.ack_o.value = 0

    async def read(self, address: int) -> int:
        """Perform a read operation on the Wishbone bus.

        Args:
            address (int): The address to read from.

        Returns:
            int: The data read from the address.
        """
        self.dut.start_i.value = 1
        self.dut.we_i.value = 0  # Read enable
        self.dut.ack_o.value = 0
        self.dut.address_i.value = address
        await RisingEdge(self.dut.clk)
        self.dut.ack_o.value = 1
        await RisingEdge(self.dut.clk)
        self.dut.ack_o.value = 0
        return self.dut.data_o.value


class WishboneMonitor:
    """Monitor for Wishbone bus. Captures signals and stores monitored data.
    """

    def __init__(self, dut: Any) -> None:
        """Initialize the Wishbone monitor.

        Args:
            dut: The device under test.
        """
        self.dut = dut
        self.data: Dict[str, Any] = {}

    async def monitor(self) -> None:
        """Monitor the Wishbone signals and store the data.
        """
        while True:
            await RisingEdge(self.dut.clk)
            self.data["start"] = self.dut.start_i.value
            self.data["ack"] = self.dut.ack_o.value
            self.data["address"] = self.dut.address_i.value
            self.data["data"] = self.dut.data_o.value


class WishboneScoreboard:
    """Scoreboard for validating the Wishbone interface.
    """

    def __init__(self) -> None:
        """Initialize the Wishbone scoreboard.
        """
        self.expected: Dict[str, int] = {}

    def expect(self, signal: str, value: int) -> None:
        """Record the expected value of a signal.

        Args:
            signal (str): The signal name.
            value (int): The expected value.
        """
        self.expected[signal] = value

    def check(self, monitor_data: Dict[str, Any]) -> None:
        """Check the monitored data against the expected values.

        Args:
            monitor_data (dict): The data captured by the monitor.
        """
        for signal, expected_value in self.expected.items():
            actual_value = monitor_data.get(signal)
            if actual_value != expected_value:
                raise ValueError(f"Signal {signal} value mismatch: expected {expected_value}, got {actual_value}")


@cocotb.test()
async def test_wb_interface(dut: Any) -> None:
    """Test the Wishbone interface by performing write and read operations
    and validating results using a scoreboard.

    Args:
        dut: The device under test.
    """
    # Initialize clock and start it
    clock = Clock(dut.clk, 10, units="ns")  # 10 ns clock period
    cocotb.fork(clock.start())

    # Initialize driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Start monitoring in the background
    cocotb.fork(monitor.monitor())

    # Perform a write operation
    await driver.write(0x10, 0x1234)
    scoreboard.expect("data", 0x1234)

    # Perform a read operation
    data = await driver.read(0x10)
    scoreboard.check(monitor.data)

    assert data == 0x1234, f"Read data mismatch: expected 0x1234, got {data}"
