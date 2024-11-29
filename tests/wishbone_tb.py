import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


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
        # Use a clock edge instead of a fixed delay for acknowledgment
        while True:
            await RisingEdge(self.dut.clk)
            if self.dut.wb_ack_i.value == 1:
                self.dut.wb_ack_i.value = 0
                break

    async def read(self, address):
        self.dut.start_i.value = 1
        self.dut.we_i.value = 0  # Read enable
        self.dut.addr_i.value = address
        await RisingEdge(self.dut.clk)
        self.dut.start_i.value = 0
        await RisingEdge(self.dut.clk)  # Wait for the output data to be stable
        return self.dut.wb_dat_o.value


class WishboneMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.data = {
            "wb_stb_o": 0,
            "wb_cyc_o": 0,
            "wb_adr_o": 0,
            "wb_dat_o": 0,
            "wb_ack_i": 0,
            "busy_o": 0,
        }

    async def monitor(self):
        while True:
            await RisingEdge(self.dut.clk)
            # Update data atomically to avoid race conditions
            self.data.update(
                {
                    "wb_stb_o": self.dut.wb_stb_o.value,
                    "wb_cyc_o": self.dut.wb_cyc_o.value,
                    "wb_adr_o": self.dut.wb_adr_o.value,
                    "wb_dat_o": self.dut.wb_dat_o.value,
                    "wb_ack_i": self.dut.wb_ack_i.value,
                    "busy_o": self.dut.busy_o.value,
                }
            )


class WishboneScoreboard:
    def __init__(self):
        self.expected = {}

    def expect(self, signal, value):
        self.expected[signal] = value

    def check(self, monitor_data):
        for signal, expected_value in self.expected.items():
            actual_value = monitor_data.get(signal)
            assert actual_value == expected_value, (
                f"{signal} mismatch: Expected {expected_value}, got {actual_value}"
            )


async def apply_reset(dut, cycles=3):
    dut.a_reset_l.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    dut.a_reset_l.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_wb_interface(dut):
    # Generate a clock signal
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Apply reset
    print("Applying reset")
    await apply_reset(dut)
    print("Reset complete")

    # Instantiate driver, monitor, and scoreboard
    driver = WishboneDriver(dut)
    monitor = WishboneMonitor(dut)
    scoreboard = WishboneScoreboard()

    # Start monitoring
    cocotb.start_soon(monitor.monitor())

    # Expected values for the write operation
    write_address = 0x0010
    write_data = 0x1234
    scoreboard.expect("wb_stb_o", 1)
    scoreboard.expect("wb_cyc_o", 1)
    scoreboard.expect("wb_adr_o", write_address)
    scoreboard.expect("wb_dat_o", write_data)

    # Start Write Operation
    print("Starting write operation")
    await driver.write(write_address, write_data)

    # Simulate Wishbone acknowledgment
    print("Waiting for acknowledgment signal")
    await driver.ack()

    # Verify `busy_o` deasserts after completion
    print("Verifying busy signal deassertion")
    for _ in range(5):  # Wait for up to 5 clock cycles
        await RisingEdge(dut.clk)
        if dut.busy_o.value == 0:
            break
    else:
        assert False, "Busy signal not deasserted after write operation"

    print("Write operation completed successfully")

    # Check outputs
    scoreboard.check(monitor.data)

    # Start Read Operation
    print("Starting read operation")
    read_data = await driver.read(write_address)

    # Check if the data read matches the expected value
    assert read_data == write_data, f"Read data mismatch: Expected {write_data}, got {read_data}"
    print(f"Read operation completed successfully. Data: {read_data}")
