import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import logging
from typing import Any, Dict


class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, dut: Any) -> None:
        """Initialize the driver with the DUT (Device Under Test)."""
        self.dut = dut

    async def write(self, address: int, data: int, tag: str = "Write") -> None:
        """Write data to the Wishbone bus."""
        self.dut.wishbone.adr.value = address
        self.dut.wishbone.dat.value = data
        self.dut.wishbone.cyc.value = 1
        self.dut.wishbone.stb.value = 1
        self.dut.wishbone.we.value = 1
        logging.info(f"{tag}: Address: {address}, Data: {data}")
        await RisingEdge(self.dut.clk)
        self.dut.wishbone.cyc.value = 0
        self.dut.wishbone.stb.value = 0

    async def read(self, address: int, tag: str = "Read") -> int:
        """Read data from the Wishbone bus."""
        self.dut.wishbone.adr.value = address
        self.dut.wishbone.cyc.value = 1
        self.dut.wishbone.stb.value = 1
        self.dut.wishbone.we.value = 0
        await RisingEdge(self.dut.clk)
        data = self.dut.wishbone.dat.value
        self.dut.wishbone.cyc.value = 0
        self.dut.wishbone.stb.value = 0
        logging.info(f"{tag}: Address: {address}, Data: {data}")
        return data


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
