import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, Event
from cocotb.queue import Queue
from cocotb.utils import get_sim_time


class WishboneTransaction:
    """Transaction: Data members for each Wishbone signal."""

    def __init__(self):
        """Initialize transaction data members."""
        self.address = 0
        self.data = 0
        self.expected_data = 0

    def print_transaction(self, tag: str = "") -> None:
        """Print details of the transaction.

        Args:
            tag (str): Optional tag for the transaction details.
        """
        print(tag, f"Address: {self.address}, Data: {self.data}, Expected: {self.expected_data}")


class WishboneGenerator:
    """Generator: Generate random transactions for DUT."""

    def __init__(self, queue: Queue, event: Event, count: int):
        """Initialize the generator with required parameters.

        Args:
            queue (Queue): Queue to store generated transactions.
            event (Event): Event to signal completion.
            count (int): Number of transactions to generate.
        """
        self.queue = queue
        self.event = event
        self.count = count
        self.event.clear()

    async def gen_data(self) -> None:
        """Generate data and push transactions to the queue."""
        for i in range(self.count):
            transaction = WishboneTransaction()
            transaction.address = i
            transaction.data = i * 2
            self.queue.put_nowait(transaction)
        self.event.set()


class WishboneDriver:
    """Driver: Apply random transactions to DUT."""

    def __init__(self, queue: Queue, dut):
        """Initialize the driver with required parameters.

        Args:
            queue (Queue): Queue from which transactions are consumed.
            dut: DUT object to drive.
        """
        self.queue = queue
        self.dut = dut

    async def reset_dut(self) -> None:
        """Apply reset to the DUT."""
        self.dut.rst.value = 1
        self.dut.wishbone.adr.value = 0
        self.dut.wishbone.dat.value = 0
        self.dut.wishbone.we.value = 0
        self.dut.wishbone.cyc.value = 0
        print("-------- Reset Applied @", str(get_sim_time(units="ns")), "--------")
        await Timer(50, units="ns")
        self.dut.rst.value = 0
        print("-------- Reset Released @", str(get_sim_time(units="ns")), "--------")

    async def recv_data(self) -> None:
        """Receive data from the DUT."""
        while True:
            transaction = await self.queue.get()
            await RisingEdge(self.dut.clk)
            self.dut.wishbone.adr.value = transaction.address
            self.dut.wishbone.dat.value = transaction.data
            self.dut.wishbone.cyc.value = 1
            await RisingEdge(self.dut.ack)
            self.dut.wishbone.cyc.value = 0
            print("Transaction Completed: Address =", transaction.address, "Data =", transaction.data)


class Scoreboard:
    """Scoreboard: Verify the correctness of transactions."""

    def __init__(self, dut):
        """Initialize scoreboard with the DUT object."""
        self.dut = dut
        self.expected_transactions = {}
        self.received_transactions = {}

    def add_expected_transaction(self, transaction: WishboneTransaction) -> None:
        """Add an expected transaction to the scoreboard.

        Args:
            transaction (WishboneTransaction): The expected transaction.
        """
        self.expected_transactions[transaction.address] = transaction

    def check_transaction(self, transaction: WishboneTransaction) -> None:
        """Check if received transaction matches the expected one.

        Args:
            transaction (WishboneTransaction): The received transaction.
        """
        if transaction.address in self.expected_transactions:
            expected = self.expected_transactions[transaction.address]
            if expected.data == transaction.data:
                print(f"Transaction Passed: Address: {transaction.address}, Data: {transaction.data}")
            else:
                print(f"Transaction Failed: Address: {transaction.address}, Expected: {expected.data}, Got: {transaction.data}")
        else:
            print(f"Unexpected Transaction: Address: {transaction.address}, Data: {transaction.data}")


class Testbench:
    """Testbench: Initialize and run the test with cocotb."""

    def __init__(self, dut):
        """Initialize the testbench with the DUT object.

        Args:
            dut: The design under test (DUT).
        """
        self.dut = dut
        self.queue = Queue()
        self.event = Event()
        self.generator = WishboneGenerator(self.queue, self.event, count=10)
        self.driver = WishboneDriver(self.queue, dut)
        self.scoreboard = Scoreboard(dut)

    async def run(self) -> None:
        """Run the testbench."""
        # Start the clock
        cocotb.fork(Clock(self.dut.clk, 10, units="ns").start())

        # Apply reset
        await self.driver.reset_dut()

        # Start transaction generation and driver tasks
        cocotb.fork(self.generator.gen_data())
        cocotb.fork(self.driver.recv_data())

        # Wait for transactions to complete
        await self.event.wait()

        # Add expected transactions to scoreboard and check
        for transaction in list(self.queue._queue):
            self.scoreboard.add_expected_transaction(transaction)
            self.scoreboard.check_transaction(transaction)


# Testbench entry point
@cocotb.coroutine
async def run_test(dut):
    """Test entry point for cocotb."""
    tb = Testbench(dut)
    await tb.run()
