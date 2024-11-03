import cocotb
from cocotb.triggers import RisingEdge, ClockCycles, Event
from cocotb.clock import Clock
from cocotb.queue import Queue
from cocotb_coverage.crv import Randomized

# Transaction class for Wishbone transaction data members
class WishboneTransaction(Randomized):
    def __init__(self, we=0, strb=0, addr=0, wdata=0, rdata=0, ack=0):
        Randomized.__init__(self)
        self.we = we
        self.strb = strb
        self.addr = addr
        self.wdata = wdata
        self.rdata = rdata
        self.ack = ack
        # Define random constraints
        self.add_rand("we", [0, 1])
        self.add_rand("strb", [0, 1])
        self.add_rand("addr", list(range(256)))
        self.add_rand("wdata", list(range(256)))

# Generator for creating random transactions
class WishboneGenerator():
    def __init__(self, queue, event, count):
        self.queue = queue
        self.event = event
        self.count = count
        self.event.clear()

    async def gen_data(self):
        for _ in range(self.count):
            trans = WishboneTransaction()
            trans.randomize()
            print(f"[GEN]: we={trans.we}, strb={trans.strb}, addr={trans.addr}, wdata={trans.wdata}")
            await self.queue.put(trans)
            await self.event.wait()
            self.event.clear()

# Driver for applying transactions to DUT
class WishboneDriver():
    def __init__(self, queue, dut):
        self.queue = queue
        self.dut = dut

    async def reset_dut(self):
        self.dut.rst.value = 1
        self.dut.we.value = 0
        self.dut.strb.value = 0
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        await ClockCycles(self.dut.clk, 10)
        self.dut.rst.value = 0
        await ClockCycles(self.dut.clk, 5)
        print("[DRV]: Reset Done")

    async def apply_data(self):
        while True:
            trans = await self.queue.get()
            self.dut.we.value = trans.we
            self.dut.strb.value = trans.strb
            self.dut.addr.value = trans.addr
            self.dut.wdata.value = trans.wdata
            await RisingEdge(self.dut.clk)
            await RisingEdge(self.dut.clk)

# Monitor for capturing DUT responses
class WishboneMonitor():
    def __init__(self, dut, queue):
        self.dut = dut
        self.queue = queue

    async def sample_data(self):
        while True:
            await RisingEdge(self.dut.clk)
            trans = WishboneTransaction()
            trans.we = self.dut.we.value.integer
            trans.strb = self.dut.strb.value.integer
            trans.addr = self.dut.addr.value.integer
            trans.wdata = self.dut.wdata.value.integer
            trans.rdata = self.dut.rdata.value.integer
            trans.ack = self.dut.ack.value.integer
            await self.queue.put(trans)
            print(f"[MON]: Captured rdata={trans.rdata}, ack={trans.ack}")

# Scoreboard for verification
class WishboneScoreboard():
    def __init__(self, queue, event):
        self.queue = queue
        self.event = event
        self.memory = [0x11] * 256  # Default memory values

    async def compare_data(self):
        while True:
            trans = await self.queue.get()
            if trans.strb == 0:
                print("[SCO]: Invalid Strobe Signal")
            else:
                if trans.we:
                    self.memory[trans.addr] = trans.wdata
                    print(f"[SCO]: Write successful at addr={trans.addr}")
                else:
                    if trans.rdata == self.memory[trans.addr]:
                        print(f"[SCO]: Read matches expected value at addr={trans.addr}")
                    else:
                        print(f"[SCO]: Read mismatch at addr={trans.addr}")
            self.event.set()

# Main test for Wishbone interface
@cocotb.test()
async def test_wishbone(dut):
    queue_gen_drv = Queue()
    queue_drv_sco = Queue()
    event = Event()

    # Create instances of each component
    gen = WishboneGenerator(queue_gen_drv, event, count=10)
    drv = WishboneDriver(queue_gen_drv, dut)
    mon = WishboneMonitor(dut, queue_drv_sco)
    sco = WishboneScoreboard(queue_drv_sco, event)

    # Start the clock
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # Reset the DUT
    await drv.reset_dut()

    # Start tasks
    cocotb.start_soon(gen.gen_data())
    cocotb.start_soon(drv.apply_data())
    cocotb.start_soon(mon.sample_data())
    cocotb.start_soon(sco.compare_data())

    # Run the test for a specified time
    await ClockCycles(dut.clk, 200)
