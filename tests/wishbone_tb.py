import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, Event
from cocotb.queue import Queue
from cocotb.utils import get_sim_time


# Transaction: Data members for each Wishbone signal
class WishboneTransaction:
    def __init__(self):
        self.address = 0
        self.data = 0
        self.expected_data = 0

    def print_transaction(self, tag=""):
        print(tag, f"Address: {self.address}, Data: {self.data}, Expected: {self.expected_data}")


# Generator: Generate random transactions for DUT
class WishboneGenerator:
    def __init__(self, queue, event, count):
        self.queue = queue
        self.event = event
        self.count = count
        self.event.clear()

    async def gen_data(self):
        for i in range(self.count):
            transaction = WishboneTransaction()
            transaction.address = i * 4  # Increment address for each transaction
            transaction.data = i + 0xA  # Generate some data
            transaction.expected_data = transaction.data
            transaction.print_transaction("[GEN]")
            await self.queue.put(transaction)
            await self.event.wait()
            self.event.clear()


# Driver: Apply random transactions to DUT
class WishboneDriver:
    def __init__(self, queue, dut):
        self.queue = queue
        self.dut = dut

    async def reset_dut(self):
        self.dut.rst.value = 1
        self.dut.wishbone.adr.value = 0
        self.dut.wishbone.dat.value = 0
        self.dut.wishbone.we.value = 0
        self.dut.wishbone.cyc.value = 0
        print("-------- Reset Applied @", str(get_sim_time(units="ns")), "--------")
        await Timer(50, units="ns")
        self.dut.rst.value = 0
        print("-------- Reset Released @", str(get_sim_time(units="ns")), "--------")

    async def recv_data(self):
        while True:
            transaction = await self.queue.get()
            transaction.print_transaction("[DRV]")
            self.dut.wishbone.adr.value = transaction.address
            self.dut.wishbone.dat.value = transaction.data
            self.dut.wishbone.we.value = 1
            self.dut.wishbone.cyc.value = 1
            await RisingEdge(self.dut.clk)
            self.dut.wishbone.we.value = 0
            self.dut.wishbone.cyc.value = 0
            await RisingEdge(self.dut.clk)


# Monitor: Collect the response from the DUT
class WishboneMonitor:
    def __init__(self, dut, queue):
        self.dut = dut
        self.queue = queue

    async def sample_data(self):
        while True:
            transaction = WishboneTransaction()
            await RisingEdge(self.dut.clk)
            if self.dut.wishbone.cyc.value:
                transaction.address = self.dut.wishbone.adr.value.integer
                transaction.data = self.dut.wishbone.dat.value.integer
                await self.queue.put(transaction)
                print("[MON]", f"Address: {transaction.address}, Data: {transaction.data}")


# Scoreboard: Validate the DUT's behavior
class WishboneScoreboard:
    def __init__(self, queue, event):
        self.queue = queue
        self.event = event

    async def compare_data(self):
        while True:
            transaction = await self.queue.get()
            print("[SCO]", f"Address: {transaction.address}, Data: {transaction.data}")
            if transaction.data == transaction.expected_data:
                print("Test Passed")
            else:
                print("Test Failed")
            self.event.set()


@cocotb.test()
async def test_wishbone(dut):
    queue1 = Queue()
    queue2 = Queue()
    event = Event()

    gen = WishboneGenerator(queue1, event, 5)
    drv = WishboneDriver(queue1, dut)
    mon = WishboneMonitor(dut, queue2)
    sco = WishboneScoreboard(queue2, event)

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    await drv.reset_dut()
    cocotb.start_soon(gen.gen_data())
    cocotb.start_soon(drv.recv_data())
    cocotb.start_soon(mon.sample_data())
    cocotb.start_soon(sco.compare_data())

    await Timer(5000, units="ns")
