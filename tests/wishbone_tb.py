from typing import Any
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, Event
from cocotb.queue import Queue
from cocotb.utils import get_sim_time


class WishboneTransaction:
    """Transaction: Data members for each Wishbone signal."""
    
    def __init__(self, address: int, data: int, expected_data: int, tag: str = '') -> None:
        """
        Initialize a transaction with address, data, expected_data, and optional tag.
        
        Args:
            address (int): Address for the transaction.
            data (int): Data to be written to the address.
            expected_data (int): Expected data after the transaction.
            tag (str): Optional tag for the transaction details.
        """
        self.address = address
        self.data = data
        self.expected_data = expected_data
        self.tag = tag


class WishboneDriver:
    """Driver for Wishbone bus. Provides methods for performing read and write operations."""

    def __init__(self, queue: Queue, dut: Any) -> None:
        """Initialize the driver with required parameters."""
        self.queue = queue
        self.dut = dut

    async def apply_reset(self) -> None:
        """Apply and release reset signal."""
        self.dut.rst.value = 1
        await Timer(50, units="ns")
        self.dut.rst.value = 0
        print("-------- Reset Released @", str(get_sim_time(units="ns")), "--------")
        await Timer(50, units="ns")

    async def send_transaction(self, transaction: WishboneTransaction) -> None:
        """Driver: Apply random transactions to DUT."""
        self.dut.wishbone.adr.value = transaction.address
        self.dut.wishbone.dat.value = transaction.data
        self.dut.wishbone.we.value = 1
        self.dut.wishbone.cyc.value = 1
        self.dut.wishbone.stb.value = 1
        print(transaction.tag, f"Address: {transaction.address}, Data: {transaction.data}, Expected: {transaction.expected_data}")
        
        await RisingEdge(self.dut.clk)
        self.dut.wishbone.cyc.value = 0
        self.dut.wishbone.stb.value = 0
        await RisingEdge(self.dut.ack)
        print("Transaction Completed: Address =", transaction.address, "Data =", transaction.data)


class WishboneScoreboard:
    """Scoreboard: Verify the correctness of transactions."""

    def __init__(self, dut: Any) -> None:
        """Initialize scoreboard with the DUT object."""
        self.dut = dut
        self.expected_transactions: Queue = Queue()

    def add_expected_transaction(self, transaction: WishboneTransaction) -> None:
        """Add an expected transaction to the scoreboard."""
        self.expected_transactions.put_nowait(transaction)

    def check_transaction(self, transaction: WishboneTransaction) -> None:
        """Check the received transaction against the expected transaction."""
        try:
            expected = self.expected_transactions.get_nowait()
            if expected.data == transaction.data:
                print(f"Transaction Passed: Address: {transaction.address}, Data: {transaction.data}")
            else:
                print(f"Transaction Failed: Address: {transaction.address}, Expected: {expected.data}, Got: {transaction.data}")
        except Exception as e:
            print(f"Unexpected Transaction: Address: {transaction.address}, Data: {transaction.data}")
            print("Error:", e)


class Testbench:
    """Testbench: Initialize and run the test with cocotb."""

    def __init__(self, dut: Any) -> None:
        """Initialize the testbench with the DUT object."""
        self.dut = dut
        self.driver = WishboneDriver(Queue(), dut)
        self.scoreboard = WishboneScoreboard(dut)

    async def run_test(self) -> None:
        """Test entry point for cocotb."""
        await self.driver.apply_reset()

        # Create transactions and add them to the scoreboard
        transaction1 = WishboneTransaction(address=0x00, data=0x01, expected_data=0x01, tag="Write Transaction")
        self.scoreboard.add_expected_transaction(transaction1)

        # Send transaction and check the result
        await self.driver.send_transaction(transaction1)
        self.scoreboard.check_transaction(transaction1)


# Testbench entry point
@cocotb.coroutine
async def run_test(dut: Any) -> None:
    """Test entry point for cocotb."""
    tb = Testbench(dut)
    await tb.run_test()

