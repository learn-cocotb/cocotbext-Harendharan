import logging
from cocotb.triggers import RisingEdge, Timer
from typing import Any
from cocotb.utils import get_sim_time

class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, dut: Any) -> None:
        self.dut = dut
        self.busy = False

    async def write(self, address: int, data: int) -> None:
        """Write data to the specified address."""
        self.busy = True
        self.dut.wb_cyc <= 1
        self.dut.wb_stb <= 1
        self.dut.wb_we <= 1
        self.dut.wb_addr <= address
        self.dut.wb_data <= data
        await RisingEdge(self.dut.clk)
        self.dut.wb_stb <= 0
        self.dut.wb_cyc <= 0
        self.busy = False

    async def read(self, address: int) -> int:
        """Read data from the specified address."""
        self.busy = True
        self.dut.wb_cyc <= 1
        self.dut.wb_stb <= 1
        self.dut.wb_we <= 0
        self.dut.wb_addr <= address
        await RisingEdge(self.dut.clk)
        self.dut.wb_stb <= 0
        self.dut.wb_cyc <= 0
        self.busy = False
        return int(self.dut.wb_data)

class WishboneTB:
    """Testbench for the Wishbone interface."""

    def __init__(self, dut: Any) -> None:
        """Initialize the testbench with the DUT (Device Under Test)."""
        self.dut = dut
        self.driver = WishboneDriver(dut)

    async def reset(self) -> None:
        """Reset the DUT."""
        self.dut.rst.value = 1
        await Timer(50, units="ns")
        self.dut.rst.value = 0
        logging.info(f"-------- Reset Released @ {get_sim_time(units='ns')} --------")
        await Timer(50, units="ns")

    async def run(self) -> None:
        """Run the Wishbone transactions."""
        await self.reset()

        # Perform write and read operations
        await self.driver.write(0x10, 0x1234, "Write 1")
        await self.driver.write(0x20, 0x5678, "Write 2")

        data = await self.driver.read(0x10, "Read 1")
        if data == 0x1234:
            logging.info(f"Transaction Passed: Address: 0x10, Data: {data}")
        else:
            logging.error(f"Transaction Failed: Address: 0x10, Expected: 0x1234, Got: {data}")

        data = await self.driver.read(0x20, "Read 2")
        if data == 0x5678:
            logging.info(f"Transaction Passed: Address: 0x20, Data: {data}")
        else:
            logging.error(f"Transaction Failed: Address: 0x20, Expected: 0x5678, Got: {data}")
