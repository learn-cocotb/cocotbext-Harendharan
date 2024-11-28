import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

class WishboneDriver:
    def __init__(self, dut):
        self.dut = dut

    async def write(self, address, data):
        self.dut.start_i.value = 1
        self.dut.we_i.value = 1  # Write enable
        self.dut.addr_i.value = address
        self.dut.data_i.value = data
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0

    async def ack(self):
        await Timer(20, units="ns")  # Delay for acknowledgment
        self.dut.wb_ack_i.value = 1
        await RisingEdge(self.dut.clk)
        self.dut.wb_ack_i.value = 0

    async def read(self, address):
        self.dut.start_i.value = 1
        self.dut.we_i.value = 0  # Read enable (Write is disabled)
        self.dut.addr_i.value = address
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0
        await RisingEdge(self.dut.clk)  # Wait for the output data to be stable
        return self.dut.wb_dat_o.value


class WishboneMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.data = {}

    async def monitor(self):
        while True:
            await RisingEdge(self.dut.clk)
            self.data['wb_stb_o'] = self.dut.wb_stb_o.value
            self.data['wb_cyc_o'] = self.dut.wb_cyc_o.value
            self.data['wb_adr_o'] = self.dut.wb_adr_o.value
            self.data['wb_dat_o'] = self.dut.wb_dat_o.value
            self.data['wb_ack_i'] = self.dut.wb_ack_i.value
            self.data['busy_o'] = self.dut.busy_o.value


class WishboneScoreboard:
    def __init__(self):
        self.expected = {}

    def expect(self, signal, value):
        self.expected[signal] = value

    def check(self, monitor_data):
        for signal, expected_value in self.expected.items():
            if monitor_data.get(signal) != expected_value:
                raise AssertionError(f"{signal} mismatch: Expected {expected_value}, got {monitor_data.get(signal)}")


@cocotb.test()
async def test_wb_interface(dut):

    # Generate a clock signal clk
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())  # 10ns clock period

    # Apply reset
    print("Applying reset")
    dut.a_reset_l.value = 0
    for _ in range(3):  # Keep reset for 3 clock cycles
        await RisingEdge(dut.clk)
    dut.a_reset_l.value = 1
    await RisingEdge(dut.clk)
    print("Reset complete.")

    # Instantiate driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Start monitoring
    cocotb.start_soon(monitor.monitor())

    # Expected values for the write operation
    scoreboard.expect('wb_stb_o', 1)
    scoreboard.expect('wb_cyc_o', 1)
    scoreboard.expect('wb_adr_o', 0x0010)
    scoreboard.expect('wb_dat_o', 0x1234)

    # Start Write Operation
    print("Starting Write Operation")
    await driver.write(0x0010, 0x1234)

    # Simulate Wishbone acknowledgment
    print("Simulating acknowledgment signal")
    await driver.ack()

    # Verify busy_o deasserts after completion
    for _ in range(5):  # Wait for up to 5 clock cycles
        await RisingEdge(dut.clk)
        if dut.busy_o.value == 0:
            break
    else:
        print("Error: Busy signal not deasserted after write operation")
        assert False, "Busy signal not deasserted after write"

    print("Write operation completed successfully")

    # Check outputs 
    scoreboard.check(monitor.data)

    # Start Read Operation
    print("Starting Read Operation")
    read_data = await driver.read(0x0010)

    # Check if the data read matches the expected value
    assert read_data == 0x1234, f"Read data mismatch: Expected 0x1234, got {read_data}"
    print(f"Read operation completed successfully, Data: {read_data}")
