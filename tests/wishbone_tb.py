import logging
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time
from typing import Any

# Setup logging for test output
logging.basicConfig(level=logging.INFO)

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, dut: Any) -> None:
        self.dut = dut
        self.clock = None  # Assuming a clock is defined somewhere
        self.reset()

    def reset(self):
        """Resets the driver."""
        self.dut.rst.value = 1
        logging.info(f"-------- Reset Applied @ {get_sim_time(units='ns')} --------")
        # Hold reset for a few cycles
        self.dut.rst.value = 0
        logging.info(f"-------- Reset Released @ {get_sim_time(units='ns')} --------")

    async def write(self, addr, data):
        """Write data to the Wishbone bus."""
        self.dut.addr.value = addr
        self.dut.write_data.value = data
        self.dut.we.value = 1  # Set write enable
        self.dut.stb.value = 1  # Set strobe
        await RisingEdge(self.dut.clk)  # Wait for one clock cycle
        logging.info(f"Write to address {addr}: {data}")
        self.dut.stb.value = 0  # Deassert strobe after operation
        self.dut.we.value = 0  # Deassert write enable

    async def read(self, addr):
        """Read data from the Wishbone bus."""
        self.dut.addr.value = addr
        self.dut.stb.value = 1  # Set strobe
        await RisingEdge(self.dut.clk)  # Wait for one clock cycle
        data = self.dut.read_data.value
        logging.info(f"Read from address {addr}: {data}")
        self.dut.stb.value = 0  # Deassert strobe
        return data


class WishboneScoreboard:
    """Scoreboard to compare expected vs actual data on the Wishbone bus."""

    def __init__(self):
        self.expected_data = {}  # Holds expected data for comparison
        self.errors = 0

    def add_expected(self, addr, data):
        """Add expected data for a given address."""
        self.expected_data[addr] = data

    def check(self, addr, data):
        """Check if the actual data matches the expected data."""
        if addr in self.expected_data:
            expected = self.expected_data[addr]
            if expected != data:
                logging.error(f"Error: Expected {expected} but got {data} at address {addr}")
                self.errors += 1
            else:
                logging.info(f"Passed: Address {addr} matches expected data {data}")
        else:
            logging.warning(f"No expected data for address {addr}")


@cocotb.coroutine
def test_wishbone(dut):
    """Test function for the Wishbone interface."""
    
    # Initialize the driver and scoreboard
    driver = WishboneDriver(dut)
    scoreboard = WishboneScoreboard()

    # Apply reset to initialize the DUT
    driver.reset()

    # Test: Write to a specific address
    addr1 = 0x1000
    data1 = 0xDEADBEEF
    await driver.write(addr1, data1)
    scoreboard.add_expected(addr1, data1)

    # Test: Read from the same address
    read_data1 = await driver.read(addr1)
    scoreboard.check(addr1, read_data1)

    # Test: Write to another address
    addr2 = 0x2000
    data2 = 0x12345678
    await driver.write(addr2, data2)
    scoreboard.add_expected(addr2, data2)

    # Test: Read from the second address
    read_data2 = await driver.read(addr2)
    scoreboard.check(addr2, read_data2)

    # Final Check for errors in the scoreboard
    if scoreboard.errors == 0:
        logging.info(f"Test Passed @ {get_sim_time(units='ns')}")
    else:
        logging.error(f"Test Failed with {scoreboard.errors} errors @ {get_sim_time(units='ns')}")
        raise TestFailure(f"Test failed with {scoreboard.errors} errors.")


# Factory to run the test
test_factory = TestFactory(test_wishbone)
test_factory.generate_tests()
